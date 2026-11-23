"""Report the waiting charge of a finished Book now return trip.
 * Only the Passenger of the booking can report, only after the trip is COMPLETED and only when a waiting charge was added; once per trip, within 7 days.
   The reason is optional (300 characters). Reporting never blocks the payment or anything else: the charge stands until the Owner answers.
 * The Owner of the vehicle keeps the charge, or lowers it (never raises it). A lowered charge not yet paid simply changes the total; when the booking
   is already paid, the difference becomes `refund_due` and a REFUND support ticket is opened for the Admins, who pay it back with the refund tools.
 * If the Owner never answers, the charge stays and the Passenger can ask the Support chat."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID
import copy
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.api.routers.api import current
from app.core.errors import ApiError
from app.dependencies.database import get_db
from app.models.charge_report_models import WaitingChargeReport
from app.models.hire_models import Booking, Trip
from app.models.support_models import SupportMessage, SupportTicket
from app.services.hire_services import notify

router = APIRouter(prefix='/api/v1', tags=['Waiting charge reports'])
REPORT_DAYS = 7


class NewReport(BaseModel):
    reason: str | None = Field(default=None, max_length=300)


class Answer(BaseModel):
    keep: bool
    new_charge: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    note: str | None = Field(default=None, max_length=300)


def report_out(row):
    return {'id': str(row.id), 'created_at': row.created_at.isoformat(), 'reason': row.reason, 'charge': format(row.charge, '.2f'), 'status': row.status,
            'new_charge': format(row.new_charge, '.2f') if row.new_charge is not None else None,
            'refund_due': format(row.refund_due, '.2f') if row.refund_due is not None else None,
            'owner_note': row.owner_note, 'resolved_at': row.resolved_at.isoformat() if row.resolved_at else None}


def waiting_charge(booking):
    try:
        return Decimal(str(((booking.price_snapshot or {}).get('waiting') or {}).get('charge') or '0'))
    except Exception:
        return Decimal('0')


def trip_and_booking(db, trip_id):
    trip = db.get(Trip, trip_id)
    booking = db.get(Booking, trip.booking_id) if trip and trip.booking_id else None
    if not trip or not booking:
        raise ApiError(404, 'TRIP_NOT_FOUND', 'This trip was not found.')
    return trip, booking


def owner_of(trip, booking):
    return trip.operating_owner_user_id or booking.owner_user_id


@router.get('/trips/{trip_id}/charge-report')
def charge_report(trip_id: UUID, user=Depends(current), db: Session = Depends(get_db)):
    trip, booking = trip_and_booking(db, trip_id)
    owner = owner_of(trip, booking)
    if user.id not in (booking.passenger_user_id, owner):
        raise ApiError(404, 'TRIP_NOT_FOUND', 'This trip was not found.')
    row = db.scalar(select(WaitingChargeReport).where(WaitingChargeReport.trip_id == trip.id))
    charge = waiting_charge(booking)
    ended = trip.actual_end_at or datetime.now(timezone.utc)
    can = bool(user.id == booking.passenger_user_id and not row and trip.status == 'COMPLETED' and charge > 0
               and datetime.now(timezone.utc) < ended + timedelta(days=REPORT_DAYS))
    return {'report': report_out(row) if row else None, 'can_report': can, 'charge': format(charge, '.2f') if charge > 0 else None,
            'is_owner': user.id == owner, 'paid': booking.payment_status_snapshot == 'PAID'}


@router.post('/trips/{trip_id}/charge-report', status_code=201)
def report_charge(trip_id: UUID, body: NewReport, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    request.app.state.store.rate(f'charge-report:{user.id}', 20, 3600)
    trip, booking = trip_and_booking(db, trip_id)
    if booking.passenger_user_id != user.id:
        raise ApiError(404, 'TRIP_NOT_FOUND', 'This trip was not found.')
    charge = waiting_charge(booking)
    if trip.status != 'COMPLETED' or charge <= 0:
        raise ApiError(409, 'NO_WAITING_CHARGE', 'This trip has no waiting charge to report.')
    if datetime.now(timezone.utc) >= (trip.actual_end_at or datetime.now(timezone.utc)) + timedelta(days=REPORT_DAYS):
        raise ApiError(409, 'REPORT_TOO_LATE', f'A waiting charge can be reported for {REPORT_DAYS} days after the trip.')
    row = WaitingChargeReport(trip_id=trip.id, booking_id=booking.id, passenger_user_id=user.id, owner_user_id=owner_of(trip, booking),
                              reason=(body.reason or '').strip() or None, charge=charge)
    db.add(row)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ApiError(409, 'REPORT_EXISTS', 'You have already reported the waiting charge of this trip.')
    notify(db, booking, 'Waiting charge reported', 'The Passenger asked the Owner to look at the waiting charge of this trip. Payment is not held up.', trip.driver_user_id)
    db.commit()
    return report_out(row)


@router.post('/charge-reports/{report_id}/answer')
def answer_report(report_id: UUID, body: Answer, user=Depends(current), db: Session = Depends(get_db)):
    row = db.scalar(select(WaitingChargeReport).where(WaitingChargeReport.id == report_id).with_for_update())
    if not row or row.owner_user_id != user.id:
        raise ApiError(404, 'REPORT_NOT_FOUND', 'This report was not found.')
    if row.status != 'OPEN':
        raise ApiError(409, 'REPORT_ANSWERED', 'This report was already answered.')
    booking = db.scalar(select(Booking).where(Booking.id == row.booking_id).with_for_update())
    trip = db.get(Trip, row.trip_id)
    note = (body.note or '').strip() or None
    now = datetime.now(timezone.utc)
    if body.keep:
        row.status, row.owner_note, row.resolved_at = 'KEPT', note, now
        notify(db, booking, 'Waiting charge kept', 'The Owner checked the waiting charge and kept it.' + (f' Note: {note}' if note else ''), trip.driver_user_id)
    else:
        if body.new_charge is None or body.new_charge >= row.charge:
            raise ApiError(422, 'VALIDATION_ERROR', 'The new waiting charge must be lower than the charge now.', [{'field': 'new_charge', 'message': 'Must be lower than the charge now.'}])
        difference = row.charge - body.new_charge
        row.status, row.new_charge, row.owner_note, row.resolved_at = 'REDUCED', body.new_charge, note, now
        if booking.payment_status_snapshot == 'PAID':
            row.refund_due = difference
            ticket = SupportTicket(user_id=row.passenger_user_id, workspace_role='PASSENGER', category='REFUND', booking_id=booking.id, status='OPEN',
                                   subject=f'Refund of LKR {difference:.2f}: waiting charge lowered', admin_unread=True, user_unread=False)
            db.add(ticket); db.flush()
            db.add(SupportMessage(ticket_id=ticket.id, sender_user_id=row.passenger_user_id, from_admin=False,
                                  body=f'[Automatic message] The Owner lowered the waiting charge of booking {booking.booking_reference} from LKR {row.charge:.2f} to LKR {body.new_charge:.2f}. '
                                       f'The booking was already paid, so LKR {difference:.2f} is to be refunded to the Passenger.'))
        else:
            booking.total_amount = booking.total_amount - difference
            snapshot = copy.deepcopy(booking.price_snapshot)
            snapshot['waiting'] = {**snapshot.get('waiting', {}), 'charge': format(body.new_charge, '.2f'), 'lowered_from': format(row.charge, '.2f')}
            booking.price_snapshot = snapshot
        notify(db, booking, 'Waiting charge lowered',
               f'The Owner lowered the waiting charge from LKR {row.charge:.2f} to LKR {body.new_charge:.2f}.'
               + (' The difference will be refunded.' if row.refund_due else '') + (f' Note: {note}' if note else ''), trip.driver_user_id)
    db.commit()
    return report_out(row)
