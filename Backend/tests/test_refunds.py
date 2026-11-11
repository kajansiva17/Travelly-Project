"""Refunds and Passenger ticket cancellation (owner decisions, 11 Nov 2026).

Schedule: more than 72 h before departure 100%, 24-72 h 50%, under 24 h 0%. The system queues the refund; an Admin
approves (Sandbox: money back at once; PayHere: done in the PayHere portal, then recorded) or rejects with a reason.
"""
import json
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
import pytest
from sqlalchemy import select, update
from app.models.hire_models import Booking, Notification
from app.models.payment_models import Payment
from app.models.seat_models import ScheduledTripSeat
from test_ticket_holds import api, person, ticket, configure_hold, hold_body
from test_payments import held, intent, outcome, signed
from test_payhere import payhere, notify, intent as payhere_intent


@pytest.fixture
def paid(client, held):
    payment = intent(client, held).json()
    assert outcome(client, held, payment['id']).json()['status'] == 'PAID'
    return {**held, 'payment': payment}


def at(monkeypatch, t, hours_before):
    import app.api.routers.refund_api as module
    moment = datetime.fromisoformat(t['trip']['departure_at']) - timedelta(hours=hours_before)
    monkeypatch.setattr(module, 'now', lambda: moment)


def cancel(client, t, reason='Plans changed'):
    return api(client, t['passenger'], 'post', f"/bookings/{t['booking']['id']}/ticket-cancellation", {'reason': reason})


def refunds(client, t):
    return api(client, t['admin'], 'get', '/admin/refunds').json()


def decide(client, t, refund, decision='APPROVE', reason=None, version=None):
    body = {'expected_version': version or refund['version'], 'decision': decision}
    if reason:
        body['reason'] = reason
    return api(client, t['admin'], 'post', f"/admin/refunds/{refund['id']}/decision", body)


def test_cancelling_24_to_72_hours_before_frees_the_seats_and_queues_half(client, paid, monkeypatch):
    at(monkeypatch, paid, 48)
    done = cancel(client, paid)
    assert done.status_code == 200, done.text
    body = done.json()
    assert body['status'] == 'CANCELLED' and body['refund_percent'] == 50 and body['hours_before_departure'] == 48
    assert body['refund']['amount'] == '1500.00' and body['refund']['transaction_type'] == 'PARTIAL_REFUND'
    assert body['refund']['status'] == 'PENDING' and body['refund']['cause'] == 'PASSENGER_CANCELLATION'
    with client.app.state.sessions() as db:
        seats = db.scalars(select(ScheduledTripSeat.seat_status).where(ScheduledTripSeat.id.in_(
            [UUID(paid['seats']['A1']), UUID(paid['seats']['A2'])]))).all()
        snapshot = db.get(Booking, UUID(paid['booking']['id'])).cancellation_policy_snapshot
    assert seats == ['AVAILABLE', 'AVAILABLE'] and snapshot['refund_percent'] == 50
    assert cancel(client, paid).json()['code'] == 'TICKET_NOT_CANCELLABLE'


def test_more_than_72_hours_is_full_and_under_24_is_nothing(client, paid, monkeypatch):
    at(monkeypatch, paid, 80)
    full = cancel(client, paid).json()
    assert full['refund_percent'] == 100 and full['refund']['amount'] == '3000.00' and full['refund']['transaction_type'] == 'FULL_REFUND'


def test_under_24_hours_no_refund(client, paid, monkeypatch):
    at(monkeypatch, paid, 10)
    late = cancel(client, paid).json()
    assert late['refund_percent'] == 0 and late['refund'] is None and late['status'] == 'CANCELLED'
    with client.app.state.sessions() as db:
        assert db.scalar(select(Payment.id).where(Payment.original_payment_id == UUID(paid['payment']['id']))) is None


def test_only_paid_tickets_before_departure_can_be_cancelled(client, held, monkeypatch):
    unpaid = cancel(client, held)
    assert unpaid.status_code == 409 and unpaid.json()['code'] == 'TICKET_NOT_CANCELLABLE'
    payment = intent(client, held).json()
    outcome(client, held, payment['id'])
    at(monkeypatch, held, -1)
    gone = cancel(client, held)
    assert gone.status_code == 409 and gone.json()['code'] == 'DEPARTURE_STARTED'
    assert api(client, person(client), 'post', f"/bookings/{held['booking']['id']}/ticket-cancellation", {'reason': 'x'}).status_code == 404


