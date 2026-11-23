"""Book now return: the vehicle leaving the waiting spot asks the Driver; reporting the waiting charge; the Owner's kilometre check."""
from datetime import timedelta
from decimal import Decimal
from uuid import UUID
from sqlalchemy import select
from app.models.charge_report_models import WaitingChargeReport
from app.models.hire_models import Booking, Notification, Trip
from app.models.support_models import SupportTicket
from conftest import bearer
from test_instant_booking import ask_trip, begin, finish_with, ride, trip_call, trip_version  # noqa: F401  (ride is a fixture)
from test_hire_pricing import external_driver, hire_setup  # noqa: F401
from test_rates import rate_owner, rule  # noqa: F401

HERE = {'latitude': '6.950000', 'longitude': '79.900000'}
FAR = {'latitude': '6.960000', 'longitude': '79.900000'}   # about 1.1 km away


def move(client, c, trip_id, where):
    done = client.patch(f'/api/v1/trips/{trip_id}/location', headers=bearer(c.owner), json={'expected_version': trip_version(client, c.owner, trip_id), **where})
    assert done.status_code == 200, done.text


def wait_of(client, c, trip_id):
    return client.get(f'/api/v1/trips/{trip_id}', headers=bearer(c.passenger)).json()['wait']


def waiting_at_destination(client, c):
    item, accepted = ask_trip(client, c, True)
    trip_id = accepted['trip_id']
    begin(client, c, trip_id)
    move(client, c, trip_id, HERE)
    assert trip_call(client, c.owner, trip_id, 'wait/start').status_code == 200
    return item, accepted, trip_id


def charged_trip(client, c):
    """A finished return trip with 30 minutes of waiting beyond the free minutes."""
    item, accepted = ask_trip(client, c, True)
    trip_id = accepted['trip_id']
    free = Decimal(item['waiting']['free_minutes'])
    begin(client, c, trip_id)
    assert trip_call(client, c.owner, trip_id, 'wait/start').status_code == 200
    assert trip_call(client, c.owner, trip_id, 'wait/end').status_code == 200
    with client.app.state.sessions() as db:
        trip = db.get(Trip, UUID(trip_id))
        trip.wait_started_at = trip.wait_ended_at - timedelta(minutes=float(free + 30))
        db.commit()
    finish_with(client, c, accepted)
    return item, accepted, trip_id


def test_leaving_the_spot_asks_the_driver_and_the_waiting_ends_where_the_vehicle_left(client, ride):
    c = ride
    item, accepted, trip_id = waiting_at_destination(client, c)
    assert trip_call(client, c.owner, trip_id, 'wait/answer', still_waiting=False).json()['code'] == 'NO_WAITING_QUESTION'
    move(client, c, trip_id, FAR)
    wait = wait_of(client, c, trip_id)
    assert wait['state'] == 'MOVED' and wait['moved_at'] and wait['ended_at'] is None
    with client.app.state.sessions() as db:
        asked = db.scalars(select(Notification).where(Notification.booking_id == UUID(accepted['booking_id']), Notification.title == 'The vehicle moved away')).all()
        assert len(asked) == 1
    move(client, c, trip_id, {'latitude': '6.970000', 'longitude': '79.900000'})   # moving further does not ask again
    with client.app.state.sessions() as db:
        assert len(db.scalars(select(Notification).where(Notification.booking_id == UUID(accepted['booking_id']), Notification.title == 'The vehicle moved away')).all()) == 1
    assert trip_call(client, c.passenger, trip_id, 'wait/answer', still_waiting=False).status_code == 404   # only the Driver answers
    answered = trip_call(client, c.owner, trip_id, 'wait/answer', still_waiting=False)
    assert answered.status_code == 200, answered.text
    ended = wait_of(client, c, trip_id)
    assert ended['state'] == 'RETURNING' and ended['source'] == 'DRIVER' and ended['ended_at'] == wait['moved_at']


def test_still_waiting_keeps_the_clock_running_and_measures_the_spot_again_from_here(client, ride):
    c = ride
    item, accepted, trip_id = waiting_at_destination(client, c)
    move(client, c, trip_id, FAR)
    assert wait_of(client, c, trip_id)['state'] == 'MOVED'
    assert trip_call(client, c.owner, trip_id, 'wait/answer', still_waiting=True).status_code == 200
    again = wait_of(client, c, trip_id)
    assert again['state'] == 'WAITING' and again['moved_at'] is None
    move(client, c, trip_id, FAR)   # still at the new spot: no new question
    assert wait_of(client, c, trip_id)['state'] == 'WAITING'


def test_an_unanswered_question_charges_only_until_the_vehicle_left(client, ride):
    c = ride
    item, accepted, trip_id = waiting_at_destination(client, c)
    free = Decimal(item['waiting']['free_minutes'])
    move(client, c, trip_id, FAR)
    with client.app.state.sessions() as db:
        trip = db.get(Trip, UUID(trip_id))
        trip.wait_started_at = trip.wait_moved_at - timedelta(minutes=float(free + 20))
        db.commit()
    finish_with(client, c, accepted)   # finished without answering
    with client.app.state.sessions() as db:
        trip = db.get(Trip, UUID(trip_id))
        booking = db.get(Booking, UUID(accepted['booking_id']))
        assert trip.wait_ended_at == trip.wait_moved_at and trip.wait_source == 'GPS'
        assert Decimal(booking.price_snapshot['waiting']['minutes']) == free + 20


