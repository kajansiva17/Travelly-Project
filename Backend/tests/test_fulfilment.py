"""Protected fulfilment, first slice (matrix 54-58; PRD D08; owner decisions 12 Nov 2026).

A missed deadline only escalates. A reported problem keeps paid bookings confirmed while Travelly works on it.
Only when Travelly cannot fulfil does every paid seat get a full refund.
"""
from datetime import datetime, timedelta, timezone
from uuid import UUID
from sqlalchemy import select, update
from app.models.hire_models import Booking, Notification, ScheduledTrip, Trip
from app.models.payment_models import Payment
from app.models.seat_models import ScheduledTripSeat
from test_ticket_holds import api, person, ticket, configure_hold, hold_body
from test_payments import held
from test_refunds import paid


def departure(client, t):
    with client.app.state.sessions() as db:
        return db.get(ScheduledTrip, UUID(t['trip']['id']))


def protected(client, t, deadline):
    with client.app.state.sessions() as db:
        db.execute(update(ScheduledTrip).where(ScheduledTrip.id == UUID(t['trip']['id'])).values(
            fulfilment_policy='MINIMUM_SEATS_WITH_PROTECTED_FULFILMENT', minimum_confirmed_seats=3,
            decision_deadline=datetime.now(timezone.utc) + deadline))
        db.commit()


def commit(client, t, who=None):
    return api(client, who or t['owner'], 'post', f"/scheduled-trips/{t['trip']['id']}/commit",
               {'expected_version': departure(client, t).version})


def problem(client, t, reason='The bus engine failed its inspection.'):
    return api(client, t['owner'], 'post', f"/scheduled-trips/{t['trip']['id']}/problem",
               {'expected_version': departure(client, t).version, 'reason': reason})


def cannot_fulfil(client, t, reason='No equivalent vehicle is available for this date.'):
    return api(client, t['admin'], 'post', f"/admin/scheduled-trips/{t['trip']['id']}/cannot-fulfil",
               {'expected_version': departure(client, t).version, 'reason': reason})


def notices(client, user, kind):
    with client.app.state.sessions() as db:
        return db.scalars(select(Notification).where(Notification.recipient_user_id == UUID(user['id']),
                                                     Notification.notification_type == kind)).all()


def listed(client, t):
    return any(item['id'] == t['trip']['id'] for item in client.get('/api/v1/scheduled-trips').json()['items'])


def test_the_owner_commits_a_minimum_seats_departure_and_it_keeps_selling(client, paid):
    protected(client, paid, timedelta(hours=12))
    done = commit(client, paid)
    assert done.status_code == 200, done.text
    assert done.json()['status'] == 'COMMITTED' and done.json()['committed_at'] and done.json()['booked_seats'] == 2
    assert notices(client, paid['passenger'], 'BOOKING_CONFIRMED')
    assert listed(client, paid)
    stranger = person(client, 'OWNER')
    assert commit(client, paid, who=stranger).status_code == 404


def test_a_fixed_departure_is_already_guaranteed(client, ticket):
    refused = commit(client, ticket)
    assert refused.status_code == 409 and refused.json()['code'] == 'DEPARTURE_ALREADY_GUARANTEED'


def test_a_missed_deadline_only_escalates_to_the_admin(client, paid):
    protected(client, paid, timedelta(minutes=-5))
    queue = api(client, paid['admin'], 'get', '/admin/departures/attention')
    assert queue.status_code == 200, queue.text
    item = next(i for i in queue.json()['items'] if i['id'] == paid['trip']['id'])
    assert item['status'] == 'DECISION_REQUIRED' and item['booked_seats'] == 2 and item['paid_amount'] == '3000.00'
    with client.app.state.sessions() as db:
        booking = db.get(Booking, UUID(paid['booking']['id']))
        refunds = db.scalars(select(Payment).where(Payment.booking_id == booking.id, Payment.transaction_type != 'PAYMENT')).all()
    assert booking.status == 'CONFIRMED' and booking.payment_status_snapshot == 'PAID' and not refunds
    assert notices(client, paid['admin'], 'ADMIN_ACTION')
    assert not listed(client, paid)  # no new sales while Travelly decides
    # The Owner can still run it with the original vehicle.
    assert commit(client, paid).json()['status'] == 'COMMITTED'
    assert listed(client, paid)