def test_admin_approves_a_sandbox_refund_and_the_money_goes_back(client, paid, monkeypatch):
    at(monkeypatch, paid, 48)
    cancel(client, paid)
    listed = refunds(client, paid)
    assert listed['waiting'] == 1 and listed['items'][0]['status'] == 'PENDING'
    refund = listed['items'][0]
    assert refund['booking_reference'] and refund['original_amount'] == '3000.00' and refund['cancellation']['refund_percent'] == 50
    assert decide(client, paid, refund, version=refund['version'] + 1).status_code == 409
    approved = decide(client, paid, refund)
    assert approved.status_code == 200, approved.text
    assert approved.json()['status'] == 'PAID' and approved.json()['refunded_at']
    assert decide(client, paid, approved.json()).json()['code'] == 'REFUND_ALREADY_DECIDED'
    with client.app.state.sessions() as db:
        original = db.get(Payment, UUID(paid['payment']['id']))
        booking = db.get(Booking, UUID(paid['booking']['id']))
        kinds = db.scalars(select(Notification.notification_type).where(Notification.booking_id == booking.id,
                                                                       Notification.title == 'Refund sent')).all()
    assert original.status == 'PARTIALLY_REFUNDED' and booking.payment_status_snapshot == 'PARTIALLY_REFUNDED' and kinds == ['REFUND']
    history = api(client, paid['passenger'], 'get', f"/bookings/{paid['booking']['id']}/payments").json()['items']
    assert [h['transaction_type'] for h in history] == ['PAYMENT', 'PARTIAL_REFUND']


def test_rejecting_needs_a_reason_and_keeps_the_payment(client, paid, monkeypatch):
    at(monkeypatch, paid, 80)
    cancel(client, paid)
    refund = refunds(client, paid)['items'][0]
    assert decide(client, paid, refund, 'REJECT').json()['code'] == 'REASON_REQUIRED'
    rejected = decide(client, paid, refund, 'REJECT', 'Duplicate request, already refunded at the counter.')
    assert rejected.status_code == 200 and rejected.json()['status'] == 'FAILED' and rejected.json()['failure_code'] == 'REFUND_REJECTED'
    with client.app.state.sessions() as db:
        assert db.get(Payment, UUID(paid['payment']['id'])).status == 'PAID'
    assert api(client, paid['passenger'], 'get', '/admin/refunds').status_code == 403


def test_a_payhere_refund_is_processed_in_the_portal_then_recorded(client, payhere, monkeypatch):
    payment = payhere_intent(client, payhere).json()
    assert notify(client, payment['payment_reference']).json()['status'] == 'PAID'
    at(monkeypatch, payhere, 80)
    assert cancel(client, payhere).status_code == 200
    refund = refunds(client, payhere)['items'][0]
    assert refund['provider_name'] == 'PAYHERE'
    processing = decide(client, payhere, refund).json()
    assert processing['status'] == 'PROCESSING'
    early = api(client, payhere['admin'], 'post', f"/admin/refunds/{refund['id']}/complete",
                {'expected_version': processing['version'], 'provider_reference': 'PH-REFUND-77'})
    assert early.status_code == 200 and early.json()['status'] == 'PAID' and early.json()['provider_reference'] == 'PH-REFUND-77'
    with client.app.state.sessions() as db:
        assert db.get(Payment, UUID(payment['id'])).status == 'REFUNDED'


def test_admin_refunds_a_payment_directly_once(client, paid):
    url = f"/payments/{paid['payment']['id']}/refunds"
    both = api(client, paid['admin'], 'post', url, {'full': True, 'amount': '10.00', 'reason': 'Goodwill', 'idempotency_key': uuid4().hex})
    assert both.status_code == 422
    too_much = api(client, paid['admin'], 'post', url, {'full': False, 'amount': '5000.00', 'reason': 'Goodwill', 'idempotency_key': uuid4().hex})
    assert too_much.status_code == 422 and too_much.json()['code'] == 'REFUND_AMOUNT_INVALID'
    key = uuid4().hex
    part = api(client, paid['admin'], 'post', url, {'full': False, 'amount': '500.00', 'reason': 'Late departure goodwill', 'idempotency_key': key})
    assert part.status_code == 201, part.text
    assert part.json()['status'] == 'PAID' and part.json()['cause'] == 'ADMIN' and part.json()['amount'] == '500.00'
    again = api(client, paid['admin'], 'post', url, {'full': False, 'amount': '500.00', 'reason': 'Late departure goodwill', 'idempotency_key': key})
    assert again.json()['id'] == part.json()['id']
    rest = api(client, paid['admin'], 'post', url, {'full': True, 'reason': 'Trip cancelled by operator', 'idempotency_key': uuid4().hex})
    assert rest.status_code == 201 and rest.json()['amount'] == '2500.00'
    with client.app.state.sessions() as db:
        assert db.get(Payment, UUID(paid['payment']['id'])).status == 'REFUNDED'
    assert api(client, paid['owner'], 'post', url, {'full': True, 'reason': 'x', 'idempotency_key': uuid4().hex}).status_code == 403


def test_money_after_the_hold_ended_queues_a_full_refund(client, held):
    pending = intent(client, held).json()
    with client.app.state.sessions() as db:
        db.execute(update(ScheduledTripSeat).where(ScheduledTripSeat.held_by_booking_id == UUID(held['booking']['id']))
                   .values(hold_expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)))
        db.commit()
    signed(client, {'payment_reference': pending['payment_reference'], 'provider_reference': 'SBX-LATE', 'outcome': 'SUCCEEDED',
                    'amount': '3000.00', 'currency': 'LKR'})
    refund = refunds(client, held)['items'][0]
    assert refund['cause'] == 'PAYMENT_AFTER_HOLD' and refund['amount'] == '3000.00' and refund['status'] == 'PENDING'
