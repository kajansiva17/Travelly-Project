"""Book now (owner decision 23 Nov 2026), the PickMe way for three-wheelers, cars and vans: the Passenger stands at the pickup, sees the vehicles that are
online close by with their fare, picks one, and the person sending that vehicle's location (the Driver, or the Owner who drives) accepts within
90 seconds. There is no 2-hour window and no 15-minute preparation here: the live phone position is the proof the vehicle is near.

 * Only vehicles whose Owner switched "Accept Book now" on (vehicles.instant_booking), that are online with a fresh position and are free right now.
 * The fare is the Owner's own LOCAL per-km rate for the real route, the same price engine as a planned hire. The fare the Passenger saw must still be
   the fare when the request is made.
 * Accepting creates the confirmed booking and the trip, so pickup code, start, odometer, finish and payment are the normal trip steps.
 * No background job: a request that was not answered in time is marked EXPIRED the next time anyone reads or writes the requests (lazy expiry)."""
import secrets
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
from app.services.pricing_scope import private_hire_scope

router = APIRouter(prefix='/api/v1', tags=['Book now'])
OFFER_SECONDS = 90
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


class Ask(BaseModel):
    vehicle_id: UUID
    pickup: Point
    destination: Place
    passenger_count: int = Field(default=1, strict=True, ge=1, le=20)
    fare: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


def now_utc():
    return datetime.now(timezone.utc)


def expire_stale(db, now):
    db.execute(update(RideRequest).where(RideRequest.status == 'OFFERED', RideRequest.expires_at <= now).values(status='EXPIRED', responded_at=now))
    db.flush()


def book_now_service(db):
    for service in db.scalars(select(ServiceType).where(ServiceType.category == 'PRIVATE_HIRE', ServiceType.is_active.is_(True)).order_by(ServiceType.created_at)):
        if private_hire_scope(service) == 'LOCAL' and catalogue_status(service) == 'ACTIVE':
            return service
    raise ApiError(409, 'BOOK_NOW_UNAVAILABLE', 'Book now is not available right now.')


