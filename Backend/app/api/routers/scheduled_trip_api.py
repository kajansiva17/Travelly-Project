"""Seat layouts and scheduled Ticket departures (matrix 32-39) on the approved PRD tables.

vehicle_seats            versioned 2D layout per vehicle (never rewritten; a new version deactivates the old rows)
scheduled_trips          one Ticket departure and its frozen promise (DRAFT -> PUBLISHED)
scheduled_trip_seats     per-departure seat inventory, created when the departure is published

Holds, bookings, travellers and payment are the next step and are intentionally not implemented here.
"""
import secrets
from decimal import Decimal
from datetime import date as Date, datetime, time, timedelta, timezone
from typing import Optional
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.orm import Session
from app.api.routers.api import current, require_role, touch
from app.core.errors import ApiError
from app.dependencies.database import get_db
from app.models import User, UserRole
from app.models.hire_models import Booking, Route, RouteStop, ScheduledTrip, Trip
from app.models.rate_models import ServiceType
from app.models.review_models import Vehicle
from app.models.seat_models import BookingTraveller, ScheduledTripSeat, VehicleSeat
from app.schemas.scheduled_trip_schemas import BoardingMark, DepartureCreate, DeparturePatch, DriverLookup, PublishRequest, SeatLayoutIn
from app.services.availability import no_vehicle_conflict

router = APIRouter(prefix='/api/v1', tags=['Ticket departures'])
ZONE = ZoneInfo('Asia/Colombo')
CURRENCY = 'LKR'
LISTED = ('PUBLISHED', 'BOOKING_OPEN')          # statuses a Passenger can search and book
HIDDEN = ('DRAFT',)                              # never publicly readable
REQUIRED_FIELDS = ('route_id', 'vehicle_id', 'departure_at', 'estimated_arrival_at', 'booking_cutoff_at',
                   'fare_per_seat', 'fulfilment_policy', 'accepted_time_window_minutes', 'accepted_replacement_terms')


def now():
    return datetime.now(timezone.utc)


def invalid(message):
    return ApiError(422, 'VALIDATION_ERROR', message)


def optional_user(request: Request, db: Session):
    """Public reads may add private detail for a signed-in owner; an absent header means anonymous."""
    if not request.headers.get('authorization'):
        return None
    return current(request, db)


def has_role(db, user_id, role):
    return bool(db.scalar(select(UserRole.id).where(UserRole.user_id == user_id, UserRole.role_code == role,
                                                      UserRole.approval_status == 'APPROVED')))


def ticket_service(db):
    service = db.scalar(select(ServiceType).where(ServiceType.category == 'TICKET_HIRE', ServiceType.is_active.is_(True))
                        .order_by(ServiceType.display_order, ServiceType.id).limit(1))
    if not service:
        raise ApiError(409, 'TICKET_SERVICE_NOT_CONFIGURED', 'The Ticket Hire service is not configured.')
    return service


def vehicle_summary(vehicle):
    return {'public_vehicle_reference': vehicle.public_vehicle_reference, 'vehicle_type_code': vehicle.vehicle_type_code,
            'make': vehicle.make, 'model': vehicle.model, 'air_conditioned': vehicle.air_conditioned,
            'seat_capacity': vehicle.seat_capacity}


def available_count(db, trip_id):
    return db.scalar(select(func.count()).select_from(ScheduledTripSeat).where(
        ScheduledTripSeat.scheduled_trip_id == trip_id,
        or_(ScheduledTripSeat.seat_status == 'AVAILABLE',
            and_(ScheduledTripSeat.seat_status == 'HELD', ScheduledTripSeat.hold_expires_at <= now()))))


