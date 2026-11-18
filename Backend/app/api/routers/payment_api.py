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

Slice 2 — private hire (owner decisions, 11 Nov 2026): no advance; the Passenger pays the full amount after the trip is
COMPLETED, online (same intents/providers) or in cash if the Owner accepts cash for that vehicle service. Cash is
collected at the END only and needs both sides: the Passenger confirms they paid, the collector (the trip's Driver or
the self-driving Owner) confirms they received it. Commission still applies to cash; the Owner owes it to Travelly
(owner_settlement_status COMMISSION_DUE). Online private-hire payments are payable to the Owner at once (trip done).
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
from app.api.routers.api import current, require_role, touch
from app.api.routers.review_api import admin, locked_authority
from app.api.routers.ticket_booking_api import lock_trip, release_expired
from app.core.config import get_settings
from app.core.errors import ApiError
from app.dependencies.database import get_db
from app.models import User, UserRole
from app.models.hire_models import Booking, Notification, Trip
from app.models.payment_models import Payment
from app.models.rate_models import ServiceType, VehicleService
from app.models.review_models import Vehicle
from app.models.seat_models import BookingTraveller, ScheduledTripSeat
from app.schemas.payment_schemas import CashReceipt, CheckoutRequest, PaymentIntentRequest, PaymentOptions, PaymentSettings, SandboxOutcome
from app.services.pricing_scope import long_distance
from app.services.payment_providers import PAYHERE, SANDBOX, payment_settings, provider_for, providers, service_days, split
from app.services.refunds import queue_refund

router = APIRouter(prefix='/api/v1', tags=['Payments'])
OPEN = ('PENDING', 'PROCESSING')
WAITING = OPEN + ('CASH_AWAITING_CONFIRMATION',)  # any payment still in flight blocks a second one
HIRED = ('PRIVATE_HIRE', 'RENTAL')  # paid after the trip is completed
ALL_PROVIDERS = {'SANDBOX': SANDBOX, 'PAYHERE': PAYHERE}  # for reading old payments and webhooks, even if not offered now


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


def payer_for(provider, user, details):
    """Details the provider needs for this payment: name, email and phone from the account, the rest from the Pay screen."""
    details = details.model_dump() if details else {}
    payer = {'full_name': user.full_name, 'email': user.email or details.get('email'), 'phone': user.phone_e164 or details.get('phone'),
             'address': details.get('address'), 'city': details.get('city')}
    missing = [name for name in provider.payer_required(user) if not payer.get(name)]
    if missing:
        raise ApiError(422, 'PAYER_DETAILS_REQUIRED', 'Enter the details the payment provider needs.',
                       [{'field': f'payer.{name}', 'message': 'This field is required.'} for name in missing])
    return payer


def cash_accepted(db, booking):
    row = db.scalar(select(VehicleService).where(VehicleService.vehicle_id == booking.vehicle_id,
                                                 VehicleService.service_type_id == booking.service_type_id))
    return bool(row and (row.owner_terms or {}).get('cash', {}).get('accepted') is True)


def finished_trip(db, booking):
    return db.scalar(select(Trip).where(Trip.booking_id == booking.id, Trip.status == 'COMPLETED')
                     .order_by(Trip.created_at.desc()).limit(1))


def latest_of(db, booking):
    return db.scalar(select(Payment).where(Payment.booking_id == booking.id, Payment.transaction_type == 'PAYMENT')
                     .order_by(Payment.created_at.desc(), Payment.id.desc()).limit(1))


