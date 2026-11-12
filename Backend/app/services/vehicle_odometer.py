"""The vehicle's total odometer (vehicles.current_odometer_km) moves forward only.

PRD 9.1: keep actual readings distinct from trip distance; never add a reading to an accumulated distance; flag a
decreasing or inconsistent reading for review instead of applying it (meter replacement or data correction).
"""
from datetime import datetime, timezone
from sqlalchemy import select
from app.api.routers.api import touch
from app.models.review_models import Vehicle


def advance_odometer(db, vehicle_id, reading, actor, moment=None):
    """Apply an actual reading if it is ahead of the stored one. Returns 'APPLIED', 'SAME' or 'LOWER'."""
    vehicle = db.scalar(select(Vehicle).where(Vehicle.id == vehicle_id).with_for_update().execution_options(populate_existing=True))
    if vehicle is None or reading is None:
        return 'SAME'
    current = vehicle.current_odometer_km
    if current is not None and reading < current:
        return 'LOWER'
    if current is not None and reading == current:
        return 'SAME'
    vehicle.current_odometer_km = reading
    vehicle.odometer_updated_at = moment or datetime.now(timezone.utc)
    touch(vehicle)
    vehicle.updated_by = actor
    return 'APPLIED'
