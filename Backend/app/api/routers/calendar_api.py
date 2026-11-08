"""Owner dated restrictions. No booking/assignment/payment mutation authority."""
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, Request
from pydantic import AwareDatetime, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.routers.api import current, touch
from app.dependencies.database import get_db
from app.core.errors import ApiError
from app.api.routers.rate_api import owned
from app.schemas.rate_schemas import RateModel
from app.schemas.hire_schemas import Version
from app.api.routers.review_api import admin, query_values
from app.models.review_models import Vehicle
from app.models import User, UserRole
from app.models.hire_models import VehicleRecord, Notification
from app.services.availability import KINDS, WITHDRAWN, occupancy, protected, references

router = APIRouter(prefix='/api/v1', tags=['Vehicle availability'])


class Reason(RateModel):
    reason: str = Field(min_length=1, max_length=2000)

    @field_validator('reason')
    @classmethod
    def nonblank(cls, value):
        if not value.strip(): raise ValueError('Enter a reason.')
        return value.strip()


class Block(Reason):
    kind: Literal['PERSONAL', 'MAINTENANCE', 'EMERGENCY']
    start_at: AwareDatetime
    end_at: AwareDatetime

    @model_validator(mode='after')
    def interval(self):
        if self.end_at <= self.start_at: raise ValueError('End must be after start.')
        return self


class EditBlock(Block, Version): pass
class Withdraw(Reason, Version): pass


def summary(row):
    state = row.approval_status or 'UNCLASSIFIED'
    return {'id': str(row.id), 'vehicle_id': str(row.vehicle_id), 'version': row.version,
            'kind': state.removeprefix('WITHDRAWN_'), 'withdrawn': state in WITHDRAWN,
            'start_at': row.start_at.isoformat(), 'end_at': row.end_at.isoformat(), 'reason': row.notes,
            'status': state, 'recorded_by': str(row.recorded_by_user_id),
            'updated_by': str(row.updated_by), 'updated_at': row.updated_at.isoformat()}


def date_range(request):
    params = query_values(request, {'start_at', 'end_at'})
    try:
        start, end = [datetime.fromisoformat(params[k].replace('Z', '+00:00')) for k in ('start_at', 'end_at')]
        if start.utcoffset() is None or end.utcoffset() is None or not timedelta(0) < end-start <= timedelta(days=93): raise ValueError()
    except (KeyError, ValueError, TypeError):
        raise ApiError(422, 'VALIDATION_ERROR', 'Choose offset-aware start/end times spanning at most 93 days.') from None
    return start, end


def calendar(vehicle, request, user, db, reviewer=False):
    start, end = date_range(request)
    events = occupancy(db, vehicle.id, start, end)
    for e in events:
        e['editable'] = not reviewer and e['source'] == 'BLOCK' and e['recorded_by'] == str(user.id) and e['status'] in KINDS
        if e['source'] == 'BLOCK':
            e['kind'] = (e['status'] or 'UNCLASSIFIED').removeprefix('WITHDRAWN_')
            # Query the entire block, not just the visible range, for complete support references.
            e['affected_commitments'] = references(protected(occupancy(db, vehicle.id, e['start_at'], e['end_at']))) if e['status'] == 'EMERGENCY' else []
        e.pop('recorded_by', None)
    return {'complete': True, 'checked_at': datetime.now(timezone.utc), 'time_zone': 'Asia/Colombo',
            'availability_status': vehicle.availability_status, 'verification_status': vehicle.verification_status,
            'events': events}