def payment_view(db, booking, viewer):
    """What a private-hire booking page needs to show and offer for payment (owner decision: after the trip only)."""
    provider = provider_for(db.get(ServiceType, booking.service_type_id))
    passenger = db.get(User, booking.passenger_user_id)
    latest = latest_of(db, booking)
    trip = finished_trip(db, booking)
    due = booking.booking_type in HIRED and booking.status == 'COMPLETED' and booking.payment_status_snapshot != 'PAID'
    cash = None
    if latest is not None and latest.payment_method == 'CASH':
        settled = latest.status == 'PAID'
        cash = {'payment_id': str(latest.id), 'status': latest.status,
                'passenger_confirmed': settled or latest.created_by == booking.passenger_user_id,
                'collector_confirmed': settled or (trip is not None and latest.created_by == trip.driver_user_id)}
    return {'payment_status': booking.payment_status_snapshot, 'amount_due': format(booking.total_amount, '.2f') if due and booking.total_amount is not None else None,
            'currency': booking.currency, 'payment_due': due,
            'payment_provider': provider.name if provider else None, 'payment_method': provider.methods[0] if provider else None,
            'payer_details_required': provider.payer_required(passenger) if provider else [],
            'cash_accepted': cash_accepted(db, booking), 'cash_collection_stage': 'END',
            'collector_user_id': str(trip.driver_user_id) if trip and trip.driver_user_id else None,
            'cash': cash, 'latest_payment': None if latest is None else {
                'id': str(latest.id), 'payment_reference': latest.payment_reference, 'status': latest.status,
                'payment_method': latest.payment_method, 'provider_name': latest.provider_name,
                'amount': format(latest.amount, '.2f'), 'currency': latest.currency,
                'failure_code': latest.failure_code, 'failure_message': latest.failure_message}}


# --------------------------------------------------------------------------- 65 create intent

@router.post('/bookings/{booking_id}/payment-intents', status_code=201)
def create_intent(booking_id: UUID, body: PaymentIntentRequest, user=Depends(current), db: Session = Depends(get_db)):
    booking = db.get(Booking, booking_id)
    if not booking or booking.passenger_user_id != user.id:
        raise ApiError(404, 'BOOKING_NOT_FOUND', 'Booking not found.')
    if booking.booking_type not in ('TICKET_HIRE',) + HIRED:
        raise ApiError(409, 'PAYMENT_NOT_AVAILABLE', 'Online payment for this booking type is not available yet.')
    ticket = booking.booking_type == 'TICKET_HIRE'
    stored_key = f'{user.id.hex}:{body.idempotency_key}'
    moment = now()
    if ticket:
        lock_trip(db, booking.current_scheduled_trip_id)
        release_expired(db, booking.current_scheduled_trip_id, moment)
    booking = lock_booking(db, booking.id)
    replay = db.scalar(select(Payment).where(Payment.idempotency_key == stored_key))
    if replay:
        db.commit()
        if replay.booking_id != booking.id:
            raise ApiError(409, 'IDEMPOTENCY_KEY_REUSED', 'This request key was already used for another payment.')
        used = ALL_PROVIDERS[replay.provider_name]
        checkout = used.checkout(replay, booking, payer_for(used, user, body.payer)) if replay.status in OPEN else None
        return JSONResponse(status_code=200, content={**payment_out(replay), 'checkout': checkout})
    if booking.payment_status_snapshot == 'PAID' or (ticket and booking.status == 'CONFIRMED'):
        db.commit()
        raise ApiError(409, 'BOOKING_ALREADY_PAID', 'This booking is already paid.')
    if not ticket and booking.status != 'COMPLETED':
        # Owner decision (CF01): no advance. Private hire is paid once the trip is completed.
        raise ApiError(409, 'PAYMENT_NOT_DUE', 'Payment opens when the trip is completed.')
    if ticket and not hold_is_active(db, booking):
        db.commit()  # keep any expired-hold release made above
        if booking.status == 'CANCELLED':
            raise ApiError(410, 'HOLD_EXPIRED', 'The seat hold has ended. Choose your seats again.')
        raise ApiError(409, 'HOLD_NOT_ACTIVE', 'This booking has no active seat hold.')
    if Decimal(body.amount) != booking.total_amount or body.currency != booking.currency:
        raise ApiError(422, 'PAYMENT_AMOUNT_MISMATCH', 'Pay the full amount shown.',
                       [{'field': 'amount', 'message': f'{format(booking.total_amount, ".2f")} {booking.currency}'}])
    service = db.get(ServiceType, booking.service_type_id)
    provider = provider_for(service)
    if provider is None:
        raise ApiError(409, 'PAYMENT_PROVIDER_UNAVAILABLE', 'Online payment is not available right now.')
    if body.method not in provider.methods:
        raise ApiError(422, 'PAYMENT_METHOD_UNAVAILABLE', 'Choose one of: ' + ', '.join(provider.methods) + '.')
    payer = payer_for(provider, user, body.payer)
    waiting = db.scalar(select(Payment.id).where(Payment.booking_id == booking.id, Payment.transaction_type == 'PAYMENT',
                                                 Payment.status.in_(WAITING)))
    if waiting:
        raise ApiError(409, 'PAYMENT_IN_PROGRESS', 'A payment for this booking is already in progress.',
                       [{'field': 'payment_id', 'message': str(waiting)}])
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
    return {**payment_out(payment), 'checkout': provider.checkout(payment, booking, payer)}


