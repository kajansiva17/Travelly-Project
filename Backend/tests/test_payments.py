"""Payments slice 1: online Ticket seats through the Sandbox provider, on the PRD `payments` table.

Owner decisions (11 Nov 2026): Sandbox now, PayHere later; commission is an Admin percentage per service type;
the gateway fee comes out of the Owner's share.
"""
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4
import pytest
from sqlalchemy import select, update
from app.models.hire_models import Booking, Notification
from app.models.payment_models import Payment
from app.models.seat_models import ScheduledTripSeat
from app.services.payment_providers import SANDBOX
from test_ticket_holds import api, person, ticket, configure_hold, hold_body
from test_departure_trips import drivable, journey, at_departure


@pytest.fixture
def held(client, ticket):
    """A Passenger holding seats A1 and A2 (2 x 1500.00 = 3000.00)."""
    configure_hold(client, ticket)
    passenger = person(client)
    booking = api(client, passenger, 'post', '/bookings/ticket-holds', hold_body(ticket, ['A1', 'A2']))
    assert booking.status_code == 201, booking.text
    return {**ticket, 'passenger': passenger, 'booking': booking.json()}


def intent(client, t, amount='3000.00', method='SANDBOX', key=None, who=None):
    return api(client, who or t['passenger'], 'post', f"/bookings/{t['booking']['id']}/payment-intents",
               {'amount': amount, 'currency': 'LKR', 'method': method, 'idempotency_key': key or uuid4().hex})


def outcome(client, t, payment_id, result='SUCCEEDED', who=None):
    return api(client, who or t['passenger'], 'post', f'/payments/{payment_id}/sandbox-outcome', {'outcome': result})


def seat_states(client, t):
    with client.app.state.sessions() as db:
        return {str(s.id): s.seat_status for s in db.scalars(select(ScheduledTripSeat).where(
            ScheduledTripSeat.id.in_([UUID(t['seats'][c]) for c in ('A1', 'A2')])))}


def expire_hold(client, t):
    with client.app.state.sessions() as db:
        db.execute(update(ScheduledTripSeat).where(ScheduledTripSeat.held_by_booking_id == UUID(t['booking']['id']))
                   .values(hold_expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)))
        db.commit()


def test_paying_in_full_books_the_seats_and_confirms_the_booking(client, held):
    created = intent(client, held)
    assert created.status_code == 201, created.text
    payment = created.json()
    assert payment['status'] == 'PENDING' and payment['amount'] == '3000.00' and payment['provider_name'] == 'SANDBOX'
    assert payment['checkout']['mode'] == 'SANDBOX'
    paid = outcome(client, held, payment['id'])
    assert paid.status_code == 200, paid.text
    assert paid.json()['status'] == 'PAID' and paid.json()['booking_status'] == 'CONFIRMED'
    assert set(seat_states(client, held).values()) == {'BOOKED'}
    ticket_view = api(client, held['passenger'], 'get', f"/bookings/{held['booking']['id']}/ticket").json()
    assert ticket_view['status'] == 'CONFIRMED' and ticket_view['payment_status'] == 'PAID' and not ticket_view['hold_active']
    with client.app.state.sessions() as db:
        kinds = sorted(db.scalars(select(Notification.notification_type)
                                  .where(Notification.booking_id == UUID(held['booking']['id']))).all())
    assert kinds == ['BOOKING_CONFIRMED', 'PAYMENT']
    again = outcome(client, held, payment['id'])
    assert again.status_code == 200 and again.json()['status'] == 'PAID'
    assert intent(client, held).json()['code'] == 'BOOKING_ALREADY_PAID'


def test_the_full_amount_and_an_available_method_are_required(client, held):
    short = intent(client, held, amount='1500.00')
    assert short.status_code == 422 and short.json()['code'] == 'PAYMENT_AMOUNT_MISMATCH'
    card = intent(client, held, method='CARD')
    assert card.status_code == 422 and card.json()['code'] == 'PAYMENT_METHOD_UNAVAILABLE'
    stranger = intent(client, held, who=person(client))
    assert stranger.status_code == 404