@router.get('/vehicles/{vehicle_id}/calendar')
def owner_calendar(vehicle_id: UUID, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    return calendar(owned(db, request, user, vehicle_id), request, user, db)


@router.get('/admin/vehicles/{vehicle_id}/calendar')
def admin_calendar(vehicle_id: UUID, request: Request, user=Depends(admin), db: Session = Depends(get_db)):
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle: raise ApiError(404, 'VEHICLE_NOT_FOUND', 'Vehicle not found.')
    return calendar(vehicle, request, user, db, True)


def support(db, row, affected):
    admins = db.scalars(select(User.id).join(UserRole, UserRole.user_id == User.id).where(
        UserRole.role_code == 'ADMIN', UserRole.approval_status == 'APPROVED', User.account_status.in_(('ACTIVE', 'PENDING_VERIFICATION')))).all()
    for uid in admins:
        db.add(Notification(recipient_user_id=uid, notification_type='ADMIN_ACTION', channel='IN_APP',
            title='Emergency vehicle maintenance', body=f'Maintenance interval: {row.start_at.isoformat()} to {row.end_at.isoformat()}. Review affected commitments and arrange fulfilment/support. No booking, reservation or payment was changed.',
            action_required=True, action_payload={'vehicle_id': str(row.vehicle_id), 'block_id': str(row.id),
                'affected_commitments': [{'source': e['source'], 'id': e['id']} for e in affected]}, status='QUEUED'))


def mutate(vehicle_id, body, request, user, db, block_id=None, withdraw=False):
    with request.app.state.audit.coordinated():
        owned(db, request, user, vehicle_id, lock=True)
        row = None
        before = None
        if block_id:
            row = db.scalar(select(VehicleRecord).where(VehicleRecord.id == block_id, VehicleRecord.vehicle_id == vehicle_id,
                VehicleRecord.record_type == 'AVAILABILITY_BLOCK', VehicleRecord.recorded_by_user_id == user.id)
                .with_for_update().execution_options(populate_existing=True))
            if not row: raise ApiError(404, 'BLOCK_NOT_FOUND', 'Block not found.')
            if row.version != body.expected_version: raise ApiError(409, 'VERSION_CONFLICT', 'Block changed. Refresh the calendar before retrying.')
            if row.approval_status in WITHDRAWN: raise ApiError(409, 'BLOCK_WITHDRAWN', 'This block was already withdrawn. Create a new block if needed.')
            if row.approval_status not in KINDS: raise ApiError(409, 'BLOCK_CLASSIFICATION_REQUIRED', 'This retained block needs operator classification before editing.')
            before = summary(row)
        start, end = (row.start_at, row.end_at) if withdraw else (body.start_at, body.end_at)
        affected = protected(occupancy(db, vehicle_id, start, end))
        if not withdraw and body.kind != 'EMERGENCY' and affected:
            raise ApiError(409, 'VEHICLE_COMMITMENTS_REQUIRE_RESOLUTION', 'Resolve overlapping commitments before saving this ordinary block. Emergency maintenance retains commitments for Admin support.',
                [{'field': 'interval', 'message': e['source'] + ' ' + e['reference']} for e in affected[:20]])
        if row:
            touch(row)
        else:
            row = VehicleRecord(vehicle_id=vehicle_id, recorded_by_user_id=user.id, recorded_at=datetime.now(timezone.utc),
                record_type='AVAILABILITY_BLOCK', created_by=user.id)
            db.add(row)
        row.updated_by = user.id
        if withdraw: row.approval_status = 'WITHDRAWN_' + row.approval_status
        else:
            row.start_at, row.end_at, row.notes, row.approval_status = body.start_at, body.end_at, body.reason, body.kind
        db.flush()
        if not withdraw and row.approval_status == 'EMERGENCY' and affected: support(db, row, affected)
        after = summary(row)
        request.app.state.audit.commit(db, actor=user.id, target={'resource': 'vehicle_records', 'id': str(row.id), 'purpose': 'AVAILABILITY_BLOCK'},
            previous_status=before['status'] if before else None, new_status=row.approval_status,
            previous_version=before['version'] if before else 0, new_version=row.version, full_reason=body.reason,
            previous_decision_evidence={'before': before, 'after': after, 'action': 'WITHDRAW' if withdraw else 'EDIT' if before else 'CREATE'},
            trace_id=request.state.trace_id)
    return {**after, 'affected_commitments': references(affected)}


@router.post('/vehicles/{vehicle_id}/availability-blocks', status_code=201)
def create_block(vehicle_id: UUID, body: Block, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    return mutate(vehicle_id, body, request, user, db)


@router.patch('/vehicles/{vehicle_id}/availability-blocks/{block_id}')
def edit_block(vehicle_id: UUID, block_id: UUID, body: EditBlock, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    return mutate(vehicle_id, body, request, user, db, block_id)


@router.post('/vehicles/{vehicle_id}/availability-blocks/{block_id}/withdraw')
def withdraw_block(vehicle_id: UUID, block_id: UUID, body: Withdraw, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    return mutate(vehicle_id, body, request, user, db, block_id, True)
