import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from pydantic import ValidationError
from sqlalchemy import select, text
from app.models import User, UserRole
from app.schemas import RegisterRequest, email_address
from app.security import hasher
from conftest import signed_in, bearer, captured_token


@pytest.mark.parametrize('email', [' 1John@gmail.com ', 'john+travel@gmail.com', 'UPPER@EXAMPLE.COM', 'first.last@example.com'])
def test_public_email_accepts_valid_usernames(email):
    assert email_address(email) == email.strip().lower()


@pytest.mark.parametrize('email', ['.john@example.com', 'john.@example.com', 'jo..hn@example.com', 'john@localhost', 'john@local', 'john @example.com', 'john@exam ple.com', 'john@example.com\nother', 'john@example.invalid', '@example.com', 'john@', 'john@@example.com'])
def test_invalid_public_emails(email):
    with pytest.raises(ValueError): email_address(email)


@pytest.mark.parametrize('field,value', [('accept_terms', 1), ('accept_terms', False), ('phone_e164', None), ('email', None)])
def test_new_registration_required_details(passenger, field, value):
    with pytest.raises(ValidationError): RegisterRequest(**{**passenger, field: value})


def test_registration_verification_and_atomic_replay(client, passenger):
    result = client.post('/api/v1/auth/register', json=passenger)
    assert result.status_code == 201, result.text
    data = result.json()
    assert data['email_delivery'] == 'captured' and data['email_verified_at'] is None
    assert 'access_token' not in data and data['approved_roles'] == ['PASSENGER']
    login = client.post('/api/v1/auth/login', json={'identifier': passenger['email'], 'password': passenger['password']})
    assert login.json()['status'] == 'verification_required' and 'access_token' not in login.json()
    token = captured_token(client)
    assert token not in result.text
    assert client.post('/api/v1/auth/password/reset', json={'token': token, 'password': 'AnotherStrong1!'}).status_code == 400
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: client.post('/api/v1/auth/email/verify', json={'token': token}).status_code, range(2)))
    assert sorted(results) == [200, 400]
    login = client.post('/api/v1/auth/login', json={'identifier': passenger['email'].upper(), 'password': passenger['password']})
    profile = client.get('/api/v1/users/me', headers=bearer(login.json())).json()
    assert profile['account_status'] == 'ACTIVE' and profile['email_verified_at']
    assert profile['phone_verified_at'] is None and profile['approved_roles'] == ['PASSENGER']


def test_expired_links_resend_and_delivery_failure(client, passenger, monkeypatch):
    result = client.post('/api/v1/auth/register', json=passenger).json()
    token = captured_token(client)
    state, store = client.app.state.auth_state, client.app.state.store
    store.client.delete(state.key('verify', token))
    assert client.post('/api/v1/auth/email/verify', json={'token': token}).status_code == 400
    assert client.post('/api/v1/auth/email/resend', json={'ticket': result['verification_ticket']}).status_code == 429
    # Expire only the isolated test's per-user cooldown, not global session/other-user state.
    from app.security import digest
    store.client.delete(store.key('limit:' + digest('email-minute:verify:' + result['id'])))
    monkeypatch.setattr(client.app.state.mailer, 'send', lambda *args: 'failed')
    failed = client.post('/api/v1/auth/email/resend', json={'ticket': result['verification_ticket']})
    assert failed.status_code == 200 and failed.json()['email_delivery'] == 'failed'
    assert 'could not' in failed.json()['message']
    assert client.post('/api/v1/auth/email/verify', json={'token': result['verification_ticket']}).status_code == 400


@pytest.mark.parametrize('outcome', ['failed', 'daily_limit'])
def test_creation_survives_mail_failure_without_verifying(client, passenger, monkeypatch, outcome):
    monkeypatch.setattr(client.app.state.mailer, 'send', lambda *args: outcome)
    result = client.post('/api/v1/auth/register', json=passenger)
    assert result.status_code == 201 and result.json()['email_delivery'] == outcome
    with client.app.state.sessions() as db:
        user = db.get(User, UUID(result.json()['id']))
        assert not user.email_verified_at and user.email_login_required
        assert len(db.scalars(select(UserRole).where(UserRole.user_id == user.id)).all()) == 1


