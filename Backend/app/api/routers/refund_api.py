"""Refunds (matrix 68) and Passenger ticket cancellation, on the PRD `payments` table. See app/services/refunds.py.

    POST /bookings/{id}/ticket-cancellation   Passenger cancels a paid ticket -> seats freed, refund queued by schedule
    GET  /admin/refunds                       Admin: refunds waiting first, then recent ones
    POST /admin/refunds/{id}/decision         Admin approves (Sandbox: money back at once; PayHere: PROCESSING) or rejects
    POST /admin/refunds/{id}/complete         Admin records a PayHere refund done in the PayHere portal (or by bank transfer)
    POST /admin/refunds/{id}/payhere          Admin sends a refused PayHere refund through the Refund API again
    POST /payments/{id}/refunds               Admin refunds a payment directly (full or part), approved at once

Lock order as everywhere: scheduled_trips -> bookings -> scheduled_trip_seats (by id) -> payments.
"""
import copy
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, Request
from sqlalchemy import case, select
from sqlalchemy.orm import Session
from app.api.routers.api import current, require_role, touch
from app.api.routers.review_api import admin, locked_authority
from app.api.routers.ticket_booking_api import booking_out, lock_trip
from app.core.errors import ApiError
from app.dependencies.database import get_db
from app.models.hire_models import Booking, Notification, ScheduledTrip
from app.models.payment_models import Payment
from app.models.seat_models import BookingTraveller, ScheduledTripSeat
from app.schemas.payment_schemas import RefundCompletion, RefundDecision, RefundRequest, TicketCancellation
from app.services.payment_providers import money
from app.services import payhere_refunds
from app.services.refunds import POLICY, REFUNDS, already_refunded, cause_of, finish_refund, queue_refund, refund_percent

router = APIRouter(prefix='/api/v1', tags=['Refunds'])
STARTED = ('IN_PROGRESS', 'COMPLETED', 'CANCELLED', 'DISRUPTED')


def now():
    return datetime.now(timezone.utc)


def refund_out(row, booking=None, original=None):
    return {'id': str(row.id), 'payment_reference': row.payment_reference, 'booking_id': str(row.booking_id),
            'booking_reference': booking.booking_reference if booking else None,
            'original_payment_id': str(row.original_payment_id) if row.original_payment_id else None,
            'original_payment_reference': original.payment_reference if original else None,
            'original_amount': format(original.amount, '.2f') if original else None,
            'transaction_type': row.transaction_type, 'cause': cause_of(row), 'amount': format(row.amount, '.2f'),
            'currency': row.currency, 'provider_name': row.provider_name, 'payment_method': row.payment_method,
            'status': row.status, 'version': row.version, 'created_at': row.created_at.isoformat(),
            'refunded_at': row.refunded_at.isoformat() if row.refunded_at else None,
            'provider_reference': row.provider_reference, 'failure_code': row.failure_code, 'failure_message': row.failure_message,
            'cancellation': booking.cancellation_policy_snapshot if booking and booking.cancellation_policy_snapshot else None}


# --------------------------------------------------------------------------- Passenger cancels a paid ticket

