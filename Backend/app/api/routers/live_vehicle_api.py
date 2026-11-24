"""Go online: the vehicle's live location comes from a phone, nobody types it (owner decision 23 Nov 2026).

 * The Owner (own vehicle) or a Driver the Owner has ACTIVE in My drivers presses "Go online" for one vehicle. While online, that phone sends
   the position every few seconds. It is the same vehicle position hire matching already uses (source GPS), so a vehicle that sent a position
   in the last 15 minutes is AVAILABLE for an immediate pickup with no Owner location confirmation.
 * Only the latest point is kept; there is no history. Going offline (or no position for 15 minutes) ends it.
 * A Passenger can see the vehicles that are online near a place: approximate distance and minutes only, never coordinates or the Owner.
 * One person sends for one vehicle at a time; a Driver cannot take over a vehicle someone else is sending for, the Owner always can."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.routers.api import current
from app.core.errors import ApiError
from app.dependencies.database import get_db
from app.models import User
from app.models.hire_models import OwnerDriver
from app.models.review_models import Vehicle
from app.services.hire_services import approved
from app.services.location_matching import LOCATION_FRESHNESS
from app.services.odometer_proof import distance_km

router = APIRouter(prefix='/api/v1', tags=['Live vehicles'])
CITY_SPEED_KMH = 30.0   # only for the approximate "minutes away"
NOT_READY = ('DRAFT', 'PENDING_VERIFICATION', 'MAINTENANCE', 'SUSPENDED', 'INACTIVE')


class Live(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_m: float | None = Field(default=None, ge=0, le=1000)


def can_operate(db, user, vehicle):
    if vehicle.owner_user_id == user.id:
        return bool(approved(db, user.id, 'OWNER'))
    link = db.scalar(select(OwnerDriver.id).where(OwnerDriver.owner_user_id == vehicle.owner_user_id, OwnerDriver.driver_user_id == user.id,
                                                  OwnerDriver.status == 'ACTIVE'))
    return bool(link and approved(db, user.id, 'DRIVER'))


def not_ready(vehicle):
    if vehicle.verification_status != 'APPROVED' or not vehicle.is_published:
        return 'This vehicle is not approved and published yet.'
    if vehicle.availability_status in NOT_READY:
        return 'This vehicle is not available for hire right now.'
    if not vehicle.accepts_hire_bookings:
        return 'Turn on hire bookings for this vehicle first.'
    return None


def is_fresh(vehicle, now):
    return vehicle.current_location_observed_at is not None and now - vehicle.current_location_observed_at <= LOCATION_FRESHNESS


def is_online(vehicle, now):
    return vehicle.live_online_user_id is not None and is_fresh(vehicle, now)


def stop(vehicle, now):
    """Offline. The last position is kept as the vehicle's last known place, but it must stop counting as live at once, so it is
    marked just older than the 15-minute freshness window (matching then asks for a confirmation instead of trusting it)."""
    vehicle.live_online_user_id = vehicle.live_online_since = None
    if is_fresh(vehicle, now):
        vehicle.current_location_observed_at = now - LOCATION_FRESHNESS - timedelta(seconds=1)


def state(vehicle, user, now):
    return {'vehicle_id': str(vehicle.id), 'online': is_online(vehicle, now), 'sending': vehicle.live_online_user_id == user.id,
            'since': vehicle.live_online_since.isoformat() if vehicle.live_online_since else None,
            'last_seen_at': vehicle.current_location_observed_at.isoformat() if vehicle.current_location_observed_at else None}


def locked(db, vehicle_id):
    return db.scalar(select(Vehicle).where(Vehicle.id == vehicle_id).with_for_update().execution_options(populate_existing=True))


@router.post('/vehicles/{vehicle_id}/live/online')
def go_online(vehicle_id: UUID, user=Depends(current), db: Session = Depends(get_db)):
    vehicle = locked(db, vehicle_id)
    if not vehicle or not can_operate(db, user, vehicle):
        raise ApiError(404, 'VEHICLE_NOT_FOUND', 'This vehicle was not found.')
    reason = not_ready(vehicle)
    if reason:
        raise ApiError(409, 'VEHICLE_NOT_READY', reason)
    now = datetime.now(timezone.utc)
    holder = vehicle.live_online_user_id
    if holder and holder != user.id and is_online(vehicle, now) and vehicle.owner_user_id != user.id:
        raise ApiError(409, 'VEHICLE_ALREADY_ONLINE', 'Someone else is already sending this vehicle\'s location.')
    for other in db.scalars(select(Vehicle).where(Vehicle.live_online_user_id == user.id, Vehicle.id != vehicle.id).with_for_update()).all():
        stop(other, now)   # one vehicle per person
    if holder != user.id:
        vehicle.live_online_user_id, vehicle.live_online_since = user.id, now
    db.commit()
    return state(vehicle, user, now)


@router.post('/vehicles/{vehicle_id}/live/offline')
def go_offline(vehicle_id: UUID, user=Depends(current), db: Session = Depends(get_db)):
    vehicle = locked(db, vehicle_id)
    if not vehicle or user.id not in (vehicle.live_online_user_id, vehicle.owner_user_id):
        raise ApiError(404, 'VEHICLE_NOT_FOUND', 'This vehicle was not found.')
    now = datetime.now(timezone.utc)
    if vehicle.live_online_user_id:
        stop(vehicle, now)
        db.commit()
    return state(vehicle, user, now)


class InstantSwitch(BaseModel):
    enabled: bool


@router.patch('/vehicles/{vehicle_id}/live/instant-booking')
def set_instant_booking(vehicle_id: UUID, body: InstantSwitch, user=Depends(current), db: Session = Depends(get_db)):
    """Only the Owner. When on, a Passenger who accepts the price of an immediate pickup is confirmed at once while the vehicle is online."""
    vehicle = locked(db, vehicle_id)
    if not vehicle or vehicle.owner_user_id != user.id or not approved(db, user.id, 'OWNER'):
        raise ApiError(404, 'VEHICLE_NOT_FOUND', 'This vehicle was not found.')
    vehicle.instant_booking = body.enabled   # not a position change: the vehicle version stays
    db.commit()
    return {'vehicle_id': str(vehicle.id), 'instant_booking': bool(vehicle.instant_booking)}


@router.put('/vehicles/{vehicle_id}/live/location')
def send_location(vehicle_id: UUID, body: Live, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    request.app.state.store.rate(f'live-location:{vehicle_id}', 60, 60)
    vehicle = locked(db, vehicle_id)
    if not vehicle or vehicle.live_online_user_id != user.id:
        raise ApiError(409, 'NOT_ONLINE', 'Go online for this vehicle first.')
    now = datetime.now(timezone.utc)
    if not can_operate(db, user, vehicle):
        stop(vehicle, now)   # the Owner removed this Driver, or the role ended
        db.commit()
        raise ApiError(403, 'NOT_ALLOWED', 'You can no longer send this vehicle\'s location.')
    vehicle.current_latitude = Decimal(str(round(body.latitude, 6)))
    vehicle.current_longitude = Decimal(str(round(body.longitude, 6)))
    vehicle.current_location_accuracy_m = None if body.accuracy_m is None else Decimal(str(round(body.accuracy_m, 2)))
    vehicle.current_location_source = 'GPS'
    vehicle.current_location_observed_at = now   # the vehicle version is not touched, like the trip GPS
    db.commit()
    return state(vehicle, user, now)


@router.get('/me/live-vehicles')
def my_live_vehicles(user=Depends(current), db: Session = Depends(get_db)):
    """The vehicles this person can send a live position for: an Owner's own, or those of Owners who listed them as a Driver."""
    owner_ids = set()
    if approved(db, user.id, 'OWNER'):
        owner_ids.add(user.id)
    if approved(db, user.id, 'DRIVER'):
        owner_ids |= set(db.scalars(select(OwnerDriver.owner_user_id).where(OwnerDriver.driver_user_id == user.id, OwnerDriver.status == 'ACTIVE')))
    vehicles = db.scalars(select(Vehicle).where(Vehicle.owner_user_id.in_(owner_ids), Vehicle.verification_status == 'APPROVED')
                          .order_by(Vehicle.registration_number)).all() if owner_ids else []
    owners = {u.id: u for u in db.scalars(select(User).where(User.id.in_({v.owner_user_id for v in vehicles})))} if vehicles else {}
    now = datetime.now(timezone.utc)
    items = []
    for v in vehicles:
        reason = not_ready(v)
        online = is_online(v, now)
        owner = owners.get(v.owner_user_id)
        items.append({**state(v, user, now), 'registration_number': v.registration_number, 'name': v.display_name or ' '.join(filter(None, [v.make, v.model])) or None,
                      'owner_name': (owner.display_name or owner.full_name) if owner and v.owner_user_id != user.id else None,
                      'ready': reason is None, 'not_ready_reason': reason, 'taken_by_someone_else': bool(online and v.live_online_user_id != user.id),
                      'instant_booking': bool(v.instant_booking)})
    return {'items': items}