def test_a_repeated_request_returns_the_same_payment_and_only_one_can_be_open(client, held):
    key = uuid4().hex
    first = intent(client, held, key=key)
    replay = intent(client, held, key=key)
    assert first.status_code == 201 and replay.status_code == 200
    assert replay.json()['id'] == first.json()['id']
    other = intent(client, held)
    assert other.status_code == 409 and other.json()['code'] == 'PAYMENT_IN_PROGRESS'
    assert other.json()['field_errors'] == [{'field': 'payment_id', 'message': first.json()['id']}]
    view = api(client, held['passenger'], 'get', f"/bookings/{held['booking']['id']}/ticket").json()
    assert view['latest_payment']['id'] == first.json()['id'] and view['latest_payment']['status'] == 'PENDING'
    assert view['payment_status'] == 'PENDING'


def test_a_failed_payment_keeps_the_hold_so_the_passenger_can_try_again(client, held):
    first = intent(client, held).json()
    failed = outcome(client, held, first['id'], 'FAILED')
    assert failed.status_code == 200 and failed.json()['status'] == 'FAILED'
    assert failed.json()['booking_status'] == 'REQUESTED'
    assert set(seat_states(client, held).values()) == {'HELD'}
    assert outcome(client, held, first['id']).json()['code'] == 'PAYMENT_NOT_PENDING'
    second = intent(client, held).json()
    assert outcome(client, held, second['id']).json()['status'] == 'PAID'
    history = api(client, held['passenger'], 'get', f"/bookings/{held['booking']['id']}/payments").json()
    assert [p['status'] for p in history['items']] == ['FAILED', 'PAID'] and history['payment_status'] == 'PAID'


def test_no_payment_after_the_hold_has_ended(client, held):
    pending = intent(client, held).json()
    expire_hold(client, held)
    late = outcome(client, held, pending['id'])
    assert late.status_code == 410 and late.json()['code'] == 'HOLD_EXPIRED'
    assert set(seat_states(client, held).values()) == {'AVAILABLE'}
    with client.app.state.sessions() as db:
        row = db.get(Payment, UUID(pending['id']))
        assert row.status == 'FAILED' and row.failure_code == 'HOLD_EXPIRED'
        assert db.get(Booking, UUID(held['booking']['id'])).status == 'CANCELLED'
    assert intent(client, held).status_code == 410


def test_releasing_the_hold_fails_the_waiting_payment(client, held):
    pending = intent(client, held).json()
    released = api(client, held['passenger'], 'delete', f"/bookings/{held['booking']['id']}/seat-hold", {})
    assert released.status_code == 204, released.text
    with client.app.state.sessions() as db:
        row = db.get(Payment, UUID(pending['id']))
        assert row.status == 'FAILED' and row.failure_code == 'BOOKING_CANCELLED'


def signed(client, body, signature=None):
    raw = json.dumps(body).encode()
    return client.post('/api/v1/payments/webhooks/sandbox', content=raw,
                       headers={'content-type': 'application/json',
                                'x-travelly-signature': signature or SANDBOX.sign(raw)})


def test_provider_events_must_be_signed_and_a_retry_never_charges_twice(client, held):
    pending = intent(client, held).json()
    event = {'payment_reference': pending['payment_reference'], 'provider_reference': 'SBX-1', 'outcome': 'SUCCEEDED',
             'amount': '3000.00', 'currency': 'LKR'}
    forged = signed(client, event, signature='0' * 64)
    assert forged.status_code == 401 and forged.json()['code'] == 'INVALID_SIGNATURE'
    first = signed(client, event)
    retry = signed(client, event)
    assert first.status_code == 200 and retry.status_code == 200
    assert first.json()['status'] == retry.json()['status'] == 'PAID'
    with client.app.state.sessions() as db:
        rows = db.scalars(select(Payment).where(Payment.booking_id == UUID(held['booking']['id']))).all()
    assert len(rows) == 1 and rows[0].provider_reference == 'SBX-1'
    wrong = signed(client, {**event, 'amount': '1.00'})
    assert wrong.status_code == 422 and wrong.json()['code'] == 'PAYMENT_AMOUNT_MISMATCH'


def test_money_that_arrives_after_the_hold_is_recorded_and_flagged_for_refund(client, held):
    pending = intent(client, held).json()
    expire_hold(client, held)
    late = signed(client, {'payment_reference': pending['payment_reference'], 'provider_reference': 'SBX-LATE',
                           'outcome': 'SUCCEEDED', 'amount': '3000.00', 'currency': 'LKR'})
    assert late.status_code == 200 and late.json()['status'] == 'PAID'
    assert set(seat_states(client, held).values()) == {'AVAILABLE'}
    with client.app.state.sessions() as db:
        row = db.get(Payment, UUID(pending['id']))
        assert row.failure_code == 'SEATS_RELEASED_REFUND_DUE'
        assert db.get(Booking, UUID(held['booking']['id'])).status == 'CANCELLED'


