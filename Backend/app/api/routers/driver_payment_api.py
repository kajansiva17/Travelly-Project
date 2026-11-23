"""Owner pays Driver, for one completed trip.

 * The Owner records the payment: an amount and how it was paid.
 * ONLINE (a bank or wallet transfer made outside Travelly, with its reference): recorded and final at once. Travelly moves no money.
 * CASH: waits until the Driver confirms they received it. The Driver can instead say it was not received; the Owner may then record it again.
 * The Owner and the Driver each see it in their own list and report. The Passenger's payment to the Owner is separate (payments)."""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.api.routers.api import current, require_role
from app.core.errors import ApiError
from app.dependencies.database import get_db
from app.models import User
from app.models.driver_payment_models import DriverPayment
from app.models.hire_models import Notification, Trip

router = APIRouter(prefix='/api/v1', tags=['Driver payments'])
ZERO = Decimal('0')


class Record(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    method: Literal['CASH', 'ONLINE']
    reference: str | None = Field(default=None, max_length=80)

    @field_validator('reference')
    @classmethod
    def tidy(cls, value):
        value = (value or '').strip()
        return value or None


class Decline(BaseModel):
    note: str = Field(min_length=1, max_length=300)

    @field_validator('note')
    @classmethod
    def tidy(cls, value):
        value = value.strip()
        if not value:
            raise ValueError('A note is required.')
        return value


def money(value):
    return format((value or ZERO).quantize(Decimal('0.01')), '.2f')


def tell(db, user_id, trip, title, body, payment):
    db.add(Notification(recipient_user_id=user_id, booking_id=trip.booking_id, trip_id=trip.id, notification_type='PAYMENT', channel='IN_APP',
                        title=title, body=body, action_required=False,
                        action_payload={'kind': 'DRIVER_PAYMENT', 'payment_id': str(payment.id)}, status='QUEUED'))


def view(row, trip, other):
    return {'id': str(row.id), 'trip_id': str(row.trip_id), 'trip_reference': trip.trip_reference,
            'trip_date': (trip.actual_end_at or trip.scheduled_end_at).isoformat() if (trip.actual_end_at or trip.scheduled_end_at) else None,
            'amount': money(row.amount), 'currency': row.currency, 'method': row.method, 'reference': row.reference,
            'status': row.status, 'recorded_at': row.owner_recorded_at.isoformat(),
            'driver_confirmed_at': row.driver_confirmed_at.isoformat() if row.driver_confirmed_at else None,
            'driver_note': row.driver_note,
            'other_party': {'reference': other.public_user_reference, 'name': other.display_name or other.full_name} if other else None}


def totals(rows):
    confirmed = sum((r.amount for r in rows if r.status == 'CONFIRMED'), ZERO)
    waiting = sum((r.amount for r in rows if r.status == 'PENDING_DRIVER'), ZERO)
    return {'confirmed_total': money(confirmed), 'waiting_total': money(waiting),
            'confirmed_count': sum(1 for r in rows if r.status == 'CONFIRMED'), 'waiting_count': sum(1 for r in rows if r.status == 'PENDING_DRIVER')}


@router.post('/trips/{trip_id}/driver-payment', status_code=201)
def record_payment(trip_id: UUID, body: Record, user=Depends(current), db: Session = Depends(get_db)):
    """Owner: record what you paid the Driver of this completed trip."""
    require_role(db, user, 'OWNER')
    if body.method == 'ONLINE' and not body.reference:
        raise ApiError(422, 'VALIDATION_ERROR', 'Enter the transfer reference for an online payment.',
                       [{'field': 'reference', 'code': 'required', 'message': 'Enter the transfer reference.'}])
    trip = db.scalar(select(Trip).where(Trip.id == trip_id).with_for_update())
    if not trip or trip.operating_owner_user_id != user.id:
        raise ApiError(404, 'TRIP_NOT_FOUND', 'This trip was not found.')
    if not trip.driver_user_id or trip.driver_user_id == user.id:
        raise ApiError(409, 'NO_SEPARATE_DRIVER', 'This trip had no separate Driver to pay.')
    if trip.status != 'COMPLETED':
        raise ApiError(409, 'TRIP_NOT_COMPLETED', 'You can record the Driver payment after the trip is completed.')
    live = db.scalar(select(DriverPayment.id).where(DriverPayment.trip_id == trip.id, DriverPayment.status != 'DECLINED'))
    if live:
        raise ApiError(409, 'DRIVER_PAYMENT_EXISTS', 'A payment for this trip is already recorded.')
    now = datetime.now(timezone.utc)
    online = body.method == 'ONLINE'
    row = DriverPayment(trip_id=trip.id, owner_user_id=user.id, driver_user_id=trip.driver_user_id, amount=body.amount, method=body.method,
                        reference=body.reference if online else (body.reference or None), status='CONFIRMED' if online else 'PENDING_DRIVER',
                        owner_recorded_at=now)
    db.add(row)
    db.flush()
    owner_name = user.display_name or user.public_user_reference
    if online:
        tell(db, trip.driver_user_id, trip, 'Payment recorded', f'{owner_name} recorded an online payment of {money(row.amount)} {row.currency} for trip {trip.trip_reference}.', row)
    else:
        tell(db, trip.driver_user_id, trip, 'Confirm the cash payment', f'{owner_name} says they paid you {money(row.amount)} {row.currency} in cash for trip {trip.trip_reference}. Please confirm.', row)
    db.commit()
    driver = db.get(User, row.driver_user_id)
    return view(row, trip, driver)


@router.post('/driver-payments/{payment_id}/confirm')
def confirm_payment(payment_id: UUID, user=Depends(current), db: Session = Depends(get_db)):
    """Driver: I received this cash."""
    require_role(db, user, 'DRIVER')
    row = db.scalar(select(DriverPayment).where(DriverPayment.id == payment_id, DriverPayment.driver_user_id == user.id).with_for_update())
    if not row:
        raise ApiError(404, 'PAYMENT_NOT_FOUND', 'This payment was not found.')
    if row.status != 'PENDING_DRIVER':
        raise ApiError(409, 'PAYMENT_NOT_WAITING', 'This payment is not waiting for your confirmation.')
    now = datetime.now(timezone.utc)
    row.status, row.driver_confirmed_at, row.updated_at = 'CONFIRMED', now, now
    trip = db.get(Trip, row.trip_id)
    tell(db, row.owner_user_id, trip, 'Driver confirmed the cash payment', f'{user.display_name or user.public_user_reference} confirmed {money(row.amount)} {row.currency} for trip {trip.trip_reference}.', row)
    db.commit()
    return view(row, trip, db.get(User, row.owner_user_id))


@router.post('/driver-payments/{payment_id}/decline')
def decline_payment(payment_id: UUID, body: Decline, user=Depends(current), db: Session = Depends(get_db)):
    """Driver: I did not receive this cash."""
    require_role(db, user, 'DRIVER')
    row = db.scalar(select(DriverPayment).where(DriverPayment.id == payment_id, DriverPayment.driver_user_id == user.id).with_for_update())
    if not row:
        raise ApiError(404, 'PAYMENT_NOT_FOUND', 'This payment was not found.')
    if row.status != 'PENDING_DRIVER':
        raise ApiError(409, 'PAYMENT_NOT_WAITING', 'This payment is not waiting for your confirmation.')
    row.status, row.driver_note, row.updated_at = 'DECLINED', body.note, datetime.now(timezone.utc)
    trip = db.get(Trip, row.trip_id)
    tell(db, row.owner_user_id, trip, 'Driver did not confirm the cash payment', f'{user.display_name or user.public_user_reference} says the cash for trip {trip.trip_reference} was not received: {body.note}', row)
    db.commit()
    return view(row, trip, db.get(User, row.owner_user_id))


@router.get('/trips/{trip_id}/driver-payment')
def trip_payment(trip_id: UUID, user=Depends(current), db: Session = Depends(get_db)):
    """The Owner or the Driver of the trip: the live payment for it, or null."""
    trip = db.get(Trip, trip_id)
    if not trip or user.id not in (trip.operating_owner_user_id, trip.driver_user_id):
        raise ApiError(404, 'TRIP_NOT_FOUND', 'This trip was not found.')
    row = db.scalar(select(DriverPayment).where(DriverPayment.trip_id == trip.id).order_by(DriverPayment.created_at.desc()))
    if not row:
        return {'payment': None, 'can_record': bool(user.id == trip.operating_owner_user_id and trip.driver_user_id and trip.driver_user_id != user.id and trip.status == 'COMPLETED')}
    other = db.get(User, row.driver_user_id if user.id == row.owner_user_id else row.owner_user_id)
    can = bool(user.id == trip.operating_owner_user_id and row.status == 'DECLINED')
    return {'payment': view(row, trip, other), 'can_record': can}


@router.get('/owners/me/driver-payments')
def owner_payments(user=Depends(current), db: Session = Depends(get_db)):
    require_role(db, user, 'OWNER')
    rows = db.execute(select(DriverPayment, Trip).join(Trip, Trip.id == DriverPayment.trip_id)
                      .where(DriverPayment.owner_user_id == user.id, DriverPayment.status != 'DECLINED')
                      .order_by(DriverPayment.created_at.desc()).limit(200)).all()
    people = {u.id: u for u in db.scalars(select(User).where(User.id.in_({p.driver_user_id for p, _ in rows}))).all()} if rows else {}
    return {'items': [view(p, t, people.get(p.driver_user_id)) for p, t in rows], 'totals': totals([p for p, _ in rows])}


@router.get('/drivers/me/payments')
def driver_payments(user=Depends(current), db: Session = Depends(get_db)):
    require_role(db, user, 'DRIVER')
    rows = db.execute(select(DriverPayment, Trip).join(Trip, Trip.id == DriverPayment.trip_id)
                      .where(DriverPayment.driver_user_id == user.id, DriverPayment.status != 'DECLINED')
                      .order_by(DriverPayment.created_at.desc()).limit(200)).all()
    people = {u.id: u for u in db.scalars(select(User).where(User.id.in_({p.owner_user_id for p, _ in rows}))).all()} if rows else {}
    return {'items': [view(p, t, people.get(p.owner_user_id)) for p, t in rows], 'totals': totals([p for p, _ in rows])}
