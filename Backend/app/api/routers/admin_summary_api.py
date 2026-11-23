"""Admin dashboard summary (read only, nothing stored): the numbers on the Command Centre tiles.
 * trips today (Sri Lanka day), trips on the road now, trips finished today
 * money today: collected and Travelly commission on payments captured today (kept payments only, the same rule as the monthly Admin report)
 * bookings made on each of the last 7 days
 * vehicles with a fresh position (the 15-minute rule), marked online (Go online) and on a trip, for the live map."""
from datetime import datetime, time, timedelta, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.api.routers.review_api import admin
from app.dependencies.database import get_db
from app.models.hire_models import Booking, Trip
from app.models.payment_models import Payment
from app.models.review_models import Vehicle
from app.services.admin_report import KEPT
from app.services.location_matching import LOCATION_FRESHNESS
from app.services.owner_report import COLOMBO, ZERO, money

router = APIRouter(prefix='/api/v1', tags=['Admin summary'])
ON_THE_ROAD = ('IN_PROGRESS', 'BREAKDOWN', 'ASSISTANCE_REQUIRED')
MAP_LIMIT = 300


@router.get('/admin/dashboard-summary')
def dashboard_summary(user=Depends(admin), db: Session = Depends(get_db)):
    moment = datetime.now(timezone.utc)
    today = moment.astimezone(COLOMBO).date()
    day_start = datetime.combine(today, time(0), COLOMBO).astimezone(timezone.utc)
    day_end = day_start + timedelta(days=1)
    trips_today = db.scalar(select(func.count()).select_from(Trip).where(Trip.scheduled_start_at >= day_start, Trip.scheduled_start_at < day_end, Trip.status != 'CANCELLED')) or 0
    on_the_road = db.scalar(select(func.count()).select_from(Trip).where(Trip.status.in_(ON_THE_ROAD))) or 0
    finished_today = db.scalar(select(func.count()).select_from(Trip).where(Trip.status == 'COMPLETED', Trip.actual_end_at >= day_start, Trip.actual_end_at < day_end)) or 0
    when = func.coalesce(Payment.captured_at, Payment.created_at)
    collected, commission = db.execute(select(func.coalesce(func.sum(Payment.amount), 0), func.coalesce(func.sum(Payment.commission_amount), 0))
                                       .where(Payment.transaction_type == 'PAYMENT', Payment.status.in_(KEPT), when >= day_start, when < day_end)).one()
    first = day_start - timedelta(days=6)
    counts = {}
    for (created,) in db.execute(select(Booking.created_at).where(Booking.created_at >= first, Booking.created_at < day_end)):
        key = created.astimezone(COLOMBO).date()
        counts[key] = counts.get(key, 0) + 1
    days = [today - timedelta(days=offset) for offset in range(6, -1, -1)]
    trend = [{'date': d.isoformat(), 'bookings': counts.get(d, 0)} for d in days]
    busy = set(db.scalars(select(Trip.vehicle_id).where(Trip.status.in_(ON_THE_ROAD))))
    vehicles = db.scalars(select(Vehicle).where(Vehicle.current_location_observed_at >= moment - LOCATION_FRESHNESS, Vehicle.current_latitude.is_not(None),
                                                 Vehicle.current_longitude.is_not(None)).order_by(Vehicle.current_location_observed_at.desc()).limit(MAP_LIMIT)).all()
    return {'currency': 'LKR', 'date': today.isoformat(),
            'trips': {'today': trips_today, 'on_the_road': on_the_road, 'finished_today': finished_today},
            'money_today': {'collected': money(collected or ZERO), 'commission': money(commission or ZERO)},
            'booking_trend': trend,
            'live_vehicles': [{'id': str(v.id), 'reference': v.public_vehicle_reference, 'registration': v.registration_number,
                               'latitude': float(v.current_latitude), 'longitude': float(v.current_longitude), 'online': v.live_online_user_id is not None,
                               'on_trip': v.id in busy, 'seconds_ago': int((moment - v.current_location_observed_at).total_seconds())} for v in vehicles]}