def legacy(client, email=None, password='old password with spaces'):
    with client.app.state.sessions() as db:
        user = User(public_user_reference='USR-' + uuid4().hex[:16].upper(), full_name='Legacy Passenger',
            email=email or uuid4().hex + '@example.com', password_hash=hasher.hash(password), email_login_required=False)
        db.add(user); db.flush()
        db.add(UserRole(user_id=user.id, role_code='PASSENGER', approval_status='APPROVED', approved_at=user.created_at))
        db.commit()
        return str(user.id), str(user.email), password


def test_old_password_and_unverified_account_remain_usable(client):
    uid, email, password = legacy(client)
    result = client.post('/api/v1/auth/login', json={'identifier': email, 'password': password})
    assert result.status_code == 200 and 'access_token' in result.json()
    profile = client.get('/api/v1/users/me', headers=bearer(result.json())).json()
    assert profile['id'] == uid and profile['email_verified_at'] is None
    sent = client.post('/api/v1/users/me/email-verification', json={}, headers=bearer(result.json()))
    assert sent.json()['email_delivery'] == 'captured'
    assert client.post('/api/v1/auth/email/verify', json={'token': captured_token(client)}).status_code == 200


def test_recovery_is_generic_and_revokes_all_sessions_without_changing_roles(client, passenger):
    user, tokens = signed_in(client, passenger)
    role = client.post('/api/v1/users/me/role-requests', json={'role_code': 'OWNER'}, headers=bearer(tokens)).json()
    existing = client.post('/api/v1/auth/password/forgot', json={'email': passenger['email']})
    missing = client.post('/api/v1/auth/password/forgot', json={'email': 'missing@example.com'})
    assert existing.status_code == missing.status_code == 202 and existing.json() == missing.json()
    token = captured_token(client, 'reset')
    weak = client.post('/api/v1/auth/password/reset', json={'token': token, 'password': 'no strength'})
    assert weak.status_code == 422 and 'no strength' not in weak.text
    result = client.post('/api/v1/auth/password/reset', json={'token': token, 'password': 'NewTravellyPass1!'})
    assert result.status_code == 200
    assert client.get('/api/v1/users/me', headers=bearer(tokens)).status_code == 401
    assert client.post('/api/v1/auth/refresh', json={'refresh_token': tokens['refresh_token']}).status_code == 401
    assert client.post('/api/v1/auth/password/reset', json={'token': token, 'password': 'YetAnotherPass1!'}).status_code == 400
    login = client.post('/api/v1/auth/login', json={'identifier': passenger['email'], 'password': 'NewTravellyPass1!'}).json()
    roles = client.get('/api/v1/users/me/roles', headers=bearer(login)).json()['items']
    assert any(r['id'] == role['id'] and r['approval_status'] == 'PENDING' for r in roles)
    assert client.get('/api/v1/users/me', headers=bearer(login)).json()['id'] == user['id']


def test_recovery_never_sends_to_unverified_or_restricted_account(client, passenger):
    result = client.post('/api/v1/auth/register', json=passenger).json()
    before = list(client.app.state.settings.mail_capture_dir.glob('*.eml'))
    assert client.post('/api/v1/auth/password/forgot', json={'email': passenger['email']}).status_code == 202
    assert list(client.app.state.settings.mail_capture_dir.glob('*.eml')) == before
    with client.app.state.sessions() as db:
        db.get(User, UUID(result['id'])).account_status = 'BLOCKED'; db.commit()
    assert client.post('/api/v1/auth/email/verify', json={'token': captured_token(client)}).status_code == 403


@pytest.fixture(scope='module')
def signing_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def google(client, monkeypatch, signing_key):
    monkeypatch.setattr(client.app.state.google.keys, 'get_signing_key_from_jwt', lambda _: SimpleNamespace(key=signing_key.public_key()))
    def credential(email='new@gmail.com', *, headers=None, **overrides):
        path = '/api/v1/users/me/google/challenge' if headers else '/api/v1/auth/google/challenge'
        challenge = client.post(path, json={}, headers=headers).json()
        claims = {'iss': 'https://accounts.google.com', 'aud': client.app.state.settings.google_client_id,
            'sub': 'google-subject-1', 'iat': int(time.time()), 'exp': int(time.time()) + 300,
            'nonce': challenge['nonce'], 'email': email, 'email_verified': True, 'name': 'Google Passenger', **overrides}
        return {'credential': jwt.encode(claims, signing_key, algorithm='RS256', headers={'kid': 'test-key'}), 'challenge': challenge['challenge']}
    return credential


