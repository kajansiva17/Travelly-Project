"""Ticket seat holds (matrix 40-41) on the approved PRD tables.

bookings               one TICKET_HIRE header per hold, status REQUESTED while the hold is active
booking_travellers     one traveller per held seat
scheduled_trip_seats   AVAILABLE -> HELD (held_by_booking_id, hold_expires_at) -> AVAILABLE on release/expiry

Not here, by decision: payment and confirmation (HELD -> BOOKED, REQUESTED -> CONFIRMED) wait for the payments
step; boarding waits for Trip operations. A hold therefore always ends by release or expiry for now.

Lock order everywhere: scheduled_trips row -> bookings row -> scheduled_trip_seats rows (by id). This prevents
double booking and deadlocks between hold, release and the expiry job.
"""
import copy
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.api.routers.api import current, require_role, touch
from app.api.routers.review_api import admin, locked_authority
from app.core.errors import ApiError
from app.dependencies.database import get_db
from app.models.hire_models import Booking, Route, RouteStop, ScheduledTrip
from app.models.rate_models import ServiceType
from app.models.seat_models import BookingTraveller, ScheduledTripSeat, VehicleSeat
from app.schemas.ticket_booking_schemas import HoldRelease, TicketHoldRequest, TicketHoldSettings

router = APIRouter(prefix='/api/v1', tags=['Ticket holds'])
BOOKABLE = ('PUBLISHED', 'BOOKING_OPEN')
EXPIRED_REASON = 'Seat hold expired.'
ASSURANCE = {'FIXED_GUARANTEED': 'FIXED_DEPARTURE', 'MINIMUM_SEATS_WITH_PROTECTED_FULFILMENT': 'TRAVELLY_PROTECTED'}


def now():
    return datetime.now(timezone.utc)


def hold_minutes(service):
    value = (service.settings or {}).get('hold_minutes') if service else None
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None


def lock_trip(db, trip_id):
    return db.scalar(select(ScheduledTrip).where(ScheduledTrip.id == trip_id).with_for_update()
                     .execution_options(populate_existing=True))


def release_expired(db, trip_id, moment=None):
    """Return expired HELD seats of one locked departure to AVAILABLE and cancel their REQUESTED bookings.

    The caller must already hold the scheduled_trips row lock. BOOKED seats are never touched.
    Returns the number of released seats.
    """
    moment = moment or now()
    seats = db.scalars(select(ScheduledTripSeat).where(
        ScheduledTripSeat.scheduled_trip_id == trip_id, ScheduledTripSeat.seat_status == 'HELD',
        ScheduledTripSeat.hold_expires_at <= moment).order_by(ScheduledTripSeat.id).with_for_update()
        .execution_options(populate_existing=True)).all()
    if not seats:
        return 0
    booking_ids = sorted({s.held_by_booking_id for s in seats}, key=str)
    bookings = db.scalars(select(Booking).where(Booking.id.in_(booking_ids)).order_by(Booking.id).with_for_update()
                          .execution_options(populate_existing=True)).all()
    for seat in seats:
        free(seat, None)
    for booking in bookings:
        if booking.status == 'REQUESTED':
            cancel(db, booking, None, EXPIRED_REASON, moment)
    return len(seats)


def free(seat, actor):
    seat.seat_status = 'AVAILABLE'
    seat.held_by_booking_id = None
    seat.hold_expires_at = None
    touch(seat)
    seat.updated_by = actor


def cancel(db, booking, actor, reason, moment):
    booking.status = 'CANCELLED'
    booking.cancelled_by_user_id = actor
    booking.cancelled_at = moment
    booking.cancellation_reason = reason
    touch(booking)
    booking.updated_by = actor
    for traveller in db.scalars(select(BookingTraveller).where(BookingTraveller.booking_id == booking.id,
                                                                BookingTraveller.traveller_status == 'ACTIVE')).all():
        traveller.traveller_status = 'CANCELLED'
        touch(traveller)
        traveller.updated_by = actor