def trip_out(trip, route, vehicle, available=None, stops=None, owner_view=False):
    out = {'id': str(trip.id), 'departure_reference': trip.departure_reference, 'status': trip.status,
           'route': {'id': str(route.id), 'route_code': route.route_code, 'route_name': route.route_name,
                     'origin_name': route.origin_name, 'destination_name': route.destination_name},
           'departure_at': trip.departure_at.isoformat(), 'estimated_arrival_at': trip.estimated_arrival_at.isoformat(),
           'booking_cutoff_at': trip.booking_cutoff_at.isoformat(), 'fare_per_seat': str(trip.fare_per_seat),
           'currency': trip.currency,
           'fulfilment': {'policy': trip.fulfilment_policy, 'minimum_confirmed_seats': trip.minimum_confirmed_seats,
                          'decision_deadline': trip.decision_deadline.isoformat() if trip.decision_deadline else None,
                          'accepted_time_window_minutes': trip.accepted_time_window_minutes,
                          'accepted_replacement_terms': trip.accepted_replacement_terms},
           'vehicle': vehicle_summary(vehicle)}
    if available is not None:
        out['available_seats'] = available
    if stops is not None:
        fares = (route.route_settings or {}).get('stop_fares') or {}
        out['stop_prices_enabled'] = bool(fares)
        out['stops'] = [{'id': str(s.id), 'stop_order': s.stop_order, 'stop_name': s.stop_name,
                         'price_from_start': fares.get(str(s.id)),
                         'pickup_allowed': s.pickup_allowed, 'dropoff_allowed': s.dropoff_allowed,
                         'scheduled_offset_minutes': s.scheduled_offset_minutes} for s in stops]
    if owner_view:
        out.update({'version': trip.version, 'vehicle_id': str(trip.current_vehicle_id),
                    'operator_driver_user_id': str(trip.operator_driver_user_id) if trip.operator_driver_user_id else None})
    return out


def layout_rows(db, vehicle_id):
    """Rows of the newest layout version that is still active, or an empty list."""
    version = db.scalar(select(func.max(VehicleSeat.layout_version)).where(VehicleSeat.vehicle_id == vehicle_id,
                                                                            VehicleSeat.is_active.is_(True)))
    if version is None:
        return None, []
    rows = db.scalars(select(VehicleSeat).where(VehicleSeat.vehicle_id == vehicle_id, VehicleSeat.layout_version == version,
                                                VehicleSeat.is_active.is_(True))
                      .order_by(VehicleSeat.deck_number, VehicleSeat.row_number, VehicleSeat.column_number)).all()
    return version, rows


def seat_out(seat):
    return {'code': seat.seat_code, 'row': seat.row_number, 'column': seat.column_number, 'deck': seat.deck_number,
            'type': seat.seat_type, 'bookable': seat.is_bookable}


# --------------------------------------------------------------------------- seat layouts (32-33)

@router.get('/vehicles/{vehicle_id}/seat-layout')
def read_layout(vehicle_id: UUID, request: Request, db: Session = Depends(get_db)):
    user = optional_user(request, db)
    vehicle = db.get(Vehicle, vehicle_id)
    visible = vehicle and ((vehicle.is_published and vehicle.verification_status == 'APPROVED')
                           or (user and vehicle.owner_user_id == user.id))
    if not visible:
        raise ApiError(404, 'VEHICLE_NOT_FOUND', 'Vehicle not found.')
    version, rows = layout_rows(db, vehicle_id)
    if version is None:
        raise ApiError(404, 'SEAT_LAYOUT_NOT_FOUND', 'This vehicle has no seat layout yet.')
    return {'vehicle_id': str(vehicle_id), 'layout_version': version, 'seats': [seat_out(s) for s in rows]}


