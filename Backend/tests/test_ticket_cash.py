"""Ticket seats paid in cash on the bus, and the Owner's payment choice per vehicle service (owner decision, 25 Nov 2026).

ONLINE_ONLY (default) / CASH_ONLY / ONLINE_AND_CASH. A cash seat is booked at once; the departure's Driver marks the cash received at boarding;
cancelling before that is free and refunds nothing. Commission is owed by the Owner."""
from uuid import UUID, uuid4
import pytest
from sqlalchemy import select
from app.models.hire_models import Booking
from app.models.payment_models import Payment
from app.models.seat_models import ScheduledTripSeat
from test_departure_trips import drivable  # noqa: F401  (fixture)
from test_ticket_holds import api, configure_hold, hold_body, person, ticket  # noqa: F401


def set_mode(client, t, mode, version=1):
    return api(client, t['owner'], 'patch', f"/vehicles/{t['trip']['vehicle_id']}/services/{t['service']['id']}/payment-options",
               {'expected_version': version, 'payment_mode': mode})


def hold(client, t, seats=('A1', 'A2')):
    configure_hold(client, t)
    passenger = person(client)
    held = api(client, passenger, 'post', '/bookings/ticket-holds', hold_body(t, list(seats)))
    assert held.status_code == 201, held.text
    return passenger, held.json()


def take_cash(client, passenger, booking, key=None, amount='3000.00'):
    return api(client, passenger, 'post', f"/bookings/{booking['id']}/ticket-cash",
               {'amount': amount, 'currency': 'LKR', 'idempotency_key': key or uuid4().hex})


def test_a_ticket_service_defaults_to_online_only_and_the_owner_can_change_it(client, drivable):
    t = drivable
    passenger, booking = hold(client, t)
    view = api(client, passenger, 'get', f"/bookings/{booking['id']}/ticket").json()
    assert (view['payment_mode'], view['online_accepted'], view['cash_accepted']) == ('ONLINE_ONLY', True, False)
    assert take_cash(client, passenger, booking).json()['code'] == 'CASH_NOT_ACCEPTED'
    changed = set_mode(client, t, 'CASH_ONLY')
    assert changed.status_code == 200, changed.text
    assert (changed.json()['payment_mode'], changed.json()['online_accepted'], changed.json()['cash_accepted'],
            changed.json()['cash_collection_stage']) == ('CASH_ONLY', False, True, 'BOARDING')
    assert api(client, t['owner'], 'patch', f"/vehicles/{t['trip']['vehicle_id']}/services/{t['service']['id']}/payment-options",
               {'expected_version': changed.json()['version']}).status_code == 422   # a choice is needed
    stale = set_mode(client, t, 'ONLINE_ONLY', version=99)
    assert stale.status_code == 409 and stale.json()['code'] == 'VERSION_CONFLICT'


def test_cash_only_blocks_online_payment_and_online_and_cash_allows_both(client, drivable):
    t = drivable
    passenger, booking = hold(client, t)
    version = set_mode(client, t, 'CASH_ONLY').json()['version']
    online = api(client, passenger, 'post', f"/bookings/{booking['id']}/payment-intents",
                 {'amount': '3000.00', 'currency': 'LKR', 'method': 'SANDBOX', 'idempotency_key': uuid4().hex})
    assert online.status_code == 409 and online.json()['code'] == 'ONLINE_NOT_ACCEPTED'
    both = set_mode(client, t, 'ONLINE_AND_CASH', version).json()
    assert both['online_accepted'] and both['cash_accepted']
    online = api(client, passenger, 'post', f"/bookings/{booking['id']}/payment-intents",
                 {'amount': '3000.00', 'currency': 'LKR', 'method': 'SANDBOX', 'idempotency_key': uuid4().hex})
    assert online.status_code == 201, online.text


