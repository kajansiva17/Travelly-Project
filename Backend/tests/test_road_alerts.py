"""Road alerts (PRD matrix 86-89; owner decisions 12 Nov 2026)."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID
from sqlalchemy import select
from app.models import User
from app.models.hire_models import Notification, Trip
from app.models.road_alert_models import RoadAlert
from conftest import bearer
from test_rates import rule, rate_owner
from test_hire_pricing import hire_setup, committed
from test_trip_operations import running, place
from test_ticket_holds import api, person, ticket

HERE = {'latitude': '6.927079', 'longitude': '79.861244'}          # Colombo Fort
NEAR = {'latitude': '6.930000', 'longitude': '79.865000'}          # ~0.5 km away
FAR = {'latitude': '7.290572', 'longitude': '80.633728'}           # Kandy, ~95 km


def report(client, run, who=None, **body):
    data = {'trip_id': run.trip['id'], 'alert_type': 'POLICE_PRESENCE', **HERE, **body}
    return client.post('/api/v1/road-alerts', headers=bearer(who or run.ctx.owner), json=data)


def live(client, run):
    assert place(client, run, run.ctx.owner).status_code == 200


def language(client, user_id, code):
    with client.app.state.sessions() as db:
        db.get(User, UUID(user_id)).preferred_language = code
        db.commit()


def second_driver(client, ticket, at=NEAR):
    """Another Driver on a running trip nearby: the ticket departure's journey, set in motion."""
    driver = person(client, 'DRIVER')
    with client.app.state.sessions() as db:
        trip = db.scalar(select(Trip).where(Trip.scheduled_trip_id == UUID(ticket['trip']['id'])))
        trip.driver_user_id, trip.status = UUID(driver['id']), 'IN_PROGRESS'
        trip.actual_start_at, trip.start_odometer_km = datetime.now(timezone.utc), Decimal('10')
        trip.current_latitude, trip.current_longitude = Decimal(at['latitude']), Decimal(at['longitude'])
        trip.location_updated_at, trip.tracking_status = datetime.now(timezone.utc), 'ACTIVE'
        db.commit()
        return driver, str(trip.id)


def test_the_driver_reports_and_nearby_people_hear_it_in_their_language(client, running):
    live(client, running)
    language(client, running.ctx.passenger_id, 'ta')
    done = report(client, running)
    assert done.status_code == 201, done.text
    body = done.json()
    assert body['status'] == 'UNCONFIRMED' and body['source_input'] == 'BUTTON' and body['notified'] >= 1
    minutes = (datetime.fromisoformat(body['expires_at']) - datetime.fromisoformat(body['reported_at'])).total_seconds() / 60
    assert round(minutes) == 60   # police: one hour
    with client.app.state.sessions() as db:
        heard = db.scalars(select(Notification).where(Notification.recipient_user_id == UUID(running.ctx.passenger_id),
                                                      Notification.notification_type == 'ROAD_ALERT')).all()
    assert len(heard) == 1 and heard[0].action_payload['language'] == 'ta'
    assert heard[0].action_payload['speak'].startswith('முன்னால் போலீஸ்')
    seen = client.get(f"/api/v1/road-alerts?trip_id={running.trip['id']}", headers=bearer(running.ctx.passenger)).json()
    assert seen['items'][0]['message'].startswith('முன்னால் போலீஸ்') and seen['items'][0]['can_vote'] is False


def test_reporting_rules(client, running):
    live(client, running)
    far = report(client, running, **FAR)
    assert far.status_code == 422 and far.json()['code'] == 'ALERT_TOO_FAR'
    voice = report(client, running, source_input='VOICE', confidence_score='0.9')
    assert voice.status_code == 422 and voice.json()['code'] == 'DRIVER_CONFIRMATION_REQUIRED'
    ok = report(client, running, source_input='VOICE', confidence_score='0.9', driver_confirmed=True, alert_type='ACCIDENT')
    assert ok.status_code == 201 and ok.json()['source_input'] == 'VOICE'
    passenger = report(client, running, who=running.ctx.passenger)
    assert passenger.status_code == 403   # Passengers cannot report; only the trip's Driver
    again = report(client, running, alert_type='ACCIDENT')
    assert again.status_code == 200 and again.json()['merged'] and not again.json()['counted_as_confirmation']