@router.post('/payments/{payment_id}/checkout')
def resume_checkout(payment_id: UUID, body: CheckoutRequest, user=Depends(current), db: Session = Depends(get_db)):
    """Checkout details again for a payment that is still waiting, for example after the Pay page was reopened."""
    payment = db.get(Payment, payment_id)
    booking = db.get(Booking, payment.booking_id) if payment else None
    if not payment or not booking or booking.passenger_user_id != user.id or payment.transaction_type != 'PAYMENT':
        raise ApiError(404, 'PAYMENT_NOT_FOUND', 'Payment not found.')
    if payment.status not in OPEN:
        raise ApiError(409, 'PAYMENT_NOT_PENDING', 'This payment is no longer waiting. Start a new payment.')
    used = ALL_PROVIDERS[payment.provider_name]
    return {**payment_out(payment), 'checkout': used.checkout(payment, booking, payer_for(used, user, body.payer))}


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
            if booking.payment_status_snapshot != 'PAID' and booking.status in ('REQUESTED', 'COMPLETED'):
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
        queue_refund(db, payment, payment.amount, 'PAYMENT_AFTER_HOLD', actor)  # full refund, waiting for Admin approval
        db.commit()
        return payment
    capture(db, payment, booking, provider, event, actor, moment)
    if booking.booking_type in HIRED:
        # The trip is already completed, so the Owner's share is payable now (PRD 6.6).
        payment.owner_settlement_status = 'OWNER_PAYABLE'
        payment.owner_payable_at = moment
        tell(db, booking.passenger_user_id, booking, 'PAYMENT', 'Payment received',
             f'Payment {payment.payment_reference} received for booking {booking.booking_reference}. Thank you.')
        tell(db, booking.owner_user_id, booking, 'PAYMENT', 'Trip paid',
             f'{format(payment.amount, ".2f")} {payment.currency} paid online for booking {booking.booking_reference}.')
        db.commit()
        return payment
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
    commission, fee, net = split(payment.amount, db.get(ServiceType, booking.service_type_id), event.get('fee'), service_days(booking))
    payment.status = 'PAID'
    payment.provider_reference = event['provider_reference']
    if event.get('method'):
        payment.payment_method = event['method']  # what the Passenger actually chose on the provider page
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
    provider = ALL_PROVIDERS.get(provider_name.upper())
    if provider is None:
        raise ApiError(404, 'PROVIDER_NOT_FOUND', 'Unknown payment provider.')
    raw = await request.body()
    try:
        event = provider.parse(raw, request.headers)
    except (ValueError, KeyError, TypeError, UnicodeDecodeError):
        raise ApiError(422, 'VALIDATION_ERROR', 'The provider event is not valid.') from None
    if event is None:
        raise ApiError(401, 'INVALID_SIGNATURE', 'The provider signature is not valid.')
    if event['outcome'] is None:
        # Pending or chargeback notices: acknowledged, nothing changes here (chargebacks belong to the refunds slice).
        payment = db.scalar(select(Payment).where(Payment.payment_reference == event['payment_reference'],
                                                  Payment.provider_name == provider.name))
        if not payment:
            raise ApiError(404, 'PAYMENT_NOT_FOUND', 'Payment not found.')
        return {'payment_reference': payment.payment_reference, 'status': payment.status}
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
    provider = SANDBOX
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


# --------------------------------------------------------------------------- 70 cash receipts (private hire, END only)

