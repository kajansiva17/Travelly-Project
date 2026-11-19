"""Odometer photo proof at trip start and finish (owner decision 13 Nov 2026)."""
import io
from datetime import datetime, timedelta, timezone
from uuid import UUID
import httpx
import pytest
from PIL import Image
from app.models.hire_models import Booking, Trip
from app.models.review_models import Vehicle
from app.services import ai_assist
from conftest import bearer, check_passenger
from test_rates import rule, rate_owner
from test_hire_pricing import hire_setup, committed
from test_ticket_holds import person, api


def jpeg():
    out = io.BytesIO()
    Image.new('RGB', (64, 48), (20, 20, 20)).save(out, 'JPEG')
    return out.getvalue()


@pytest.fixture
def ready(client, hire_setup, monkeypatch):
    """A confirmed self-drive booking at its pickup time, photo rule on, the photo AI reading what `reads` says."""
    import app.api.routers.hire_api as module
    c = hire_setup
    booking = committed(client, c)
    detail = client.get(f"/api/v1/bookings/{booking['id']}", headers=bearer(c.owner)).json()
    with client.app.state.sessions() as db:
        row = db.get(Booking, UUID(booking['id']))
        start, pickup = row.start_at, row.itinerary_snapshot['itinerary']['stops'][0]['place']

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None): return (start + timedelta(minutes=1)).astimezone(tz or timezone.utc)
    monkeypatch.setattr(module, 'datetime', Clock)
    client.app.state.settings = client.app.state.settings.model_copy(update={'odometer_photo_required': True})
    monkeypatch.setenv('OPENROUTER_API_KEY', 'test-key')
    reads = {'value': None}

    def fake(name, settings, prompt, schema, image=None):
        if reads['value'] == 'offline': raise httpx.ConnectError('offline')   # every service is down, whichever keys the machine's .env holds
        assert 'odometer' in prompt.lower() and image.startswith('data:image/jpeg;base64,')
        return {'readable': False} if reads['value'] is None else {'readable': True, 'odometer_km': reads['value']}
    monkeypatch.setattr(ai_assist, 'call', fake)
    here = {'latitude': str(pickup['latitude']), 'longitude': str(pickup['longitude'])}
    return type('Ready', (), {'ctx': c, 'booking': booking, 'trip': detail['trip'], 'reads': reads, 'here': here})


def snap(client, run, stage, typed, where=None, code=None):
    if code is None:
        opened = client.post(f"/api/v1/trips/{run.trip['id']}/odometer-session", headers=bearer(run.ctx.owner), json={'stage': stage})
        assert opened.status_code == 200, opened.text
        code = opened.json()['capture_code']
    data = {'capture_code': code, 'stage': stage, 'typed_km': typed, **(where or run.here)}
    reply = client.post(f"/api/v1/trips/{run.trip['id']}/odometer-photo", headers=bearer(run.ctx.owner), data=data,
                        files={'file': ('odo.jpg', jpeg(), 'image/jpeg')})
    return reply, code


def start(client, run, km):
    trip = client.get(f"/api/v1/bookings/{run.booking['id']}", headers=bearer(run.ctx.owner)).json()['trip']
    if not trip['pickup']['verified_at']:
        check_passenger(client, run.ctx.passenger, run.ctx.owner, run.trip['id'], trip['version'])
    return client.post(f"/api/v1/trips/{run.trip['id']}/start", headers=bearer(run.ctx.owner),
                       json={'expected_version': trip['version'], 'start_odometer_km': km, 'checklist_confirmed': True})


