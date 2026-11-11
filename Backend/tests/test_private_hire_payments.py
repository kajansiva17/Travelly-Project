"""Payments slice 2: private hire is paid after the trip, online or in cash (owner decisions, 11 Nov 2026).

No advance (CF01). Cash only when the Owner accepts it for that vehicle service, collected at the END, confirmed by
both the Passenger and the collector (the trip's Driver / self-driving Owner). Commission applies to cash too and is
owed by the Owner (COMMISSION_DUE).
"""
from decimal import Decimal
from uuid import UUID, uuid4
import pytest
from sqlalchemy import select
from app.models.hire_models import Booking
from app.models.payment_models import Payment
from app.models.rate_models import ServiceType
from conftest import bearer, signed_in
from test_rates import rule, rate_owner
from test_hire_pricing import hire_setup, committed
from test_trip_operations import running


@pytest.fixture
def completed(client, running):
    c = running.ctx
    done = client.post(f"/api/v1/trips/{running.trip['id']}/complete", headers=bearer(c.owner),
                       json={'expected_version': running.trip['version'], 'end_odometer_km': '1300.5'})
    assert done.status_code == 200, done.text
    summary = client.get(f"/api/v1/bookings/{running.booking['id']}/payment-summary", headers=bearer(c.passenger)).json()
    return type('Done', (), {'ctx': c, 'booking': running.booking, 'summary': summary})


def summary(client, run, who=None):
    return client.get(f"/api/v1/bookings/{run.booking['id']}/payment-summary", headers=bearer(who or run.ctx.passenger)).json()


def pay_online(client, run, key=None):
    total = summary(client, run)['amount_due'] or run.booking['total_amount']
    return client.post(f"/api/v1/bookings/{run.booking['id']}/payment-intents", headers=bearer(run.ctx.passenger),
                       json={'amount': total, 'currency': 'LKR', 'method': 'SANDBOX', 'idempotency_key': key or uuid4().hex})


def accept_cash(client, run, accepted=True):
    service = next(s for s in client.get(f"/api/v1/vehicles/{run.ctx.vehicle_id}/services", headers=bearer(run.ctx.owner)).json()['items']
                   if s['service_type_id'] == str(run.ctx.service_id))
    return client.patch(f"/api/v1/vehicles/{run.ctx.vehicle_id}/services/{run.ctx.service_id}/payment-options",
                        headers=bearer(run.ctx.owner), json={'expected_version': service['version'], 'cash_accepted': accepted})


def cash(client, run, who, passenger, stage='END', collector=None, amount=None):
    s = summary(client, run)
    body = {'amount': amount or s['amount_due'], 'currency': 'LKR', 'collection_stage': stage,
            'collector_user_id': collector or s['collector_user_id'], 'passenger_confirmation': passenger,
            'collector_confirmation': not passenger, 'idempotency_key': uuid4().hex}
    return client.post(f"/api/v1/bookings/{run.booking['id']}/cash-receipts", headers=bearer(who), json=body)


def test_nothing_is_paid_before_the_trip_is_completed(client, running):
    early = client.post(f"/api/v1/bookings/{running.booking['id']}/payment-intents", headers=bearer(running.ctx.passenger),
                        json={'amount': running.booking['total_amount'], 'currency': 'LKR', 'method': 'SANDBOX',
                              'idempotency_key': uuid4().hex})
    assert early.status_code == 409 and early.json()['code'] == 'PAYMENT_NOT_DUE'
    assert summary(client, running)['payment_due'] is False


def test_after_the_trip_the_passenger_pays_online_and_the_owner_is_payable(client, completed):
    s = completed.summary
    assert s['payment_due'] and s['amount_due'] == completed.booking['total_amount'] and s['booking_status'] == 'COMPLETED'
    assert (s['payment_provider'], s['payment_method'], s['payer_details_required']) == ('SANDBOX', 'SANDBOX', [])
    assert s['cash_accepted'] is False and s['cash_collection_stage'] == 'END' and s['collector_user_id']
    created = pay_online(client, completed)
    assert created.status_code == 201, created.text
    paid = client.post(f"/api/v1/payments/{created.json()['id']}/sandbox-outcome", headers=bearer(completed.ctx.passenger),
                       json={'outcome': 'SUCCEEDED'})
    assert paid.status_code == 200 and paid.json()['status'] == 'PAID' and paid.json()['booking_status'] == 'COMPLETED'
    owner_view = client.get(f"/api/v1/bookings/{completed.booking['id']}/payments", headers=bearer(completed.ctx.owner)).json()['items'][0]
    assert owner_view['owner_settlement_status'] == 'OWNER_PAYABLE' and owner_view['owner_payable_at']
    after = summary(client, completed)
    assert after['payment_due'] is False and after['payment_status'] == 'PAID' and after['amount_due'] is None
    assert pay_online(client, completed).json()['code'] == 'BOOKING_ALREADY_PAID'


