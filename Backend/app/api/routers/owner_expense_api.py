"""Owner > Operations > Vehicle Expenses: every cost of the Owner's whole fleet in one list (read only, nothing new is stored).
Service, repair, fuel and charging entered on a vehicle's Maintenance page (`vehicle_records`, the same rows the monthly report adds up).
The newest 400 rows are returned; the page filters by month and vehicle itself (GET query parameters are not used)."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.routers.api import current, require_role
from app.dependencies.database import get_db
from app.models.hire_models import VehicleRecord
from app.models.review_models import Vehicle
from app.services.owner_report import SPEND, label, money

router = APIRouter(prefix='/api/v1', tags=['Owner expenses'])
LIMIT = 400


@router.get('/owners/me/expenses')
def fleet_expenses(user=Depends(current), db: Session = Depends(get_db)):
    require_role(db, user, 'OWNER')
    vehicles = {v.id: v for v in db.scalars(select(Vehicle).where(Vehicle.owner_user_id == user.id))}
    if not vehicles:
        return {'currency': 'LKR', 'vehicles': [], 'items': []}
    ids = list(vehicles)
    records = db.scalars(select(VehicleRecord).where(VehicleRecord.vehicle_id.in_(ids), VehicleRecord.record_type.in_(SPEND), VehicleRecord.amount.is_not(None))
                         .order_by(VehicleRecord.recorded_at.desc()).limit(LIMIT)).all()
    items = [{'id': str(r.id), 'source': 'RECORD', 'vehicle_id': str(r.vehicle_id), 'recorded_at': r.recorded_at.isoformat(), 'type': label(r.record_type),
              'amount': money(r.amount), 'detail': r.service_provider or r.notes, 'status': 'Recorded', 'counts': True} for r in records]
    return {'currency': 'LKR', 'vehicles': [{'id': str(v.id), 'registration': v.registration_number, 'label': v.registration_number} for v in vehicles.values()], 'items': items}