def test_start_needs_a_live_photo_that_matches_the_typed_reading(client, ready):
    assert start(client, ready, '1234.5').json()['code'] == 'ODOMETER_PROOF_REQUIRED'
    ready.reads['value'] = 1300
    wrong, code = snap(client, ready, 'START', '1234.5')
    assert wrong.status_code == 200 and wrong.json()['result'] == 'MISMATCH' and not wrong.json()['can_continue']
    assert wrong.json()['read_km'] == '1300.0'
    assert start(client, ready, '1234.5').json()['code'] == 'ODOMETER_PROOF_REQUIRED'
    reused, _ = snap(client, ready, 'START', '1234.5', code=code)
    assert reused.status_code == 409 and reused.json()['code'] == 'CAPTURE_CODE_INVALID'   # one photo per camera session
    far, _ = snap(client, ready, 'START', '1234.5', where={'latitude': '9.6615', 'longitude': '80.0255'})
    assert far.status_code == 422 and far.json()['code'] == 'NOT_AT_PICKUP'
    ready.reads['value'] = 1234
    good, _ = snap(client, ready, 'START', '1234.5')
    assert good.json()['result'] == 'MATCH' and good.json()['can_continue']
    assert start(client, ready, '1240.0').json()['code'] == 'ODOMETER_PROOF_REQUIRED'   # must be the photographed number
    started = start(client, ready, '1234.5')
    assert started.status_code == 200, started.text


def test_unreadable_photos_allow_the_typed_number_after_three_tries_and_no_reader_never_blocks(client, ready, monkeypatch):
    for attempt in (1, 2):
        dark, _ = snap(client, ready, 'START', '1234.5')
        assert dark.json()['result'] == 'UNREADABLE' and not dark.json()['can_continue'] and dark.json()['tries_unreadable'] == attempt
    third, _ = snap(client, ready, 'START', '1234.5')
    assert third.json()['result'] == 'UNREADABLE' and third.json()['can_continue']
    ready.reads['value'] = 'offline'
    unchecked, _ = snap(client, ready, 'START', '1234.5')
    assert unchecked.json()['result'] == 'NOT_CHECKED' and unchecked.json()['can_continue']
    assert start(client, ready, '1234.5').status_code == 200


def test_the_reading_never_goes_below_the_vehicle_s_last_odometer(client, ready):
    with client.app.state.sessions() as db:
        trip = db.get(Trip, UUID(ready.trip['id']))
        db.get(Vehicle, trip.vehicle_id).current_odometer_km = 2000
        db.commit()
    low, _ = snap(client, ready, 'START', '1234.5')
    assert low.status_code == 422 and low.json()['code'] == 'ODOMETER_BELOW_LAST'
    client.app.state.settings = client.app.state.settings.model_copy(update={'odometer_photo_required': False})
    assert start(client, ready, '1234.5').json()['code'] == 'ODOMETER_BELOW_LAST'   # checked even without the photo rule


def test_proof_is_shown_to_the_passenger_and_owner_and_photos_go_after_seven_days(client, ready, monkeypatch):
    ready.reads['value'] = 1234.5
    snap(client, ready, 'START', '1234.5')
    assert start(client, ready, '1234.5').status_code == 200
    trip = client.get(f"/api/v1/bookings/{ready.booking['id']}", headers=bearer(ready.ctx.owner)).json()['trip']
    early = client.post(f"/api/v1/trips/{ready.trip['id']}/complete", headers=bearer(ready.ctx.owner),
                        json={'expected_version': trip['version'], 'end_odometer_km': '1300.5'})
    assert early.json()['code'] == 'ODOMETER_PROOF_REQUIRED'
    low, _ = snap(client, ready, 'END', '1200.0')
    assert low.json()['code'] == 'ODOMETER_BELOW_START'
    ready.reads['value'] = 1300.5
    assert snap(client, ready, 'END', '1300.5')[0].json()['result'] == 'MATCH'
    done = client.post(f"/api/v1/trips/{ready.trip['id']}/complete", headers=bearer(ready.ctx.owner),
                       json={'expected_version': trip['version'], 'end_odometer_km': '1300.5'})
    assert done.status_code == 200, done.text
    seen = client.get(f"/api/v1/trips/{ready.trip['id']}/odometer-proof", headers=bearer(ready.ctx.passenger)).json()
    assert seen['distance_km'] == '66.0' and seen['start']['reading_km'] == '1234.5' and seen['end']['result'] == 'MATCH'
    assert seen['start']['photo_available'] and seen['photos_kept_days'] == 7 and 'latitude' not in seen['start']
    photo = client.get(seen['end']['photo_url'], headers=bearer(ready.ctx.passenger))
    assert photo.status_code == 200 and photo.headers['content-type'] == 'image/jpeg' and photo.content[:2] == b'\xff\xd8'
    stranger = person(client, 'DRIVER')
    assert api(client, stranger, 'get', f"/trips/{ready.trip['id']}/odometer-proof").status_code == 404
    import app.services.odometer_proof as proof_module
    with client.app.state.sessions() as db:
        ended = db.get(Trip, UUID(ready.trip['id'])).actual_end_at

    class Later(datetime):
        @classmethod
        def now(cls, tz=None): return (ended + timedelta(days=7, minutes=1)).astimezone(tz or timezone.utc)
    monkeypatch.setattr(proof_module, 'datetime', Later)
    later = client.get(f"/api/v1/trips/{ready.trip['id']}/odometer-proof", headers=bearer(ready.ctx.owner)).json()
    assert not later['start']['photo_available'] and later['start']['photo_url'] is None and later['start']['photo_deleted_at']
    assert later['start']['reading_km'] == '1234.5' and later['distance_km'] == '66.0'   # the numbers stay
    assert client.get(seen['end']['photo_url'], headers=bearer(ready.ctx.owner)).status_code == 404


