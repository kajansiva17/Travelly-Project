import os
import re
import secrets
import time
from email import policy
from email.parser import BytesParser
from types import SimpleNamespace
from uuid import uuid4

import pytest
import httpx
from pydantic import ValidationError

from app.services.auth_services import Mailer
from app.core.config import Settings, get_settings


@pytest.mark.skipif(os.getenv('MAILPIT_INTEGRATION') != '1', reason='requires a running local Mailpit inbox')
def test_live_mailpit_registration_resend_and_verification(client, passenger, caplog):
    settings = client.app.state.settings.model_copy(update={
        'mail_backend': 'mailpit', 'mail_smtp_host': '127.0.0.1', 'mail_smtp_port': 1025})
    client.app.state.settings = settings
    client.app.state.mailer = Mailer(settings, client.app.state.store)
    passenger['email'] = f'{uuid4().hex}@example.com'
    inbox = os.getenv('MAILPIT_URL', 'http://127.0.0.1:8025').rstrip('/')

    def find_verification_messages():
        response = httpx.get(inbox + '/api/v1/messages', params={'start': 0, 'limit': 100}, timeout=5)
        response.raise_for_status()
        tokens = []
        for item in response.json()['messages']:
            summary = str(item)
            if passenger['email'] not in summary or 'Verify your Travelly email' not in summary:
                continue
            message_id = item.get('ID') or item.get('id')
            raw = httpx.get(inbox + f'/api/v1/message/{message_id}/raw', timeout=5)
            raw.raise_for_status()
            message = BytesParser(policy=policy.default).parsebytes(raw.content)
            match = re.search(r'#token=([A-Za-z0-9_-]+)', message.get_content())
            if match:
                tokens.append(match.group(1))
        return tokens

    registration = client.post('/api/v1/auth/register', json=passenger)
    assert registration.status_code == 201
    assert registration.json()['email_delivery'] == 'provider_accepted'
    tokens = []
    deadline = time.monotonic() + 10
    while not tokens and time.monotonic() < deadline:
        tokens = find_verification_messages()
        if not tokens:
            time.sleep(0.25)
    assert tokens, 'Mailpit did not receive the registration verification message.'
    first_token = tokens[0]
    assert len(tokens) == 1, 'Expected one registration verification message.'
    token_not_exposed = first_token not in registration.text and first_token not in caplog.text
    assert token_not_exposed, 'A verification token was exposed outside the email.'
    state = client.app.state.auth_state
    token_key_exists = bool(client.app.state.store.client.exists(state.key('verify', first_token)))
    verify_key_count = sum(1 for _ in client.app.state.store.client.scan_iter(client.app.state.store.key('auth-flow:verify:*')))
    redis_has_token = state.read('verify', first_token) is not None
    assert redis_has_token, f'Registration email token missing in Redis (length={len(first_token)}, key_exists={token_key_exists}, verify_keys={verify_key_count}).'

    ticket = registration.json()['verification_ticket']
    throttled = client.post('/api/v1/auth/email/resend', json={'ticket': ticket})
    assert throttled.status_code == 429
    time.sleep(int(throttled.headers.get('Retry-After', '60')) + 1)

    resent = client.post('/api/v1/auth/email/resend', json={'ticket': ticket})
    assert resent.status_code == 200
    assert resent.json()['email_delivery'] == 'provider_accepted'
    tokens = find_verification_messages()
    assert len(tokens) == 2, 'Mailpit did not receive exactly one resend verification message.'
    active_tokens = [token for token in tokens if client.app.state.auth_state.read('verify', token)]
    assert len(active_tokens) == 1, 'Resend did not leave exactly one active verification token in Redis.'
    second_token = active_tokens[0]
    tokens_are_distinct = not secrets.compare_digest(second_token, first_token)
    assert tokens_are_distinct, 'Resend reused the previous verification token.'
    tokens_not_logged = first_token not in caplog.text and second_token not in caplog.text
    assert tokens_not_logged, 'A verification token was exposed in application logs.'

    state = client.app.state.auth_state
    record = state.read('verify', second_token)
    assert record is not None, 'The resent token was not stored in Redis.'
    assert record.get('email') == passenger['email'], 'The resent token is bound to the wrong email.'
    stale = client.post('/api/v1/auth/email/verify', json={'token': first_token})
    assert stale.status_code == 400, f'The replaced verification token returned HTTP {stale.status_code}.'
    verified = client.post('/api/v1/auth/email/verify', json={'token': second_token})
    assert verified.status_code == 200, f'The resent verification token returned HTTP {verified.status_code} ({verified.json().get("code")}).'
    replay = client.post('/api/v1/auth/email/verify', json={'token': second_token})
    assert replay.status_code == 400, f'The consumed verification token returned HTTP {replay.status_code}.'
    login = client.post('/api/v1/auth/login', json={'identifier': passenger['email'], 'password': passenger['password']})
    assert login.status_code == 200


