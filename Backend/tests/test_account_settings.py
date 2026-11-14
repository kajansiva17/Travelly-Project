"""Settings, Account security: sessions, password change, notification preferences (14 Nov 2026)."""
from uuid import UUID, uuid4
from sqlalchemy import select
from app.models.hire_models import Notification
from conftest import bearer
from test_hire_pricing import signed_in

PHONE = lambda: '+9477' + str(uuid4().int % 10000000).zfill(7)


def register(client):
    data = {'full_name': 'Settings Person', 'email': uuid4().hex + '@example.com', 'phone_e164': PHONE(), 'password': 'TravellyStrong1!', 'accept_terms': True}
    person, tokens = signed_in(client, data)
    return data, person, tokens


def login(client, data, agent='Mozilla/5.0 (Windows NT 10.0) Chrome/120.0 Safari/537.36', password=None):
    r = client.post('/api/v1/auth/login', json={'identifier': data['email'], 'password': password or data['password']}, headers={'user-agent': agent})
    assert r.status_code == 200, r.text
    return r.json()


def test_the_person_sees_and_ends_their_own_sessions(client):
    data, person, first = register(client)
    phone = login(client, data, 'Mozilla/5.0 (Linux; Android 14) Chrome/120.0 Mobile Safari/537.36')
    listing = client.get('/api/v1/users/me/sessions', headers=bearer(first)).json()['items']
    assert len(listing) >= 2 and listing[0]['current'] is True
    other = next(i for i in listing if i['device'] == 'Chrome on Android')
    assert not other['current'] and other['signed_in_at'] and other['last_active_at']
    assert client.delete(f"/api/v1/users/me/sessions/{listing[0]['id']}", headers=bearer(first)).status_code == 409   # this device: use Log out
    assert client.delete(f"/api/v1/users/me/sessions/{other['id']}", headers=bearer(first)).status_code == 204
    assert client.get('/api/v1/users/me', headers=bearer(phone)).status_code == 401                                    # that device is signed out
    assert client.delete(f"/api/v1/users/me/sessions/{other['id']}", headers=bearer(first)).status_code == 404
    third, fourth = login(client, data), login(client, data)
    resp = client.post('/api/v1/users/me/sessions/revoke-others', headers=bearer(first), json={}); gone = resp.json()
    assert gone['signed_out'] >= 2
    assert client.get('/api/v1/users/me', headers=bearer(first)).status_code == 200
    assert client.get('/api/v1/users/me', headers=bearer(third)).status_code == 401 and client.get('/api/v1/users/me', headers=bearer(fourth)).status_code == 401


def test_sessions_belong_to_one_person_only(client):
    _, _, mine = register(client)
    _, _, theirs = register(client)
    theirs_id = client.get('/api/v1/users/me/sessions', headers=bearer(theirs)).json()['items'][0]['id']
    assert client.delete(f'/api/v1/users/me/sessions/{theirs_id}', headers=bearer(mine)).status_code == 404
    assert client.get('/api/v1/users/me', headers=bearer(theirs)).status_code == 200
    assert client.get('/api/v1/users/me/sessions').status_code == 401


def test_changing_the_password_keeps_this_device_and_signs_out_the_others(client):
    data, _, here = register(client)
    other = login(client, data)
    path = '/api/v1/users/me/password'
    wrong = client.post(path, headers=bearer(here), json={'current_password': 'Nope-Nope-1!', 'new_password': 'BrandNewPass9!'})
    assert wrong.status_code == 422 and wrong.json()['code'] == 'CURRENT_PASSWORD_WRONG'
    same = client.post(path, headers=bearer(here), json={'current_password': data['password'], 'new_password': data['password']})
    assert same.status_code == 422 and same.json()['code'] == 'PASSWORD_UNCHANGED'
    weak = client.post(path, headers=bearer(here), json={'current_password': data['password'], 'new_password': 'short'})
    assert weak.status_code == 422
    done = client.post(path, headers=bearer(here), json={'current_password': data['password'], 'new_password': 'BrandNewPass9!'})
    assert done.status_code == 200 and done.json()['access_token'] and done.json()['refresh_token']
    assert client.get('/api/v1/users/me', headers=bearer(here)).status_code == 401              # old tokens end
    assert client.get('/api/v1/users/me', headers=bearer(other)).status_code == 401
    assert client.get('/api/v1/users/me', headers={'Authorization': 'Bearer ' + done.json()['access_token']}).status_code == 200
    assert client.post('/api/v1/auth/login', json={'identifier': data['email'], 'password': data['password']}).status_code == 401
    login(client, data, password='BrandNewPass9!')


def test_repeated_wrong_current_passwords_lock_the_change(client):
    data, _, tokens = register(client)
    for _ in range(5):
        client.post('/api/v1/users/me/password', headers=bearer(tokens), json={'current_password': 'Wrong-Wrong-1!', 'new_password': 'BrandNewPass9!'})
    locked = client.post('/api/v1/users/me/password', headers=bearer(tokens), json={'current_password': data['password'], 'new_password': 'BrandNewPass9!'})
    assert locked.status_code == 429


def test_only_optional_notifications_can_be_turned_off_and_they_stop_showing(client):
    _, person, tokens = register(client)
    prefs = client.get('/api/v1/users/me/notification-preferences', headers=bearer(tokens)).json()['items']
    by = {i['notification_type']: i for i in prefs}
    assert by['ROAD_ALERT']['can_turn_off'] and by['ROAD_ALERT']['enabled'] and not by['PAYMENT']['can_turn_off']
    refused = client.put('/api/v1/users/me/notification-preferences', headers=bearer(tokens), json={'muted': ['PAYMENT', 'ROAD_ALERT']})
    assert refused.status_code == 422 and refused.json()['code'] == 'NOTIFICATION_CANNOT_BE_TURNED_OFF'
    with client.app.state.sessions() as db:
        uid = UUID(person['id'])
        for kind in ('ROAD_ALERT', 'PAYMENT'):
            db.add(Notification(recipient_user_id=uid, notification_type=kind, channel='IN_APP', title=kind, body='x', action_required=False,
                                action_payload={}, status='QUEUED', created_by=uid, updated_by=uid))
        db.commit()
    assert {n['notification_type'] for n in client.get('/api/v1/notifications', headers=bearer(tokens)).json()['items']} == {'ROAD_ALERT', 'PAYMENT'}
    saved = client.put('/api/v1/users/me/notification-preferences', headers=bearer(tokens), json={'muted': ['ROAD_ALERT']})
    assert saved.status_code == 200 and next(i for i in saved.json()['items'] if i['notification_type'] == 'ROAD_ALERT')['enabled'] is False
    assert {n['notification_type'] for n in client.get('/api/v1/notifications', headers=bearer(tokens)).json()['items']} == {'PAYMENT'}
    client.put('/api/v1/users/me/notification-preferences', headers=bearer(tokens), json={'muted': []})
    assert len(client.get('/api/v1/notifications', headers=bearer(tokens)).json()['items']) == 2
