"""Vehicle records and maintenance summary (PRD matrix 71-73) on the PRD table vehicle_records.

    GET  /vehicles/{vehicle_id}/records               Owner or the vehicle's preferred Driver: latest records + totals
    POST /vehicles/{vehicle_id}/records               Owner: add one typed record (maintenance, fuel, charging, odometer, personal use)
    GET  /vehicles/{vehicle_id}/maintenance-summary   remaining km, estimated and genuine due dates per maintenance task

PRD rules applied (4.16 and 9.1):
- Power compatibility: BEV has no engine-oil or fuel records; charging only for BEV/PHEV; fuel type must match the
  vehicle's engine fuel.
- A fuel purchase records the actual product, litres and paid amount; charging records the amount (kWh optional).
- Records are never edited or deleted here; a correction is a new record (auditable trail).
- The odometer only moves forward. A newer record whose reading is lower than the vehicle's is kept but flagged
  approval_status NEEDS_REVIEW and does not change the vehicle (meter replacement or data correction).
- Suspected duplicates (same type, day, amount and reading) need confirm_duplicate: true.
- Maintenance estimate: remaining_km = next_due_odometer_km - current odometer; average daily km from accepted readings
  in the last 30 days; estimated_due_date = today + ceil(remaining_km / average); 'Estimated date unavailable' when the
  data is not enough. The earlier of the distance and calendar limits decides due/overdue.
Driver entries are read-only for now: Driver-entry review rules are not agreed yet (PRD 9.1). Receipts wait for the
private-media storage endpoint.
"""
import math
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.api.routers.api import current
from app.api.routers.scheduled_trip_api import has_role
from app.core.errors import ApiError
from app.dependencies.database import get_db
from app.models.hire_models import Trip, VehicleRecord
from app.models.review_models import Vehicle
from app.schemas.vehicle_record_schemas import VehicleRecordIn
from app.services.vehicle_odometer import advance_odometer

router = APIRouter(prefix='/api/v1', tags=['Vehicle records'])
COLOMBO = ZoneInfo('Asia/Colombo')
TASKS = ('OIL_CHANGE', 'OIL_FILTER_CHANGE', 'TYRE_CHANGE', 'TYRE_ROTATION', 'WHEEL_ALIGNMENT', 'WHEEL_BALANCING',
         'GENERAL_SERVICE', 'BRAKE_SERVICE', 'BATTERY_SERVICE')
MAINTENANCE = TASKS + ('REPAIR',)
ENGINE_ONLY = ('OIL_CHANGE', 'OIL_FILTER_CHANGE')
ROLLING_DAYS = 30
APPLIES = {  # which optional fields each type may carry (anything else is refused, so nothing is stored by mistake)
    **{t: {'odometer_km', 'amount', 'currency', 'next_due_odometer_km', 'genuine_calendar_due_date', 'service_provider', 'notes'} for t in TASKS},
    'REPAIR': {'odometer_km', 'amount', 'currency', 'service_provider', 'notes'},
    'FUEL_PURCHASE': {'odometer_km', 'amount', 'currency', 'quantity', 'unit', 'fuel_type', 'fuel_grade_product', 'service_provider', 'notes'},
    'EV_CHARGING': {'odometer_km', 'amount', 'currency', 'charging_kwh', 'service_provider', 'notes'},
    'ODOMETER_UPDATE': {'odometer_km', 'notes'},
    'PERSONAL_EXTRA_USE': {'start_odometer_km', 'end_odometer_km', 'notes'},
}


def now():
    return datetime.now(timezone.utc)


def problem(code, message, field=None):
    return ApiError(422, code, message, [{'field': field, 'message': message}] if field else None)


def viewable(db, vehicle_id, user):
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle or user.id not in (vehicle.owner_user_id, vehicle.default_driver_user_id):
        raise ApiError(404, 'VEHICLE_NOT_FOUND', 'Vehicle not found.')
    return vehicle


def km(value):
    return None if value is None else format(value, '.1f')


def record_out(r):
    return {'id': str(r.id), 'vehicle_id': str(r.vehicle_id), 'trip_id': str(r.trip_id) if r.trip_id else None,
            'record_type': r.record_type, 'recorded_at': r.recorded_at.isoformat(), 'odometer_km': km(r.odometer_km),
            'start_odometer_km': km(r.start_odometer_km), 'end_odometer_km': km(r.end_odometer_km),
            'amount': None if r.amount is None else format(r.amount, '.2f'), 'currency': r.currency,
            'quantity': None if r.quantity is None else format(r.quantity, '.3f'), 'unit': r.unit, 'fuel_type': r.fuel_type,
            'fuel_grade_product': r.fuel_grade_product,
            'charging_kwh': None if r.charging_kwh is None else format(r.charging_kwh, '.3f'),
            'next_due_odometer_km': km(r.next_due_odometer_km),
            'genuine_calendar_due_date': r.genuine_calendar_due_date.isoformat() if r.genuine_calendar_due_date else None,
            'service_provider': r.service_provider, 'notes': r.notes, 'review_status': r.approval_status,
            'recorded_by_user_id': str(r.recorded_by_user_id), 'created_at': r.created_at.isoformat()}


