"""Two-step verification (authenticator app) and closing the account (14 Nov 2026)."""
import time
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
from sqlalchemy import select
from app.models import User
from app.services import two_factor
from conftest import bearer
from test_account_settings import login, register
from test_hire_pricing import hire_setup  # noqa: F401
from test_rates import rate_owner  # noqa: F401

P = '/api/v1'


def now_code(secret, shift=0):
    return two_factor.code_at(secret, int(time.time() // 30) + shift)


def turn_on(client, tokens):
    setup = client.post(P + '/users/me/2fa/setup', headers=bearer(tokens), json={}).json()
    done = client.post(P + '/users/me/2fa/enable', headers=bearer(tokens), json={'code': now_code(setup['secret'])})
    assert done.status_code == 200, done.text
    return setup['secret'], done.json()['backup_codes']


def test_the_standard_one_time_code_matches_the_rfc_example_and_refuses_replays():
    import base64
    secret = base64.b32encode(b'12345678901234567890').decode().rstrip('=')
    assert two_factor.code_at(secret, 1) == '287082'                              # RFC 6238 test vector (time 59)
    step = two_factor.check(secret, '287082', None, now=59)
    assert step == 1 and two_factor.check(secret, '287082', step, now=59) is None  # the same step cannot be used twice
    assert two_factor.check(secret, '000000', None, now=59) is None and two_factor.check(secret, 'abc', None, now=59) is None


def test_turning_on_and_signing_in_with_a_code_or_a_backup_code(client):
    data, person, tokens = register(client)
    assert client.get(P + '/users/me/2fa', headers=bearer(tokens)).json() == {'enabled': False, 'enabled_at': None, 'backup_codes_left': 0}
    wrong = client.post(P + '/users/me/2fa/enable', headers=bearer(tokens), json={'code': '000000'})
    assert wrong.status_code == 409 and wrong.json()['code'] == 'TWO_FACTOR_SETUP_REQUIRED'
    setup = client.post(P + '/users/me/2fa/setup', headers=bearer(tokens), json={}).json()
    assert setup['otpauth_uri'].startswith('otpauth://totp/Travelly:') and setup['secret'] in setup['otpauth_uri']
    assert client.post(P + '/users/me/2fa/enable', headers=bearer(tokens), json={'code': '000000'}).status_code == 422
    secret, codes = setup['secret'], None
    done = client.post(P + '/users/me/2fa/enable', headers=bearer(tokens), json={'code': now_code(secret)}).json()
    codes = done['backup_codes']
    assert done['enabled'] and len(codes) == 10 and done['backup_codes_left'] == 10
    assert client.post(P + '/users/me/2fa/setup', headers=bearer(tokens), json={}).status_code == 409
    # signing in now needs the second step
    first = client.post(P + '/auth/login', json={'identifier': data['email'], 'password': data['password']}).json()
    assert first['status'] == 'two_factor_required' and 'access_token' not in first
    bad = client.post(P + '/auth/2fa', json={'challenge': first['challenge'], 'code': '000000'})
    assert bad.status_code == 422 and bad.json()['code'] == 'TWO_FACTOR_CODE_WRONG'
    good = client.post(P + '/auth/2fa', json={'challenge': first['challenge'], 'code': now_code(secret, 1)})
    assert good.status_code == 200 and client.get(P + '/users/me', headers={'Authorization': 'Bearer ' + good.json()['access_token']}).status_code == 200
    assert client.post(P + '/auth/2fa', json={'challenge': first['challenge'], 'code': now_code(secret, 1)}).status_code == 401   # challenge is used up
    # a backup code works once
    second = client.post(P + '/auth/login', json={'identifier': data['email'], 'password': data['password']}).json()
    assert client.post(P + '/auth/2fa', json={'challenge': second['challenge'], 'code': codes[0]}).status_code == 200
    third = client.post(P + '/auth/login', json={'identifier': data['email'], 'password': data['password']}).json()
    assert client.post(P + '/auth/2fa', json={'challenge': third['challenge'], 'code': codes[0]}).status_code == 422
    assert client.get(P + '/users/me/2fa', headers=bearer(tokens)).json()['backup_codes_left'] == 9


def test_wrong_codes_lock_the_second_step_and_old_sessions_keep_working(client):
    data, _, tokens = register(client)
    secret, _ = turn_on(client, tokens)
    assert client.get(P + '/users/me', headers=bearer(tokens)).status_code == 200          # the signed-in device is not asked again
    challenge = client.post(P + '/auth/login', json={'identifier': data['email'], 'password': data['password']}).json()['challenge']
    for _ in range(5):
        client.post(P + '/auth/2fa', json={'challenge': challenge, 'code': '111111'})
    assert client.post(P + '/auth/2fa', json={'challenge': challenge, 'code': now_code(secret)}).status_code == 429


def test_turning_off_and_new_backup_codes_need_password_and_a_code(client):
    data, _, tokens = register(client)
    secret, codes = turn_on(client, tokens)
    path = P + '/users/me/2fa/disable'
    assert client.post(path, headers=bearer(tokens), json={'password': 'Nope-Nope-1!', 'code': now_code(secret, 1)}).status_code == 422
    fresh = client.post(P + '/users/me/2fa/backup-codes', headers=bearer(tokens), json={'password': data['password'], 'code': codes[1]})
    assert fresh.status_code == 200 and len(fresh.json()['backup_codes']) == 10 and set(fresh.json()['backup_codes']).isdisjoint(codes)
    off = client.post(path, headers=bearer(tokens), json={'password': data['password'], 'code': now_code(secret, 1)})
    assert off.status_code == 200 and off.json()['enabled'] is False
    assert 'access_token' in login(client, data)                                        # plain sign-in again


def blockers_of(client, tokens):
    return client.get(P + '/users/me/account-closure', headers=bearer(tokens)).json()


def test_a_clean_account_can_deactivate_and_signing_in_brings_it_back(client):
    data, person, tokens = register(client)
    assert blockers_of(client, tokens) == {'can_close': True, 'blockers': [], 'delete_after_days': 30}
    refused = client.post(P + '/users/me/deactivate', headers=bearer(tokens), json={'confirm': True, 'password': 'Nope-Nope-1!'})
    assert refused.status_code == 422
    done = client.post(P + '/users/me/deactivate', headers=bearer(tokens), json={'confirm': True, 'password': data['password']})
    assert done.status_code == 200 and done.json()['status'] == 'DEACTIVATED'
    assert client.get(P + '/users/me', headers=bearer(tokens)).status_code in (401, 403)
    back = login(client, data)                                                         # signing in reactivates
    assert back['account_reactivated'] is True and back['delete_request_cancelled'] is False
    assert client.get(P + '/users/me', headers={'Authorization': 'Bearer ' + back['access_token']}).status_code == 200
    with client.app.state.sessions() as db:
        assert db.get(User, UUID(person['id'])).account_status == 'ACTIVE'


def test_open_bookings_and_commission_block_closing_and_deleting(client, hire_setup):
    c = hire_setup
    made = client.post(P + '/bookings/private-hires', headers=bearer(c.passenger), json={
        'service_type_id': str(c.service_id), 'vehicle_id': str(c.vehicle_id), 'itinerary': c.itinerary(), 'passenger_count': 2,
        'large_luggage_count': 0, 'small_luggage_count': 0, 'idempotency_key': uuid4().hex})
    assert made.status_code in (200, 201), made.text
    asked = blockers_of(client, c.passenger)
    assert asked['can_close'] is False and [b['code'] for b in asked['blockers']] == ['OPEN_BOOKINGS_AS_PASSENGER']
    owner = blockers_of(client, c.owner)
    assert 'OPEN_BOOKINGS_AS_OWNER' in [b['code'] for b in owner['blockers']]
    for path in ('deactivate', 'delete-request'):
        no = client.post(P + f'/users/me/{path}', headers=bearer(c.passenger), json={'confirm': True, 'password': 'TravellyStrong1!'})
        assert no.status_code == 409 and no.json()['code'] == 'ACCOUNT_HAS_OPEN_ITEMS'
    assert client.get(P + '/users/me', headers=bearer(c.passenger)).status_code == 200      # nothing changed


def test_a_deactivated_owner_takes_no_new_bookings(client, hire_setup):
    c = hire_setup
    from app.services import commission_overdue
    with client.app.state.sessions() as db:
        from app.models.review_models import Vehicle
        owner_id = db.get(Vehicle, c.vehicle_id).owner_user_id
        assert not commission_overdue.is_blocked(db, client.app.state.settings, owner_id)
        db.get(User, owner_id).account_status = 'DEACTIVATED'; db.commit()
        assert commission_overdue.is_blocked(db, client.app.state.settings, owner_id)
        assert owner_id in commission_overdue.blocked_owner_ids(db, client.app.state.settings)


def test_delete_request_waits_30_days_then_removes_personal_data_only(client):
    from scripts.anonymize_deleted_accounts import run
    data, person, tokens = register(client)
    done = client.post(P + '/users/me/delete-request', headers=bearer(tokens), json={'confirm': True, 'password': data['password']})
    assert done.status_code == 200 and done.json()['delete_after']
    run(client.app, datetime.now(timezone.utc) + timedelta(days=29))
    with client.app.state.sessions() as db:
        assert db.get(User, UUID(person['id'])).full_name == 'Settings Person'
    again = run(client.app, datetime.now(timezone.utc) + timedelta(days=31))
    assert again['anonymised'] >= 1
    with client.app.state.sessions() as db:
        row = db.get(User, UUID(person['id']))
        assert row.full_name == 'Deleted user' and row.account_status == 'CLOSED' and row.phone_e164 is None and row.email.endswith('@deleted.invalid')
        assert row.public_user_reference
    assert client.post(P + '/auth/login', json={'identifier': data['email'], 'password': data['password']}).status_code == 401


def test_signing_in_within_30_days_cancels_the_delete_request(client):
    data, person, tokens = register(client)
    client.post(P + '/users/me/delete-request', headers=bearer(tokens), json={'confirm': True, 'password': data['password']})
    back = login(client, data)
    assert back['account_reactivated'] is True and back['delete_request_cancelled'] is True      # the client shows "Welcome back"
    assert 'account_reactivated' not in login(client, data)                                      # a normal sign-in has neither field
    with client.app.state.sessions() as db:
        row = db.get(User, UUID(person['id']))
        assert row.account_status == 'ACTIVE' and row.deletion_requested_at is None