@router.put('/vehicles/{vehicle_id}/seat-layout')
def put_layout(vehicle_id: UUID, body: SeatLayoutIn, user=Depends(current), db: Session = Depends(get_db)):
    require_role(db, user, 'OWNER')
    vehicle = db.scalar(select(Vehicle).where(Vehicle.id == vehicle_id).with_for_update())
    if not vehicle or vehicle.owner_user_id != user.id:
        raise ApiError(404, 'VEHICLE_NOT_FOUND', 'Vehicle not found.')
    codes = [s.code.lower() for s in body.seats]
    positions = [(s.deck, s.row, s.column) for s in body.seats]
    if len(codes) != len(set(codes)):
        raise invalid('Seat codes must be unique.')
    if len(positions) != len(set(positions)):
        raise invalid('Two seats cannot share the same deck, row and column.')
    if any(s.type == 'CREW' and s.bookable for s in body.seats):
        raise invalid('Crew seats cannot be bookable.')
    bookable = sum(1 for s in body.seats if s.bookable)
    if vehicle.seat_capacity is not None and bookable > vehicle.seat_capacity:
        raise ApiError(422, 'SEAT_CAPACITY_EXCEEDED', 'The layout has more bookable seats than the vehicle capacity.')
    latest = db.scalar(select(func.max(VehicleSeat.layout_version)).where(VehicleSeat.vehicle_id == vehicle_id)) or 0
    if body.layout_version != latest + 1:
        raise ApiError(409, 'LAYOUT_VERSION_CONFLICT', f'The next layout version must be {latest + 1}.')
    db.execute(update(VehicleSeat).where(VehicleSeat.vehicle_id == vehicle_id, VehicleSeat.is_active.is_(True))
               .values(is_active=False, updated_at=func.now(), updated_by=user.id, version=VehicleSeat.version + 1))
    for seat in body.seats:
        db.add(VehicleSeat(vehicle_id=vehicle_id, layout_version=body.layout_version, seat_code=seat.code, row_number=seat.row,
                           column_number=seat.column, deck_number=seat.deck, seat_type=seat.type, is_bookable=seat.bookable,
                           created_by=user.id, updated_by=user.id))
    db.commit()
    version, rows = layout_rows(db, vehicle_id)
    return {'vehicle_id': str(vehicle_id), 'layout_version': version, 'seats': [seat_out(s) for s in rows]}


# --------------------------------------------------------------------------- departures (34-36)

def check_departure(db, owner, values, *, publishing=False):
    """Validate a complete departure value set. Returns (route, vehicle, driver_id)."""
    missing = [name for name in REQUIRED_FIELDS if values.get(name) is None]
    if missing:
        raise invalid('Missing required departure fields: ' + ', '.join(missing) + '.')
    route = db.get(Route, values['route_id'])
    if not route or route.status != 'ACTIVE' or route.created_by_owner_id not in (None, owner.id):
        raise ApiError(422, 'ROUTE_NOT_AVAILABLE', 'Choose one of your active routes.')
    fares = (route.route_settings or {}).get('stop_fares')
    if fares and values.get('fare_per_seat') is not None:
        whole = max(Decimal(v) for v in fares.values())
        if Decimal(values['fare_per_seat']) != whole:
            raise ApiError(422, 'FARE_FROM_ROUTE_PRICES',
                           f'This route has a price for each stop, so the whole-trip price is LKR {whole:.2f}.')
    vehicle = db.get(Vehicle, values['vehicle_id'])
    if not vehicle or vehicle.owner_user_id != owner.id or vehicle.verification_status != 'APPROVED' or vehicle.availability_status != 'ACTIVE':
        raise ApiError(409, 'TICKET_VEHICLE_UNAVAILABLE', 'Use an approved, active vehicle that you own.')
    departure, arrival, cutoff = values['departure_at'], values['estimated_arrival_at'], values['booking_cutoff_at']
    if departure <= now():
        raise invalid('The departure must be in the future.')
    if arrival <= departure:
        raise invalid('The estimated arrival must be after the departure.')
    if cutoff > departure:
        raise invalid('The booking cut-off cannot be after the departure.')
    if publishing and cutoff <= now():
        raise invalid('The booking cut-off has already passed.')
    policy, minimum, deadline = values['fulfilment_policy'], values.get('minimum_confirmed_seats'), values.get('decision_deadline')
    if policy == 'FIXED_GUARANTEED' and (minimum is not None or deadline is not None):
        raise invalid('A fixed guaranteed departure has no minimum seats or decision deadline.')
    if policy != 'FIXED_GUARANTEED':
        if minimum is None or deadline is None:
            raise invalid('Minimum confirmed seats and a decision deadline are required for protected fulfilment.')
        if deadline > departure:
            raise invalid('The decision deadline cannot be after the departure.')
        if publishing and deadline <= now():
            raise invalid('The decision deadline has already passed.')
    driver_id = values.get('operator_driver_user_id') or (owner.id if has_role(db, owner.id, 'DRIVER') else None)
    if driver_id and not has_role(db, driver_id, 'DRIVER'):
        raise ApiError(422, 'DRIVER_NOT_ELIGIBLE', 'Choose an approved Driver.')
    if publishing and not driver_id:
        raise ApiError(409, 'DEPARTURE_NOT_READY', 'Assign an approved Driver (or be an approved Driver yourself) before publishing.')
    return route, vehicle, driver_id