@pytest.mark.parametrize('claims', [{'iss': 'https://attacker.example'}, {'aud': 'wrong-client'}, {'exp': 1}, {'nonce': 'wrong'}, {'sub': ''}, {'azp': 'wrong'}])
def test_google_token_claim_rejections(client, google, claims):
    assert client.post('/api/v1/auth/google', json=google(**claims)).status_code == 401


def test_google_signature_and_replay_rejected(client, google):
    data = google()
    pieces = data['credential'].split('.')
    data['credential'] = '.'.join([*pieces[:2], 'invalidsignature'])
    assert client.post('/api/v1/auth/google', json=data).status_code == 401
    good = google()
    assert client.post('/api/v1/auth/google', json=good).status_code == 200
    assert client.post('/api/v1/auth/google', json=good).status_code == 401


@pytest.mark.parametrize('email,claims,verified', [('new@gmail.com', {}, True), ('person@company.com', {'hd': 'company.com'}, True), ('person@example.com', {}, False), ('new@gmail.com', {'email_verified': False}, False)])
def test_google_completion_requires_details_and_authoritative_email(client, passenger, google, email, claims, verified):
    result = client.post('/api/v1/auth/google', json=google(email, **claims)).json()
    assert result['status'] == 'completion_required'
    with client.app.state.sessions() as db: assert db.scalar(select(User.id)) is None
    details = {k: passenger[k] for k in ('full_name', 'phone_e164', 'preferred_language', 'accept_terms')}
    for field in ('full_name', 'phone_e164', 'accept_terms'):
        invalid = {k: v for k, v in details.items() if k != field}
        assert client.post('/api/v1/auth/google/complete', json={'ticket': result['ticket'], **invalid}).status_code == 422
    completed = client.post('/api/v1/auth/google/complete', json={'ticket': result['ticket'], **details})
    assert completed.status_code == 201, completed.text
    assert ('access_token' in completed.json()) == verified
    with client.app.state.sessions() as db:
        user = db.scalar(select(User)); roles = db.scalars(select(UserRole)).all()
        assert bool(user.email_verified_at) == verified and user.phone_verified_at is None
        assert user.password_hash is None and user.external_auth_subject == 'google-subject-1'
        assert [(r.role_code, r.approval_status) for r in roles] == [('PASSENGER', 'APPROVED')]
    if not verified:
        assert completed.json()['email_delivery'] == 'captured'
        assert client.post('/api/v1/auth/email/verify', json={'token': captured_token(client)}).status_code == 200
        assert 'access_token' in client.post('/api/v1/auth/google', json=google(email, **claims)).json()


def test_google_same_email_requires_authenticated_explicit_link_and_preserves_roles(client, passenger, google):
    person, tokens = signed_in(client, passenger)
    role = client.post('/api/v1/users/me/role-requests', json={'role_code': 'DRIVER'}, headers=bearer(tokens)).json()
    assert client.post('/api/v1/auth/google', json=google(passenger['email'])).json()['status'] == 'link_required'
    headers = bearer(tokens)
    data = {**google(passenger['email'], headers=headers), 'confirm': True, 'current_password': passenger['password']}
    assert client.post('/api/v1/users/me/google', json={**data, 'confirm': False}, headers=headers).status_code == 422
    assert client.post('/api/v1/users/me/google', json={**data, 'current_password': 'wrong'}, headers=headers).status_code == 400
    assert client.post('/api/v1/users/me/google', json=data, headers=headers).status_code == 200
    # Stable subject, not a changed Google email, identifies the same user.
    google_tokens = client.post('/api/v1/auth/google', json=google('changed@gmail.com')).json()
    assert client.get('/api/v1/users/me', headers=bearer(google_tokens)).json()['id'] == person['id']
    assert any(r['id'] == role['id'] for r in client.get('/api/v1/users/me/roles', headers=bearer(google_tokens)).json()['items'])
    assert 'access_token' in client.post('/api/v1/auth/login', json={'identifier': passenger['email'], 'password': passenger['password']}).json()


def test_cannot_reuse_sign_in_challenge_to_link(client, passenger, google):
    _, tokens = signed_in(client, passenger)
    assert client.post('/api/v1/users/me/google', headers=bearer(tokens), json={**google(), 'confirm': True, 'current_password': passenger['password']}).status_code == 401


