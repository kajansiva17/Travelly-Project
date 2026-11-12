"""Admin payments overview and Owner settlement, on the PRD `payments` table (PRD 6.6: payout only after completion).

    GET  /admin/payments                                   latest payments of every kind + totals
    GET  /admin/owner-settlements                          per Owner: payable to them, commission they owe, to review
    POST /admin/owner-settlements/{owner_id}/payouts       Admin records a bank transfer to the Owner (OWNER_PAYOUT rows)
    POST /admin/owner-settlements/{owner_id}/commission-receipts   Admin records commission received from the Owner
    GET  /owners/me/settlements                            the Owner's own view of the same

Settlement status on a PAYMENT row (owner_settlement_status, catalogue not frozen by the PRD):
    OWNER_PAYABLE  online money Travelly holds for the Owner (ticket: after the departure completes; private hire: when paid)
    OWNER_PAID     paid out to the Owner; an OWNER_PAYOUT row (original_payment_id = the payment) records the transfer
    COMMISSION_DUE cash the Owner collected; they owe Travelly the commission (owner decision, 11 Nov 2026)
    COMMISSION_PAID that commission was received
Partly refunded payments (owner decision 12 Nov 2026): the Owner is paid in proportion to the money Travelly keeps,
i.e. owner_net_amount x (amount - refunded) / amount, so commission and gateway fee shrink in the same proportion
(PayHere also returns its fee on the refunded part). A payment whose refund is still pending or processing is listed
under needs_review and cannot be paid out until that refund is settled. Fully refunded payments are never paid out.
"""
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.api.routers.api import current, require_role, touch
from app.api.routers.review_api import admin, locked_authority
from app.core.errors import ApiError
from app.dependencies.database import get_db
from app.models import User
from app.models.hire_models import Booking, Notification
from app.models.payment_models import Payment
from app.services.refunds import REFUNDS

router = APIRouter(prefix='/api/v1', tags=['Settlement'])
# Rows that carry an Owner share: the captured seat payment, or its REALLOCATION when another Owner took over.
OWNER_SHARE = ('PAYMENT', 'REALLOCATION')
ZERO = Decimal('0')


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class Payout(Strict):
    payment_ids: list[UUID] = Field(min_length=1, max_length=200)
    bank_reference: str = Field(min_length=1, max_length=200)
    idempotency_key: str = Field(min_length=8, max_length=40, pattern=r'^[A-Za-z0-9_-]+$')


class CommissionReceipt(Strict):
    payment_ids: list[UUID] = Field(min_length=1, max_length=200)
    reference: str = Field(min_length=1, max_length=200)
    idempotency_key: str = Field(min_length=8, max_length=40, pattern=r'^[A-Za-z0-9_-]+$')


def money(value):
    return format(value if value is not None else ZERO, '.2f')


def row_out(p, booking=None):
    return {'id': str(p.id), 'payment_reference': p.payment_reference, 'booking_id': str(p.booking_id),
            'booking_reference': booking.booking_reference if booking else None,
            'booking_type': booking.booking_type if booking else None,
            'original_payment_id': str(p.original_payment_id) if p.original_payment_id else None,
            'payee_owner_user_id': str(p.payee_owner_user_id) if p.payee_owner_user_id else None,
            'transaction_type': p.transaction_type, 'payment_method': p.payment_method, 'provider_name': p.provider_name,
            'amount': money(p.amount), 'currency': p.currency, 'status': p.status,
            'commission_amount': None if p.commission_amount is None else money(p.commission_amount),
            'owner_net_amount': None if p.owner_net_amount is None else money(p.owner_net_amount),
            'owner_settlement_status': p.owner_settlement_status, 'created_at': p.created_at.isoformat(),
            'captured_at': p.captured_at.isoformat() if p.captured_at else None,
            'owner_payable_at': p.owner_payable_at.isoformat() if p.owner_payable_at else None,
            'owner_paid_at': p.owner_paid_at.isoformat() if p.owner_paid_at else None,
            'provider_reference': p.provider_reference, 'version': p.version}


def captured_id(p):
    return p.original_payment_id if p.transaction_type == 'REALLOCATION' else p.id


def refunded(db, p, statuses=('PAID',)):
    return db.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(
        Payment.original_payment_id == captured_id(p), Payment.transaction_type.in_(REFUNDS), Payment.status.in_(statuses))) or ZERO


def refund_in_flight(db, p):
    return refunded(db, p, ('PENDING', 'PROCESSING')) > 0