def booking_out(db, booking):
    rows = db.execute(select(BookingTraveller, ScheduledTripSeat, VehicleSeat)
                      .join(ScheduledTripSeat, ScheduledTripSeat.id == BookingTraveller.scheduled_trip_seat_id)
                      .join(VehicleSeat, VehicleSeat.id == ScheduledTripSeat.vehicle_seat_id)
                      .where(BookingTraveller.booking_id == booking.id)
                      .order_by(VehicleSeat.row_number, VehicleSeat.column_number)).all()
    fares = {s['seat_id']: s['fare'] for s in booking.price_snapshot.get('seats', [])}
    held = [inv for _, inv, _ in rows if inv.seat_status == 'HELD' and inv.held_by_booking_id == booking.id]
    expires = min((inv.hold_expires_at for inv in held), default=None)
    return {'id': str(booking.id), 'booking_reference': booking.booking_reference, 'booking_type': booking.booking_type,
            'status': booking.status, 'version': booking.version, 'scheduled_trip_id': str(booking.current_scheduled_trip_id),
            'hold_active': booking.status == 'REQUESTED' and bool(held),
            'hold_expires_at': expires.isoformat() if expires else None,
            'currency': booking.currency, 'total_amount': str(booking.total_amount),
            'assurance_type': booking.assurance_type, 'itinerary': booking.itinerary_snapshot,
            'cancellation_reason': booking.cancellation_reason,
            'travellers': [{'full_name': t.full_name, 'is_primary': t.is_primary, 'traveller_status': t.traveller_status,
                            'seat_id': str(inv.id), 'seat_code': seat.seat_code, 'fare': fares.get(str(inv.id))}
                           for t, inv, seat in rows]}


def own_ticket_booking(db, booking_id, user):
    booking = db.get(Booking, booking_id)
    if not booking or booking.booking_type != 'TICKET_HIRE' or booking.passenger_user_id != user.id:
        raise ApiError(404, 'BOOKING_NOT_FOUND', 'Booking not found.')
    return booking


def check_stops(db, route_id, boarding_id, dropoff_id):
    """Each stop is optional on its own: no get-on stop means the route start, no get-off stop the route end."""
    ordered = db.scalars(select(RouteStop).where(RouteStop.route_id == route_id, RouteStop.is_active.is_(True))
                         .order_by(RouteStop.stop_order)).all()
    stops = {s.id: s for s in ordered}
    boarding = stops.get(boarding_id) if boarding_id else ordered[0]
    dropoff = stops.get(dropoff_id) if dropoff_id else ordered[-1]
    if not boarding or not dropoff:
        raise ApiError(422, 'STOP_NOT_ON_ROUTE', 'Choose active stops on this departure route.')
    if not boarding.pickup_allowed or not dropoff.dropoff_allowed:
        raise ApiError(422, 'STOP_NOT_ALLOWED', 'This stop does not allow boarding or drop-off.')
    if boarding.stop_order >= dropoff.stop_order:
        raise ApiError(422, 'STOP_ORDER_INVALID', 'The boarding stop must come before the drop-off stop.')
    return boarding, dropoff


# --------------------------------------------------------------------------- hold (40)