def itinerary_of(request, pickup, destination, start):
    return Itinerary.model_validate({'start_at': start.isoformat(), 'direction': 'ONE_WAY', 'method': 'DISTANCE',
        'stops': [{'place': pickup, 'wait_minutes': '0', 'overnight_rest': False}, {'place': destination, 'wait_minutes': '0', 'overnight_rest': False}]})


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
    return {'id': str(row.id), 'status': row.status, 'fare': str(row.fare), 'currency': row.currency, 'passenger_count': row.passenger_count,
            'pickup': place_out(row.pickup), 'destination': place_out(row.destination), 'passenger_first_name': name,
            'expires_at': row.expires_at.isoformat(), 'seconds_left': max(0, int((row.expires_at - now).total_seconds())) if row.status == 'OFFERED' else 0,
            'booking_id': str(row.booking_id) if row.booking_id else None,
            'trip_id': str(db.scalar(select(Trip.id).where(Trip.booking_id == row.booking_id))) if row.booking_id else None,
            'vehicle': {'name': ' '.join(filter(None, [vehicle.make, vehicle.model])) or None, 'colour': vehicle.colour,
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
    service = book_now_service(db)
    pickup, destination = place_dicts(request, body)
    request.app.state.rate_locations.verify(body.destination)
    itinerary = settle_hours(request, service, itinerary_of(request, pickup, destination, now + START_DELAY))
    validate_service_itinerary(service, itinerary, db, request)
    items = []
    for km, vehicle in nearby_vehicles(db, body.pickup, body.radius_km, now):
        if vehicle.live_online_user_id == user.id or vehicle.owner_user_id == user.id:
            continue
        snapshot = fare_for(request, db, vehicle, service, itinerary, body.passenger_count)
        if snapshot is None:
            continue
        items.append({'vehicle_id': str(vehicle.id), 'reference': vehicle.public_vehicle_reference, 'name': ' '.join(filter(None, [vehicle.make, vehicle.model])) or None,
                      'colour': vehicle.colour, 'vehicle_type': vehicle.vehicle_type_code, 'seats': vehicle.seat_capacity,
                      'distance_km': round(km, 1), 'minutes_away': max(1, round(km / CITY_SPEED_KMH * 60)),
                      'fare': snapshot['calculation']['total'], 'currency': 'LKR'})
        if len(items) >= MAX_OPTIONS:
            break
    db.commit()
    return {'items': items, 'radius_km': body.radius_km, 'note': 'Distances and minutes are approximate. The fare is the vehicle Owner\'s own rate for this route.'}


@router.post('/ride-now/requests', status_code=201)
def ask(body: Ask, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    """The Passenger asks one vehicle. The fare they saw must still be the fare."""
    require_role(db, user, 'PASSENGER')
    request.app.state.store.rate(f'ride-request:{user.id}', 10, 60)
    now = now_utc()
    expire_stale(db, now)
    db.commit()
    service = book_now_service(db)
    vehicle = db.get(Vehicle, body.vehicle_id)
    if not vehicle or not bookable(vehicle, now):
        raise ApiError(409, 'VEHICLE_NOT_AVAILABLE', 'This vehicle is not available right now. Choose another one.')
    if vehicle.live_online_user_id == user.id or vehicle.owner_user_id == user.id:
        raise ApiError(409, 'OWN_VEHICLE', 'You cannot book a vehicle you operate yourself.')
    if not near_enough(vehicle, km_from(vehicle, body.pickup), MAX_RADIUS_KM):
        raise ApiError(409, 'VEHICLE_TOO_FAR', 'This vehicle is too far from your pickup. Choose another one.')
    pickup, destination = place_dicts(request, body)
    request.app.state.rate_locations.verify(body.destination)
    itinerary = settle_hours(request, service, itinerary_of(request, pickup, destination, now + START_DELAY))
    validate_service_itinerary(service, itinerary, db, request)
    snapshot = fare_for(request, db, vehicle, service, itinerary, body.passenger_count)
    if snapshot is None:
        raise ApiError(409, 'VEHICLE_NOT_AVAILABLE', 'This vehicle cannot take this trip right now. Choose another one.')
    fare = Decimal(snapshot['calculation']['total'])
    if fare != body.fare:
        raise ApiError(409, 'FARE_CHANGED', 'The fare changed. Check the new fare and ask again.', [{'field': 'fare', 'message': str(fare)}])
    locked = db.scalar(select(Vehicle).where(Vehicle.id == vehicle.id).with_for_update().execution_options(populate_existing=True))
    if not bookable(locked, now) or locked.live_online_user_id != vehicle.live_online_user_id:
        raise ApiError(409, 'VEHICLE_NOT_AVAILABLE', 'This vehicle is not available right now. Choose another one.')
    row = RideRequest(passenger_user_id=user.id, vehicle_id=vehicle.id, operator_user_id=locked.live_online_user_id, service_type_id=service.id,
        pickup=pickup, destination=destination, passenger_count=body.passenger_count, fare=fare, currency='LKR', status='OFFERED',
        expires_at=now + timedelta(seconds=OFFER_SECONDS))
    db.add(row)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ApiError(409, 'REQUEST_ALREADY_OPEN', 'You already have an open request, or this vehicle was just asked. Wait a moment.') from None
    db.commit()
    return view(db, row, now)


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
    itinerary = settle_hours(request, service, itinerary_of(request, preview.pickup, preview.destination, start))   # routing before any lock
    vehicle = db.get(Vehicle, preview.vehicle_id)
    snapshot = fare_for(request, db, vehicle, service, itinerary, preview.passenger_count)
    if snapshot is None or Decimal(snapshot['calculation']['total']) != preview.fare:
        raise ApiError(409, 'FARE_CHANGED', 'This trip can no longer be taken at the quoted fare. Decline it.')
    with request.app.state.audit.coordinated():
        locked_authority(db, request, user, user.id, require_admin=False)
        row = db.scalar(select(RideRequest).where(RideRequest.id == request_id).with_for_update().execution_options(populate_existing=True))
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
        notify(db, booking, 'Book now confirmed', 'The vehicle accepted your Book now request and is on its way.', user.id)
        request.app.state.audit.commit(db, actor=user.id, target={'resource': 'bookings', 'id': str(booking.id)}, previous_status=None,
            new_status='CONFIRMED', previous_version=0, new_version=booking.version or 1, full_reason=None, previous_decision_evidence={},
            trace_id=request.state.trace_id)
    return {**view(db, row, now_utc()), 'booking': booking_summary(booking)}