def test_registration_verification_and_login_via_mailpit_transport(client, passenger, monkeypatch, caplog):
    sent = []

    class SMTP:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def send_message(self, message):
            sent.append(message)
            return {}

    monkeypatch.setattr('app.services.auth_services.smtplib.SMTP', SMTP)
    settings = client.app.state.settings.model_copy(update={'mail_backend': 'mailpit'})
    client.app.state.settings = settings
    client.app.state.mailer = Mailer(settings, client.app.state.store)

    registration = client.post('/api/v1/auth/register', json=passenger)
    assert registration.status_code == 201
    assert registration.json()['email_delivery'] == 'provider_accepted'
    assert len(sent) == 1

    token = re.search(r'#token=([A-Za-z0-9_-]+)', sent[0].get_content()).group(1)
    assert token not in registration.text
    assert token not in caplog.text
    assert client.post('/api/v1/auth/email/verify', json={'token': token}).status_code == 200
    assert client.post('/api/v1/auth/email/verify', json={'token': token}).status_code == 400
    login = client.post('/api/v1/auth/login', json={'identifier': passenger['email'], 'password': passenger['password']})
    assert login.status_code == 200


def test_mailpit_smtp_submission_uses_local_server_without_logging_tokens(monkeypatch, caplog):
    calls = {}

    class SMTP:
        def __init__(self, host, port, timeout):
            calls.update(host=host, port=port, timeout=timeout)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def send_message(self, message):
            calls['message'] = message
            return {}

    monkeypatch.setattr('app.services.auth_services.smtplib.SMTP', SMTP)
    settings = get_settings().model_copy(update={'mail_backend': 'mailpit'})
    store = SimpleNamespace(rate=lambda *args: None)
    token = 'opaque-verification-token-for-test'

    assert Mailer(settings, store).send('person@example.com', token, 'verify') == 'provider_accepted'
    assert calls['host'] == '127.0.0.1'
    assert calls['port'] == 1025
    assert calls['timeout'] == 10
    assert calls['message']['To'] == 'person@example.com'
    assert calls['message']['Subject'] == 'Verify your Travelly email'
    assert token in calls['message'].get_content()
    assert token not in caplog.text


@pytest.mark.parametrize('refused', [{'person@example.com': (550, b'rejected')}, None])
def test_mailpit_smtp_failures_return_safe_status(monkeypatch, refused):
    class SMTP:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def send_message(self, message):
            if refused is None:
                raise OSError('private transport detail')
            return refused

    monkeypatch.setattr('app.services.auth_services.smtplib.SMTP', SMTP)
    settings = get_settings().model_copy(update={'mail_backend': 'mailpit'})
    store = SimpleNamespace(rate=lambda *args: None)

    assert Mailer(settings, store).send('person@example.com', 'opaque-token', 'verify') == 'failed'


def test_mailpit_is_loopback_only_and_rejected_in_production():
    values = get_settings().model_dump()
    values.update(mail_backend='mailpit', mail_smtp_host='mail.example.com')
    with pytest.raises(ValidationError, match='loopback'):
        Settings(**values)

    values.update(mail_smtp_host='127.0.0.1', environment='production')
    with pytest.raises(ValidationError, match='Production requires HTTPS and configured real email delivery'):
        Settings(**values)