def test_the_passenger_reports_the_waiting_charge_and_the_owner_keeps_it(client, ride):
    c = ride
    item, accepted, trip_id = charged_trip(client, c)
    path = f'/api/v1/trips/{trip_id}/charge-report'
    shown = client.get(path, headers=bearer(c.passenger)).json()
    assert shown['can_report'] and shown['charge'] and shown['report'] is None
    assert client.post(path, headers=bearer(c.owner), json={}).status_code == 404   # only the Passenger reports
    made = client.post(path, headers=bearer(c.passenger), json={})   # no reason needed
    assert made.status_code == 201, made.text
    assert client.post(path, headers=bearer(c.passenger), json={}).json()['code'] == 'REPORT_EXISTS'
    assert client.get(path, headers=bearer(c.passenger)).json()['can_report'] is False
    report_id = made.json()['id']
    assert client.post(f'/api/v1/charge-reports/{report_id}/answer', headers=bearer(c.passenger), json={'keep': True}).status_code == 404
    before = Decimal(item['fare'])
    kept = client.post(f'/api/v1/charge-reports/{report_id}/answer', headers=bearer(c.owner), json={'keep': True, 'note': 'The timer was right.'})
    assert kept.status_code == 200 and kept.json()['status'] == 'KEPT'
    assert client.post(f'/api/v1/charge-reports/{report_id}/answer', headers=bearer(c.owner), json={'keep': True}).json()['code'] == 'REPORT_ANSWERED'
    with client.app.state.sessions() as db:
        assert db.get(Booking, UUID(accepted['booking_id'])).total_amount > before   # the charge stands


def test_a_lowered_charge_changes_the_total_before_payment(client, ride):
    c = ride
    item, accepted, trip_id = charged_trip(client, c)
    made = client.post(f'/api/v1/trips/{trip_id}/charge-report', headers=bearer(c.passenger), json={'reason': 'I waited about 15 minutes.'}).json()
    charge = Decimal(made['charge'])
    path = f"/api/v1/charge-reports/{made['id']}/answer"
    assert client.post(path, headers=bearer(c.owner), json={'keep': False}).status_code == 422
    assert client.post(path, headers=bearer(c.owner), json={'keep': False, 'new_charge': str(charge)}).status_code == 422   # never raised or equal
    lowered = client.post(path, headers=bearer(c.owner), json={'keep': False, 'new_charge': '100.00'})
    assert lowered.status_code == 200 and lowered.json()['status'] == 'REDUCED' and lowered.json()['refund_due'] is None
    with client.app.state.sessions() as db:
        booking = db.get(Booking, UUID(accepted['booking_id']))
        assert booking.total_amount == Decimal(item['fare']) + Decimal('100.00')
        assert booking.price_snapshot['waiting']['charge'] == '100.00'


def test_a_lowered_charge_after_payment_opens_a_refund_ticket_for_the_admins(client, ride):
    c = ride
    item, accepted, trip_id = charged_trip(client, c)
    with client.app.state.sessions() as db:
        booking = db.get(Booking, UUID(accepted['booking_id']))
        booking.payment_status_snapshot = 'PAID'
        total = booking.total_amount
        db.commit()
    made = client.post(f'/api/v1/trips/{trip_id}/charge-report', headers=bearer(c.passenger), json={}).json()
    charge = Decimal(made['charge'])
    lowered = client.post(f"/api/v1/charge-reports/{made['id']}/answer", headers=bearer(c.owner), json={'keep': False, 'new_charge': '0'})
    assert lowered.status_code == 200 and Decimal(lowered.json()['refund_due']) == charge
    with client.app.state.sessions() as db:
        assert db.get(Booking, UUID(accepted['booking_id'])).total_amount == total   # what was paid is left to the refund tools
        ticket = db.scalar(select(SupportTicket).where(SupportTicket.booking_id == UUID(accepted['booking_id'])))
        assert ticket.category == 'REFUND' and ticket.admin_unread


def test_a_trip_without_a_waiting_charge_has_nothing_to_report(client, ride):
    c = ride
    item, accepted = ask_trip(client, c, True)
    begin(client, c, accepted['trip_id'])
    finish_with(client, c, accepted)
    path = f"/api/v1/trips/{accepted['trip_id']}/charge-report"
    assert client.get(path, headers=bearer(c.passenger)).json()['can_report'] is False
    assert client.post(path, headers=bearer(c.passenger), json={}).json()['code'] == 'NO_WAITING_CHARGE'


def test_the_owner_sees_billed_and_odometer_kilometres_and_nobody_else_does(client, ride):
    c = ride
    item, accepted = ask_trip(client, c, True)
    begin(client, c, accepted['trip_id'])
    finish_with(client, c, accepted)   # odometer 1000 to 1030
    path = f"/api/v1/trips/{accepted['trip_id']}/km-summary"
    shown = client.get(path, headers=bearer(c.owner))
    assert shown.status_code == 200, shown.text
    body = shown.json()
    assert body['odometer_km'] == '30.0' and body['finished'] and body['start_odometer_km'] == '1000.0' and body['end_odometer_km'] == '1030.0'
    assert body['billed_km'] is not None and Decimal(body['extra_km']) == Decimal('30.0') - Decimal(body['billed_km'])
    assert client.get(path, headers=bearer(c.passenger)).status_code == 404
