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


# --------------------------------------------------------------------------- slice 2: replacement vehicle

from test_vehicles import approve, submitted


def spare_vehicle(client, t, codes, owner=None):
    actors = {'owner': owner or t['owner'], 'admin': t['admin']}
    vehicle = approve(client, actors, submitted(client, actors))
    seats = [{'code': 'DRV', 'row': 0, 'column': 1, 'type': 'CREW', 'bookable': False}] + [
        {'code': code, 'row': 1 + i // 2, 'column': i % 2} for i, code in enumerate(codes)]
    layout = api(client, actors['owner'], 'put', f"/vehicles/{vehicle['id']}/seat-layout", {'layout_version': 1, 'seats': seats})
    assert layout.status_code == 200, layout.text
    return vehicle


def replace(client, t, vehicle):
    return api(client, t['owner'], 'post', f"/scheduled-trips/{t['trip']['id']}/replacement-vehicle",
               {'expected_version': departure(client, t).version, 'vehicle_id': vehicle['id']})


def ticket_of(client, t):
    return api(client, t['passenger'], 'get', f"/bookings/{t['booking']['id']}/ticket").json()


def decide(client, t, decision):
    return api(client, t['passenger'], 'post', f"/bookings/{t['booking']['id']}/replacement-decision",
               {'expected_version': ticket_of(client, t)['version'], 'decision': decision})


def test_a_replacement_vehicle_moves_every_passenger_and_the_departure_runs(client, paid):
    spare = spare_vehicle(client, paid, ['A1', 'B1', 'B2'])
    early = replace(client, paid, spare)
    assert early.status_code == 409 and early.json()['code'] == 'REPLACEMENT_NOT_ALLOWED'
    assert problem(client, paid).status_code == 200
    done = replace(client, paid, spare)
    assert done.status_code == 200, done.text
    assert done.json()['status'] == 'COMMITTED' and done.json()['replacement_status'] == 'APPROVED' and done.json()['moved_seats'] == 2
    booking = ticket_of(client, paid)
    change = booking['pending_change']
    assert booking['status'] == 'CONFIRMED' and change['status'] == 'PENDING' and change['refund_if_rejected_percent'] == 100
    assert {(s['from_seat'], s['to_seat']) for s in change['seats']} == {('A1', 'A1'), ('A2', 'B1')}
    assert sorted(t['seat_code'] for t in booking['travellers']) == ['A1', 'B1'] and all(t['fare'] == '1500.00' for t in booking['travellers'])
    seat_map = client.get(f"/api/v1/scheduled-trips/{paid['trip']['id']}/seats").json()['seats']
    sellable = {s['code']: s['status'] for s in seat_map if s.get('seat_id')}
    assert sellable == {'A1': 'BOOKED', 'B1': 'BOOKED', 'B2': 'AVAILABLE'}
    with client.app.state.sessions() as db:
        run = db.scalar(select(Trip).where(Trip.scheduled_trip_id == UUID(paid['trip']['id'])))
    assert str(run.vehicle_id) == spare['id']
    assert notices(client, paid['passenger'], 'REPLACEMENT') and listed(client, paid)


def test_the_replacement_must_seat_everyone_and_belong_to_the_owner(client, paid):
    assert problem(client, paid).status_code == 200
    small = replace(client, paid, spare_vehicle(client, paid, ['A1']))
    assert small.status_code == 409 and small.json()['code'] == 'REPLACEMENT_TOO_SMALL'
    foreign = replace(client, paid, spare_vehicle(client, paid, ['A1', 'A2'], owner=person(client, 'OWNER')))
    assert foreign.status_code == 409 and foreign.json()['code'] == 'REPLACEMENT_VEHICLE_UNAVAILABLE'


def test_a_passenger_who_accepts_keeps_the_booking(client, paid):
    assert problem(client, paid).status_code == 200
    assert replace(client, paid, spare_vehicle(client, paid, ['A1', 'A2'])).status_code == 200
    accepted = decide(client, paid, 'ACCEPT')
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()['status'] == 'CONFIRMED' and accepted.json()['pending_change']['status'] == 'ACCEPTED'
    again = decide(client, paid, 'REJECT')
    assert again.status_code == 409 and again.json()['code'] == 'NO_PENDING_CHANGE'


def test_a_passenger_who_rejects_gets_a_full_refund_queued(client, paid):
    assert problem(client, paid).status_code == 200
    assert replace(client, paid, spare_vehicle(client, paid, ['A1', 'A2', 'A3'])).status_code == 200
    rejected = decide(client, paid, 'REJECT')
    assert rejected.status_code == 200, rejected.text
    body = rejected.json()
    assert body['status'] == 'CANCELLED' and body['refund']['amount'] == '3000.00' and body['refund']['status'] == 'PENDING'
    refunds = api(client, paid['admin'], 'get', '/admin/refunds').json()['items']
    assert any(r['cause'] == 'REPLACEMENT_REJECTED' and r['transaction_type'] == 'FULL_REFUND' for r in refunds)
    seat_map = client.get(f"/api/v1/scheduled-trips/{paid['trip']['id']}/seats").json()['seats']
    assert all(s['status'] == 'AVAILABLE' for s in seat_map if s.get('seat_id'))
    assert notices(client, paid['passenger'], 'REFUND')


# --------------------------------------------------------------------------- slice 3: another Owner's vehicle

from app.models import UserRole as _UserRole  # noqa: E402
from app.models.review_models import Vehicle  # noqa: E402


def other_owner_vehicle(client, t, codes):
    other = person(client, 'OWNER', 'DRIVER')
    vehicle = spare_vehicle(client, t, codes, owner=other)
    with client.app.state.sessions() as db:
        db.get(Vehicle, UUID(vehicle['id'])).is_published = True
        db.commit()
    return other, vehicle


def ask(client, t, vehicle):
    return api(client, t['owner'], 'post', f"/scheduled-trips/{t['trip']['id']}/replacement-request",
               {'expected_version': departure(client, t).version, 'vehicle_id': vehicle['id']})


def answer(client, who, offer, decision, **extra):
    with client.app.state.sessions() as db:
        version = db.get(ScheduledTrip, UUID(offer['id'])).version
    return api(client, who, 'post', f"/scheduled-trips/{offer['id']}/replacement-answer",
               {'expected_version': version, 'decision': decision, **extra})


def test_options_list_own_and_other_owners_vehicles_that_fit(client, paid):
    assert problem(client, paid).status_code == 200
    mine = spare_vehicle(client, paid, ['A1', 'A2'])
    _, theirs = other_owner_vehicle(client, paid, ['A1', 'A2', 'A3'])
    other_owner_vehicle(client, paid, ['A1'])  # too small, never offered
    options = api(client, paid['owner'], 'get', f"/scheduled-trips/{paid['trip']['id']}/replacement-options").json()
    found = {i['vehicle_id']: i for i in options['items']}
    assert options['booked_seats'] == 2 and found[mine['id']]['own'] and not found[theirs['id']]['own']
    assert found[theirs['id']]['owner_name'] and len(found) == 2
    one = api(client, paid['owner'], 'get', f"/scheduled-trips/{paid['trip']['id']}/replacement-options?reference="
              + found[theirs['id']]['public_vehicle_reference'].lower()).json()['items']
    assert [i['vehicle_id'] for i in one] == [theirs['id']]


def test_another_owner_accepts_and_takes_over_passengers_and_money(client, paid):
    assert problem(client, paid).status_code == 200
    other, vehicle = other_owner_vehicle(client, paid, ['A1', 'A2', 'A3'])
    asked = ask(client, paid, vehicle)
    assert asked.status_code == 201, asked.text
    assert asked.json()['replacement_status'] == 'AWAITING_OTHER_OWNER'
    offer = asked.json()['replacement_request']
    assert commit(client, paid).json()['code'] == 'REPLACEMENT_PENDING'
    inbox = api(client, other, 'get', '/owners/me/replacement-requests').json()['items']
    assert [i['id'] for i in inbox] == [offer['id']] and inbox[0]['booked_seats'] == 2 and inbox[0]['fare_per_seat'] == '1500.00'
    blocked = api(client, other, 'post', f"/scheduled-trips/{offer['id']}/publish", {'expected_version': inbox[0]['version'], 'publish_confirmed': True})
    assert blocked.status_code == 409 and blocked.json()['code'] == 'REPLACEMENT_REQUEST_DRAFT'
    accepted = answer(client, other, offer, 'ACCEPT')
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()['status'] == 'COMMITTED' and accepted.json()['moved_seats'] == 2
    with client.app.state.sessions() as db:
        original = db.get(ScheduledTrip, UUID(paid['trip']['id']))
        booking = db.get(Booking, UUID(paid['booking']['id']))
        rows = db.scalars(select(Payment).where(Payment.booking_id == booking.id).order_by(Payment.created_at)).all()
        run = db.scalar(select(Trip).where(Trip.scheduled_trip_id == UUID(offer['id'])))
    assert original.status == 'CANCELLED' and original.replacement_status == 'APPROVED' and str(original.final_operating_owner_user_id) == other['id']
    assert str(booking.current_scheduled_trip_id) == offer['id'] and str(booking.owner_user_id) == other['id']
    assert str(booking.original_scheduled_trip_id) == paid['trip']['id'] and str(booking.requested_owner_user_id) == paid['owner']['id']
    assert booking.pending_change['operator_changed'] and booking.pending_change['replacement_vehicle']['operator_name']
    captured = next(r for r in rows if r.transaction_type == 'PAYMENT')
    share = next(r for r in rows if r.transaction_type == 'REALLOCATION')
    assert captured.owner_settlement_status == 'REALLOCATED' and captured.status == 'PAID'
    assert str(share.payee_owner_user_id) == other['id'] and share.amount == captured.amount and share.original_payment_id == captured.id
    assert run.status == 'READY' and str(run.driver_user_id) == other['id'] and run.assignment_status == 'ACCEPTED'
    assert any(i['id'] == offer['id'] for i in client.get('/api/v1/scheduled-trips').json()['items'])
    # The passenger still answers the change; rejecting refunds the captured payment and the moved share with it.
    rejected = decide(client, paid, 'REJECT')
    assert rejected.status_code == 200, rejected.text
    refund = rejected.json()['refund']
    approved = api(client, paid['admin'], 'post', f"/admin/refunds/{refund['id']}/decision", {'expected_version': 1, 'decision': 'APPROVE'})
    assert approved.status_code == 200, approved.text
    with client.app.state.sessions() as db:
        assert db.get(Payment, captured.id).status == 'REFUNDED' and db.get(Payment, share.id).status == 'REFUNDED'


def test_a_declined_request_goes_back_to_the_owner(client, paid):
    assert problem(client, paid).status_code == 200
    other, vehicle = other_owner_vehicle(client, paid, ['A1', 'A2'])
    offer = ask(client, paid, vehicle).json()['replacement_request']
    stranger = person(client, 'OWNER')
    assert answer(client, stranger, offer, 'ACCEPT').status_code == 404
    declined = answer(client, other, offer, 'DECLINE', reason='The van is booked for a wedding.')
    assert declined.status_code == 200, declined.text
    assert declined.json()['replacement_status'] == 'REJECTED' and declined.json()['status'] == 'DISRUPTED'
    assert answer(client, other, offer, 'ACCEPT').json()['code'] == 'NO_REPLACEMENT_REQUEST'
    with client.app.state.sessions() as db:
        assert db.get(Booking, UUID(paid['booking']['id'])).status == 'CONFIRMED'
    assert commit(client, paid).json()['status'] == 'COMMITTED'


def test_the_new_owner_is_paid_out_from_the_reallocated_share(client, paid):
    assert problem(client, paid).status_code == 200
    other, vehicle = other_owner_vehicle(client, paid, ['A1', 'A2'])
    offer = ask(client, paid, vehicle).json()['replacement_request']
    assert answer(client, other, offer, 'ACCEPT').status_code == 200
    with client.app.state.sessions() as db:
        share = db.scalar(select(Payment).where(Payment.booking_id == UUID(paid['booking']['id']), Payment.transaction_type == 'REALLOCATION'))
        share.owner_settlement_status = 'OWNER_PAYABLE'   # what finishing the journey does
        db.commit()
        net = share.owner_net_amount
    theirs = api(client, other, 'get', '/owners/me/settlements').json()
    assert theirs['payable_amount'] == format(net, '.2f') and [p['id'] for p in theirs['payable']] == [str(share.id)]
    first = api(client, paid['owner'], 'get', '/owners/me/settlements').json()
    assert first['payable_amount'] == '0.00' and not first['payable']
    payout = api(client, paid['admin'], 'post', f"/admin/owner-settlements/{other['id']}/payouts",
                 {'payment_ids': [str(share.id)], 'bank_reference': 'BANK-123', 'idempotency_key': 'payout-realloc-1'})
    assert payout.status_code == 201, payout.text
