"""PayHere provider (Sandbox credentials) behind the same payment flow. Fake credentials; no network calls.

Checkout fields and the md5sig check follow https://support.payhere.lk/api-&-mobile-sdk/checkout-api.
Owner decision (11 Nov 2026): address and city are asked on the Pay screen and passed to PayHere, never stored.
"""
import hashlib
from urllib.parse import urlencode
from uuid import UUID, uuid4
import pytest
from sqlalchemy import select
from app.models.hire_models import Booking
from app.models.payment_models import Payment
from app.models.seat_models import ScheduledTripSeat
from test_ticket_holds import api, person, ticket, configure_hold, hold_body

MERCHANT, SECRET, PUBLIC = '1211149', 'test-merchant-secret', 'https://api.travelly.test'
PAYER = {'address': '12 Galle Road', 'city': 'Colombo'}


def md5(text):
    return hashlib.md5(text.encode()).hexdigest().upper()


def settings_row(client, t):
    return next(i for i in api(client, t['admin'], 'get', '/admin/payment-settings').json()['items'] if i['id'] == t['service']['id'])


def use_provider(client, t, name):
    row = settings_row(client, t)
    return api(client, t['admin'], 'patch', f"/admin/service-types/{row['id']}/payment-settings",
               {'expected_version': row['version'], 'payment_provider': name, 'commission_percent': '0', 'gateway_fee_percent': '3.3'})


@pytest.fixture
def payhere(client, ticket, monkeypatch):
    monkeypatch.setenv('PAYHERE_MERCHANT_ID', MERCHANT)
    monkeypatch.setenv('PAYHERE_MERCHANT_SECRET', SECRET)
    monkeypatch.setenv('PUBLIC_API_URL', PUBLIC)
    configure_hold(client, ticket)
    assert use_provider(client, ticket, 'PAYHERE').status_code == 200
    passenger = person(client)
    booking = api(client, passenger, 'post', '/bookings/ticket-holds', hold_body(ticket, ['A1', 'A2'])).json()
    return {**ticket, 'passenger': passenger, 'booking': booking}


def intent(client, t, payer=PAYER, method='CARD'):
    body = {'amount': '3000.00', 'currency': 'LKR', 'method': method, 'idempotency_key': uuid4().hex}
    if payer is not None:
        body['payer'] = payer
    return api(client, t['passenger'], 'post', f"/bookings/{t['booking']['id']}/payment-intents", body)


def notify(client, order_id, status_code='2', amount='3000.00', merchant=MERCHANT, secret=SECRET, method='VISA', sig=None):
    form = {'merchant_id': merchant, 'order_id': order_id, 'payment_id': '320032'+uuid4().hex[:6], 'payhere_amount': amount,
            'payhere_currency': 'LKR', 'status_code': status_code, 'method': method, 'status_message': 'test',
            'md5sig': sig or md5(merchant + order_id + amount + 'LKR' + status_code + md5(secret))}
    return client.post('/api/v1/payments/webhooks/payhere', content=urlencode(form),
                       headers={'content-type': 'application/x-www-form-urlencoded'})


def test_payhere_is_offered_only_when_its_credentials_are_set(client, ticket, monkeypatch):
    assert settings_row(client, ticket)['available_providers'] == ['SANDBOX']
    refused = use_provider(client, ticket, 'PAYHERE')
    assert refused.status_code == 422 and refused.json()['code'] == 'PAYMENT_PROVIDER_UNAVAILABLE'
    monkeypatch.setenv('PAYHERE_MERCHANT_ID', MERCHANT)
    monkeypatch.setenv('PAYHERE_MERCHANT_SECRET', SECRET)
    monkeypatch.setenv('PUBLIC_API_URL', 'http://not-https.test')
    assert settings_row(client, ticket)['available_providers'] == ['SANDBOX']  # PayHere must reach us over HTTPS
    monkeypatch.setenv('PUBLIC_API_URL', PUBLIC)
    assert settings_row(client, ticket)['available_providers'] == ['PAYHERE', 'SANDBOX']


def test_address_and_city_come_from_the_pay_screen(client, payhere):
    missing = intent(client, payhere, payer=None)
    assert missing.status_code == 422 and missing.json()['code'] == 'PAYER_DETAILS_REQUIRED'
    assert [f['field'] for f in missing.json()['field_errors']] == ['payer.address', 'payer.city']
    sandbox_method = intent(client, payhere, method='SANDBOX')
    assert sandbox_method.status_code == 422 and sandbox_method.json()['code'] == 'PAYMENT_METHOD_UNAVAILABLE'