def test_voice_is_understood_in_three_languages_but_never_sent_alone(client, running):
    owner = running.ctx.owner
    ta = client.post('/api/v1/road-alerts/voice-classify', headers=bearer(owner), json={'transcript': 'முன்னால போலீஸ் நிக்குது', 'language': 'ta'}).json()
    assert ta['alert_type'] == 'POLICE_PRESENCE' and ta['confirm_prompt'] == 'போலீஸ் எச்சரிக்கை அனுப்பவா?'
    si = client.post('/api/v1/road-alerts/voice-classify', headers=bearer(owner), json={'transcript': 'ඉස්සරහ අනතුරක් වෙලා', 'language': 'si'}).json()
    assert si['alert_type'] == 'ACCIDENT'
    en = client.post('/api/v1/road-alerts/voice-classify', headers=bearer(owner), json={'transcript': 'police speed check ahead', 'language': 'en'}).json()
    assert en['alert_type'] == 'SPEED_CHECK' and {c['alert_type'] for c in en['candidates']} == {'SPEED_CHECK', 'POLICE_PRESENCE'}
    none = client.post('/api/v1/road-alerts/voice-classify', headers=bearer(owner), json={'transcript': 'hello there', 'language': 'en'}).json()
    assert none['alert_type'] is None
    with client.app.state.sessions() as db:
        assert db.scalar(select(RoadAlert.id).limit(1)) is None   # classifying stores nothing


def test_nearby_drivers_confirm_or_deny(client, running, ticket, monkeypatch):
    live(client, running)
    alert = report(client, running).json()
    other, other_trip = second_driver(client, ticket)
    shown = api(client, other, 'get', f'/road-alerts?trip_id={other_trip}').json()['items']
    assert shown[0]['id'] == alert['id'] and shown[0]['can_vote'] and 0 < shown[0]['distance_km'] < 1
    yes = api(client, other, 'post', f"/road-alerts/{alert['id']}/votes", {'vote': 'CONFIRM'})
    assert yes.status_code == 200, yes.text
    assert yes.json()['status'] == 'ACTIVE' and yes.json()['confirmation_count'] == 1
    assert yes.json()['expires_at'] >= alert['expires_at']
    assert api(client, other, 'post', f"/road-alerts/{alert['id']}/votes", {'vote': 'DENY'}).json()['code'] == 'ALREADY_ANSWERED'
    own = client.post(f"/api/v1/road-alerts/{alert['id']}/votes", headers=bearer(running.ctx.owner), json={'vote': 'CONFIRM'})
    assert own.json()['code'] == 'OWN_ROAD_ALERT'
    # A second report of the same thing at the same place by another Driver counts as their confirmation.
    monkeypatch.setenv('ROAD_ALERT_REMOVED_AFTER_DENIALS', '1')
    hazard = report(client, running, alert_type='ROAD_HAZARD').json()
    gone = api(client, other, 'post', f"/road-alerts/{hazard['id']}/votes", {'vote': 'DENY'})
    assert gone.json()['status'] == 'REJECTED'
    far_driver, _ = second_driver(client, ticket, FAR)
    assert api(client, far_driver, 'post', f"/road-alerts/{alert['id']}/votes", {'vote': 'CONFIRM'}).json()['code'] == 'NOT_NEAR_ROAD_ALERT'


def test_admin_takes_an_alert_down_and_old_alerts_expire(client, running, ticket):
    live(client, running)
    alert = report(client, running).json()
    boss = ticket['admin']
    assert api(client, ticket['owner'], 'get', '/admin/road-alerts').status_code == 403
    listed = api(client, boss, 'get', '/admin/road-alerts?status=unconfirmed').json()['items']
    assert any(i['id'] == alert['id'] for i in listed)
    removed = api(client, boss, 'post', f"/admin/road-alerts/{alert['id']}/moderation",
                  {'expected_version': alert['version'], 'action': 'REMOVE', 'reason': 'Prank report.'})
    assert removed.status_code == 200 and removed.json()['status'] == 'REMOVED'
    assert client.get(f"/api/v1/road-alerts?trip_id={running.trip['id']}", headers=bearer(running.ctx.owner)).json()['items'] == []
    other = report(client, running, alert_type='ROADBLOCK').json()
    with client.app.state.sessions() as db:
        row = db.get(RoadAlert, UUID(other['id']))
        row.reported_at = row.reported_at - timedelta(hours=4)
        row.expires_at = row.reported_at + timedelta(hours=3)
        db.commit()
    assert client.get(f"/api/v1/road-alerts?trip_id={running.trip['id']}", headers=bearer(running.ctx.owner)).json()['items'] == []
    with client.app.state.sessions() as db:
        assert db.get(RoadAlert, UUID(other['id'])).status == 'EXPIRED'


def test_notification_list_carries_type_and_payload(client, running):
    live(client, running)
    alert = report(client, running).json()
    items = client.get('/api/v1/notifications', headers=bearer(running.ctx.passenger)).json()['items']
    road = [i for i in items if i['notification_type'] == 'ROAD_ALERT']
    assert len(road) == 1
    item = road[0]
    assert item['action_payload']['road_alert_id'] == alert['id'] and item['trip_id'] == running.trip['id']
    assert item['expires_at'] and item['created_at'] and item['read_at'] is None and item['channel']
    assert {'booking_id', 'scheduled_trip_id', 'action_required', 'response_code', 'support_vehicle_id'} <= item.keys()