@router.post('/bookings/ticket-holds', status_code=201)
def create_hold(body: TicketHoldRequest, user=Depends(current), db: Session = Depends(get_db)):
    require_role(db, user, 'PASSENGER')
    stored_key = f'{user.id.hex}:{body.idempotency_key}'
    trip = lock_trip(db, body.scheduled_trip_id)
    if not trip or trip.status not in BOOKABLE:
        raise ApiError(404, 'DEPARTURE_NOT_FOUND', 'Departure not found.')
    moment = now()
    replay = db.scalar(select(Booking).where(Booking.idempotency_key == stored_key))
    if replay:
        if replay.current_scheduled_trip_id != trip.id:
            raise ApiError(409, 'IDEMPOTENCY_KEY_REUSED', 'This request key was already used for another booking.')
        released = release_expired(db, trip.id, moment)
        db.commit()
        if released:
            db.refresh(replay)
        return JSONResponse(status_code=200, content=booking_out(db, replay))
    if trip.departure_at <= moment or trip.booking_cutoff_at <= moment:
        raise ApiError(409, 'BOOKING_CLOSED', 'Booking for this departure has closed.')
    minutes = hold_minutes(db.get(ServiceType, trip.service_type_id))
    if minutes is None:
        raise ApiError(409, 'TICKET_HOLD_NOT_CONFIGURED', 'Seat holds are not configured yet. An Admin must set the hold time.')
    route = db.get(Route, trip.route_id)
    boarding, dropoff = check_stops(db, route.id, body.boarding_stop_id, body.dropoff_stop_id)

    release_expired(db, trip.id, moment)
    seat_ids = sorted((t.seat_id for t in body.travellers), key=str)
    rows = db.execute(select(ScheduledTripSeat, VehicleSeat).join(VehicleSeat, VehicleSeat.id == ScheduledTripSeat.vehicle_seat_id)
                      .where(ScheduledTripSeat.id.in_(seat_ids), ScheduledTripSeat.scheduled_trip_id == trip.id)
                      .order_by(ScheduledTripSeat.id).with_for_update(of=ScheduledTripSeat)
                      .execution_options(populate_existing=True)).all()
    found = {inv.id: (inv, seat) for inv, seat in rows}
    if len(found) != len(seat_ids):
        raise ApiError(422, 'SEAT_NOT_ON_DEPARTURE', 'One or more seats do not belong to this departure.')
    taken = sorted(seat.seat_code for inv, seat in found.values() if inv.seat_status != 'AVAILABLE')
    if taken:
        db.commit()  # keep any expired-hold release made above
        raise ApiError(409, 'SEAT_UNAVAILABLE', 'These seats are no longer available: ' + ', '.join(taken) + '.',
                       [{'field': 'seat_id', 'message': code} for code in taken])

    expires = moment + timedelta(minutes=minutes)
    route_fares = (route.route_settings or {}).get('stop_fares')
    segment = None
    if route_fares:
        # Owner stop prices: the Passenger pays price(get-off) - price(get-on) per seat.
        segment = Decimal(route_fares[str(dropoff.id)]) - Decimal(route_fares[str(boarding.id)])
        if segment <= 0:
            raise ApiError(422, 'NO_FARE_FOR_STOPS', 'The Owner has no price for travel between these stops.')
    fares = []
    for traveller in body.travellers:
        inv, seat = found[traveller.seat_id]
        fare = segment if segment is not None else inv.fare_override if inv.fare_override is not None else trip.fare_per_seat
        fares.append({'seat_id': str(inv.id), 'seat_code': seat.seat_code, 'fare': format(Decimal(fare), '.2f')})
    total = sum((Decimal(f['fare']) for f in fares), Decimal('0'))
    terms = {'policy': trip.fulfilment_policy, 'minimum_confirmed_seats': trip.minimum_confirmed_seats,
             'decision_deadline': trip.decision_deadline.isoformat() if trip.decision_deadline else None,
             'accepted_time_window_minutes': trip.accepted_time_window_minutes,
             'accepted_replacement_terms': copy.deepcopy(trip.accepted_replacement_terms)}
    itinerary = {'departure_reference': trip.departure_reference, 'route_name': route.route_name,
                 'origin_name': route.origin_name, 'destination_name': route.destination_name,
                 'departure_at': trip.departure_at.isoformat(), 'estimated_arrival_at': trip.estimated_arrival_at.isoformat(),
                 'boarding_stop': boarding.stop_name if boarding else None, 'dropoff_stop': dropoff.stop_name if dropoff else None}
    booking = Booking(booking_reference='TKT-' + uuid4().hex[:16].upper(), passenger_user_id=user.id, booking_type='TICKET_HIRE',
                      service_type_id=trip.service_type_id, owner_user_id=trip.owner_user_id, vehicle_id=trip.current_vehicle_id,
                      original_scheduled_trip_id=trip.id, current_scheduled_trip_id=trip.id,
                      origin_text=boarding.stop_name if boarding else route.origin_name,
                      destination_text=dropoff.stop_name if dropoff else route.destination_name,
                      origin_stop_id=boarding.id if boarding else None, destination_stop_id=dropoff.id if dropoff else None,
                      start_at=trip.departure_at, end_at=trip.estimated_arrival_at, passenger_count=len(body.travellers),
                      status='REQUESTED', assurance_type=ASSURANCE[trip.fulfilment_policy], protected_terms_snapshot=terms,
                      quoted_amount=total, total_amount=total, currency=trip.currency, idempotency_key=stored_key,
                      itinerary_snapshot=itinerary,
                      price_snapshot={'currency': trip.currency, 'fare_per_seat': str(trip.fare_per_seat), 'seats': fares,
                                      'total': format(total, '.2f'),
                                      'stop_prices': None if segment is None else {
                                          'get_on': boarding.stop_name, 'get_on_price': route_fares[str(boarding.id)],
                                          'get_off': dropoff.stop_name, 'get_off_price': route_fares[str(dropoff.id)]}},
                      created_by=user.id, updated_by=user.id)
    db.add(booking)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ApiError(409, 'IDEMPOTENCY_KEY_REUSED', 'This request key was already used.') from None
    for index, traveller in enumerate(body.travellers):
        inv, _ = found[traveller.seat_id]
        inv.seat_status = 'HELD'
        inv.held_by_booking_id = booking.id
        inv.hold_expires_at = expires
        touch(inv)
        inv.updated_by = user.id
        db.add(BookingTraveller(booking_id=booking.id, full_name=traveller.full_name, contact_phone=traveller.contact_phone,
                                contact_email=traveller.contact_email, is_primary=index == 0,
                                scheduled_trip_seat_id=inv.id, boarding_stop_id=boarding.id if boarding else None,
                                dropoff_stop_id=dropoff.id if dropoff else None,
                                special_assistance=traveller.special_assistance, created_by=user.id, updated_by=user.id))
    # The departure status is left unchanged: no approved rule moves PUBLISHED -> BOOKING_OPEN on a hold.
    db.commit()
    return booking_out(db, booking)