def payable_share(db, p):
    """What the Owner is owed for this row: the whole Owner share, or its pro-rata part after a partial refund."""
    if p.status == 'PAID':
        return p.owner_net_amount or ZERO
    if p.status != 'PARTIALLY_REFUNDED' or not p.amount:
        return ZERO
    kept = max(p.amount - refunded(db, p), ZERO)
    return ((p.owner_net_amount or ZERO) * kept / p.amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def bookings_for(db, rows):
    ids = {r.booking_id for r in rows}
    return {b.id: b for b in db.scalars(select(Booking).where(Booking.id.in_(ids)))} if ids else {}


def total(db, *where, column=Payment.amount):
    return db.scalar(select(func.coalesce(func.sum(column), 0)).where(*where)) or ZERO


@router.get('/admin/payments')
def admin_payments(user=Depends(admin), db: Session = Depends(get_db)):
    rows = db.scalars(select(Payment).order_by(Payment.created_at.desc(), Payment.id.desc()).limit(200)).all()
    books = bookings_for(db, rows)
    paid = (Payment.transaction_type == 'PAYMENT', Payment.status.in_(('PAID', 'PARTIALLY_REFUNDED', 'REFUNDED')))
    return {'items': [row_out(r, books.get(r.booking_id)) for r in rows], 'totals': {
        'currency': 'LKR',
        'collected_online': money(total(db, *paid, Payment.payment_method != 'CASH')),
        'collected_cash': money(total(db, *paid, Payment.payment_method == 'CASH')),
        'refunded': money(total(db, Payment.transaction_type.in_(REFUNDS), Payment.status == 'PAID')),
        'refunds_waiting': money(total(db, Payment.transaction_type.in_(REFUNDS), Payment.status.in_(('PENDING', 'PROCESSING')))),
        'commission_earned': money(total(db, *paid, column=Payment.commission_amount)),
        'owner_payable': money(sum((payable_share(db, p) for p in db.scalars(select(Payment).where(
            Payment.owner_settlement_status == 'OWNER_PAYABLE'))), ZERO)),
        'owner_paid': money(total(db, Payment.transaction_type == 'OWNER_PAYOUT', Payment.status == 'PAID')),
        'commission_due_from_owners': money(total(db, Payment.owner_settlement_status == 'COMMISSION_DUE', column=Payment.commission_amount))}}


def settlement_for(db, owner_id):
    payments = db.scalars(select(Payment).where(Payment.payee_owner_user_id == owner_id, Payment.transaction_type.in_(OWNER_SHARE))
                          .order_by(Payment.created_at)).all()
    books = bookings_for(db, payments)
    waiting = {p.id for p in payments if p.owner_settlement_status in (None, 'OWNER_PAYABLE') and refund_in_flight(db, p)}
    payable = [p for p in payments if p.owner_settlement_status == 'OWNER_PAYABLE' and p.status in ('PAID', 'PARTIALLY_REFUNDED')
               and p.id not in waiting]
    due = [p for p in payments if p.owner_settlement_status == 'COMMISSION_DUE']
    review = [p for p in payments if p.id in waiting]
    shares = {p.id: payable_share(db, p) for p in payable}
    paid = [p for p in payments if p.owner_settlement_status in ('OWNER_PAID', 'COMMISSION_PAID')]
    owner = db.get(User, owner_id)
    return {'owner_user_id': str(owner_id), 'owner_reference': owner.public_user_reference if owner else None,
            'owner_name': (owner.display_name or owner.full_name) if owner else None, 'currency': 'LKR',
            'payable_amount': money(sum(shares.values(), ZERO)),
            'payable': [{**row_out(p, books.get(p.booking_id)), 'payable_amount': money(shares[p.id])} for p in payable],
            'commission_due_amount': money(sum((p.commission_amount or ZERO for p in due), ZERO)),
            'commission_due': [row_out(p, books.get(p.booking_id)) for p in due],
            'needs_review': [row_out(p, books.get(p.booking_id)) for p in review],
            'settled': [row_out(p, books.get(p.booking_id)) for p in paid[-50:]]}


@router.get('/admin/owner-settlements')
def admin_settlements(user=Depends(admin), db: Session = Depends(get_db)):
    owners = db.scalars(select(Payment.payee_owner_user_id).where(
        Payment.transaction_type.in_(OWNER_SHARE), Payment.payee_owner_user_id.is_not(None),
        Payment.owner_settlement_status.in_(('OWNER_PAYABLE', 'COMMISSION_DUE'))
        | (Payment.status == 'PARTIALLY_REFUNDED')).distinct()).all()
    items = [settlement_for(db, o) for o in owners]
    items.sort(key=lambda i: (-Decimal(i['payable_amount']), -Decimal(i['commission_due_amount'])))
    return {'items': items}


@router.get('/owners/me/settlements')
def my_settlements(user=Depends(current), db: Session = Depends(get_db)):
    require_role(db, user, 'OWNER')
    return settlement_for(db, user.id)


def locked_payments(db, owner_id, ids, status):
    rows = db.scalars(select(Payment).where(Payment.id.in_(ids)).order_by(Payment.id).with_for_update()
                      .execution_options(populate_existing=True)).all()
    found = {r.id: r for r in rows}
    wrong = [str(i) for i in ids if i not in found or found[i].payee_owner_user_id != owner_id
             or found[i].transaction_type not in OWNER_SHARE or found[i].owner_settlement_status != status]
    if wrong:
        raise ApiError(409, 'SETTLEMENT_NOT_ALLOWED', f'These payments are not {status} for this Owner: ' + ', '.join(wrong) + '.',
                       [{'field': 'payment_ids', 'message': w} for w in wrong])
    return [found[i] for i in ids]


@router.post('/admin/owner-settlements/{owner_id}/payouts', status_code=201)
def record_payout(owner_id: UUID, body: Payout, request: Request, user=Depends(admin), db: Session = Depends(get_db)):
    ids = list(dict.fromkeys(body.payment_ids))
    first_key = f'payout:{body.idempotency_key}:{ids[0]}'
    replay = db.scalar(select(Payment).where(Payment.idempotency_key == first_key))
    if replay:
        rows = db.scalars(select(Payment).where(Payment.idempotency_key.like(f'payout:{body.idempotency_key}:%'))).all()
        return JSONResponse(status_code=200, content={'payouts': [row_out(r) for r in rows],
                                                      'total': money(sum((r.amount for r in rows), ZERO))})
    with request.app.state.audit.coordinated():
        locked_authority(db, request, user, user.id)
        payments = locked_payments(db, owner_id, ids, 'OWNER_PAYABLE')
        moment = datetime.now(timezone.utc)
        payouts = []
        for p in payments:
            share = payable_share(db, p)
            if refund_in_flight(db, p) or share <= 0:
                raise ApiError(409, 'SETTLEMENT_NOT_ALLOWED', f'{p.payment_reference} has a refund that is not settled yet, or nothing left to pay.')
            payout = Payment(payment_reference='OPY-' + p.payment_reference[4:], booking_id=p.booking_id, original_payment_id=p.id,
                             payee_owner_user_id=owner_id, transaction_type='OWNER_PAYOUT', payment_method='BANK',
                             provider_reference=body.bank_reference, idempotency_key=f'payout:{body.idempotency_key}:{p.id}',
                             amount=share, currency=p.currency, status='PAID', captured_at=moment,
                             created_by=user.id, updated_by=user.id)
            db.add(payout)
            payouts.append(payout)
            p.owner_settlement_status = 'OWNER_PAID'
            p.owner_paid_at = moment
            touch(p); p.updated_by = user.id
        amount = sum((p.amount for p in payouts), ZERO)
        db.add(Notification(recipient_user_id=owner_id, notification_type='PAYMENT', channel='IN_APP', title='Payout sent',
                            body=f'Travelly sent you {money(amount)} LKR for {len(payouts)} payment(s). Bank reference: {body.bank_reference}.',
                            action_required=False, action_payload={}, status='QUEUED'))
        db.flush()
        request.app.state.audit.commit(db, actor=user.id, target={'resource': 'payments', 'id': str(payouts[0].id)},
                                       previous_status='OWNER_PAYABLE', new_status='OWNER_PAID', previous_version=None,
                                       new_version=None, full_reason=f'Owner payout {body.bank_reference} for {len(payouts)} payment(s).',
                                       previous_decision_evidence={'payments': [str(p.id) for p in payments]},
                                       trace_id=request.state.trace_id)
    return {'payouts': [row_out(p) for p in payouts], 'total': money(amount)}


@router.post('/admin/owner-settlements/{owner_id}/commission-receipts')
def record_commission(owner_id: UUID, body: CommissionReceipt, request: Request, user=Depends(admin), db: Session = Depends(get_db)):
    ids = list(dict.fromkeys(body.payment_ids))
    with request.app.state.audit.coordinated():
        locked_authority(db, request, user, user.id)
        rows = db.scalars(select(Payment).where(Payment.id.in_(ids))).all()
        if rows and all(r.owner_settlement_status == 'COMMISSION_PAID' for r in rows) and len(rows) == len(ids):
            return {'payments': [row_out(r) for r in rows], 'total': money(sum((r.commission_amount or ZERO for r in rows), ZERO))}
        payments = locked_payments(db, owner_id, ids, 'COMMISSION_DUE')
        for p in payments:
            p.owner_settlement_status = 'COMMISSION_PAID'
            touch(p); p.updated_by = user.id
        amount = sum((p.commission_amount or ZERO for p in payments), ZERO)
        request.app.state.audit.commit(db, actor=user.id, target={'resource': 'payments', 'id': str(payments[0].id)},
                                       previous_status='COMMISSION_DUE', new_status='COMMISSION_PAID', previous_version=None,
                                       new_version=None, full_reason=f'Commission received {body.reference} for {len(payments)} payment(s).',
                                       previous_decision_evidence={'payments': [str(p.id) for p in payments]},
                                       trace_id=request.state.trace_id)
    return {'payments': [row_out(p) for p in payments], 'total': money(amount)}