# --------------------------------------------------------------------------- 71 list

@router.get('/vehicles/{vehicle_id}/records')
def list_records(vehicle_id: UUID, user=Depends(current), db: Session = Depends(get_db)):
    vehicle = viewable(db, vehicle_id, user)
    rows = db.scalars(select(VehicleRecord).where(VehicleRecord.vehicle_id == vehicle.id, VehicleRecord.record_type != 'AVAILABILITY_BLOCK')
                      .order_by(VehicleRecord.recorded_at.desc(), VehicleRecord.created_at.desc()).limit(200)).all()

    def spent(*types):
        return format(db.scalar(select(func.coalesce(func.sum(VehicleRecord.amount), 0)).where(
            VehicleRecord.vehicle_id == vehicle.id, VehicleRecord.record_type.in_(types))) or Decimal('0'), '.2f')
    return {'vehicle_id': str(vehicle.id), 'power_type': vehicle.power_type, 'engine_fuel_type': vehicle.engine_fuel_type,
            'current_odometer_km': km(vehicle.current_odometer_km),
            'odometer_updated_at': vehicle.odometer_updated_at.isoformat() if vehicle.odometer_updated_at else None,
            'allowed_record_types': allowed_types(vehicle), 'can_add': user.id == vehicle.owner_user_id,
            'totals': {'currency': 'LKR', 'fuel': spent('FUEL_PURCHASE'), 'charging': spent('EV_CHARGING'),
                       'maintenance': spent(*MAINTENANCE)},
            'items': [record_out(r) for r in rows]}


def allowed_types(vehicle):
    power = vehicle.power_type
    types = [t for t in MAINTENANCE if not (power == 'BEV' and t in ENGINE_ONLY)]
    if power != 'BEV':
        types.append('FUEL_PURCHASE')
    if power in ('BEV', 'PHEV'):
        types.append('EV_CHARGING')
    return types + ['ODOMETER_UPDATE', 'PERSONAL_EXTRA_USE']


# --------------------------------------------------------------------------- 72 add