@router.post('/bookings/{booking_id}/ticket-cancellation')
def cancel_ticket(booking_id: UUID, body: TicketCancellation, user=Depends(current), db: Session = Depends(get_db)):
    booking = db.get(Booking, booking_id)
    if not booking or booking.booking_type != 'TICKET_HIRE' or booking.passenger_user_id != user.id:
        raise ApiError(404, 'BOOKING_NOT_FOUND', 'Booking not found.')
    departure = lock_trip(db, booking.current_scheduled_trip_id)
    booking = db.scalar(select(Booking).where(Booking.id == booking.id).with_for_update().execution_options(populate_existing=True))
    if booking.status != 'CONFIRMED' or booking.payment_status_snapshot != 'PAID':
        raise ApiError(409, 'TICKET_NOT_CANCELLABLE', 'Only a paid, confirmed ticket can be cancelled here. '
                       'An unpaid seat hold is released from the hold page.')
    if body.expected_version is not None and booking.version != body.expected_version:
        raise ApiError(409, 'VERSION_CONFLICT', 'The booking changed. Refresh before cancelling.')
    moment = now()
    if departure.status in STARTED or departure.departure_at <= moment:
        raise ApiError(409, 'DEPARTURE_STARTED', 'This departure has already left; it can no longer be cancelled.')
    seats = db.scalars(select(ScheduledTripSeat).where(ScheduledTripSeat.booked_booking_id == booking.id,
                                                        ScheduledTripSeat.seat_status == 'BOOKED')
                       .order_by(ScheduledTripSeat.id).with_for_update().execution_options(populate_existing=True)).all()
    paid = db.scalar(select(Payment).where(Payment.booking_id == booking.id, Payment.transaction_type == 'PAYMENT',
                                           Payment.status == 'PAID').order_by(Payment.created_at.desc()).limit(1)
                     .with_for_update().execution_options(populate_existing=True))
    percent, hours = refund_percent(departure.departure_at, moment)
    for seat in seats:
        seat.seat_status = 'AVAILABLE'
        seat.booked_booking_id = None
        touch(seat); seat.updated_by = user.id
    for traveller in db.scalars(select(BookingTraveller).where(BookingTraveller.booking_id == booking.id,
                                                                BookingTraveller.traveller_status == 'ACTIVE')).all():
        traveller.traveller_status = 'CANCELLED'
        touch(traveller); traveller.updated_by = user.id
    booking.status = 'CANCELLED'
    booking.cancelled_by_user_id = user.id
    booking.cancelled_at = moment
    booking.cancellation_reason = body.reason
    booking.cancellation_policy_snapshot = {**copy.deepcopy(POLICY), 'hours_before_departure': hours,
                                            'refund_percent': percent, 'cancelled_at': moment.isoformat()}
    touch(booking); booking.updated_by = user.id
    refund = None
    if paid and percent:
        refund = queue_refund(db, paid, paid.amount * Decimal(percent) / 100, 'PASSENGER_CANCELLATION', user.id)
    for recipient, text in ((booking.passenger_user_id, f'Booking {booking.booking_reference} is cancelled. ' +
                             (f'A refund of {format(refund.amount, ".2f")} {refund.currency} is waiting for approval.' if refund
                              else 'No refund applies this close to departure.')),
                            (booking.owner_user_id, f'A Passenger cancelled booking {booking.booking_reference}; '
                             f'{len(seats)} seat(s) are available again.')):
        db.add(Notification(recipient_user_id=recipient, booking_id=booking.id, scheduled_trip_id=departure.id,
                            notification_type='REFUND' if recipient == booking.passenger_user_id else 'RECONFIRMATION',
                            channel='IN_APP', title='Booking cancelled', body=text, action_required=False,
                            action_payload={'booking_id': str(booking.id)}, status='QUEUED'))
    db.commit()
    return {**booking_out(db, booking), 'refund_percent': percent, 'hours_before_departure': hours,
            'refund': refund_out(refund, booking, paid) if refund else None}


# --------------------------------------------------------------------------- Admin: refunds to approve

@router.get('/admin/refunds')
def list_refunds(user=Depends(admin), db: Session = Depends(get_db)):
    waiting_first = case((Payment.status == 'PENDING', 0), (Payment.status == 'PROCESSING', 1), else_=2)
    rows = db.scalars(select(Payment).where(Payment.transaction_type.in_(REFUNDS))
                      .order_by(waiting_first, Payment.created_at.desc()).limit(200)).all()
    return {'items': [refund_out(r, db.get(Booking, r.booking_id), db.get(Payment, r.original_payment_id)) for r in rows],
            'waiting': sum(1 for r in rows if r.status in ('PENDING', 'PROCESSING'))}


