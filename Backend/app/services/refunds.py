"""Refunds on the PRD `payments` table: a refund is a new row (FULL_REFUND / PARTIAL_REFUND) linked to the paid row
through original_payment_id. Owner decisions (11 Nov 2026):

- A Passenger who cancels a paid ticket gets: more than 72 h before departure 100%, 24-72 h 50%, under 24 h or no-show 0%
  (the PRD's suggested schedule, CF08-09).
- The system works out the amount and queues the refund; an Admin approves it (or rejects it with a reason).
- Money that arrives after a seat hold ended is refunded in full.

A refund row is PENDING while it waits for the Admin, PROCESSING while the provider is doing it (PayHere is done by the
Admin in the PayHere portal until its Refund API is connected), PAID when the money has gone back, FAILED if rejected.
Why it exists is kept in its internal idempotency key: refund:<CAUSE>:<payment id>[:<unique>].
"""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import func, select
from app.api.routers.api import touch
from app.models.hire_models import Notification
from app.models.payment_models import Payment
from app.services.payment_providers import money

REFUNDS = ('FULL_REFUND', 'PARTIAL_REFUND')
POLICY = {'policy': 'TICKET_PASSENGER_CANCELLATION_2026_11',
          'bands': [{'more_than_hours': 72, 'refund_percent': 100}, {'from_hours': 24, 'to_hours': 72, 'refund_percent': 50},
                    {'less_than_hours': 24, 'refund_percent': 0}]}


def refund_percent(departure_at, moment):
    hours = (departure_at - moment).total_seconds() / 3600
    return (100 if hours > 72 else 50 if hours >= 24 else 0), round(hours, 2)


def already_refunded(db, payment):
    """Money already returned or promised against this payment (pending, processing or done)."""
    return db.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(
        Payment.original_payment_id == payment.id, Payment.transaction_type.in_(REFUNDS),
        Payment.status.in_(('PENDING', 'PROCESSING', 'PAID')))) or Decimal('0')


def queue_refund(db, payment, amount, cause, actor, unique=None):
    """Create a PENDING refund row for the Admin to approve. Returns the row, or None when nothing is refundable."""
    amount = money(amount)
    left = payment.amount - already_refunded(db, payment)
    amount = min(amount, left)
    if amount <= 0:
        return None
    row = Payment(payment_reference='RFD-' + uuid4().hex[:20].upper(), booking_id=payment.booking_id,
                  original_payment_id=payment.id, payee_owner_user_id=payment.payee_owner_user_id,
                  transaction_type='FULL_REFUND' if amount == payment.amount else 'PARTIAL_REFUND',
                  payment_method=payment.payment_method, provider_name=payment.provider_name,
                  idempotency_key=f'refund:{cause}:{payment.id}' + (f':{unique}' if unique else ''),
                  amount=amount, currency=payment.currency, status='PENDING', created_by=actor, updated_by=actor)
    db.add(row)
    db.flush()
    return row


def cause_of(refund):
    parts = (refund.idempotency_key or '').split(':')
    return parts[1] if len(parts) > 2 and parts[0] == 'refund' else 'ADMIN'


def finish_refund(db, refund, original, booking, actor, provider_reference):
    """The money has gone back: close the refund row and mark the original payment refunded (fully or partly)."""
    moment = datetime.now(timezone.utc)
    refund.status = 'PAID'
    refund.provider_reference = provider_reference
    refund.captured_at = moment
    refund.refunded_at = moment
    touch(refund); refund.updated_by = actor
    done = db.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(
        Payment.original_payment_id == original.id, Payment.transaction_type.in_(REFUNDS), Payment.status == 'PAID')) or Decimal('0')
    original.status = 'REFUNDED' if done >= original.amount else 'PARTIALLY_REFUNDED'
    original.refunded_at = moment
    touch(original); original.updated_by = actor
    # The Owner share moved to another Owner follows the captured payment (it must not be paid out).
    for share in db.scalars(select(Payment).where(Payment.original_payment_id == original.id, Payment.transaction_type == 'REALLOCATION',
                                                  Payment.status.in_(('PAID', 'PARTIALLY_REFUNDED')))).all():
        share.status = original.status
        share.refunded_at = moment
        touch(share); share.updated_by = actor
    booking.payment_status_snapshot = original.status
    touch(booking); booking.updated_by = actor
    db.add(Notification(recipient_user_id=booking.passenger_user_id, booking_id=booking.id, notification_type='REFUND',
                        channel='IN_APP', title='Refund sent',
                        body=f'{format(refund.amount, ".2f")} {refund.currency} was refunded for booking {booking.booking_reference}.',
                        action_required=False, action_payload={'booking_id': str(booking.id), 'refund_id': str(refund.id)},
                        status='QUEUED'))
