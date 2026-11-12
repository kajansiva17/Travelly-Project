"""PayHere Refund API (https://support.payhere.lk/api-&-mobile-sdk/refund-api).

An approved PayHere refund (status PROCESSING) is sent to PayHere *after* the approval is committed:
1. In its own transaction, the refund row is marked `failure_code = PAYHERE_REQUESTED` and committed, so a second
   push (another click, a retry) can never send the same refund twice.
2. The API is called outside any database lock:
   - OAuth client_credentials with App ID:App Secret.
   - POST /merchant/v1/payment/refund with payment_id, description, and amount only for a partial refund.
3. The answer is recorded in a new transaction:
   - Accepted (status 1): the refund is finished exactly as a manual completion would be, with
     provider_reference = "PHR-<refund number>".
   - Refused: failure_code PAYHERE_REFUND_FAILED with PayHere's message. The Admin can retry, or refund in the portal
     and record it (POST /admin/refunds/{id}/complete).
   - No answer (timeout, crash): the row stays PAYHERE_REQUESTED and is never pushed again. The Admin checks the
     PayHere portal and records it.

PayHere refunds only card payments. Other methods (wallets, bank) are marked PAYHERE_MANUAL_REQUIRED: refund by bank
transfer, then record it. Without App ID/Secret nothing is sent and refunds stay manual, as before.
"""
import base64
import time
import httpx
from sqlalchemy import select
from app.core.config import get_settings
from app.api.routers.api import touch
from app.models.hire_models import Booking
from app.models.payment_models import Payment
from app.services.refunds import finish_refund

HOSTS = {'sandbox': 'https://sandbox.payhere.lk', 'live': 'https://www.payhere.lk'}
_token = {'value': None, 'expires': 0.0, 'key': None}


def configured(settings=None):
    settings = settings or get_settings()
    return bool(settings.payhere_app_id.strip() and settings.payhere_app_secret.strip())


def post(url, **kwargs):
    """The only network call (tests replace it)."""
    return httpx.post(url, timeout=15, **kwargs)


def access_token(settings):
    key = (settings.payhere_mode, settings.payhere_app_id)
    if _token['value'] and _token['key'] == key and _token['expires'] > time.time() + 30:
        return _token['value']
    basic = base64.b64encode(f'{settings.payhere_app_id.strip()}:{settings.payhere_app_secret.strip()}'.encode()).decode()
    response = post(HOSTS[settings.payhere_mode] + '/merchant/v1/oauth/token', data={'grant_type': 'client_credentials'},
                    headers={'Authorization': 'Basic ' + basic, 'Content-Type': 'application/x-www-form-urlencoded'})
    body = response.json()
    if response.status_code != 200 or not body.get('access_token'):
        raise RuntimeError('PayHere did not accept the App ID and App Secret.')
    _token.update(value=body['access_token'], expires=time.time() + int(body.get('expires_in') or 0), key=key)
    return body['access_token']


def send(settings, payment_id, amount, full, description):
    """Returns (accepted, refund_number, message). Never raises for PayHere or network problems."""
    try:
        token = access_token(settings)
        payload = {'payment_id': payment_id, 'description': description[:200]}
        if not full:
            payload['amount'] = float(amount)
        response = post(HOSTS[settings.payhere_mode] + '/merchant/v1/payment/refund', json=payload,
                        headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
        body = response.json()
        if response.status_code == 401 or body.get('error') == 'invalid_token':
            _token.update(value=None)
        if body.get('status') == 1:
            return True, str(body.get('data') or ''), body.get('msg') or 'Refund accepted.'
        return False, None, str(body.get('msg') or body.get('error_description') or body.get('error') or 'PayHere refused the refund.')[:250]
    except (httpx.HTTPError, ValueError, RuntimeError) as exc:
        return False, None, str(exc)[:250] or 'PayHere could not be reached.'


def push(sessions, refund_id, actor, settings=None):
    """Send one approved PayHere refund. Returns 'PAID', 'FAILED', 'MANUAL', 'SKIPPED'."""
    settings = settings or get_settings()
    if not configured(settings):
        return 'SKIPPED'
    with sessions() as db:
        refund = db.scalar(select(Payment).where(Payment.id == refund_id).with_for_update())
        if (not refund or refund.status != 'PROCESSING' or refund.provider_name != 'PAYHERE'
                or refund.failure_code in ('PAYHERE_REQUESTED', 'PAYHERE_MANUAL_REQUIRED')):
            return 'SKIPPED'
        original = db.get(Payment, refund.original_payment_id)
        if original.payment_method != 'CARD' or not original.provider_reference:
            refund.failure_code = 'PAYHERE_MANUAL_REQUIRED'
            refund.failure_message = 'PayHere refunds only card payments. Refund by bank transfer, then record it as complete.'
            touch(refund); refund.updated_by = actor
            db.commit()
            return 'MANUAL'
        full = refund.amount >= original.amount
        payment_id, amount = original.provider_reference, refund.amount
        description = f'Travelly refund {refund.payment_reference}'
        refund.failure_code, refund.failure_message = 'PAYHERE_REQUESTED', 'Sent to PayHere; waiting for the answer.'
        touch(refund); refund.updated_by = actor
        db.commit()
    accepted, number, message = send(settings, payment_id, amount, full, description)
    with sessions() as db:
        refund = db.scalar(select(Payment).where(Payment.id == refund_id).with_for_update())
        if refund.status != 'PROCESSING':
            return 'SKIPPED'   # recorded meanwhile (manual completion)
        if accepted:
            original = db.scalar(select(Payment).where(Payment.id == refund.original_payment_id).with_for_update())
            booking = db.scalar(select(Booking).where(Booking.id == refund.booking_id).with_for_update())
            refund.failure_code = refund.failure_message = None
            finish_refund(db, refund, original, booking, actor, ('PHR-' + number) if number else 'PHR-' + refund.payment_reference)
            outcome = 'PAID'
        else:
            refund.failure_code, refund.failure_message = 'PAYHERE_REFUND_FAILED', message
            touch(refund); refund.updated_by = actor
            outcome = 'FAILED'
        db.commit()
    return outcome


def push_many(sessions, refund_ids, actor, settings=None):
    return {str(i): push(sessions, i, actor, settings) for i in refund_ids}