def test_checkout_fields_are_signed_on_the_server(client, payhere):
    created = intent(client, payhere)
    assert created.status_code == 201, created.text
    payment, checkout = created.json(), created.json()['checkout']
    assert checkout['action'] == 'https://sandbox.payhere.lk/pay/checkout' and checkout['method'] == 'POST'
    fields = checkout['fields']
    assert fields['merchant_id'] == MERCHANT and fields['order_id'] == payment['payment_reference']
    assert fields['amount'] == '3000.00' and fields['currency'] == 'LKR'
    assert fields['hash'] == md5(MERCHANT + payment['payment_reference'] + '3000.00' + 'LKR' + md5(SECRET))
    assert fields['notify_url'] == PUBLIC + '/api/v1/payments/webhooks/payhere'
    assert fields['return_url'].endswith(f"/travel/book/tickets?booking={payhere['booking']['id']}&payment=returned")
    assert (fields['first_name'], fields['last_name'], fields['address'], fields['city']) == ('Test', 'Person', '12 Galle Road', 'Colombo')
    assert SECRET not in str(created.json())
    with client.app.state.sessions() as db:
        row = db.get(Payment, UUID(payment['id']))
        assert row.provider_name == 'PAYHERE' and row.payment_method == 'CARD'


def test_a_signed_success_notice_books_the_seats(client, payhere):
    payment = intent(client, payhere).json()
    done = notify(client, payment['payment_reference'], method='HELAPAY')
    assert done.status_code == 200 and done.json()['status'] == 'PAID'
    again = notify(client, payment['payment_reference'], method='HELAPAY')
    assert again.status_code == 200 and again.json()['status'] == 'PAID'
    with client.app.state.sessions() as db:
        row = db.get(Payment, UUID(payment['id']))
        assert row.payment_method == 'BANK' and row.provider_reference.startswith('320032')
        assert (row.commission_amount, row.owner_net_amount) == (0, 2901)  # 3.3% PayHere fee comes out of the Owner's share
        assert db.get(Booking, UUID(payhere['booking']['id'])).status == 'CONFIRMED'
        seats = db.scalars(select(ScheduledTripSeat.seat_status).where(ScheduledTripSeat.booked_booking_id == UUID(payhere['booking']['id']))).all()
    assert seats == ['BOOKED', 'BOOKED']


def test_forged_or_foreign_notices_are_refused(client, payhere):
    payment = intent(client, payhere).json()
    assert notify(client, payment['payment_reference'], sig='0' * 32).status_code == 401
    assert notify(client, payment['payment_reference'], merchant='999999').status_code == 401
    assert notify(client, payment['payment_reference'], secret='wrong-secret').status_code == 401
    as_json = client.post('/api/v1/payments/webhooks/payhere', json={'order_id': payment['payment_reference']})
    assert as_json.status_code == 415
    with client.app.state.sessions() as db:
        assert db.get(Payment, UUID(payment['id'])).status == 'PENDING'


def test_failed_cancelled_and_pending_notices(client, payhere):
    payment = intent(client, payhere).json()
    pending = notify(client, payment['payment_reference'], status_code='0')
    assert pending.status_code == 200 and pending.json()['status'] == 'PENDING'
    failed = notify(client, payment['payment_reference'], status_code='-2')
    assert failed.status_code == 200 and failed.json()['status'] == 'FAILED'
    with client.app.state.sessions() as db:
        row = db.get(Payment, UUID(payment['id']))
        assert row.failure_code == 'PAYHERE_FAILED'
        assert db.get(Booking, UUID(payhere['booking']['id'])).status == 'REQUESTED'


def test_a_waiting_payhere_payment_can_be_reopened_but_not_through_the_sandbox(client, payhere):
    payment = intent(client, payhere).json()
    reopened = api(client, payhere['passenger'], 'post', f"/payments/{payment['id']}/checkout", {'payer': PAYER})
    assert reopened.status_code == 200 and reopened.json()['checkout']['fields']['order_id'] == payment['payment_reference']
    no_payer = api(client, payhere['passenger'], 'post', f"/payments/{payment['id']}/checkout", {})
    assert no_payer.status_code == 422 and no_payer.json()['code'] == 'PAYER_DETAILS_REQUIRED'
    sandbox = api(client, payhere['passenger'], 'post', f"/payments/{payment['id']}/sandbox-outcome", {'outcome': 'SUCCEEDED'})
    assert sandbox.status_code == 404
    assert api(client, person(client), 'post', f"/payments/{payment['id']}/checkout", {'payer': PAYER}).status_code == 404
    notify(client, payment['payment_reference'])
    closed = api(client, payhere['passenger'], 'post', f"/payments/{payment['id']}/checkout", {'payer': PAYER})
    assert closed.status_code == 409 and closed.json()['code'] == 'PAYMENT_NOT_PENDING'
