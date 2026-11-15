"""Trip operations: the assigned operator runs a started trip through to completion.

Live location, breakdown and completion all belong to the operator assigned to the trip.
Everything here uses the existing trips row; no new table and no new status.
"""
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
import pytest
from sqlalchemy import select
from app.models.hire_models import Booking, Notification, Trip
from conftest import bearer, signed_in, check_passenger
from test_rates import rule, rate_owner
from test_hire_pricing import hire_setup, committed


@pytest.fixture
def running(client, hire_setup, monkeypatch):
    """A confirmed self-drive booking whose trip the Owner has already started."""
    import app.api.routers.hire_api as module
    c = hire_setup
    booking = committed(client, c)
    detail = client.get(f"/api/v1/bookings/{booking['id']}", headers=bearer(c.owner)).json()
    with client.app.state.sessions() as db:
        start = db.get(Booking, UUID(booking['id'])).start_at

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None): return (start + timedelta(minutes=1)).astimezone(tz or timezone.utc)
    check_passenger(client, c.passenger, c.owner, detail['trip']['id'], detail['trip']['version'])
    monkeypatch.setattr(module, 'datetime', Clock)
    result = client.post(f"/api/v1/trips/{detail['trip']['id']}/start", headers=bearer(c.owner),
                         json={'expected_version': detail['trip']['version'], 'start_odometer_km': '1234.5',
                               'checklist_confirmed': True})
    assert result.status_code == 200, result.text
    fresh = client.get(f"/api/v1/bookings/{booking['id']}", headers=bearer(c.owner)).json()
    assert fresh['status'] == 'IN_PROGRESS' and fresh['trip']['status'] == 'IN_PROGRESS'
    return type('Running', (), {'ctx': c, 'booking': fresh, 'trip': fresh['trip']})


def place(client, run, who, **changes):
    body = {'expected_version': run.trip['version'], 'latitude': '6.927079', 'longitude': '79.861244', **changes}
    return client.patch(f"/api/v1/trips/{run.trip['id']}/location", headers=bearer(who), json=body)


def test_only_the_assigned_operator_reports_the_live_position(client, running):
    c = running.ctx
    moved = place(client, running, c.owner, accuracy_m='12.5', speed_kph='42.00')
    assert moved.status_code == 200, moved.text
    assert moved.json()['tracking_status'] == 'ACTIVE'
    assert moved.json()['location']['latitude'] == '6.927079'
    assert moved.json()['location']['speed_kph'] == '42.00'
    assert place(client, running, c.passenger).status_code == 404  # the Passenger is carried, not driving


def test_the_people_on_the_booking_see_the_position_and_strangers_do_not(client, running):
    c = running.ctx
    assert place(client, running, c.owner).status_code == 200
    seen = client.get(f"/api/v1/trips/{running.trip['id']}", headers=bearer(c.passenger))
    assert seen.status_code == 200, seen.text
    assert seen.json()['location']['longitude'] == '79.861244'
    stranger = signed_in(client, {'full_name': 'Passer By', 'email': uuid4().hex + '@example.com',
                                  'phone_e164': '+9477' + str(uuid4().int % 10000000).zfill(7),
                                  'password': 'TravellyStrong1!', 'accept_terms': True})[1]
    assert client.get(f"/api/v1/trips/{running.trip['id']}", headers=bearer(stranger)).status_code == 404


def test_a_stale_version_never_overwrites_a_newer_position(client, running):
    c = running.ctx
    first = place(client, running, c.owner)
    assert first.status_code == 200
    again = place(client, running, c.owner)  # still the old version
    assert again.status_code == 409 and again.json()['code'] == 'VERSION_CONFLICT'


