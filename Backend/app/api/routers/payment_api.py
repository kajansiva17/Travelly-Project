"""Payments (matrix 65-67) on the approved PRD `payments` table — slice 1: online Ticket seats.

PRD 6.6: online Ticket booking needs the full payable amount before a seat becomes BOOKED; payment creation uses a unique
idempotency key; webhook retries never create a second charge; Owner payout happens only after completion.

Flow
    POST /bookings/{id}/payment-intents      Passenger, while the seat hold is active -> payments row PENDING
    POST /payments/webhooks/{provider}       signed provider event (the real path)
    POST /payments/{id}/sandbox-outcome      Sandbox only: the Passenger chooses success/failure; same code path
    success  -> payment PAID (commission and Owner net fixed), seats HELD -> BOOKED, booking REQUESTED -> CONFIRMED
    failure  -> payment FAILED; the hold stays until it expires, so the Passenger can try again
    GET  /bookings/{id}/payments             Passenger, Owner or Admin

Lock order (same as ticket holds): scheduled_trips -> bookings -> scheduled_trip_seats (by id) -> payments.
Private hire (pay after the trip, cash or online) is slice 2.
"""
import json
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.api.routers.api import current, touch
from app.api.routers.review_api import admin, locked_authority
from app.api.routers.ticket_booking_api import lock_trip, release_expired
from app.core.config import get_settings
from app.core.errors import ApiError
from app.dependencies.database import get_db
from app.models import UserRole
from app.models.hire_models import Booking, Notification
from app.models.payment_models import Payment
from app.models.rate_models import ServiceType
from app.models.seat_models import BookingTraveller, ScheduledTripSeat
from app.schemas.payment_schemas import PaymentIntentRequest, PaymentSettings, SandboxOutcome
from app.services.payment_providers import PROVIDERS, payment_settings, provider_for, split

router = APIRouter(prefix='/api/v1', tags=['Payments'])
OPEN = ('PENDING', 'PROCESSING')


def now():
    return datetime.now(timezone.utc)


def is_admin(db, user):
    return bool(db.scalar(select(UserRole.id).where(UserRole.user_id == user.id, UserRole.role_code == 'ADMIN',
                                                    UserRole.approval_status == 'APPROVED')))


def payment_out(payment, full=False):
    out = {'id': str(payment.id), 'payment_reference': payment.payment_reference, 'booking_id': str(payment.booking_id),
           'transaction_type': payment.transaction_type, 'payment_method': payment.payment_method,
           'provider_name': payment.provider_name, 'amount': format(payment.amount, '.2f'), 'currency': payment.currency,
           'status': payment.status, 'version': payment.version, 'created_at': payment.created_at.isoformat(),
           'captured_at': payment.captured_at.isoformat() if payment.captured_at else None,
           'failure_code': payment.failure_code, 'failure_message': payment.failure_message}
    if full:
        fee = None
        if payment.commission_amount is not None and payment.owner_net_amount is not None:
            fee = format(payment.amount - payment.commission_amount - payment.owner_net_amount, '.2f')
        out.update({'commission_amount': None if payment.commission_amount is None else format(payment.commission_amount, '.2f'),
                    'gateway_fee_amount': fee,
                    'owner_net_amount': None if payment.owner_net_amount is None else format(payment.owner_net_amount, '.2f'),
                    'owner_settlement_status': payment.owner_settlement_status,
                    'owner_payable_at': payment.owner_payable_at.isoformat() if payment.owner_payable_at else None,
                    'owner_paid_at': payment.owner_paid_at.isoformat() if payment.owner_paid_at else None})
    return out


def lock_booking(db, booking_id):
    return db.scalar(select(Booking).where(Booking.id == booking_id).with_for_update().execution_options(populate_existing=True))


def lock_payment(db, payment_id):
    return db.scalar(select(Payment).where(Payment.id == payment_id).with_for_update().execution_options(populate_existing=True))


def held_seats(db, booking):
    return db.scalars(select(ScheduledTripSeat).where(ScheduledTripSeat.held_by_booking_id == booking.id,
                                                       ScheduledTripSeat.seat_status == 'HELD')
                      .order_by(ScheduledTripSeat.id).with_for_update().execution_options(populate_existing=True)).all()


def hold_is_active(db, booking):
    seats = held_seats(db, booking)
    count = len(db.scalars(select(BookingTraveller.id).where(BookingTraveller.booking_id == booking.id,
                                                            BookingTraveller.traveller_status == 'ACTIVE')).all())
    return seats if booking.status == 'REQUESTED' and seats and len(seats) == count else None


