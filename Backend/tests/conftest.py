from pathlib import Path
from uuid import uuid4
import re
from email import policy
from email.parser import BytesParser
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text
from app.config import get_settings
from app.database import make_engine
from app.main import create_app
from app.sessions import SessionStore


@pytest.fixture(scope='session')
def postgres_engine():
    settings = get_settings()
    schema = 'travelly_test_' + uuid4().hex
    assert re.fullmatch(r'travelly_test_[a-f0-9]{32}', schema)
    control = make_engine(settings.database_url)
    with control.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = make_engine(settings.database_url, connect_args={'options': f'-csearch_path={schema},public'})
    try:
        cfg = Config(str(Path(__file__).parents[1] / 'alembic.ini'))
        with engine.begin() as connection:
            cfg.attributes['connection'] = connection
            cfg.attributes['schema'] = schema
            command.upgrade(cfg, 'head')
        yield engine
    finally:
        engine.dispose()
        with control.begin() as connection:
            # Only the random test schema above, never public or an externally supplied name.
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        control.dispose()


@pytest.fixture
def client(postgres_engine, tmp_path):
    from app.review_operator import initialize
    settings = get_settings().model_copy(update={'private_document_root': tmp_path / 'private-documents',
        'review_audit_root': tmp_path / 'audit', 'review_database_identity': str(uuid4()),
        'review_audit_endpoint': None, 'review_audit_auth_file': None,
        'mail_backend': 'capture', 'mail_capture_dir': tmp_path / 'mail',
        'google_client_id': 'test-client.apps.googleusercontent.com'})
    initialize(settings, restrict_acl=False)
    store = SessionStore(settings.redis_url, prefix='travelly-test:' + uuid4().hex + ':')
    assert store.client.ping()
    app = create_app(settings, postgres_engine, store)
    with TestClient(app) as c:
        yield c
    keys = list(store.client.scan_iter(store.prefix + '*'))
    if keys:
        store.client.delete(*keys)
    store.client.close()
    with postgres_engine.begin() as connection:
        # search_path is pinned to the random test schema on this engine.
        connection.execute(text('TRUNCATE user_roles, users CASCADE'))


@pytest.fixture
def passenger():
    return {'full_name': 'Test Passenger', 'email': f'{uuid4().hex}@example.com', 'password': 'TravellyStrong1!', 'preferred_language': 'en', 'phone_e164': '+9477' + str(uuid4().int % 10000000).zfill(7), 'accept_terms': True}


def signed_in(client, passenger):
    registration = client.post('/api/v1/auth/register', json=passenger)
    assert registration.status_code == 201, registration.text
    verified = client.post('/api/v1/auth/email/verify', json={'token': captured_token(client)})
    assert verified.status_code == 200, verified.text
    tokens = client.post('/api/v1/auth/login', json={'identifier': passenger.get('email') or passenger['phone_e164'], 'password': passenger['password']})
    assert tokens.status_code == 200, tokens.text
    return registration.json(), tokens.json()


def bearer(tokens):
    return {'Authorization': 'Bearer ' + tokens['access_token']}


def captured_token(client, purpose='verify'):
    subject = 'Verify your Travelly email' if purpose == 'verify' else 'Reset your Travelly password'
    paths = sorted(client.app.state.settings.mail_capture_dir.glob('*.eml'), key=lambda p: p.stat().st_mtime_ns, reverse=True)
    for path in paths:
        message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
        if message['Subject'] == subject:
            return re.search(r'#token=([A-Za-z0-9_-]+)', message.get_content()).group(1)
    raise AssertionError('No captured email for the requested purpose')