# --------------------------------------------------------------------------- read and release (41)

@router.get('/bookings/{booking_id}/ticket')
def read_ticket_booking(booking_id: UUID, user=Depends(current), db: Session = Depends(get_db)):
    booking = own_ticket_booking(db, booking_id, user)
    if booking.status == 'REQUESTED' and lock_trip(db, booking.current_scheduled_trip_id):
        if release_expired(db, booking.current_scheduled_trip_id):
            db.commit()
            db.refresh(booking)
        else:
            db.rollback()
    return booking_out(db, booking)


@router.delete('/bookings/{booking_id}/seat-hold', status_code=204)
def release_hold(booking_id: UUID, body: HoldRelease | None = None, user=Depends(current), db: Session = Depends(get_db)):
    body = body or HoldRelease()
    booking = own_ticket_booking(db, booking_id, user)
    moment = now()
    lock_trip(db, booking.current_scheduled_trip_id)
    release_expired(db, booking.current_scheduled_trip_id, moment)
    booking = db.scalar(select(Booking).where(Booking.id == booking_id).with_for_update().execution_options(populate_existing=True))
    if booking.status != 'REQUESTED':
        db.commit()
        if booking.status == 'CANCELLED' and booking.cancellation_reason == EXPIRED_REASON and booking.cancelled_by_user_id is None:
            raise ApiError(410, 'HOLD_EXPIRED', 'This seat hold has already expired and the seats were released.')
        raise ApiError(409, 'HOLD_NOT_ACTIVE', 'This booking has no active seat hold.')
    if body.expected_version is not None and booking.version != body.expected_version:
        raise ApiError(409, 'VERSION_CONFLICT', 'The booking changed. Refresh before releasing.')
    seats = db.scalars(select(ScheduledTripSeat).where(ScheduledTripSeat.held_by_booking_id == booking.id,
                                                        ScheduledTripSeat.seat_status == 'HELD')
                       .order_by(ScheduledTripSeat.id).with_for_update().execution_options(populate_existing=True)).all()
    for seat in seats:
        free(seat, user.id)
    cancel(db, booking, user.id, body.reason, moment)
    db.commit()
    return Response(status_code=204)


# --------------------------------------------------------------------------- Admin hold time (service_types.settings)

def ticket_service_out(row):
    return {'id': str(row.id), 'code': row.code, 'name': row.name, 'is_active': row.is_active, 'version': row.version,
            'hold_minutes': hold_minutes(row)}


@router.get('/admin/ticket-services')
def list_ticket_services(user=Depends(admin), db: Session = Depends(get_db)):
    rows = db.scalars(select(ServiceType).where(ServiceType.category == 'TICKET_HIRE').order_by(ServiceType.code).limit(50)).all()
    return {'items': [ticket_service_out(r) for r in rows]}


@router.patch('/admin/ticket-services/{service_id}/hold-settings')
def update_hold_settings(service_id: UUID, body: TicketHoldSettings, request: Request, user=Depends(admin),
                         db: Session = Depends(get_db)):
    with request.app.state.audit.coordinated():
        locked_authority(db, request, user, user.id)
        row = db.scalar(select(ServiceType).where(ServiceType.id == service_id, ServiceType.category == 'TICKET_HIRE')
                        .with_for_update().execution_options(populate_existing=True))
        if not row:
            raise ApiError(404, 'SERVICE_NOT_FOUND', 'Ticket service not found.')
        if row.version != body.expected_version:
            raise ApiError(409, 'VERSION_CONFLICT', 'Service configuration changed. Reload before saving.')
        before, old = row.version, copy.deepcopy(row.settings)
        row.settings = {**(row.settings or {}), 'hold_minutes': body.hold_minutes}
        touch(row)
        row.updated_by = user.id
        request.app.state.audit.commit(db, actor=user.id, target={'resource': 'service_types', 'id': str(row.id)},
                                       previous_status=None, new_status=None, previous_version=before, new_version=row.version,
                                       full_reason=None, previous_decision_evidence={'settings': old},
                                       trace_id=request.state.trace_id)
    return ticket_service_out(row)