@router.post('/bookings/{booking_id}/cash-receipts')
def cash_receipt(booking_id: UUID, body: CashReceipt, user=Depends(current), db: Session = Depends(get_db)):
    booking = db.get(Booking, booking_id)
    trip = finished_trip(db, booking) if booking else None
    collector = trip.driver_user_id if trip else None
    if not booking or user.id not in (booking.passenger_user_id, collector):
        raise ApiError(404, 'BOOKING_NOT_FOUND', 'Booking not found.')
    if booking.booking_type not in HIRED:
        raise ApiError(409, 'CASH_NOT_AVAILABLE', 'Cash is available only for private hire and rental.')
    if body.collection_stage != 'END':
        raise ApiError(422, 'CASH_COLLECTION_STAGE_INVALID', 'Cash is collected at the end of the trip.',
                       [{'field': 'collection_stage', 'message': 'Use END.'}])
    if booking.status != 'COMPLETED' or trip is None:
        raise ApiError(409, 'PAYMENT_NOT_DUE', 'Payment opens when the trip is completed.')
    if not cash_accepted(db, booking):
        raise ApiError(409, 'CASH_NOT_ACCEPTED', 'The Owner does not accept cash for this vehicle. Pay online instead.')
    if body.collector_user_id != collector:
        raise ApiError(422, 'COLLECTOR_NOT_ASSIGNED', 'The collector must be the Driver of this trip.',
                       [{'field': 'collector_user_id', 'message': str(collector)}])
    passenger = user.id == booking.passenger_user_id
    if (passenger and (not body.passenger_confirmation or body.collector_confirmation)) or \
            (not passenger and (not body.collector_confirmation or body.passenger_confirmation)):
        raise ApiError(422, 'CONFIRMATION_NOT_YOURS', 'Confirm only your own part: the Passenger that they paid, '
                       'the collector that they received the money.')
    if Decimal(body.amount) != booking.total_amount or body.currency != booking.currency:
        raise ApiError(422, 'PAYMENT_AMOUNT_MISMATCH', 'Confirm the full amount of the trip.',
                       [{'field': 'amount', 'message': f'{format(booking.total_amount, ".2f")} {booking.currency}'}])
    booking = lock_booking(db, booking.id)
    current_cash = db.scalar(select(Payment).where(Payment.booking_id == booking.id, Payment.transaction_type == 'PAYMENT',
                                                   Payment.payment_method == 'CASH', Payment.status.in_(('CASH_AWAITING_CONFIRMATION', 'PAID')))
                             .with_for_update().execution_options(populate_existing=True))
    if current_cash is None:
        if booking.payment_status_snapshot == 'PAID':
            db.commit()
            raise ApiError(409, 'BOOKING_ALREADY_PAID', 'This booking is already paid.')
        waiting = db.scalar(select(Payment.id).where(Payment.booking_id == booking.id, Payment.transaction_type == 'PAYMENT',
                                                     Payment.status.in_(OPEN)))
        if waiting:
            raise ApiError(409, 'PAYMENT_IN_PROGRESS', 'An online payment for this booking is already in progress.',
                           [{'field': 'payment_id', 'message': str(waiting)}])
        current_cash = Payment(payment_reference='PAY-' + uuid4().hex[:20].upper(), booking_id=booking.id,
                               payee_owner_user_id=booking.owner_user_id, transaction_type='PAYMENT', payment_method='CASH',
                               idempotency_key=f'{user.id.hex}:{body.idempotency_key}', amount=booking.total_amount,
                               currency=booking.currency, status='CASH_AWAITING_CONFIRMATION', created_by=user.id, updated_by=user.id)
        db.add(current_cash)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            raise ApiError(409, 'IDEMPOTENCY_KEY_REUSED', 'This request key was already used.') from None
        booking.payment_status_snapshot = 'CASH_AWAITING_CONFIRMATION'
        touch(booking); booking.updated_by = user.id
        other = collector if passenger else booking.passenger_user_id
        db.add(Notification(recipient_user_id=other, booking_id=booking.id, trip_id=trip.id, notification_type='PAYMENT',
                            channel='IN_APP', title='Confirm the cash payment',
                            body=f'Please confirm {format(booking.total_amount, ".2f")} {booking.currency} in cash for booking {booking.booking_reference}.',
                            action_required=True, action_payload={'booking_id': str(booking.id), 'payment_id': str(current_cash.id)},
                            status='QUEUED'))
        db.commit()
        return JSONResponse(status_code=201, content=cash_out(current_cash, booking, collector))
    if current_cash.status == 'PAID' or current_cash.created_by == user.id:
        db.commit()
        return cash_out(current_cash, booking, collector)  # repeat of a confirmation already given
    # The other side confirms: the cash payment is settled. Commission is owed by the Owner (owner decision).
    moment = now()
    commission, _, net = split(current_cash.amount, db.get(ServiceType, booking.service_type_id), 0, service_days(booking))
    current_cash.status = 'PAID'
    current_cash.authorized_at = current_cash.created_at
    current_cash.captured_at = moment
    current_cash.commission_amount = commission
    current_cash.owner_net_amount = net
    current_cash.owner_settlement_status = 'COMMISSION_DUE' if commission > 0 else None
    touch(current_cash); current_cash.updated_by = user.id
    booking.payment_status_snapshot = 'PAID'
    touch(booking); booking.updated_by = user.id
    for recipient in (booking.passenger_user_id, booking.owner_user_id):
        tell(db, recipient, booking, 'PAYMENT', 'Cash payment confirmed',
             f'Both sides confirmed {format(current_cash.amount, ".2f")} {current_cash.currency} in cash for booking {booking.booking_reference}.')
    db.commit()
    return cash_out(current_cash, booking, collector)