def test_migration_grandfathers_existing_accounts_without_changing_identity_or_roles():
    from pathlib import Path
    from alembic import command
    from alembic.config import Config
    from app.config import get_settings
    from app.database import make_engine
    settings = get_settings()
    schema = 'travelly_test_' + uuid4().hex
    control = make_engine(settings.database_url)
    engine = make_engine(settings.database_url, connect_args={'options': f'-csearch_path={schema},public'})
    uid, role_id = uuid4(), uuid4()
    encoded = hasher.hash('old password with spaces')
    try:
        with control.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        cfg = Config(str(Path(__file__).parents[1] / 'alembic.ini'))
        with engine.begin() as connection:
            cfg.attributes.update(connection=connection, schema=schema)
            command.upgrade(cfg, '0003_review_documents')
            connection.execute(text("INSERT INTO users (id, public_user_reference, full_name, email, password_hash) VALUES (:id, :ref, 'Legacy Passenger', 'legacy@example.com', :password)"), {'id': uid, 'ref': 'USR-' + uuid4().hex[:16].upper(), 'password': encoded})
            connection.execute(text("INSERT INTO user_roles (id, user_id, role_code, approval_status, approved_at) VALUES (:id, :uid, 'PASSENGER', 'APPROVED', now())"), {'id': role_id, 'uid': uid})
            command.upgrade(cfg, 'head')
            row = connection.execute(text('SELECT * FROM users WHERE id = :id'), {'id': uid}).mappings().one()
            assert row['email_login_required'] is False and row['auth_version'] == 0
            assert row['password_hash'] == encoded and row['email_verified_at'] is None
            assert connection.scalar(text('SELECT id FROM user_roles WHERE user_id = :id'), {'id': uid}) == role_id
            connection.execute(text("INSERT INTO users (public_user_reference, full_name, email, password_hash) VALUES (:ref, 'New Passenger', 'new@example.com', :password)"), {'ref': 'USR-' + uuid4().hex[:16].upper(), 'password': encoded})
            assert connection.scalar(text("SELECT email_login_required FROM users WHERE email = 'new@example.com'")) is True
            tables = set(connection.scalars(text('SELECT tablename FROM pg_tables WHERE schemaname = :schema'), {'schema': schema}))
            assert tables == {'users', 'user_roles', 'vehicles', 'documents', 'alembic_version'}
    finally:
        engine.dispose()
        with control.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        control.dispose()


@pytest.mark.parametrize('status,payload,outcome', [(201, {'messageId': 'test-id'}, 'provider_accepted'), (201, {}, 'failed'), (402, {}, 'daily_limit'), (429, {}, 'daily_limit'), (500, {}, 'failed')])
def test_brevo_response_and_quota_are_honest_without_sending_mail(monkeypatch, status, payload, outcome):
    import httpx
    from app.auth_services import Mailer
    from app.config import get_settings
    from app.errors import ApiError
    settings = get_settings().model_copy(update={'mail_backend': 'brevo', 'brevo_api_key': 'test-placeholder', 'mail_from_email': 'sender@travelly.test'})
    calls = []
    def post(url, **kwargs):
        calls.append(url)
        assert kwargs['json']['to'] == [{'email': 'recipient@example.com'}]
        return httpx.Response(status, json=payload)
    monkeypatch.setattr('app.auth_services.httpx.post', post)
    store = SimpleNamespace(rate=lambda *args: None)
    mailer = Mailer(settings, store)
    assert mailer.send('recipient@example.com', 'opaque-test-token', 'verify') == outcome
    assert calls == ['https://api.brevo.com/v3/smtp/email']
    def exhausted(*args): raise ApiError(429, 'RATE_LIMITED', 'Try later.')
    store.rate = exhausted
    assert mailer.send('recipient@example.com', 'opaque-test-token', 'verify') == 'daily_limit'
    assert len(calls) == 1


def test_touch_preserves_database_timestamp_order():
    from datetime import timedelta
    from app.api import touch
    future = datetime.now(timezone.utc) + timedelta(seconds=1)
    row = SimpleNamespace(created_at=future, updated_at=future, version=1)
    touch(row)
    assert row.updated_at >= row.created_at and row.version == 2