def tell(db, recipient, booking, kind, title, body):
    db.add(Notification(recipient_user_id=recipient, booking_id=booking.id, scheduled_trip_id=booking.current_scheduled_trip_id,
                        notification_type=kind, channel='IN_APP', title=title, body=body, action_required=False,
                        action_payload={'booking_id': str(booking.id)}, status='QUEUED'))


# --------------------------------------------------------------------------- 65 create intent

@router.post('/bookings/{booking_id}/payment-intents', status_code=201)
def create_intent(booking_id: UUID, body: PaymentIntentRequest, user=Depends(current), db: Session = Depends(get_db)):
    booking = db.get(Booking, booking_id)
    if not booking or booking.passenger_user_id != user.id:
        raise ApiError(404, 'BOOKING_NOT_FOUND', 'Booking not found.')
    if booking.booking_type != 'TICKET_HIRE':
        raise ApiError(409, 'PAYMENT_NOT_AVAILABLE', 'Online payment for this booking type is not available yet.')
    stored_key = f'{user.id.hex}:{body.idempotency_key}'
    moment = now()
    lock_trip(db, booking.current_scheduled_trip_id)
    release_expired(db, booking.current_scheduled_trip_id, moment)
    booking = lock_booking(db, booking.id)
    replay = db.scalar(select(Payment).where(Payment.idempotency_key == stored_key))
    if replay:
        db.commit()
        if replay.booking_id != booking.id:
            raise ApiError(409, 'IDEMPOTENCY_KEY_REUSED', 'This request key was already used for another payment.')
        return JSONResponse(status_code=200, content={**payment_out(replay), 'checkout': PROVIDERS[replay.provider_name].checkout(replay)})
    if booking.payment_status_snapshot == 'PAID' or booking.status == 'CONFIRMED':
        db.commit()
        raise ApiError(409, 'BOOKING_ALREADY_PAID', 'This booking is already paid.')
    if not hold_is_active(db, booking):
        db.commit()  # keep any expired-hold release made above
        if booking.status == 'CANCELLED':
            raise ApiError(410, 'HOLD_EXPIRED', 'The seat hold has ended. Choose your seats again.')
        raise ApiError(409, 'HOLD_NOT_ACTIVE', 'This booking has no active seat hold.')
    if Decimal(body.amount) != booking.total_amount or body.currency != booking.currency:
        raise ApiError(422, 'PAYMENT_AMOUNT_MISMATCH', 'Pay the full amount shown for these seats.',
                       [{'field': 'amount', 'message': f'{format(booking.total_amount, ".2f")} {booking.currency}'}])
    service = db.get(ServiceType, booking.service_type_id)
    provider = provider_for(service)
    if provider is None:
        raise ApiError(409, 'PAYMENT_PROVIDER_UNAVAILABLE', 'Online payment is not available right now.')
    if body.method not in provider.methods:
        raise ApiError(422, 'PAYMENT_METHOD_UNAVAILABLE', 'Choose one of: ' + ', '.join(provider.methods) + '.')
    if db.scalar(select(Payment.id).where(Payment.booking_id == booking.id, Payment.transaction_type == 'PAYMENT',
                                          Payment.status.in_(OPEN))):
        raise ApiError(409, 'PAYMENT_IN_PROGRESS', 'A payment for this booking is already in progress.')
    payment = Payment(payment_reference='PAY-' + uuid4().hex[:20].upper(), booking_id=booking.id,
                      payee_owner_user_id=booking.owner_user_id, transaction_type='PAYMENT', payment_method=body.method,
                      provider_name=provider.name, idempotency_key=stored_key, amount=booking.total_amount,
                      currency=booking.currency, status='PENDING', created_by=user.id, updated_by=user.id)
    db.add(payment)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ApiError(409, 'IDEMPOTENCY_KEY_REUSED', 'This request key was already used.') from None
    booking.payment_status_snapshot = 'PENDING'
    touch(booking); booking.updated_by = user.id
    db.commit()
    return {**payment_out(payment), 'checkout': provider.checkout(payment)}


# --------------------------------------------------------------------------- 66 provider event (shared by webhook and Sandbox)