def test_the_daily_job_deletes_old_photos(client, ready, monkeypatch):
    import importlib.util, sys
    from pathlib import Path
    import app.services.odometer_proof as proof_module
    ready.reads['value'] = 1234.5
    snap(client, ready, 'START', '1234.5')
    with client.app.state.sessions() as db:
        trip = db.get(Trip, UUID(ready.trip['id']))
        trip.status = 'CANCELLED'
        db.commit()
    spec = importlib.util.spec_from_file_location('odo_job', Path(__file__).parents[1] / 'scripts' / 'delete_old_odometer_photos.py')
    job = importlib.util.module_from_spec(spec); spec.loader.exec_module(job)
    assert job.run(client.app) == 0   # not yet 7 days

    class Later(datetime):
        @classmethod
        def now(cls, tz=None): return datetime.now(tz or timezone.utc) + timedelta(days=8)
    monkeypatch.setattr(proof_module, 'datetime', Later)
    assert job.run(client.app) == 1


def test_the_trip_map_has_the_route_from_start_to_end(client, ready):
    shown = client.get(f"/api/v1/trips/{ready.trip['id']}/map", headers=bearer(ready.ctx.passenger))
    assert shown.status_code == 200, shown.text
    body = shown.json()
    assert body['points'][0]['kind'] == 'START' and body['points'][-1]['kind'] == 'END' and body['position'] is None
    assert body['points'][0]['latitude'] == ready.here['latitude']
    stranger = person(client, 'DRIVER')
    assert api(client, stranger, 'get', f"/trips/{ready.trip['id']}/map").status_code == 404


def test_active_trips_list_shows_a_running_trip_to_its_people_and_then_hides_it(client, ready):
    c = ready.ctx
    client.app.state.settings = client.app.state.settings.model_copy(update={'odometer_photo_required': False})
    assert client.get('/api/v1/trips/active', headers=bearer(c.owner)).json() == {'items': []}   # not started yet
    assert client.get('/api/v1/trips/active').status_code == 401
    assert start(client, ready, '1234.5').status_code == 200
    mine = client.get('/api/v1/trips/active', headers=bearer(c.owner))
    assert mine.status_code == 200, mine.text
    [item] = mine.json()['items']
    assert item['trip_id'] == ready.trip['id'] and item['kind'] == 'PRIVATE_HIRE' and 'OWNER' in item['viewer_roles']
    assert item['origin'] and item['destination'] and item['vehicle'] and item['actual_start_at'] and item['start_odometer_km'] == '1234.5'
    riding = client.get('/api/v1/trips/active', headers=bearer(c.passenger)).json()['items']
    assert [i['trip_id'] for i in riding] == [ready.trip['id']] and riding[0]['viewer_roles'] == ['PASSENGER']
    stranger = person(client)['tokens']
    assert client.get('/api/v1/trips/active', headers=bearer(stranger)).json() == {'items': []}
    detail = client.get(f"/api/v1/trips/{ready.trip['id']}", headers=bearer(c.owner))
    assert detail.status_code == 200      # the path /trips/active did not break /trips/{id}
