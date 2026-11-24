"""Book now (owner decision 23 Nov 2026), the PickMe way for three-wheelers, cars and vans: the Passenger stands at the pickup, sees the vehicles that are
online close by with their fare, picks one, and the person sending that vehicle's location (the Driver, or the Owner who drives) accepts within
90 seconds. There is no 2-hour window and no 15-minute preparation here: the live phone position is the proof the vehicle is near.

 * Only vehicles whose Owner switched "Accept Book now" on (vehicles.instant_booking), that are online with a fresh position and are free right now.
 * The fare is the Owner's own LOCAL per-km rate for the real route, the same price engine as a planned hire. The fare the Passenger saw must still be
   the fare when the request is made.
 * Accepting creates the confirmed booking and the trip, so pickup code, start, odometer, finish and payment are the normal trip steps.
 * No background job: a request that was not answered in time is marked EXPIRED the next time anyone reads or writes the requests (lazy expiry)."""
import secrets
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.api.routers.api import current, require_role
from app.api.routers.hire_api import offer, settle_hours, validate_service_itinerary, service_for, catalogue_status
from app.api.routers.trip_review_api import vehicle_ratings
from app.api.routers.live_vehicle_api import CITY_SPEED_KMH, can_operate, is_online, not_ready
from app.api.routers.review_api import locked_authority
from app.core.errors import ApiError
from app.dependencies.database import get_db
from app.models import User
from app.models.hire_models import Booking, Trip
from app.models.review_models import Vehicle
from app.models.rate_models import ServiceType
from app.models.ride_models import RideRequest
from app.schemas.hire_schemas import Itinerary
from app.schemas.rate_schemas import Place
from app.services.hire_services import booking_summary, notify
from app.services.location_matching import LOCATION_FRESHNESS
from app.services.odometer_proof import distance_km
from app.services.airports import min_distance_km
from app.services.pricing_scope import private_hire_scope

router = APIRouter(prefix='/api/v1', tags=['Book now'])
OFFER_SECONDS = 120
START_DELAY = timedelta(minutes=1)
MAX_OPTIONS = 8
MAX_RADIUS_KM = 20.0


