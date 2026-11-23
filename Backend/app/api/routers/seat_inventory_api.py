"""Owner > Seat inventory: how full every ticket departure of the Owner is (read only, nothing new is stored).
For each of the Owner's newest 100 departures: seats for sale, available, held (a Passenger is paying), booked, and the amount of the booked seats.
An expired hold counts as available, the same as the seat map does. The page filters upcoming/past and by status itself (no GET query parameters)."""
from datetime import datetime, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session
from app.api.routers.api import current, require_role
from app.dependencies.database import get_db
from app.models.hire_models import Route, ScheduledTrip
from app.models.review_models import Vehicle
from app.models.seat_models import ScheduledTripSeat

router = APIRouter(prefix='/api/v1', tags=['Seat inventory'])
LIMIT = 100


@router.get('/owners/me/seat-inventory')
def seat_inventory(user=Depends(current), db: Session = Depends(get_db)):
    require_role(db, user, 'OWNER')
    moment = datetime.now(timezone.utc)
    rows = db.execute(select(ScheduledTrip, Route, Vehicle).join(Route, Route.id == ScheduledTrip.route_id).join(Vehicle, Vehicle.id == ScheduledTrip.current_vehicle_id)
                      .where(ScheduledTrip.owner_user_id == user.id).order_by(ScheduledTrip.departure_at.desc()).limit(LIMIT)).all()
    ids = [trip.id for trip, _, _ in rows]
    counts = {}
    if ids:
        expired = (ScheduledTripSeat.seat_status == 'HELD') & (ScheduledTripSeat.hold_expires_at <= moment)
        bucket = case((expired, 'AVAILABLE'), else_=ScheduledTripSeat.seat_status)
        for trip_id, status, number in db.execute(select(ScheduledTripSeat.scheduled_trip_id, bucket, func.count()).where(ScheduledTripSeat.scheduled_trip_id.in_(ids))
                                                  .group_by(ScheduledTripSeat.scheduled_trip_id, bucket)):
            counts.setdefault(trip_id, {})[status] = number
    money = {trip_id: amount for trip_id, amount in db.execute(
        select(ScheduledTripSeat.scheduled_trip_id, func.coalesce(func.sum(func.coalesce(ScheduledTripSeat.fare_override, ScheduledTrip.fare_per_seat)), 0))
        .join(ScheduledTrip, ScheduledTrip.id == ScheduledTripSeat.scheduled_trip_id)
        .where(ScheduledTripSeat.scheduled_trip_id.in_(ids), ScheduledTripSeat.seat_status == 'BOOKED').group_by(ScheduledTripSeat.scheduled_trip_id))} if ids else {}
    items = []
    for trip, route, vehicle in rows:
        c = counts.get(trip.id, {})
        total = sum(c.values())
        items.append({'id': str(trip.id), 'departure_reference': trip.departure_reference, 'status': trip.status,
                      'route': f'{route.origin_name} → {route.destination_name}', 'departure_at': trip.departure_at.isoformat(),
                      'vehicle': vehicle.registration_number, 'currency': trip.currency, 'fare_per_seat': str(trip.fare_per_seat),
                      'seats': {'total': total, 'available': c.get('AVAILABLE', 0), 'held': c.get('HELD', 0), 'booked': c.get('BOOKED', 0),
                                'other': total - c.get('AVAILABLE', 0) - c.get('HELD', 0) - c.get('BOOKED', 0)},
                      'booked_amount': format((money.get(trip.id) or Decimal('0')).quantize(Decimal('0.01')), '.2f'),
                      'minimum_confirmed_seats': trip.minimum_confirmed_seats, 'fulfilment_policy': trip.fulfilment_policy,
                      'decision_deadline': trip.decision_deadline.isoformat() if trip.decision_deadline else None})
    return {'items': items}