def test_breakdown_keeps_the_booking_running_and_tells_both_sides(client, running):
    c = running.ctx
    reported = client.post(f"/api/v1/trips/{running.trip['id']}/breakdown", headers=bearer(c.owner),
                           json={'expected_version': running.trip['version'], 'kind': 'BREAKDOWN',
                                 'details': 'Front tyre burst near Kegalle.'})
    assert reported.status_code == 200, reported.text
    assert reported.json()['trip']['status'] == 'BREAKDOWN'
    assert reported.json()['trip']['breakdown_details'] == 'Front tyre burst near Kegalle.'
    assert reported.json()['status'] == 'IN_PROGRESS'  # the booking is not cancelled by a breakdown
    with client.app.state.sessions() as db:
        told = db.scalars(select(Notification.recipient_user_id)
                          .where(Notification.booking_id == UUID(running.booking['id']),
                                 Notification.title == 'The trip needs help')).all()
    assert len(set(told)) == 2  # Passenger and Owner; the Driver here is the Owner


def test_a_broken_down_trip_can_still_be_completed(client, running):
    c = running.ctx
    reported = client.post(f"/api/v1/trips/{running.trip['id']}/breakdown", headers=bearer(c.owner),
                           json={'expected_version': running.trip['version'], 'kind': 'ASSISTANCE_REQUIRED',
                                 'details': 'Passenger needs help with luggage.'})
    assert reported.status_code == 200, reported.text
    done = client.post(f"/api/v1/trips/{running.trip['id']}/complete", headers=bearer(c.owner),
                       json={'expected_version': reported.json()['trip']['version'], 'end_odometer_km': '1300.5'})
    assert done.status_code == 200, done.text
    assert done.json()['trip']['status'] == 'COMPLETED'


def test_completion_records_the_distance_and_stops_tracking(client, running):
    c = running.ctx
    moved = place(client, running, c.owner)
    assert moved.status_code == 200
    done = client.post(f"/api/v1/trips/{running.trip['id']}/complete", headers=bearer(c.owner),
                       json={'expected_version': moved.json()['version'], 'end_odometer_km': '1300.5',
                             'completion_notes': 'Dropped at the gate.'})
    assert done.status_code == 200, done.text
    trip = done.json()['trip']
    assert trip['status'] == 'COMPLETED' and done.json()['status'] == 'COMPLETED'
    assert trip['end_odometer_km'] == '1300.5' and trip['calculated_distance_km'] == '66.0'
    assert trip['tracking_status'] == 'ENDED' and trip['location'] is None  # tracking stops with the trip
    assert trip['completion_notes'] == 'Dropped at the gate.'
    again = client.post(f"/api/v1/trips/{running.trip['id']}/complete", headers=bearer(c.owner),
                        json={'expected_version': trip['version'], 'end_odometer_km': '1400.0'})
    assert again.status_code == 409 and again.json()['code'] == 'TRIP_NOT_READY'
    assert place(client, running, c.owner).status_code == 409  # no position after the trip ends


def test_the_closing_odometer_cannot_be_lower_than_the_start(client, running):
    c = running.ctx
    refused = client.post(f"/api/v1/trips/{running.trip['id']}/complete", headers=bearer(c.owner),
                          json={'expected_version': running.trip['version'], 'end_odometer_km': '1000.0'})
    assert refused.status_code == 422 and refused.json()['code'] == 'VALIDATION_ERROR'
    with client.app.state.sessions() as db:
        assert db.get(Trip, UUID(running.trip['id'])).status == 'IN_PROGRESS'


def test_position_and_completion_need_a_started_trip(client, hire_setup):
    c = hire_setup
    booking = committed(client, c)
    detail = client.get(f"/api/v1/bookings/{booking['id']}", headers=bearer(c.owner)).json()
    trip = detail['trip']
    early = client.patch(f"/api/v1/trips/{trip['id']}/location", headers=bearer(c.owner),
                         json={'expected_version': trip['version'], 'latitude': '6.9', 'longitude': '79.8'})
    assert early.status_code == 409 and early.json()['code'] == 'TRIP_NOT_READY'
    closing = client.post(f"/api/v1/trips/{trip['id']}/complete", headers=bearer(c.owner),
                          json={'expected_version': trip['version'], 'end_odometer_km': '1300.5'})
    assert closing.status_code == 409 and closing.json()['code'] == 'TRIP_NOT_READY'