def cash_out(payment, booking, collector):
    settled = payment.status == 'PAID'
    return {**payment_out(payment), 'booking_payment_status': booking.payment_status_snapshot,
            'passenger_confirmed': settled or payment.created_by == booking.passenger_user_id,
            'collector_confirmed': settled or payment.created_by == collector}


@router.get('/bookings/{booking_id}/payment-summary')
def payment_summary(booking_id: UUID, user=Depends(current), db: Session = Depends(get_db)):
    """The payment panel of a private-hire booking: what is due, how it can be paid, and where the cash confirmation is."""
    booking = db.get(Booking, booking_id)
    trip = finished_trip(db, booking) if booking else None
    allowed = booking and (user.id in (booking.passenger_user_id, booking.owner_user_id) or (trip and user.id == trip.driver_user_id)
                           or is_admin(db, user))
    if not allowed or booking.booking_type not in HIRED:
        raise ApiError(404, 'BOOKING_NOT_FOUND', 'Booking not found.')
    return {'booking_id': str(booking.id), 'booking_status': booking.status, **payment_view(db, booking, user)}


# --------------------------------------------------------------------------- Owner: accept cash per vehicle service

@router.patch('/vehicles/{vehicle_id}/services/{service_type_id}/payment-options')
def update_payment_options(vehicle_id: UUID, service_type_id: UUID, body: PaymentOptions, user=Depends(current),
                           db: Session = Depends(get_db)):
    require_role(db, user, 'OWNER')
    vehicle = db.scalar(select(Vehicle).where(Vehicle.id == vehicle_id, Vehicle.owner_user_id == user.id))
    if not vehicle:
        raise ApiError(404, 'VEHICLE_NOT_FOUND', 'Vehicle not found.')
    service = db.get(ServiceType, service_type_id)
    row = db.scalar(select(VehicleService).where(VehicleService.vehicle_id == vehicle.id, VehicleService.service_type_id == service_type_id)
                    .with_for_update().execution_options(populate_existing=True))
    if not service or not row:
        raise ApiError(404, 'VEHICLE_SERVICE_NOT_FOUND', 'Save this service and its prices first.')
    if service.category == 'TICKET_HIRE' and body.cash_accepted:
        raise ApiError(422, 'CASH_NOT_ALLOWED', 'Ticket seats are paid online only.',
                       [{'field': 'cash_accepted', 'message': 'Not available for ticket departures.'}])
    if row.version != body.expected_version:
        raise ApiError(409, 'VERSION_CONFLICT', 'This service changed. Reload before saving.')
    row.owner_terms = {**(row.owner_terms or {}), 'cash': {'accepted': body.cash_accepted, 'collection_stage': 'END'}}
    touch(row); row.updated_by = user.id
    db.commit()
    return {'vehicle_id': str(vehicle.id), 'service_type_id': str(service_type_id), 'version': row.version,
            'cash_accepted': body.cash_accepted, 'cash_collection_stage': 'END'}


