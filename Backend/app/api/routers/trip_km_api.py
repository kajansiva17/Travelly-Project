"""Owner's kilometre check for a finished trip: the kilometres the Passenger was charged for (the route estimate saved with the booking) next to the kilometres
the vehicle really covered (end odometer minus start odometer). The difference shows detours or private use. It never changes the Passenger's fare."""
from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.routers.api import current
from app.api.routers.charge_report_api import owner_of, trip_and_booking
from app.core.errors import ApiError
from app.dependencies.database import get_db

router = APIRouter(prefix='/api/v1', tags=['Trip kilometres'])


@router.get('/trips/{trip_id}/km-summary')
def km_summary(trip_id: UUID, user=Depends(current), db: Session = Depends(get_db)):
    trip, booking = trip_and_booking(db, trip_id)
    if user.id != owner_of(trip, booking):
        raise ApiError(404, 'TRIP_NOT_FOUND', 'This trip was not found.')
    usage = (((booking.itinerary_snapshot or {}).get('measurement') or {}).get('usage')) or {}
    billed = usage.get('distance_km')
    billed = Decimal(str(billed)) if billed not in (None, '') else None
    odometer = trip.calculated_distance_km
    extra = (odometer - billed) if billed is not None and odometer is not None else None
    return {'billed_km': format(billed, '.1f') if billed is not None else None,
            'odometer_km': format(odometer, '.1f') if odometer is not None else None,
            'extra_km': format(extra, '.1f') if extra is not None else None,
            'start_odometer_km': format(trip.start_odometer_km, '.1f') if trip.start_odometer_km is not None else None,
            'end_odometer_km': format(trip.end_odometer_km, '.1f') if trip.end_odometer_km is not None else None,
            'finished': trip.status == 'COMPLETED'}