def settings_for(client, t):
    items = api(client, t['admin'], 'get', '/admin/payment-settings').json()['items']
    return next(i for i in items if i['id'] == t['service']['id'])


def test_admin_sets_commission_and_fee_and_the_owner_absorbs_the_fee(client, held):
    current = settings_for(client, held)
    assert current['payment_provider'] == 'SANDBOX' and current['commission_percent'] == '0.00'
    body = {'expected_version': current['version'], 'payment_provider': 'SANDBOX',
            'commission_percent': '10', 'gateway_fee_percent': '2.5'}
    saved = api(client, held['admin'], 'patch', f"/admin/service-types/{current['id']}/payment-settings", body)
    assert saved.status_code == 200, saved.text
    assert saved.json()['commission_percent'] == '10.00' and saved.json()['gateway_fee_percent'] == '2.50'
    stale = api(client, held['admin'], 'patch', f"/admin/service-types/{current['id']}/payment-settings", body)
    assert stale.status_code == 409
    payment = intent(client, held).json()
    outcome(client, held, payment['id'])
    owner_view = api(client, held['owner'], 'get', f"/bookings/{held['booking']['id']}/payments").json()['items'][0]
    assert (owner_view['commission_amount'], owner_view['gateway_fee_amount'], owner_view['owner_net_amount']) == \
        ('300.00', '75.00', '2625.00')
    passenger_view = api(client, held['passenger'], 'get', f"/bookings/{held['booking']['id']}/payments").json()['items'][0]
    assert passenger_view['amount'] == '3000.00' and 'owner_net_amount' not in passenger_view
    assert api(client, person(client), 'get', f"/bookings/{held['booking']['id']}/payments").status_code == 404


def test_only_connected_providers_and_sane_percentages_are_accepted(client, held):
    current = settings_for(client, held)
    url = f"/admin/service-types/{current['id']}/payment-settings"
    base = {'expected_version': current['version'], 'payment_provider': 'SANDBOX', 'commission_percent': '0', 'gateway_fee_percent': '0'}
    payhere = api(client, held['admin'], 'patch', url, {**base, 'payment_provider': 'PAYHERE'})
    assert payhere.status_code == 422 and payhere.json()['code'] == 'PAYMENT_PROVIDER_UNAVAILABLE'
    over = api(client, held['admin'], 'patch', url, {**base, 'commission_percent': '80', 'gateway_fee_percent': '30'})
    assert over.status_code == 422 and over.json()['code'] == 'PAYMENT_SETTINGS_INVALID'
    assert api(client, held['admin'], 'patch', url, {**base, 'commission_percent': '101'}).status_code == 422
    assert api(client, held['owner'], 'patch', url, base).status_code == 403


def test_after_payment_the_driver_boards_and_completion_makes_it_payable_to_the_owner(client, drivable, monkeypatch):
    t = drivable
    configure_hold(client, t)
    passenger = person(client)
    booking = api(client, passenger, 'post', '/bookings/ticket-holds', hold_body(t, ['A1'])).json()
    t = {**t, 'passenger': passenger, 'booking': booking}
    payment = intent(client, t, amount='1500.00').json()
    assert outcome(client, t, payment['id']).json()['status'] == 'PAID'
    run = journey(client, t['trip']['id'])
    at_departure(monkeypatch, client, t)
    started = api(client, t['owner'], 'post', f"/trips/{run.id}/start",
                  {'expected_version': run.version, 'start_odometer_km': '4000.0', 'checklist_confirmed': True})
    assert started.status_code == 200, started.text
    traveller = api(client, t['owner'], 'get', f"/scheduled-trips/{t['trip']['id']}/travellers").json()['items'][0]
    assert traveller['can_board']
    boarded = api(client, t['owner'], 'post', f"/scheduled-trips/{t['trip']['id']}/boardings", {'traveller_id': traveller['traveller_id']})
    assert boarded.status_code == 200, boarded.text
    done = api(client, t['owner'], 'post', f"/trips/{run.id}/complete",
               {'expected_version': started.json()['version'], 'end_odometer_km': '4120.0'})
    assert done.status_code == 200, done.text
    owner_view = api(client, t['owner'], 'get', f"/bookings/{booking['id']}/payments").json()['items'][0]
    assert owner_view['owner_settlement_status'] == 'OWNER_PAYABLE' and owner_view['owner_payable_at']