def test_a_reported_problem_keeps_paid_bookings_and_ends_open_holds(client, paid):
    other = person(client)  # the hold time is already configured by the fixture
    hold = api(client, other, 'post', '/bookings/ticket-holds', hold_body(paid, ['A3']))
    assert hold.status_code == 201, hold.text
    done = problem(client, paid)
    assert done.status_code == 200, done.text
    assert done.json()['status'] == 'DISRUPTED' and done.json()['held_seats'] == 0
    with client.app.state.sessions() as db:
        assert db.get(Booking, UUID(paid['booking']['id'])).status == 'CONFIRMED'
        assert db.get(Booking, UUID(hold.json()['id'])).status == 'CANCELLED'
        assert db.get(ScheduledTripSeat, UUID(paid['seats']['A3'])).seat_status == 'AVAILABLE'
    assert notices(client, paid['passenger'], 'REPLACEMENT') and notices(client, paid['admin'], 'ADMIN_ACTION')
    assert not listed(client, paid)
    again = problem(client, paid)
    assert again.status_code == 409 and again.json()['code'] == 'DEPARTURE_NOT_REPORTABLE'


def test_an_unsold_departure_is_simply_withdrawn(client, ticket):
    done = problem(client, ticket)
    assert done.status_code == 200, done.text
    assert done.json()['status'] == 'CANCELLED'
    with client.app.state.sessions() as db:
        seats = db.scalars(select(ScheduledTripSeat.seat_status).where(ScheduledTripSeat.scheduled_trip_id == UUID(ticket['trip']['id']))).all()
        run = db.scalar(select(Trip).where(Trip.scheduled_trip_id == UUID(ticket['trip']['id'])))
    assert set(seats) == {'BLOCKED'} and run.status == 'CANCELLED'


def test_when_travelly_cannot_fulfil_every_paid_seat_is_refunded_in_full(client, paid):
    early = cannot_fulfil(client, paid)
    assert early.status_code == 409 and early.json()['code'] == 'DEPARTURE_NOT_ESCALATED'
    assert problem(client, paid).status_code == 200
    done = cannot_fulfil(client, paid)
    assert done.status_code == 200, done.text
    body = done.json()
    assert body['status'] == 'CANCELLED' and body['replacement_status'] == 'FAILED'
    assert len(body['refunds']) == 1 and body['refunds'][0]['amount'] == '3000.00' and body['refunds'][0]['status'] == 'PAID'
    with client.app.state.sessions() as db:
        booking = db.get(Booking, UUID(paid['booking']['id']))
        original = db.get(Payment, UUID(paid['payment']['id']))
        seat = db.get(ScheduledTripSeat, UUID(paid['seats']['A1']))
        run = db.scalar(select(Trip).where(Trip.scheduled_trip_id == UUID(paid['trip']['id'])))
    assert booking.status == 'CANCELLED' and booking.cancellation_policy_snapshot['refund_percent'] == 100
    assert original.status == 'REFUNDED' and booking.payment_status_snapshot == 'REFUNDED'
    assert seat.seat_status == 'BLOCKED' and run.status == 'CANCELLED'
    assert notices(client, paid['passenger'], 'REFUND')
    refunds = api(client, paid['admin'], 'get', '/admin/refunds').json()['items']
    assert any(r['cause'] == 'DEPARTURE_NOT_FULFILLED' and r['transaction_type'] == 'FULL_REFUND' for r in refunds)
    assert cannot_fulfil(client, paid).status_code == 409


def test_only_admins_see_the_attention_list(client, ticket):
    assert api(client, ticket['owner'], 'get', '/admin/departures/attention').status_code == 403
