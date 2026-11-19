"""Pickup verification: the Passenger shows a QR code, or reads out the six digits under it.

Nothing secret is stored. Both values are derived from the application secret and the trip's
pickup_code_version, so the Passenger sees the same code again and a new code is a new version.
"""
from uuid import UUID, uuid4
import pytest
from app.models.hire_models import Trip
from app.services.pickup_codes import MAX_ATTEMPTS, pin_for, token_for
from conftest import bearer, signed_in
from test_rates import rule, rate_owner
from test_hire_pricing import hire_setup, committed


@pytest.fixture
def ready(client, hire_setup):
    """A confirmed self-drive booking: the Owner is the assigned operator, the Passenger is someone else."""
    c = hire_setup
    booking = committed(client, c)
    detail = client.get(f"/api/v1/bookings/{booking['id']}", headers=bearer(c.owner)).json()
    return type('Ready', (), {'ctx': c, 'booking': detail, 'trip': detail['trip']})


def code(client, run, who=None):
    return client.get(f"/api/v1/trips/{run.trip['id']}/pickup-code", headers=bearer(who or run.ctx.passenger))


def verify(client, run, body, who=None):
    return client.post(f"/api/v1/trips/{run.trip['id']}/pickup-verifications",
                       headers=bearer(who or run.ctx.owner), json={'expected_version': run.trip['version'], **body})


def test_the_passenger_sees_the_same_code_every_time_and_nothing_is_stored(client, ready):
    first = code(client, ready)
    assert first.status_code == 200, first.text
    again = code(client, ready)
    assert again.json()['pin'] == first.json()['pin'] == pin_for(UUID(ready.trip['id']), 1)
    assert again.json()['qr_token'] == token_for(UUID(ready.trip['id']), 1)
    assert len(first.json()['pin']) == 6 and first.json()['pin'].isdigit()
    with client.app.state.sessions() as db:
        trip = db.get(Trip, UUID(ready.trip['id']))
        assert trip.pickup_code_version == 1 and trip.pickup_code_issued_at is not None
        assert trip.version == ready.trip['version']  # issuing a code is not a change the Driver reloads for
        assert first.json()['pin'] not in str(trip.__dict__)  # the code itself is never written down


def test_only_the_passenger_holds_the_code(client, ready):
    c = ready.ctx
    assert code(client, ready, c.owner).status_code == 404  # the operator must ask, not look it up
    stranger = signed_in(client, {'full_name': 'Passer By', 'email': uuid4().hex + '@example.com',
                                  'phone_e164': '+9477' + str(uuid4().int % 10000000).zfill(7),
                                  'password': 'TravellyStrong1!', 'accept_terms': True})[1]
    assert code(client, ready, stranger).status_code == 404


def test_the_driver_checks_the_passenger_with_the_scanned_code(client, ready):
    issued = code(client, ready).json()
    done = verify(client, ready, {'qr_token': issued['qr_token']})
    assert done.status_code == 200, done.text
    assert done.json()['verified_at'] and done.json()['trip']['pickup']['verified_at']
    repeated = verify(client, ready, {'qr_token': issued['qr_token']})
    assert repeated.status_code == 200 and repeated.json()['verified_at'] == done.json()['verified_at']


def test_the_six_digits_work_when_the_scan_does_not(client, ready):
    issued = code(client, ready).json()
    done = verify(client, ready, {'pin': issued['pin']})
    assert done.status_code == 200, done.text
    assert done.json()['trip']['pickup']['verified_at']


def test_a_wrong_code_counts_down_and_then_locks(client, ready):
    code(client, ready)
    for left in range(MAX_ATTEMPTS - 1, -1, -1):
        refused = verify(client, ready, {'pin': '000000' if left else '111111'})
        assert refused.status_code == 422 and refused.json()['code'] == 'PICKUP_CODE_INVALID', refused.text
    locked = verify(client, ready, {'pin': code(client, ready).json()['pin']})
    assert locked.status_code == 409 and locked.json()['code'] == 'PICKUP_CODE_LOCKED'
    fresh = client.post(f"/api/v1/trips/{ready.trip['id']}/pickup-code/reissue", headers=bearer(ready.ctx.passenger), json={})
    assert fresh.status_code == 200, fresh.text
    assert verify(client, ready, {'pin': fresh.json()['pin']}).status_code == 200


def test_a_new_code_stops_the_old_one(client, ready):
    old = code(client, ready).json()
    fresh = client.post(f"/api/v1/trips/{ready.trip['id']}/pickup-code/reissue", headers=bearer(ready.ctx.passenger), json={})
    assert fresh.status_code == 200, fresh.text
    assert fresh.json()['pin'] != old['pin'] and fresh.json()['qr_token'] != old['qr_token']
    assert verify(client, ready, {'pin': old['pin']}).status_code == 422
    assert verify(client, ready, {'pin': fresh.json()['pin']}).status_code == 200


def test_a_code_cannot_be_checked_before_the_passenger_opens_it(client, ready):
    refused = verify(client, ready, {'pin': '123456'})
    assert refused.status_code == 409 and refused.json()['code'] == 'PICKUP_CODE_NOT_ISSUED'


def test_one_value_at_a_time(client, ready):
    issued = code(client, ready).json()
    both = verify(client, ready, {'pin': issued['pin'], 'qr_token': issued['qr_token']})
    assert both.status_code == 422
    neither = verify(client, ready, {})
    assert neither.status_code == 422


def test_the_trip_cannot_start_until_the_passenger_is_checked(client, ready, monkeypatch):
    import app.api.routers.hire_api as module
    from datetime import datetime, timedelta, timezone
    from app.models.hire_models import Booking
    run = ready
    with client.app.state.sessions() as db:
        start = db.get(Booking, UUID(run.booking['id'])).start_at

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None): return (start + timedelta(minutes=1)).astimezone(tz or timezone.utc)
    monkeypatch.setattr(module, 'datetime', Clock)
    body = {'expected_version': run.trip['version'], 'start_odometer_km': '1234.5', 'checklist_confirmed': True}
    blocked = client.post(f"/api/v1/trips/{run.trip['id']}/start", headers=bearer(run.ctx.owner), json=body)
    assert blocked.status_code == 409 and blocked.json()['code'] == 'PICKUP_NOT_VERIFIED', blocked.text
    shown = client.get(f"/api/v1/trips/{run.trip['id']}", headers=bearer(run.ctx.owner)).json()
    assert shown['pickup']['required'] is True and shown['pickup']['verified_at'] is None
    pin = code(client, run).json()['pin']
    assert verify(client, run, {'pin': pin}).status_code == 200
    started = client.post(f"/api/v1/trips/{run.trip['id']}/start", headers=bearer(run.ctx.owner), json=body)
    assert started.status_code == 200, started.text