def trip_values(trip):
    return {name: getattr(trip, key) for name, key in (
        ('route_id', 'route_id'), ('vehicle_id', 'current_vehicle_id'), ('departure_at', 'departure_at'),
        ('estimated_arrival_at', 'estimated_arrival_at'), ('booking_cutoff_at', 'booking_cutoff_at'),
        ('fare_per_seat', 'fare_per_seat'), ('fulfilment_policy', 'fulfilment_policy'),
        ('minimum_confirmed_seats', 'minimum_confirmed_seats'), ('decision_deadline', 'decision_deadline'),
        ('accepted_time_window_minutes', 'accepted_time_window_minutes'),
        ('accepted_replacement_terms', 'accepted_replacement_terms'), ('operator_driver_user_id', 'operator_driver_user_id'))}


def apply_values(trip, values, driver_id):
    trip.route_id = values['route_id']
    trip.original_vehicle_id = trip.current_vehicle_id = values['vehicle_id']
    for name in ('departure_at', 'estimated_arrival_at', 'booking_cutoff_at', 'fare_per_seat', 'fulfilment_policy',
                 'minimum_confirmed_seats', 'decision_deadline', 'accepted_time_window_minutes', 'accepted_replacement_terms'):
        setattr(trip, name, values.get(name))
    trip.operator_driver_user_id = driver_id


def owned_trip(db, trip_id, user, *, lock=False):
    query = select(ScheduledTrip).where(ScheduledTrip.id == trip_id)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    trip = db.scalar(query)
    if not trip or trip.owner_user_id != user.id:
        raise ApiError(404, 'DEPARTURE_NOT_FOUND', 'Departure not found.')
    return trip


@router.get('/owners/me/drivers')
def owner_drivers(user=Depends(current), db: Session = Depends(get_db)):
    """Drivers this Owner may choose from for a departure.

    There is no standing Owner-Driver network, so this is only the people the Owner has already
    worked with: a vehicle's preferred Driver, a Driver on one of their trips or departures, and
    the Owner themselves when they hold an approved Driver role. Anyone else is found by public
    reference through POST /owners/me/drivers/lookup. Contact details are never listed here.
    """
    require_role(db, user, 'OWNER')
    sources = {}
    for driver_id in db.scalars(select(Vehicle.default_driver_user_id)
                                .where(Vehicle.owner_user_id == user.id, Vehicle.default_driver_user_id.is_not(None))):
        sources.setdefault(driver_id, 'Preferred Driver for one of your vehicles')
    for driver_id in db.scalars(select(Trip.driver_user_id)
                                .where(Trip.operating_owner_user_id == user.id, Trip.driver_user_id.is_not(None))):
        sources.setdefault(driver_id, 'Drove one of your trips')
    for driver_id in db.scalars(select(ScheduledTrip.operator_driver_user_id)
                                .where(ScheduledTrip.owner_user_id == user.id,
                                       ScheduledTrip.operator_driver_user_id.is_not(None))):
        sources.setdefault(driver_id, 'Drove one of your departures')
    if has_role(db, user.id, 'DRIVER'):
        sources[user.id] = 'You'
    if not sources:
        return {'items': [], 'message': 'No Driver has worked with you yet. Add one by public reference.'}
    rows = db.scalars(select(User).where(User.id.in_(list(sources)))).all()
    items = [{'id': str(row.id), 'reference': row.public_user_reference,
              'display_name': row.display_name or row.public_user_reference,
              'eligible': has_role(db, row.id, 'DRIVER'), 'how_you_know_them': sources[row.id]} for row in rows]
    items.sort(key=lambda item: (not item['eligible'], item['display_name'].lower()))
    return {'items': items, 'message': 'Only Drivers you have already worked with. Add anyone else by public reference.'}