def apply_event(db, provider, event, actor=None, sandbox=False):
    payment = db.scalar(select(Payment).where(Payment.payment_reference == event['payment_reference'],
                                              Payment.provider_name == provider.name))
    if not payment:
        raise ApiError(404, 'PAYMENT_NOT_FOUND', 'Payment not found.')
    if event['outcome'] not in ('SUCCEEDED', 'FAILED'):
        raise ApiError(422, 'VALIDATION_ERROR', 'Unknown payment outcome.')
    booking = db.get(Booking, payment.booking_id)
    moment = now()
    if booking.booking_type == 'TICKET_HIRE':
        lock_trip(db, booking.current_scheduled_trip_id)
        release_expired(db, booking.current_scheduled_trip_id, moment)
    booking = lock_booking(db, booking.id)
    seats = hold_is_active(db, booking) if booking.booking_type == 'TICKET_HIRE' else None
    payment = lock_payment(db, payment.id)
    if Decimal(event['amount']) != payment.amount or event['currency'] != payment.currency:
        db.commit()
        raise ApiError(422, 'PAYMENT_AMOUNT_MISMATCH', 'The provider amount does not match this payment.')
    if payment.status == 'PAID':
        db.commit()
        return payment  # retry of an event already applied: never a second charge
    if event['outcome'] == 'FAILED':
        if payment.status in OPEN:
            payment.status = 'FAILED'
            payment.failure_code = event.get('failure_code') or 'PROVIDER_DECLINED'
            payment.failure_message = 'The payment did not go through. No money was taken.'
            touch(payment); payment.updated_by = actor
            if booking.status == 'REQUESTED':
                booking.payment_status_snapshot = 'FAILED'
                touch(booking); booking.updated_by = actor
        db.commit()
        return payment
    if sandbox and payment.status not in OPEN:
        db.commit()
        if payment.failure_code == 'HOLD_EXPIRED':
            raise ApiError(410, 'HOLD_EXPIRED', 'The seat hold has ended. Choose your seats again.')
        raise ApiError(409, 'PAYMENT_NOT_PENDING', 'This payment is no longer waiting. Start a new payment.')
    if booking.booking_type == 'TICKET_HIRE' and not seats:
        if sandbox:
            # Nothing was charged yet, so a Sandbox success after the hold ended is simply refused.
            if payment.status in OPEN:
                payment.status = 'FAILED'
                payment.failure_code = 'HOLD_EXPIRED'
                payment.failure_message = 'The seat hold ended before payment. No money was taken.'
                touch(payment); payment.updated_by = actor
            db.commit()
            raise ApiError(410, 'HOLD_EXPIRED', 'The seat hold has ended. Choose your seats again.')
        # A real provider already took the money: record it and flag the refund; never seat someone twice.
        capture(db, payment, booking, provider, event, actor, moment)
        payment.failure_code = 'SEATS_RELEASED_REFUND_DUE'
        payment.failure_message = 'Payment arrived after the seat hold ended. A refund is due.'
        db.commit()
        return payment
    capture(db, payment, booking, provider, event, actor, moment)
    for seat in seats or []:
        seat.seat_status = 'BOOKED'
        seat.booked_booking_id = booking.id
        seat.held_by_booking_id = None
        seat.hold_expires_at = None
        touch(seat); seat.updated_by = actor
    booking.status = 'CONFIRMED'
    booking.confirmed_at = moment
    touch(booking); booking.updated_by = actor
    tell(db, booking.passenger_user_id, booking, 'BOOKING_CONFIRMED', 'Seats confirmed',
         f'Payment {payment.payment_reference} received. Your seats are booked.')
    if booking.owner_user_id:
        tell(db, booking.owner_user_id, booking, 'PAYMENT', 'Seat payment received',
             f'{format(payment.amount, ".2f")} {payment.currency} for booking {booking.booking_reference}.')
    db.commit()
    return payment


def capture(db, payment, booking, provider, event, actor, moment):
    commission, fee, net = split(payment.amount, db.get(ServiceType, booking.service_type_id), event.get('fee'))
    payment.status = 'PAID'
    payment.provider_reference = event['provider_reference']
    payment.authorized_at = payment.authorized_at or moment
    payment.captured_at = moment
    payment.commission_amount = commission
    payment.owner_net_amount = net
    payment.failure_code = None
    payment.failure_message = None
    touch(payment); payment.updated_by = actor
    booking.payment_status_snapshot = 'PAID'
    touch(booking); booking.updated_by = actor