def test_cash_needs_the_owner_to_accept_it(client, completed):
    refused = cash(client, completed, completed.ctx.passenger, passenger=True)
    assert refused.status_code == 409 and refused.json()['code'] == 'CASH_NOT_ACCEPTED'
    enabled = accept_cash(client, completed)
    assert enabled.status_code == 200 and enabled.json()['cash_accepted'] is True
    assert summary(client, completed)['cash_accepted'] is True
    stale = client.patch(f"/api/v1/vehicles/{completed.ctx.vehicle_id}/services/{completed.ctx.service_id}/payment-options",
                         headers=bearer(completed.ctx.owner), json={'expected_version': 1, 'cash_accepted': False})
    assert stale.status_code == 409


def test_cash_is_settled_only_when_both_sides_confirm_and_commission_is_owed(client, completed):
    assert accept_cash(client, completed).status_code == 200
    with client.app.state.sessions() as db:
        service = db.get(ServiceType, completed.ctx.service_id)
        service.settings = {**service.settings, 'commission_percent': '10.00'}
        db.commit()
    first = cash(client, completed, completed.ctx.passenger, passenger=True)
    assert first.status_code == 201, first.text
    assert first.json()['status'] == 'CASH_AWAITING_CONFIRMATION'
    assert (first.json()['passenger_confirmed'], first.json()['collector_confirmed']) == (True, False)
    again = cash(client, completed, completed.ctx.passenger, passenger=True)
    assert again.status_code == 200 and again.json()['id'] == first.json()['id'] and again.json()['status'] == 'CASH_AWAITING_CONFIRMATION'
    waiting = summary(client, completed, completed.ctx.owner)
    assert waiting['payment_status'] == 'CASH_AWAITING_CONFIRMATION' and waiting['cash']['passenger_confirmed'] and not waiting['cash']['collector_confirmed']
    online = pay_online(client, completed)
    assert online.status_code == 409 and online.json()['code'] == 'PAYMENT_IN_PROGRESS'
    settled = cash(client, completed, completed.ctx.owner, passenger=False)
    assert settled.status_code == 200 and settled.json()['status'] == 'PAID'
    assert settled.json()['passenger_confirmed'] and settled.json()['collector_confirmed']
    with client.app.state.sessions() as db:
        row = db.get(Payment, UUID(first.json()['id']))
        total = db.get(Booking, UUID(completed.booking['id'])).total_amount
        assert row.payment_method == 'CASH' and row.provider_name is None
        assert row.commission_amount == (total / 10).quantize(Decimal('0.01')) and row.owner_net_amount == total - row.commission_amount
        assert row.owner_settlement_status == 'COMMISSION_DUE'


def test_cash_rules_end_only_own_confirmation_right_collector(client, completed):
    assert accept_cash(client, completed).status_code == 200
    start = cash(client, completed, completed.ctx.passenger, passenger=True, stage='START')
    assert start.status_code == 422 and start.json()['code'] == 'CASH_COLLECTION_STAGE_INVALID'
    s = summary(client, completed)
    body = {'amount': s['amount_due'], 'currency': 'LKR', 'collection_stage': 'END', 'collector_user_id': s['collector_user_id'],
            'passenger_confirmation': True, 'collector_confirmation': True, 'idempotency_key': uuid4().hex}
    both = client.post(f"/api/v1/bookings/{completed.booking['id']}/cash-receipts", headers=bearer(completed.ctx.passenger), json=body)
    assert both.status_code == 422 and both.json()['code'] == 'CONFIRMATION_NOT_YOURS'
    wrong = cash(client, completed, completed.ctx.passenger, passenger=True, collector=str(uuid4()))
    assert wrong.status_code == 422 and wrong.json()['code'] == 'COLLECTOR_NOT_ASSIGNED'
    short = cash(client, completed, completed.ctx.passenger, passenger=True, amount='1.00')
    assert short.status_code == 422 and short.json()['code'] == 'PAYMENT_AMOUNT_MISMATCH'
    stranger = signed_in(client, {'full_name': 'Passer By', 'email': uuid4().hex + '@example.com',
                                  'phone_e164': '+9477' + str(uuid4().int % 10000000).zfill(7),
                                  'password': 'TravellyStrong1!', 'accept_terms': True})[1]
    assert cash(client, completed, stranger, passenger=True).status_code == 404
    assert client.get(f"/api/v1/bookings/{completed.booking['id']}/payment-summary", headers=bearer(stranger)).status_code == 404


def test_an_open_online_payment_blocks_cash(client, completed):
    assert accept_cash(client, completed).status_code == 200
    assert pay_online(client, completed).status_code == 201
    blocked = cash(client, completed, completed.ctx.passenger, passenger=True)
    assert blocked.status_code == 409 and blocked.json()['code'] == 'PAYMENT_IN_PROGRESS'