@router.post('/owners/me/drivers/lookup')
def lookup_driver(body: DriverLookup, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    """Find a Driver for a departure by their public reference (USR-...), for Owners with no Driver history.

    Eligibility is exactly the rule POST/PATCH /scheduled-trips apply to operator_driver_user_id: an APPROVED Driver
    role. Only the public reference, the display name and eligibility are returned; the user id only when eligible,
    because it is only useful to assign them. No contact details, documents or other roles. Rate-limited per Owner.
    """
    require_role(db, user, 'OWNER')
    request.app.state.store.rate(f'owner-driver-lookup:{user.id}', 30, 300)
    row = db.scalar(select(User).where(User.public_user_reference == body.driver_reference))
    if not row:
        raise ApiError(404, 'DRIVER_NOT_FOUND', 'No Travelly user has this reference. Check it with the Driver.')
    eligible = has_role(db, row.id, 'DRIVER')
    return {'id': str(row.id) if eligible else None, 'reference': row.public_user_reference,
            'display_name': row.display_name or row.public_user_reference, 'eligible': eligible,
            'message': 'Approved Driver. You can assign them to this departure.' if eligible
            else 'This person is not an approved Driver yet, so they cannot drive a departure.'}


@router.post('/scheduled-trips', status_code=201)
def create_departure(body: DepartureCreate, user=Depends(current), db: Session = Depends(get_db)):
    require_role(db, user, 'OWNER')
    values = body.model_dump()
    route, vehicle, driver_id = check_departure(db, user, values)
    service = ticket_service(db)
    trip = ScheduledTrip(departure_reference='DEP-' + uuid4().hex[:16].upper(), owner_user_id=user.id, service_type_id=service.id,
                         currency=CURRENCY, status='DRAFT', created_by=user.id, updated_by=user.id)
    apply_values(trip, values, driver_id)
    db.add(trip)
    db.commit()
    return trip_out(trip, route, vehicle, owner_view=True)


@router.patch('/scheduled-trips/{trip_id}')
def update_departure(trip_id: UUID, body: DeparturePatch, user=Depends(current), db: Session = Depends(get_db)):
    require_role(db, user, 'OWNER')
    changes = body.model_dump(exclude_unset=True, exclude={'expected_version'})
    if not changes:
        raise invalid('Provide at least one field to change.')
    trip = owned_trip(db, trip_id, user, lock=True)
    if trip.status != 'DRAFT':
        raise ApiError(409, 'DEPARTURE_NOT_DRAFT', 'Only a draft departure can be edited.')
    if trip.version != body.expected_version:
        raise ApiError(409, 'VERSION_CONFLICT', 'The departure changed. Refresh before saving.')
    values = {**trip_values(trip), **changes}
    route, vehicle, driver_id = check_departure(db, user, values)
    apply_values(trip, values, driver_id)
    touch(trip)
    trip.updated_by = user.id
    db.commit()
    return trip_out(trip, route, vehicle, owner_view=True)


@router.post('/scheduled-trips/{trip_id}/publish')
def publish_departure(trip_id: UUID, body: PublishRequest, user=Depends(current), db: Session = Depends(get_db)):
    require_role(db, user, 'OWNER')
    trip = owned_trip(db, trip_id, user, lock=True)
    if trip.status != 'DRAFT':
        raise ApiError(409, 'DEPARTURE_NOT_DRAFT', 'This departure is not a draft.')
    if trip.version != body.expected_version:
        raise ApiError(409, 'VERSION_CONFLICT', 'The departure changed. Refresh before publishing.')
    db.scalar(select(Vehicle.id).where(Vehicle.id == trip.current_vehicle_id).with_for_update())
    route, vehicle, _ = check_departure(db, user, trip_values(trip), publishing=True)
    _, seats = layout_rows(db, vehicle.id)
    bookable = [s for s in seats if s.is_bookable]
    if not bookable:
        raise ApiError(409, 'SEAT_LAYOUT_REQUIRED', 'Create a seat layout with at least one bookable seat first.')
    if trip.minimum_confirmed_seats is not None and trip.minimum_confirmed_seats > len(bookable):
        raise invalid('The minimum confirmed seats exceeds the number of bookable seats.')
    no_vehicle_conflict(db, vehicle.id, trip.departure_at, trip.estimated_arrival_at)
    for seat in bookable:
        db.add(ScheduledTripSeat(scheduled_trip_id=trip.id, vehicle_seat_id=seat.id, seat_status='AVAILABLE',
                                 created_by=user.id, updated_by=user.id))
    trip.status = 'PUBLISHED'
    # The departure now has a journey the assigned operator runs: same trips row as a private hire,
    # linked by scheduled_trip_id instead of booking_id.
    operator = trip.operator_driver_user_id
    db.add(Trip(trip_reference='TRP-' + secrets.token_hex(10).upper(), scheduled_trip_id=trip.id,
                vehicle_id=vehicle.id, operating_owner_user_id=trip.owner_user_id, driver_user_id=operator,
                assignment_type='OWNER_SELF_DRIVE' if operator == trip.owner_user_id else 'EXTERNAL_DRIVER',
                assignment_status='ACCEPTED' if operator == trip.owner_user_id else 'PENDING',
                status='READY', scheduled_start_at=trip.departure_at, scheduled_end_at=trip.estimated_arrival_at,
                created_by=user.id, updated_by=user.id))
    touch(trip)
    trip.updated_by = user.id
    db.commit()
    return trip_out(trip, route, vehicle, available=len(bookable), owner_view=True)


# --------------------------------------------------------------------------- public reads (37-39)

@router.get('/scheduled-trips')
def search_departures(request: Request, route_id: Optional[UUID] = None, origin: str = Query('', max_length=100),
                      destination: str = Query('', max_length=100), date: Optional[str] = Query(None, max_length=10),
                      min_seats: int = Query(1, ge=1, le=100), mine: bool = False, driving: bool = False,
                      limit: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0, le=10000),
                      db: Session = Depends(get_db)):
    query = select(ScheduledTrip, Route, Vehicle).join(Route, Route.id == ScheduledTrip.route_id).join(
        Vehicle, Vehicle.id == ScheduledTrip.current_vehicle_id)
    if mine:
        user = current(request, db)
        require_role(db, user, 'OWNER')
        query = query.where(ScheduledTrip.owner_user_id == user.id)
    elif driving:
        # The departures this Driver is assigned to drive, so they can board the Travellers waiting for them.
        user = current(request, db)
        require_role(db, user, 'DRIVER')
        query = query.where(ScheduledTrip.id.in_(
            select(Trip.scheduled_trip_id).where(Trip.driver_user_id == user.id,
                                                 Trip.status.in_(('READY', 'IN_PROGRESS', 'BREAKDOWN', 'ASSISTANCE_REQUIRED')))))
    else:
        query = query.where(ScheduledTrip.status.in_(LISTED), ScheduledTrip.departure_at > now(), ScheduledTrip.booking_cutoff_at > now())
    if route_id:
        query = query.where(ScheduledTrip.route_id == route_id)
    for column, value in ((Route.origin_name, origin), (Route.destination_name, destination)):
        if value.strip():
            escaped = value.strip().replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
            query = query.where(column.ilike('%' + escaped + '%', escape='\\'))
    if date:
        try:
            day = Date.fromisoformat(date)
        except ValueError:
            raise invalid('Enter the date as YYYY-MM-DD.') from None
        start = datetime.combine(day, time.min, ZONE)
        query = query.where(ScheduledTrip.departure_at >= start, ScheduledTrip.departure_at < start + timedelta(days=1))
    rows = db.execute(query.order_by(ScheduledTrip.departure_at, ScheduledTrip.id).limit(limit).offset(offset)).all()
    items = []
    for trip, route, vehicle in rows:
        free = available_count(db, trip.id)
        if not mine and free < min_seats:
            continue
        items.append(trip_out(trip, route, vehicle, available=free, owner_view=mine))
    return {'items': items, 'limit': limit, 'offset': offset}