@router.post('/payments/webhooks/{provider_name}')
async def provider_webhook(provider_name: str, request: Request, db: Session = Depends(get_db)):
    provider = PROVIDERS.get(provider_name.upper())
    if provider is None:
        raise ApiError(404, 'PROVIDER_NOT_FOUND', 'Unknown payment provider.')
    raw = await request.body()
    try:
        event = provider.parse(raw, request.headers)
    except (ValueError, KeyError, TypeError):
        raise ApiError(422, 'VALIDATION_ERROR', 'The provider event is not valid.') from None
    if event is None:
        raise ApiError(401, 'INVALID_SIGNATURE', 'The provider signature is not valid.')
    payment = apply_event(db, provider, event)
    return {'payment_reference': payment.payment_reference, 'status': payment.status}


@router.post('/payments/{payment_id}/sandbox-outcome')
def sandbox_outcome(payment_id: UUID, body: SandboxOutcome, user=Depends(current), db: Session = Depends(get_db)):
    if get_settings().environment == 'production':
        raise ApiError(404, 'PAYMENT_NOT_FOUND', 'Payment not found.')
    payment = db.get(Payment, payment_id)
    booking = db.get(Booking, payment.booking_id) if payment else None
    if not payment or not booking or booking.passenger_user_id != user.id or payment.provider_name != 'SANDBOX':
        raise ApiError(404, 'PAYMENT_NOT_FOUND', 'Payment not found.')
    provider = PROVIDERS['SANDBOX']
    applied = apply_event(db, provider, provider.event(payment, body.outcome, None if body.outcome == 'SUCCEEDED' else 'SANDBOX_DECLINED'),
                          actor=user.id, sandbox=True)
    return {**payment_out(applied), 'booking_status': db.get(Booking, applied.booking_id).status}


# --------------------------------------------------------------------------- 67 history

@router.get('/bookings/{booking_id}/payments')
def booking_payments(booking_id: UUID, user=Depends(current), db: Session = Depends(get_db)):
    booking = db.get(Booking, booking_id)
    reviewer = is_admin(db, user)
    if not booking or (user.id not in (booking.passenger_user_id, booking.owner_user_id) and not reviewer):
        raise ApiError(404, 'BOOKING_NOT_FOUND', 'Booking not found.')
    full = reviewer or user.id == booking.owner_user_id
    rows = db.scalars(select(Payment).where(Payment.booking_id == booking.id).order_by(Payment.created_at, Payment.id)).all()
    return {'booking_id': str(booking.id), 'payment_status': booking.payment_status_snapshot,
            'items': [payment_out(p, full) for p in rows]}


# --------------------------------------------------------------------------- Admin payment settings (service_types.settings)

def settings_out(row):
    return {'id': str(row.id), 'code': row.code, 'name': row.name, 'category': row.category, 'is_active': row.is_active,
            'version': row.version, **payment_settings(row), 'available_providers': sorted(PROVIDERS)}


@router.get('/admin/payment-settings')
def list_payment_settings(user=Depends(admin), db: Session = Depends(get_db)):
    rows = db.scalars(select(ServiceType).order_by(ServiceType.display_order, ServiceType.code).limit(100)).all()
    return {'items': [settings_out(r) for r in rows]}


@router.patch('/admin/service-types/{service_id}/payment-settings')
def update_payment_settings(service_id: UUID, body: PaymentSettings, request: Request, user=Depends(admin),
                            db: Session = Depends(get_db)):
    if body.payment_provider not in PROVIDERS:
        raise ApiError(422, 'PAYMENT_PROVIDER_UNAVAILABLE', f'{body.payment_provider} is not connected yet. Use SANDBOX for now.')
    with request.app.state.audit.coordinated():
        locked_authority(db, request, user, user.id)
        row = db.scalar(select(ServiceType).where(ServiceType.id == service_id).with_for_update()
                        .execution_options(populate_existing=True))
        if not row:
            raise ApiError(404, 'SERVICE_NOT_FOUND', 'Service not found.')
        if row.version != body.expected_version:
            raise ApiError(409, 'VERSION_CONFLICT', 'Service configuration changed. Reload before saving.')
        before, old = row.version, json.loads(json.dumps(row.settings or {}))
        row.settings = {**(row.settings or {}), 'payment_provider': body.payment_provider,
                        'commission_percent': body.commission_percent, 'gateway_fee_percent': body.gateway_fee_percent}
        touch(row)
        row.updated_by = user.id
        request.app.state.audit.commit(db, actor=user.id, target={'resource': 'service_types', 'id': str(row.id)},
                                       previous_status=None, new_status=None, previous_version=before, new_version=row.version,
                                       full_reason=None, previous_decision_evidence={'settings': old},
                                       trace_id=request.state.trace_id)
    return settings_out(row)