@router.post('/vehicles/{vehicle_id}/records', status_code=201)
def add_record(vehicle_id: UUID, body: VehicleRecordIn, user=Depends(current), db: Session = Depends(get_db)):
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle or vehicle.owner_user_id != user.id or not has_role(db, user.id, 'OWNER'):
        raise ApiError(404, 'VEHICLE_NOT_FOUND', 'Vehicle not found.')
    kind = body.record_type
    if kind not in allowed_types(vehicle):
        raise problem('RECORD_NOT_COMPATIBLE', f'A {kind.replace("_", " ").lower()} record does not apply to a {vehicle.power_type or "vehicle"} '
                      'with this power type.', 'record_type')
    given = {k for k, v in body.model_dump(exclude={'record_type', 'recorded_at', 'confirm_duplicate'}).items() if v is not None}
    extra = sorted(given - APPLIES[kind])
    if extra:
        raise ApiError(422, 'FIELD_NOT_APPLICABLE', f'These fields do not apply to {kind}: ' + ', '.join(extra) + '.',
                       [{'field': f, 'message': 'Not used for this record type.'} for f in extra])
    moment = now()
    if body.recorded_at > moment + timedelta(minutes=5):
        raise problem('VALIDATION_ERROR', 'The record time cannot be in the future.', 'recorded_at')
    if body.amount is not None and (body.currency or 'LKR') != 'LKR':
        raise problem('VALIDATION_ERROR', 'Amounts are recorded in LKR.', 'currency')
    if kind == 'FUEL_PURCHASE':
        for name in ('fuel_grade_product', 'quantity', 'amount'):
            if getattr(body, name) is None:
                raise problem('VALIDATION_ERROR', 'A fuel purchase needs the actual product, the litres and the paid amount.', name)
        if vehicle.engine_fuel_type and body.fuel_type and body.fuel_type != vehicle.engine_fuel_type:
            raise problem('RECORD_NOT_COMPATIBLE', f'This vehicle uses {vehicle.engine_fuel_type.lower()}.', 'fuel_type')
    if kind == 'EV_CHARGING' and body.amount is None:
        raise problem('VALIDATION_ERROR', 'A charging record needs the paid amount (kWh is optional).', 'amount')
    if kind == 'ODOMETER_UPDATE' and body.odometer_km is None:
        raise problem('VALIDATION_ERROR', 'Enter the odometer reading.', 'odometer_km')
    if kind == 'PERSONAL_EXTRA_USE':
        if body.start_odometer_km is None or body.end_odometer_km is None or body.end_odometer_km < body.start_odometer_km:
            raise problem('VALIDATION_ERROR', 'Enter the start and end odometer; the end cannot be lower than the start.', 'end_odometer_km')
    if body.next_due_odometer_km is not None and body.odometer_km is not None and body.next_due_odometer_km <= body.odometer_km:
        raise problem('VALIDATION_ERROR', 'The next service distance must be above the reading at this service.', 'next_due_odometer_km')
    if body.genuine_calendar_due_date is not None and body.genuine_calendar_due_date <= body.recorded_at.astimezone(COLOMBO).date():
        raise problem('VALIDATION_ERROR', 'The next service date must be after this record.', 'genuine_calendar_due_date')
    reading = body.end_odometer_km if kind == 'PERSONAL_EXTRA_USE' else body.odometer_km
    if not body.confirm_duplicate:
        day = body.recorded_at.astimezone(COLOMBO).date()
        same = select(VehicleRecord.id).where(
            VehicleRecord.vehicle_id == vehicle.id, VehicleRecord.record_type == kind,
            func.date(func.timezone('Asia/Colombo', VehicleRecord.recorded_at)) == day,
            VehicleRecord.amount.is_(None) if body.amount is None else VehicleRecord.amount == body.amount,
            VehicleRecord.odometer_km.is_(None) if body.odometer_km is None else VehicleRecord.odometer_km == body.odometer_km)
        if db.scalar(same.limit(1)):
            raise ApiError(409, 'POSSIBLE_DUPLICATE', 'A record like this already exists for that day. Send again with '
                           'confirm_duplicate: true if it is a separate entry.')
    vehicle = db.scalar(select(Vehicle).where(Vehicle.id == vehicle.id).with_for_update().execution_options(populate_existing=True))
    review, status = None, 'NO_READING'
    if reading is not None:
        newer = vehicle.odometer_updated_at is None or body.recorded_at >= vehicle.odometer_updated_at
        if not newer:
            status = 'HISTORICAL'  # an older entry being filled in: kept, the vehicle's newer reading stays
        else:
            outcome = advance_odometer(db, vehicle.id, reading, user.id, body.recorded_at)
            status = {'APPLIED': 'APPLIED', 'SAME': 'UNCHANGED', 'LOWER': 'NEEDS_REVIEW'}[outcome]
            if outcome == 'LOWER':
                review = 'NEEDS_REVIEW'  # newer than the stored reading but lower: meter change or a typing mistake
    row = VehicleRecord(vehicle_id=vehicle.id, recorded_by_user_id=user.id, record_type=kind, recorded_at=body.recorded_at,
                        odometer_km=body.odometer_km, start_odometer_km=body.start_odometer_km, end_odometer_km=body.end_odometer_km,
                        amount=body.amount, currency=(body.currency or 'LKR') if body.amount is not None else None,
                        quantity=body.quantity, unit=(body.unit or 'L') if kind == 'FUEL_PURCHASE' else None,
                        fuel_type=(body.fuel_type or vehicle.engine_fuel_type) if kind == 'FUEL_PURCHASE' else None,
                        fuel_grade_product=body.fuel_grade_product, charging_kwh=body.charging_kwh,
                        next_due_odometer_km=body.next_due_odometer_km, genuine_calendar_due_date=body.genuine_calendar_due_date,
                        service_provider=body.service_provider, notes=body.notes, approval_status=review,
                        created_by=user.id, updated_by=user.id)
    db.add(row)
    db.commit()
    return {**record_out(row), 'odometer_status': status}


# --------------------------------------------------------------------------- 73 maintenance summary