def test_a_cash_seat_is_booked_at_once_and_the_driver_marks_the_cash_received(client, drivable):
    t = drivable   # the Owner drives this departure
    passenger, booking = hold(client, t)
    set_mode(client, t, 'CASH_ONLY')
    assert take_cash(client, passenger, booking, amount='1500.00').json()['code'] == 'PAYMENT_AMOUNT_MISMATCH'
    created = take_cash(client, passenger, booking, key='cash-key-0001')
    assert created.status_code == 201, created.text
    body = created.json()
    assert body['status'] == 'CASH_AWAITING_CONFIRMATION' and body['payment_method'] == 'CASH' and body['booking_status'] == 'CONFIRMED'
    again = take_cash(client, passenger, booking, key='cash-key-0001')
    assert again.status_code == 200 and again.json()['id'] == body['id']
    assert take_cash(client, passenger, booking).json()['code'] == 'BOOKING_ALREADY_PAID'
    with client.app.state.sessions() as db:
        seats = db.scalars(select(ScheduledTripSeat).where(ScheduledTripSeat.booked_booking_id == UUID(booking['id']))).all()
        assert len(seats) == 2 and {s.seat_status for s in seats} == {'BOOKED'}
    view = api(client, passenger, 'get', f"/bookings/{booking['id']}/ticket").json()
    assert view['status'] == 'CONFIRMED' and view['payment_status'] == 'CASH_AWAITING_CONFIRMATION'
    assert api(client, passenger, 'get', f"/bookings/{booking['id']}/boarding-code").status_code == 200   # the code opens: seats are booked
    path = f"/scheduled-trips/{t['trip']['id']}/travellers"
    listed = api(client, t['owner'], 'get', path).json()['items']
    assert all(item['cash_due'] and item['amount'] == '3000.00' for item in listed)
    cash_path = f"/scheduled-trips/{t['trip']['id']}/bookings/{booking['id']}/cash-received"
    assert api(client, passenger, 'post', cash_path, {}).status_code == 404                  # not the Passenger
    done = api(client, t['owner'], 'post', cash_path, {})
    assert done.status_code == 200, done.text
    assert done.json()['payment_status'] == 'PAID' and done.json()['amount'] == '3000.00'
    assert api(client, t['owner'], 'post', cash_path, {}).json()['payment_status'] == 'PAID'   # repeating changes nothing
    with client.app.state.sessions() as db:
        payment = db.scalar(select(Payment).where(Payment.booking_id == UUID(booking['id'])))
        assert payment.status == 'PAID' and payment.owner_settlement_status in ('COMMISSION_DUE', 'CASH_COLLECTED')
        assert db.get(Booking, UUID(booking['id'])).payment_status_snapshot == 'PAID'
    listed = api(client, t['owner'], 'get', path).json()['items']
    assert not any(item['cash_due'] for item in listed) and listed[0]['payment_status'] == 'PAID'


def test_cancelling_a_cash_seat_before_paying_is_free_and_refunds_nothing(client, drivable):
    t = drivable
    passenger, booking = hold(client, t)
    set_mode(client, t, 'ONLINE_AND_CASH')
    assert take_cash(client, passenger, booking).status_code == 201
    cancelled = api(client, passenger, 'post', f"/bookings/{booking['id']}/ticket-cancellation", {'reason': 'Changed my plans'})
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()['status'] == 'CANCELLED' and cancelled.json()['refund'] is None
    with client.app.state.sessions() as db:
        payment = db.scalar(select(Payment).where(Payment.booking_id == UUID(booking['id'])))
        assert payment.status == 'FAILED' and payment.failure_code == 'CANCELLED_BEFORE_CASH'
        assert not db.scalars(select(ScheduledTripSeat).where(ScheduledTripSeat.booked_booking_id == UUID(booking['id']))).all()
    nothing = api(client, t['owner'], 'post', f"/scheduled-trips/{t['trip']['id']}/bookings/{booking['id']}/cash-received", {})
    assert nothing.status_code == 409 and nothing.json()['code'] == 'NO_CASH_DUE'


def test_only_the_departure_driver_collects_and_only_for_cash_bookings(client, drivable):
    t = drivable
    passenger, booking = hold(client, t)
    set_mode(client, t, 'ONLINE_AND_CASH')
    path = f"/scheduled-trips/{t['trip']['id']}/bookings/{booking['id']}/cash-received"
    assert api(client, t['owner'], 'post', path, {}).json()['code'] == 'NO_CASH_DUE'            # only held, no cash booking yet
    assert api(client, person(client), 'post', path, {}).status_code == 404                     # a stranger