@router.get('/hire/nearby-now')
def nearby_now(request: Request, latitude: float = Query(ge=-90, le=90), longitude: float = Query(ge=-180, le=180),
               radius_km: float = Query(10, gt=0, le=50), user=Depends(current), db: Session = Depends(get_db)):
    """Passenger: vehicles online near a place right now (a position in the last 15 minutes), nearest first. Approximate only."""
    request.app.state.store.rate(f'nearby-now:{user.id}', 30, 60)
    now = datetime.now(timezone.utc)
    rows = db.scalars(select(Vehicle).where(Vehicle.live_online_user_id.is_not(None), Vehicle.verification_status == 'APPROVED', Vehicle.is_published.is_(True),
                                            Vehicle.accepts_hire_bookings.is_(True), Vehicle.availability_status == 'ACTIVE',
                                            Vehicle.current_location_observed_at >= now - LOCATION_FRESHNESS)).all()
    items = []
    for v in rows:
        if v.current_latitude is None or v.current_longitude is None:
            continue
        km = distance_km(latitude, longitude, float(v.current_latitude), float(v.current_longitude))
        if km > radius_km or (v.pickup_distance_km is not None and km > float(v.pickup_distance_km)):
            continue
        items.append({'vehicle_id': str(v.id), 'reference': v.public_vehicle_reference, 'vehicle_type': v.vehicle_type_code, 'seats': v.seat_capacity,
                      'name': v.display_name or ' '.join(filter(None, [v.make, v.model])) or None, 'colour': v.colour, 'distance_km': round(km, 1),
                      'minutes_away': max(1, round(km / CITY_SPEED_KMH * 60)), 'instant_booking': bool(v.instant_booking),
                      'updated_seconds_ago': int((now - v.current_location_observed_at).total_seconds())})
    items.sort(key=lambda i: i['distance_km'])
    return {'items': items[:20], 'radius_km': radius_km, 'note': 'Distances and minutes are approximate (straight line).'}