def readings(db, vehicle, since):
    """Accepted actual odometer readings in the period: records (not flagged) and trip start/finish readings."""
    points = []
    for r in db.scalars(select(VehicleRecord).where(VehicleRecord.vehicle_id == vehicle.id, VehicleRecord.recorded_at >= since,
                                                    VehicleRecord.approval_status.is_(None), VehicleRecord.record_type != 'AVAILABILITY_BLOCK')):
        value = r.end_odometer_km if r.record_type == 'PERSONAL_EXTRA_USE' else r.odometer_km
        if value is not None:
            points.append((r.recorded_at, value))
    for t in db.scalars(select(Trip).where(Trip.vehicle_id == vehicle.id, Trip.actual_start_at >= since)):
        if t.start_odometer_km is not None:
            points.append((t.actual_start_at, t.start_odometer_km))
        if t.end_odometer_km is not None and t.actual_end_at:
            points.append((t.actual_end_at, t.end_odometer_km))
    return sorted(points)


@router.get('/vehicles/{vehicle_id}/maintenance-summary')
def maintenance_summary(vehicle_id: UUID, user=Depends(current), db: Session = Depends(get_db)):
    vehicle = viewable(db, vehicle_id, user)
    moment = now()
    today = moment.astimezone(COLOMBO).date()
    since = moment - timedelta(days=ROLLING_DAYS)
    points = readings(db, vehicle, since)
    average = None
    if len(points) >= 2:
        days = (points[-1][0] - points[0][0]).total_seconds() / 86400
        distance = max(p[1] for p in points) - min(p[1] for p in points)
        if days >= 1 and distance > 0:
            average = Decimal(distance) / Decimal(str(days))
    current_km = vehicle.current_odometer_km
    items = []
    for task in TASKS:
        if vehicle.power_type == 'BEV' and task in ENGINE_ONLY:
            continue
        last = db.scalar(select(VehicleRecord).where(VehicleRecord.vehicle_id == vehicle.id, VehicleRecord.record_type == task)
                         .order_by(VehicleRecord.recorded_at.desc(), VehicleRecord.created_at.desc()).limit(1))
        item = {'task': task, 'last_done_at': None, 'last_odometer_km': None, 'next_due_odometer_km': None, 'remaining_km': None,
                'estimated_due_date': None, 'estimate_note': None, 'genuine_calendar_due_date': None, 'days_to_calendar_due': None,
                'due_by': None, 'status': 'NOT_RECORDED'}
        if last:
            item.update({'last_done_at': last.recorded_at.isoformat(), 'last_odometer_km': km(last.odometer_km),
                         'next_due_odometer_km': km(last.next_due_odometer_km),
                         'genuine_calendar_due_date': last.genuine_calendar_due_date.isoformat() if last.genuine_calendar_due_date else None,
                         'status': 'NO_LIMIT_SET'})
            distance_date = None
            if last.next_due_odometer_km is not None and current_km is not None:
                remaining = last.next_due_odometer_km - current_km
                item['remaining_km'] = km(remaining)
                if remaining <= 0:
                    distance_date = today
                elif average:
                    distance_date = today + timedelta(days=math.ceil(remaining / average))
                if distance_date:
                    item['estimated_due_date'] = distance_date.isoformat()
                else:
                    item['estimate_note'] = 'Estimated date unavailable'
            calendar = last.genuine_calendar_due_date
            if calendar:
                item['days_to_calendar_due'] = (calendar - today).days
            limits = [(d, why) for d, why in ((distance_date, 'DISTANCE'), (calendar, 'DATE')) if d]
            remaining_value = None if item['remaining_km'] is None else Decimal(item['remaining_km'])
            if limits or remaining_value is not None:
                first = min(limits)[0] if limits else None
                item['due_by'] = min(limits)[1] if limits else 'DISTANCE'
                overdue = (remaining_value is not None and remaining_value < 0) or (calendar is not None and calendar < today)
                due = (remaining_value is not None and remaining_value == 0) or (first is not None and first <= today)
                item['status'] = 'OVERDUE' if overdue else 'DUE' if due else 'UPCOMING'
        items.append(item)
    order = {'OVERDUE': 0, 'DUE': 1, 'UPCOMING': 2, 'NO_LIMIT_SET': 3, 'NOT_RECORDED': 4}
    items.sort(key=lambda i: (order[i['status']], i['estimated_due_date'] or i['genuine_calendar_due_date'] or '9999'))
    return {'vehicle_id': str(vehicle.id), 'power_type': vehicle.power_type, 'current_odometer_km': km(current_km),
            'odometer_updated_at': vehicle.odometer_updated_at.isoformat() if vehicle.odometer_updated_at else None,
            'average_daily_km': None if average is None else format(average, '.1f'),
            'data_period': {'from': since.isoformat(), 'to': moment.isoformat(), 'days': ROLLING_DAYS, 'readings': len(points)},
            'estimate_note': None if average else 'Estimated date unavailable: not enough odometer readings in the last 30 days.',
            'items': items}