def readable_trip(db, request, trip_id):
    trip = db.get(ScheduledTrip, trip_id)
    if not trip:
        raise ApiError(404, 'DEPARTURE_NOT_FOUND', 'Departure not found.')
    if trip.status in HIDDEN:
        user = optional_user(request, db)
        if not user or user.id != trip.owner_user_id:
            raise ApiError(404, 'DEPARTURE_NOT_FOUND', 'Departure not found.')
    return trip


@router.get('/scheduled-trips/{trip_id}')
def read_departure(trip_id: UUID, request: Request, db: Session = Depends(get_db)):
    trip = readable_trip(db, request, trip_id)
    route = db.get(Route, trip.route_id)
    vehicle = db.get(Vehicle, trip.current_vehicle_id)
    stops = db.scalars(select(RouteStop).where(RouteStop.route_id == route.id, RouteStop.is_active.is_(True))
                       .order_by(RouteStop.stop_order)).all()
    user = optional_user(request, db) if request.headers.get('authorization') else None
    return trip_out(trip, route, vehicle, available=available_count(db, trip.id), stops=stops,
                    owner_view=bool(user and user.id == trip.owner_user_id))


@router.get('/scheduled-trips/{trip_id}/seats')
def read_seats(trip_id: UUID, request: Request, db: Session = Depends(get_db)):
    trip = readable_trip(db, request, trip_id)
    rows = db.execute(select(ScheduledTripSeat, VehicleSeat).join(VehicleSeat, VehicleSeat.id == ScheduledTripSeat.vehicle_seat_id)
                      .where(ScheduledTripSeat.scheduled_trip_id == trip.id)
                      .order_by(VehicleSeat.deck_number, VehicleSeat.row_number, VehicleSeat.column_number)).all()
    moment = now()
    items = []
    for inventory, seat in rows:
        status = inventory.seat_status
        if status == 'HELD' and inventory.hold_expires_at and inventory.hold_expires_at <= moment:
            status = 'AVAILABLE'  # an expired hold is released lazily by the hold step; readers must not see it as held
        fare = inventory.fare_override if inventory.fare_override is not None else trip.fare_per_seat
        items.append({'seat_id': str(inventory.id), **seat_out(seat), 'status': status, 'fare': str(fare)})
    if rows:
        # Publication snapshots the seats this departure sells. Return the rest of that same layout
        # version too (Driver, seats not for sale, and seats the layout changed after publication) so
        # the reader can draw the whole vehicle. They have no inventory for this departure, so they
        # carry no seat_id, status or fare and are reported as not bookable here.
        snapshot = rows[0][1]
        taken = [seat.id for _, seat in rows]
        others = db.scalars(select(VehicleSeat)
                            .where(VehicleSeat.vehicle_id == snapshot.vehicle_id,
                                   VehicleSeat.layout_version == snapshot.layout_version,
                                   VehicleSeat.id.not_in(taken))
                            .order_by(VehicleSeat.deck_number, VehicleSeat.row_number, VehicleSeat.column_number)).all()
        items.extend({**seat_out(seat), 'bookable': False} for seat in others)
    return {'scheduled_trip_id': str(trip.id), 'currency': trip.currency, 'seats': items}