def locked_refund(db, refund_id, expected_version):
    refund = db.scalar(select(Payment).where(Payment.id == refund_id, Payment.transaction_type.in_(REFUNDS)))
    if not refund:
        raise ApiError(404, 'REFUND_NOT_FOUND', 'Refund not found.')
    booking = db.scalar(select(Booking).where(Booking.id == refund.booking_id).with_for_update().execution_options(populate_existing=True))
    original = db.scalar(select(Payment).where(Payment.id == refund.original_payment_id).with_for_update().execution_options(populate_existing=True))
    refund = db.scalar(select(Payment).where(Payment.id == refund.id).with_for_update().execution_options(populate_existing=True))
    if refund.version != expected_version:
        raise ApiError(409, 'VERSION_CONFLICT', 'This refund changed. Reload before deciding.')
    return refund, original, booking


def approve(db, refund, original, booking, actor):
    if refund.provider_name == 'SANDBOX':
        finish_refund(db, refund, original, booking, actor, 'SBX-' + refund.payment_reference)
    else:
        refund.status = 'PROCESSING'  # PayHere: the Admin refunds in the PayHere portal, then records it as complete
        touch(refund); refund.updated_by = actor


def audit(request, db, user, refund, before, previous_status, reason):
    request.app.state.audit.commit(db, actor=user.id, target={'resource': 'payments', 'id': str(refund.id)},
                                   previous_status=previous_status, new_status=refund.status, previous_version=before,
                                   new_version=refund.version, full_reason=reason, previous_decision_evidence=None,
                                   trace_id=request.state.trace_id)


@router.post('/admin/refunds/{refund_id}/decision')
def decide_refund(refund_id: UUID, body: RefundDecision, request: Request, user=Depends(admin), db: Session = Depends(get_db)):
    if body.decision == 'REJECT' and not body.reason:
        raise ApiError(422, 'REASON_REQUIRED', 'Give the reason for rejecting this refund.', [{'field': 'reason', 'message': 'Required.'}])
    with request.app.state.audit.coordinated():
        locked_authority(db, request, user, user.id)
        refund, original, booking = locked_refund(db, refund_id, body.expected_version)
        if refund.status != 'PENDING':
            raise ApiError(409, 'REFUND_ALREADY_DECIDED', 'This refund was already decided.')
        before, previous = refund.version, refund.status
        if body.decision == 'APPROVE':
            approve(db, refund, original, booking, user.id)
        else:
            refund.status = 'FAILED'
            refund.failure_code = 'REFUND_REJECTED'
            refund.failure_message = 'Rejected by Admin.'
            touch(refund); refund.updated_by = user.id
        audit(request, db, user, refund, before, previous, body.reason or 'Refund approved by Admin.')
    return after_approval(request, db, user, refund, booking, original)


def after_approval(request, db, user, refund, booking, original):
    """Once the approval is committed, a PayHere refund is sent through the Refund API when it is configured."""
    if refund.status == 'PROCESSING' and refund.provider_name == 'PAYHERE':
        payhere_refunds.push(request.app.state.sessions, refund.id, user.id)
        for row in (refund, original, booking):
            db.refresh(row)
    return refund_out(refund, booking, original)