class Point(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class Options(BaseModel):
    pickup: Point
    destination: Place
    passenger_count: int = Field(default=1, strict=True, ge=1, le=20)
    radius_km: float = Field(default=5.0, gt=0, le=MAX_RADIUS_KM)
    round_trip: bool = False   # go, wait at the destination (charged by the minute actually waited, after the Owner's free minutes) and come back


class Pick(BaseModel):
    vehicle_id: UUID
    fare: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class Broadcast(BaseModel):
    """One ask to several vehicles: each with the fare the Passenger saw for it."""
    pickup: Point
    destination: Place
    passenger_count: int = Field(default=1, strict=True, ge=1, le=20)
    round_trip: bool = False
    vehicles: list[Pick] = Field(min_length=1, max_length=MAX_OPTIONS)


class Ask(BaseModel):
    vehicle_id: UUID
    pickup: Point
    destination: Place
    passenger_count: int = Field(default=1, strict=True, ge=1, le=20)
    fare: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    round_trip: bool = False


def now_utc():
    return datetime.now(timezone.utc)


def expire_stale(db, now):
    db.execute(update(RideRequest).where(RideRequest.status == 'OFFERED', RideRequest.expires_at <= now).values(status='EXPIRED', responded_at=now))
    db.flush()


def book_now_service(db, request=None, itinerary=None, round_trip=False):
    """Book now has no distance limit: the route decides the service. Under the Admin's line (one way; a return counts double) the vehicle's Local
    rates apply, at or above it the Long distance rates. Without an active Long distance service every trip is priced as Local."""
    local = long = None
    for service in db.scalars(select(ServiceType).where(ServiceType.category == 'PRIVATE_HIRE', ServiceType.is_active.is_(True)).order_by(ServiceType.created_at)):
        if catalogue_status(service) != 'ACTIVE':
            continue
        scope = private_hire_scope(service)
        if scope == 'LOCAL' and local is None: local = service
        if scope == 'LONG_DISTANCE' and long is None: long = service
    if local is None:
        raise ApiError(409, 'BOOK_NOW_UNAVAILABLE', 'Book now is not available right now.')
    if long is not None and request is not None and itinerary is not None:
        base = min_distance_km(long)
        km = request.app.state.hire_routing.road_km(itinerary.stops) if base else None
        if km is not None and km >= base * (2 if round_trip else 1):
            return long
    return local


def method_of(service):
    return 'DAY_HIRE' if private_hire_scope(service) == 'LONG_DISTANCE' else 'DISTANCE'


def itinerary_of(request, pickup, destination, start, round_trip=False, method='DISTANCE'):
    """A return is priced as one chain pickup -> destination -> pickup with no planned wait; the real wait is charged when the trip ends."""
    stops = [pickup, destination] + ([pickup] if round_trip else [])
    return Itinerary.model_validate({'start_at': start.isoformat(), 'direction': 'ONE_WAY', 'method': method,
        'stops': [{'place': place, 'wait_minutes': '0', 'overnight_rest': False} for place in stops]})


def place_dicts(request, body):
    pickup = request.app.state.rate_locations.signed('My location', round(body.pickup.latitude, 6), round(body.pickup.longitude, 6))
    destination = body.destination.model_dump(mode='json')
    return pickup, destination


def bookable(vehicle, now):
    """Online with a fresh phone position, the Owner's Book now switch on, and ready for hire."""
    return bool(vehicle and vehicle.instant_booking and is_online(vehicle, now) and not_ready(vehicle) is None)


def km_from(vehicle, point):
    return distance_km(point.latitude, point.longitude, float(vehicle.current_latitude), float(vehicle.current_longitude))


def near_enough(vehicle, km, radius):
    return km <= radius and (vehicle.pickup_distance_km is None or km <= float(vehicle.pickup_distance_km))


def nearby_vehicles(db, point, radius, now):
    taken = set(db.scalars(select(RideRequest.vehicle_id).where(RideRequest.status == 'OFFERED')))
    rows = db.scalars(select(Vehicle).where(Vehicle.live_online_user_id.isnot(None), Vehicle.instant_booking.is_(True),
        Vehicle.current_latitude.isnot(None), Vehicle.current_location_observed_at >= now - LOCATION_FRESHNESS)).all()
    found = []
    for vehicle in rows:
        if vehicle.id in taken or not_ready(vehicle):
            continue
        km = km_from(vehicle, point)
        if near_enough(vehicle, km, radius):
            found.append((km, vehicle))
    found.sort(key=lambda pair: pair[0])
    return found


def fare_for(request, db, vehicle, service, itinerary, passengers):
    """The vehicle's own LOCAL rate for this route, or None when it cannot be priced or is busy right now."""
    if vehicle.seat_capacity is None or passengers > vehicle.seat_capacity:
        return None
    try:
        return offer(request, db, vehicle, service, itinerary)
    except ApiError:
        return None


def place_out(place):
    return {'label': place['label'], 'latitude': place['latitude'], 'longitude': place['longitude']}


def view(db, row, now):
    vehicle = db.get(Vehicle, row.vehicle_id)
    passenger = db.get(User, row.passenger_user_id)
    name = (passenger.display_name or passenger.full_name or '').split(' ')[0] if passenger else None
    return {'id': str(row.id), 'group_id': str(row.group_id) if row.group_id else None, 'status': row.status, 'fare': str(row.fare), 'currency': row.currency, 'passenger_count': row.passenger_count, 'round_trip': bool(row.round_trip),
            'pickup': place_out(row.pickup), 'destination': place_out(row.destination), 'passenger_first_name': name,
            'expires_at': row.expires_at.isoformat(), 'seconds_left': max(0, int((row.expires_at - now).total_seconds())) if row.status == 'OFFERED' else 0,
            'booking_id': str(row.booking_id) if row.booking_id else None,
            'trip_id': str(db.scalar(select(Trip.id).where(Trip.booking_id == row.booking_id))) if row.booking_id else None,
            'vehicle': {'name': vehicle.display_name or ' '.join(filter(None, [vehicle.make, vehicle.model])) or None, 'colour': vehicle.colour,
                        'registration_number': vehicle.registration_number, 'vehicle_type': vehicle.vehicle_type_code, 'seats': vehicle.seat_capacity}}


def participant(db, request_id, user, now, *, passenger=False, operator=False):
    expire_stale(db, now)
    row = db.get(RideRequest, request_id)
    allowed = row and ((not operator and row.passenger_user_id == user.id) or (not passenger and row.operator_user_id == user.id))
    if not allowed:
        raise ApiError(404, 'REQUEST_NOT_FOUND', 'This request was not found.')
    return row


@router.post('/ride-now/options')
def options(body: Options, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    """Online vehicles near the Passenger, nearest first, each with its own fare for this route."""
    require_role(db, user, 'PASSENGER')
    request.app.state.store.rate(f'ride-options:{user.id}', 20, 60)
    now = now_utc()
    expire_stale(db, now)
    pickup, destination = place_dicts(request, body)
    request.app.state.rate_locations.verify(body.destination)
    service = book_now_service(db, request, itinerary_of(request, pickup, destination, now + START_DELAY, body.round_trip), body.round_trip)
    itinerary = settle_hours(request, service, itinerary_of(request, pickup, destination, now + START_DELAY, body.round_trip, method_of(service)))
    validate_service_itinerary(service, itinerary, db, request, check_distance=False)
    found = nearby_vehicles(db, body.pickup, body.radius_km, now)
    ratings = vehicle_ratings(db, [vehicle.id for _, vehicle in found])
    items = []
    for km, vehicle in found:
        if vehicle.live_online_user_id == user.id or vehicle.owner_user_id == user.id:
            continue
        snapshot = fare_for(request, db, vehicle, service, itinerary, body.passenger_count)
        if snapshot is None:
            continue
        items.append({'vehicle_id': str(vehicle.id), 'reference': vehicle.public_vehicle_reference, 'name': vehicle.display_name or ' '.join(filter(None, [vehicle.make, vehicle.model])) or None,
                      'colour': vehicle.colour, 'vehicle_type': vehicle.vehicle_type_code, 'seats': vehicle.seat_capacity,
                      'distance_km': round(km, 1), 'minutes_away': max(1, round(km / CITY_SPEED_KMH * 60)),
                      'fare': snapshot['calculation']['total'], 'currency': 'LKR', 'rating': ratings.get(vehicle.id)}
                     | ({'waiting': {'free_minutes': snapshot['rule']['free_wait_minutes'], 'hour_rate': snapshot['rule']['waiting_hour_rate']}} if body.round_trip else {}))
        if len(items) >= MAX_OPTIONS:
            break
    db.commit()
    return {'items': items, 'radius_km': body.radius_km, 'note': 'Distances and minutes are approximate. The fare is the vehicle Owner\'s own rate for this route.'}


def check_pick(request, db, user, vehicle_id, fare, body, service, itinerary, now):
    """One vehicle of an ask: it must be free, close enough and still at the fare the Passenger saw."""
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle or not bookable(vehicle, now):
        raise ApiError(409, 'VEHICLE_NOT_AVAILABLE', 'This vehicle is not available right now. Choose another one.')
    if db.scalar(select(RideRequest.id).where(RideRequest.vehicle_id == vehicle.id, RideRequest.status == 'OFFERED').limit(1)):
        raise ApiError(409, 'VEHICLE_NOT_AVAILABLE', 'This vehicle was just asked by someone else. Choose another one.')
    if vehicle.live_online_user_id == user.id or vehicle.owner_user_id == user.id:
        raise ApiError(409, 'OWN_VEHICLE', 'You cannot book a vehicle you operate yourself.')
    if not near_enough(vehicle, km_from(vehicle, body.pickup), MAX_RADIUS_KM):
        raise ApiError(409, 'VEHICLE_TOO_FAR', 'This vehicle is too far from your pickup. Choose another one.')
    snapshot = fare_for(request, db, vehicle, service, itinerary, body.passenger_count)
    if snapshot is None:
        raise ApiError(409, 'VEHICLE_NOT_AVAILABLE', 'This vehicle cannot take this trip right now. Choose another one.')
    current_fare = Decimal(snapshot['calculation']['total'])
    if current_fare != fare:
        raise ApiError(409, 'FARE_CHANGED', 'The fare changed. Check the new fare and ask again.', [{'field': 'fare', 'message': str(current_fare)}])
    return vehicle, current_fare


def open_requests(request, db, user, body, picks):
    """Ask one or several vehicles at once (one group). Each row carries that vehicle's own fare; the first operator to accept gets the trip
    (accept_request cancels the others). With a single pick every problem is raised as before; with several, a vehicle that no longer fits is skipped."""
    require_role(db, user, 'PASSENGER')
    request.app.state.store.rate(f'ride-request:{user.id}', 10, 60)
    now = now_utc()
    expire_stale(db, now)
    db.commit()
    db.scalar(select(User.id).where(User.id == user.id).with_for_update())   # two taps at once cannot both open a group
    if db.scalar(select(RideRequest.id).where(RideRequest.passenger_user_id == user.id, RideRequest.status == 'OFFERED').limit(1)):
        raise ApiError(409, 'REQUEST_ALREADY_OPEN', 'You already have an open request, or this vehicle was just asked. Wait a moment.')
    pickup, destination = place_dicts(request, body)
    request.app.state.rate_locations.verify(body.destination)
    service = book_now_service(db, request, itinerary_of(request, pickup, destination, now + START_DELAY, body.round_trip), body.round_trip)
    itinerary = settle_hours(request, service, itinerary_of(request, pickup, destination, now + START_DELAY, body.round_trip, method_of(service)))
    validate_service_itinerary(service, itinerary, db, request, check_distance=False)
    valid, skipped = [], []
    for pick in picks:
        try:
            valid.append(check_pick(request, db, user, pick.vehicle_id, pick.fare, body, service, itinerary, now))
        except ApiError as exc:
            if len(picks) == 1: raise
            skipped.append({'vehicle_id': str(pick.vehicle_id), 'code': exc.code})
    if not valid:
        raise ApiError(409, 'VEHICLE_NOT_AVAILABLE', 'None of these vehicles can take this trip right now. Search again.')
    group, rows = uuid4(), []
    for vehicle, fare in sorted(valid, key=lambda pair: str(pair[0].id)):   # a fixed order so two asks never wait for each other
        locked = db.scalar(select(Vehicle).where(Vehicle.id == vehicle.id).with_for_update().execution_options(populate_existing=True))
        if not bookable(locked, now) or locked.live_online_user_id != vehicle.live_online_user_id:
            if len(picks) == 1:
                raise ApiError(409, 'VEHICLE_NOT_AVAILABLE', 'This vehicle is not available right now. Choose another one.')
            skipped.append({'vehicle_id': str(vehicle.id), 'code': 'VEHICLE_NOT_AVAILABLE'}); continue
        row = RideRequest(passenger_user_id=user.id, vehicle_id=vehicle.id, operator_user_id=locked.live_online_user_id, service_type_id=service.id, group_id=group,
            pickup=pickup, destination=destination, passenger_count=body.passenger_count, round_trip=body.round_trip, fare=fare, currency='LKR', status='OFFERED',
            expires_at=now + timedelta(seconds=OFFER_SECONDS))
        db.add(row); rows.append(row)
    if not rows:
        raise ApiError(409, 'VEHICLE_NOT_AVAILABLE', 'None of these vehicles can take this trip right now. Search again.')
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ApiError(409, 'REQUEST_ALREADY_OPEN', 'You already have an open request, or this vehicle was just asked. Wait a moment.') from None
    db.commit()
    return rows, skipped, now


@router.post('/ride-now/requests', status_code=201)
def ask(body: Ask, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    """The Passenger asks one vehicle. The fare they saw must still be the fare."""
    rows, _, now = open_requests(request, db, user, body, [Pick(vehicle_id=body.vehicle_id, fare=body.fare)])
    return view(db, rows[0], now)


@router.post('/ride-now/requests/broadcast', status_code=201)
def ask_many(body: Broadcast, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    """PickMe style: the Passenger asks several nearby vehicles at once, each at its own fare. The first operator to accept gets the trip."""
    rows, skipped, now = open_requests(request, db, user, body, body.vehicles)
    return {'group_id': str(rows[0].group_id), 'items': [view(db, row, now) for row in rows], 'skipped': skipped}


def group_view(db, group_id, user, now):
    expire_stale(db, now)
    rows = db.scalars(select(RideRequest).where(RideRequest.group_id == group_id, RideRequest.passenger_user_id == user.id).order_by(RideRequest.created_at, RideRequest.id)).all()
    if not rows:
        raise ApiError(404, 'REQUEST_NOT_FOUND', 'This request was not found.')
    accepted = next((row for row in rows if row.status == 'ACCEPTED'), None)
    open_rows = [row for row in rows if row.status == 'OFFERED']
    statuses = {row.status for row in rows}
    ended = 'EXPIRED' if 'EXPIRED' in statuses else 'DECLINED' if 'DECLINED' in statuses else 'CANCELLED'
    return {'group_id': str(group_id), 'status': 'ACCEPTED' if accepted else 'OPEN' if open_rows else 'ENDED', 'ended_because': None if accepted or open_rows else ended,
            'asked': len(rows), 'still_waiting': len(open_rows), 'declined': sum(row.status == 'DECLINED' for row in rows),
            'seconds_left': max((max(0, int((row.expires_at - now).total_seconds())) for row in open_rows), default=0),
            'accepted': view(db, accepted, now) if accepted else None}


@router.get('/ride-now/groups/{group_id}')
def read_group(group_id: UUID, user=Depends(current), db: Session = Depends(get_db)):
    now = now_utc()
    result = group_view(db, group_id, user, now)
    db.commit()
    return result


@router.post('/ride-now/groups/{group_id}/cancel')
def cancel_group(group_id: UUID, user=Depends(current), db: Session = Depends(get_db)):
    now = now_utc()
    expire_stale(db, now)
    db.execute(update(RideRequest).where(RideRequest.group_id == group_id, RideRequest.passenger_user_id == user.id, RideRequest.status == 'OFFERED')
               .values(status='CANCELLED', responded_at=now))
    result = group_view(db, group_id, user, now)
    db.commit()
    return result


@router.get('/ride-now/requests/{request_id}')
def read_request(request_id: UUID, user=Depends(current), db: Session = Depends(get_db)):
    now = now_utc()
    row = participant(db, request_id, user, now)
    db.commit()
    return view(db, row, now)


@router.get('/me/ride-requests')
def my_requests(user=Depends(current), db: Session = Depends(get_db)):
    """What is waiting for this person to accept: the open requests for the vehicle they are sending the location of."""
    now = now_utc()
    expire_stale(db, now)
    rows = db.scalars(select(RideRequest).where(RideRequest.operator_user_id == user.id, RideRequest.status == 'OFFERED').order_by(RideRequest.created_at)).all()
    items = [view(db, row, now) for row in rows]
    db.commit()
    return {'items': items}


def close(request_id, user, db, new_status, *, passenger):
    now = now_utc()
    row = participant(db, request_id, user, now, passenger=passenger, operator=not passenger)
    if row.status != 'OFFERED':
        raise ApiError(409, 'REQUEST_NOT_OPEN', 'This request is no longer open.')
    row.status, row.responded_at = new_status, now
    if passenger and row.group_id:   # the Passenger cancels the whole ask, not one vehicle of it
        db.execute(update(RideRequest).where(RideRequest.group_id == row.group_id, RideRequest.status == 'OFFERED').values(status='CANCELLED', responded_at=now))
    db.commit()
    return view(db, row, now)


@router.post('/ride-now/requests/{request_id}/cancel')
def cancel_request(request_id: UUID, user=Depends(current), db: Session = Depends(get_db)):
    return close(request_id, user, db, 'CANCELLED', passenger=True)


@router.post('/ride-now/requests/{request_id}/decline')
def decline_request(request_id: UUID, user=Depends(current), db: Session = Depends(get_db)):
    return close(request_id, user, db, 'DECLINED', passenger=False)


@router.post('/ride-now/requests/{request_id}/accept')
def accept_request(request_id: UUID, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    """The operator accepts: the confirmed booking and the trip are created in one step."""
    now = now_utc()
    preview = participant(db, request_id, user, now, operator=True)
    db.commit()
    if preview.status != 'OFFERED':
        raise ApiError(409, 'REQUEST_NOT_OPEN', 'This request is no longer open.' if preview.status != 'EXPIRED' else 'This request was not answered in time.')
    service = service_for(db, preview.service_type_id, new_offer=False)
    start = now + START_DELAY
    itinerary = settle_hours(request, service, itinerary_of(request, preview.pickup, preview.destination, start, preview.round_trip, method_of(service)))   # routing before any lock
    vehicle = db.get(Vehicle, preview.vehicle_id)
    snapshot = fare_for(request, db, vehicle, service, itinerary, preview.passenger_count)
    if snapshot is None or Decimal(snapshot['calculation']['total']) != preview.fare:
        raise ApiError(409, 'FARE_CHANGED', 'This trip can no longer be taken at the quoted fare. Decline it.')
    with request.app.state.audit.coordinated():
        locked_authority(db, request, user, user.id, require_admin=False)
        # Every request of this ask is locked together, so two vehicles accepting at the same moment cannot both win.
        siblings = db.scalars(select(RideRequest).where(RideRequest.group_id == preview.group_id).order_by(RideRequest.id).with_for_update().execution_options(populate_existing=True)).all() if preview.group_id else []
        row = next((r for r in siblings if r.id == request_id), None) or db.scalar(select(RideRequest).where(RideRequest.id == request_id).with_for_update().execution_options(populate_existing=True))
        if any(r.status == 'ACCEPTED' for r in siblings):
            raise ApiError(409, 'REQUEST_NOT_OPEN', 'Another vehicle already took this trip.')
        locked_vehicle = db.scalar(select(Vehicle).where(Vehicle.id == preview.vehicle_id).with_for_update().execution_options(populate_existing=True))
        if row.status != 'OFFERED' or row.expires_at <= now_utc():
            raise ApiError(409, 'REQUEST_NOT_OPEN', 'This request was not answered in time.')
        if locked_vehicle.live_online_user_id != user.id or not bookable(locked_vehicle, now) or not can_operate(db, user, locked_vehicle):
            raise ApiError(409, 'NOT_ONLINE', 'Go online for this vehicle to accept the request.')
        self_drive = user.id == locked_vehicle.owner_user_id
        reserved_end = datetime.fromisoformat(snapshot['reserved_end_at'])
        pickup, destination = row.pickup, row.destination
        booking = Booking(booking_reference='BKG-' + secrets.token_hex(10).upper(), passenger_user_id=row.passenger_user_id, booking_type='PRIVATE_HIRE',
            service_type_id=service.id, requested_owner_user_id=locked_vehicle.owner_user_id, owner_user_id=locked_vehicle.owner_user_id,
            vehicle_id=locked_vehicle.id, origin_text=pickup['label'], destination_text=destination['label'], start_at=start, end_at=reserved_end,
            passenger_count=row.passenger_count, large_luggage_count=0, small_luggage_count=0, status='CONFIRMED', assurance_type='STANDARD_HIRE',
            currency='LKR', idempotency_key='RIDE-' + row.id.hex, itinerary_snapshot={'itinerary': snapshot['itinerary'], 'measurement': snapshot['measurement']},
            price_snapshot={'initial': snapshot, 'current': snapshot}, accepted_quote_digest=snapshot['digest'], quoted_amount=row.fare, total_amount=row.fare,
            accepted_at=now, confirmed_at=now, vehicle_committed=True, pending_change={}, created_by=row.passenger_user_id, updated_by=user.id)
        db.add(booking); db.flush()
        db.add(Trip(trip_reference='TRP-' + secrets.token_hex(10).upper(), booking_id=booking.id, vehicle_id=locked_vehicle.id,
            operating_owner_user_id=locked_vehicle.owner_user_id, driver_user_id=user.id,
            assignment_type='OWNER_SELF_DRIVE' if self_drive else 'EXTERNAL_DRIVER', assignment_status='ACCEPTED', status='READY',
            scheduled_start_at=start, scheduled_end_at=reserved_end, created_by=user.id, updated_by=user.id))
        row.status, row.responded_at, row.booking_id = 'ACCEPTED', now, booking.id
        for other in siblings:
            if other.id != row.id and other.status == 'OFFERED':
                other.status, other.responded_at = 'CANCELLED', now
        notify(db, booking, 'Book now confirmed', 'The vehicle accepted your Book now request and is on its way.', user.id)
        request.app.state.audit.commit(db, actor=user.id, target={'resource': 'bookings', 'id': str(booking.id)}, previous_status=None,
            new_status='CONFIRMED', previous_version=0, new_version=booking.version or 1, full_reason=None, previous_decision_evidence={},
            trace_id=request.state.trace_id)
    return {**view(db, row, now_utc()), 'booking': booking_summary(booking)}