# --------------------------------------------------------------------------- boarding

def departure_crew(db, trip_id, user):
    """The departure and its journey, for the Owner who runs it or the Driver who drives it."""
    departure = db.scalar(select(ScheduledTrip).where(ScheduledTrip.id == trip_id))
    if not departure:
        raise ApiError(404, 'DEPARTURE_NOT_FOUND', 'Departure not found.')
    run = db.scalar(select(Trip).where(Trip.scheduled_trip_id == departure.id, Trip.status != 'CANCELLED')
                    .order_by(Trip.created_at.desc()).limit(1))
    allowed = {departure.owner_user_id} | ({run.driver_user_id} if run and run.driver_user_id else set())
    if user.id not in allowed:
        raise ApiError(404, 'DEPARTURE_NOT_FOUND', 'Departure not found.')
    return departure, run


@router.get('/scheduled-trips/{trip_id}/travellers')
def departure_travellers(trip_id: UUID, user=Depends(current), db: Session = Depends(get_db)):
    """Who the assigned Driver expects on this departure, in seat order.

    A seat that is only held is listed too, with its seat status, so the Driver can see it is
    waiting for payment rather than missing."""
    departure, run = departure_crew(db, trip_id, user)
    stops = {row.id: row.stop_name for row in db.scalars(select(RouteStop).where(RouteStop.route_id == departure.route_id))}
    rows = db.execute(select(BookingTraveller, ScheduledTripSeat, VehicleSeat)
                      .join(ScheduledTripSeat, ScheduledTripSeat.id == BookingTraveller.scheduled_trip_seat_id)
                      .join(VehicleSeat, VehicleSeat.id == ScheduledTripSeat.vehicle_seat_id)
                      .where(ScheduledTripSeat.scheduled_trip_id == departure.id,
                             BookingTraveller.traveller_status.notin_(('CANCELLED', 'MOVED')))
                      .order_by(VehicleSeat.deck_number, VehicleSeat.row_number, VehicleSeat.column_number)).all()
    items = [{'traveller_id': str(traveller.id), 'full_name': traveller.full_name, 'seat_code': seat.seat_code,
              'status': traveller.traveller_status, 'is_primary': traveller.is_primary,
              'seat_status': inventory.seat_status, 'can_board': inventory.seat_status == 'BOOKED',
              'gets_on': stops.get(traveller.boarding_stop_id), 'gets_off': stops.get(traveller.dropoff_stop_id)}
             for traveller, inventory, seat in rows]
    return {'scheduled_trip_id': str(departure.id), 'trip_id': str(run.id) if run else None,
            'departure_at': departure.departure_at.isoformat(), 'status': departure.status, 'items': items,
            'boarded': sum(1 for item in items if item['status'] in ('BOARDED', 'COMPLETED'))}