# --------------------------------------------------------------------------- Admin payment settings (service_types.settings)

def settings_out(row, settings=None):
    return {'id': str(row.id), 'code': row.code, 'name': row.name, 'category': row.category, 'is_active': row.is_active,
            'version': row.version, **payment_settings(row), 'supports_multi_day_commission': long_distance(row), 'available_providers': sorted(providers(settings))}


@router.get('/admin/payment-settings')
def list_payment_settings(request: Request, user=Depends(admin), db: Session = Depends(get_db)):
    rows = db.scalars(select(ServiceType).order_by(ServiceType.display_order, ServiceType.code).limit(100)).all()
    return {'items': [settings_out(r, request.app.state.settings) for r in rows]}


@router.patch('/admin/service-types/{service_id}/payment-settings')
def update_payment_settings(service_id: UUID, body: PaymentSettings, request: Request, user=Depends(admin),
                            db: Session = Depends(get_db)):
    if body.payment_provider not in providers(request.app.state.settings):
        raise ApiError(422, 'PAYMENT_PROVIDER_UNAVAILABLE', f'{body.payment_provider} is not connected yet. Add its credentials first, or use SANDBOX.',
                       [{'field': 'payment_provider', 'message': 'Not connected yet.'}])
    multi = body.multi_day_commission_percent
    if multi is not None:
        if Decimal(multi) + Decimal(body.gateway_fee_percent) > 100:
            raise ApiError(422, 'PAYMENT_SETTINGS_INVALID', 'Multi-day commission and gateway fee together cannot be more than 100%.',
                           [{'field': 'multi_day_commission_percent', 'message': 'Commission + gateway fee must be 100% or less.'}])
    if Decimal(body.commission_percent) + Decimal(body.gateway_fee_percent) > 100:
        # The Owner must always keep something: commission and the gateway fee both come out of the fare.
        raise ApiError(422, 'PAYMENT_SETTINGS_INVALID', 'Commission and gateway fee together cannot be more than 100%.',
                       [{'field': 'gateway_fee_percent', 'message': 'Commission + gateway fee must be 100% or less.'}])
    with request.app.state.audit.coordinated():
        locked_authority(db, request, user, user.id)
        row = db.scalar(select(ServiceType).where(ServiceType.id == service_id).with_for_update()
                        .execution_options(populate_existing=True))
        if not row:
            raise ApiError(404, 'SERVICE_NOT_FOUND', 'Service not found.')
        if row.version != body.expected_version:
            raise ApiError(409, 'VERSION_CONFLICT', 'Service configuration changed. Reload before saving.')
        if multi is not None and not long_distance(row):
            raise ApiError(422, 'MULTI_DAY_COMMISSION_NOT_ALLOWED', 'A separate multi-day commission is only for Long-distance services.',
                           [{'field': 'multi_day_commission_percent', 'message': 'Only for Long-distance services.'}])
        before, old = row.version, json.loads(json.dumps(row.settings or {}))
        new = {**(row.settings or {}), 'payment_provider': body.payment_provider,
               'commission_percent': body.commission_percent, 'gateway_fee_percent': body.gateway_fee_percent}
        new.pop('multi_day_commission_percent', None)
        if multi is not None:
            new['multi_day_commission_percent'] = multi
        row.settings = new
        touch(row)
        row.updated_by = user.id
        request.app.state.audit.commit(db, actor=user.id, target={'resource': 'service_types', 'id': str(row.id)},
                                       previous_status=None, new_status=None, previous_version=before, new_version=row.version,
                                       full_reason=None, previous_decision_evidence={'settings': old},
                                       trace_id=request.state.trace_id)
    return settings_out(row, request.app.state.settings)