@router.post('/admin/refunds/{refund_id}/payhere')
def retry_payhere(refund_id: UUID, request: Request, user=Depends(admin), db: Session = Depends(get_db)):
    """Send an approved PayHere refund again after PayHere refused it (PAYHERE_REFUND_FAILED). A refund already sent
    and still waiting for PayHere's answer (PAYHERE_REQUESTED) is never sent twice: check the portal and record it."""
    refund = db.get(Payment, refund_id)
    if not refund or refund.transaction_type not in REFUNDS:
        raise ApiError(404, 'REFUND_NOT_FOUND', 'Refund not found.')
    if not payhere_refunds.configured():
        raise ApiError(409, 'PAYHERE_REFUND_API_OFF', 'The PayHere Refund API is not set up (PAYHERE_APP_ID, PAYHERE_APP_SECRET).')
    if refund.status != 'PROCESSING' or refund.provider_name != 'PAYHERE' or refund.failure_code not in (None, 'PAYHERE_REFUND_FAILED'):
        raise ApiError(409, 'REFUND_NOT_RETRYABLE', 'Only an approved PayHere card refund that PayHere refused can be sent again.')
    db.rollback()
    if refund.failure_code == 'PAYHERE_REFUND_FAILED':
        with request.app.state.sessions() as fresh:
            row = fresh.scalar(select(Payment).where(Payment.id == refund_id).with_for_update())
            if row.failure_code == 'PAYHERE_REFUND_FAILED':
                row.failure_code = None
                fresh.commit()
    payhere_refunds.push(request.app.state.sessions, refund_id, user.id)
    db.expire_all()
    refund = db.get(Payment, refund_id)
    return refund_out(refund, db.get(Booking, refund.booking_id), db.get(Payment, refund.original_payment_id))


@router.post('/admin/refunds/{refund_id}/complete')
def complete_refund(refund_id: UUID, body: RefundCompletion, request: Request, user=Depends(admin), db: Session = Depends(get_db)):
    with request.app.state.audit.coordinated():
        locked_authority(db, request, user, user.id)
        refund, original, booking = locked_refund(db, refund_id, body.expected_version)
        if refund.status != 'PROCESSING':
            raise ApiError(409, 'REFUND_NOT_PROCESSING', 'Only an approved refund that is being processed can be completed.')
        before = refund.version
        finish_refund(db, refund, original, booking, user.id, body.provider_reference)
        audit(request, db, user, refund, before, 'PROCESSING', 'Refund completed in the provider portal.')
    return refund_out(refund, booking, original)


@router.post('/payments/{payment_id}/refunds', status_code=201)
def admin_refund(payment_id: UUID, body: RefundRequest, request: Request, user=Depends(admin), db: Session = Depends(get_db)):
    if body.full == (body.amount is not None):
        raise ApiError(422, 'VALIDATION_ERROR', 'Choose a full refund or give an amount, not both.',
                       [{'field': 'amount', 'message': 'Leave empty for a full refund.'}])
    with request.app.state.audit.coordinated():
        locked_authority(db, request, user, user.id)
        paid = db.get(Payment, payment_id)
        if not paid or paid.transaction_type != 'PAYMENT':
            raise ApiError(404, 'PAYMENT_NOT_FOUND', 'Payment not found.')
        booking = db.scalar(select(Booking).where(Booking.id == paid.booking_id).with_for_update().execution_options(populate_existing=True))
        paid = db.scalar(select(Payment).where(Payment.id == paid.id).with_for_update().execution_options(populate_existing=True))
        replay = db.scalar(select(Payment).where(Payment.idempotency_key == f'refund:ADMIN:{paid.id}:{body.idempotency_key}'))
        if replay:
            return refund_out(replay, booking, paid)  # same request again: no second refund
        if paid.status not in ('PAID', 'PARTIALLY_REFUNDED'):
            raise ApiError(409, 'PAYMENT_NOT_REFUNDABLE', 'Only a paid payment can be refunded.')
        left = paid.amount - already_refunded(db, paid)
        amount = left if body.full else money(body.amount)
        if amount <= 0 or amount > left:
            raise ApiError(422, 'REFUND_AMOUNT_INVALID', f'At most {format(left, ".2f")} {paid.currency} can still be refunded.',
                           [{'field': 'amount', 'message': format(left, '.2f')}])
        refund = queue_refund(db, paid, amount, 'ADMIN', user.id, unique=body.idempotency_key)
        before = refund.version
        approve(db, refund, paid, booking, user.id)
        audit(request, db, user, refund, before, 'PENDING', body.reason)
    return after_approval(request, db, user, refund, booking, paid)