@router.post('/scheduled-trips/{trip_id}/boardings')
def mark_boarded(trip_id: UUID, body: BoardingMark, user=Depends(current), db: Session = Depends(get_db)):
    """The assigned Driver marks one traveller as boarded. Repeating it changes nothing."""
    departure, run = departure_crew(db, trip_id, user)
    if not run or run.driver_user_id != user.id:
        raise ApiError(403, 'NOT_THE_DEPARTURE_DRIVER', 'Only the assigned Driver records boarding.')
    if run.status not in ('READY', 'IN_PROGRESS'):
        raise ApiError(409, 'TRIP_NOT_READY', 'Boarding belongs to a departure that has not finished.')
    traveller = db.scalar(select(BookingTraveller).where(BookingTraveller.id == body.traveller_id)
                          .with_for_update().execution_options(populate_existing=True))
    inventory = db.get(ScheduledTripSeat, traveller.scheduled_trip_seat_id) if traveller and traveller.scheduled_trip_seat_id else None
    if not traveller or not inventory or inventory.scheduled_trip_id != departure.id:
        raise ApiError(404, 'TRAVELLER_NOT_FOUND', 'That traveller is not on this departure.')
    if traveller.traveller_status in ('CANCELLED', 'MOVED'):
        raise ApiError(409, 'TRAVELLER_NOT_TRAVELLING', 'This traveller is no longer on the departure.')
    if inventory.seat_status != 'BOOKED':
        raise ApiError(409, 'SEAT_NOT_PAID', 'This seat is held but not paid for, so the traveller cannot board yet.')
    if traveller.traveller_status == 'ACTIVE':
        traveller.traveller_status = 'BOARDED'
        touch(traveller)
        traveller.updated_by = user.id
        db.commit()
    seat = db.get(VehicleSeat, inventory.vehicle_seat_id)
    return {'traveller_id': str(traveller.id), 'seat_code': seat.seat_code if seat else None,
            'full_name': traveller.full_name, 'status': traveller.traveller_status}
