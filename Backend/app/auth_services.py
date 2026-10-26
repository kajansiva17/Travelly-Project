"""Purpose-bound auth capabilities, private development mail and Google signatures."""
import json
import os
import secrets
import tempfile
import time
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import quote
import httpx
import jwt
from jwt import PyJWKClient
from .errors import ApiError
from .schemas import email_address
from .security import digest


class AuthState:
    def __init__(self, store):
        self.store, self.client = store, store.client

    def key(self, purpose, token):
        return self.store.key('auth-flow:' + purpose + ':' + digest(token))

    def issue(self, purpose, data, ttl=1800, subject=None):
        token = secrets.token_urlsafe(32)
        key = self.key(purpose, token)
        value = json.dumps(data)
        if subject:
            index = self.store.key('auth-latest:' + purpose + ':' + str(subject))
            self.client.eval("""
                local old = redis.call('GET', KEYS[2])
                if old then redis.call('DEL', old) end
                redis.call('SET', KEYS[1], ARGV[1], 'EX', ARGV[2])
                redis.call('SET', KEYS[2], KEYS[1], 'EX', ARGV[2])
                return 1
            """, 2, key, index, value, ttl)
        else:
            self.client.set(key, value, ex=ttl)
        return token

    def read(self, purpose, token, consume=False):
        if not isinstance(token, str) or not 30 <= len(token) <= 100:
            return None
        key = self.key(purpose, token)
        value = self.client.getdel(key) if consume else self.client.get(key)
        return json.loads(value) if value else None

    def discard(self, purpose, token):
        self.client.delete(self.key(purpose, token))


class Mailer:
    def __init__(self, settings, store):
        self.settings, self.store = settings, store

    def send(self, recipient, token, purpose):
        s = self.settings
        day = datetime.now(timezone.utc).date().isoformat()
        try:
            self.store.rate('mail-day:' + day, s.mail_daily_limit, 86400)
        except ApiError:
            return 'daily_limit'
        route = 'verify-email' if purpose == 'verify' else 'reset-password'
        subject = 'Verify your Travelly email' if purpose == 'verify' else 'Reset your Travelly password'
        link = s.frontend_url.rstrip('/') + '/' + route + '#token=' + quote(token, safe='')
        body = f'{subject}\n\nOpen this link and confirm the action within 30 minutes:\n{link}\n\nThis link can be used once. If you did not request it, ignore this email.'
        if s.mail_backend == 'capture':
            if s.environment == 'production':
                return 'failed'
            root = s.mail_capture_dir or Path(tempfile.gettempdir()) / 'travelly-mail'
            try:
                root.mkdir(parents=True, exist_ok=True)
                message = EmailMessage()
                message['From'], message['To'], message['Subject'] = s.mail_from_email, recipient, subject
                message.set_content(body)
                # Random filenames, never derived from recipient or token; no HTTP capture endpoint.
                path = root / (secrets.token_hex(16) + '.eml')
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, 'wb') as output:
                    output.write(message.as_bytes()); output.flush(); os.fsync(output.fileno())
                return 'captured'
            except OSError:
                return 'failed'
        if not s.brevo_api_key or s.mail_from_email.endswith('@example.com'):
            return 'failed'
        try:
            response = httpx.post('https://api.brevo.com/v3/smtp/email', timeout=10,
                headers={'api-key': s.brevo_api_key, 'accept': 'application/json'},
                json={'sender': {'email': s.mail_from_email, 'name': 'Travelly'},
                      'to': [{'email': recipient}], 'subject': subject, 'textContent': body})
            if response.status_code == 201 and response.json().get('messageId'):
                return 'provider_accepted'
            if response.status_code in (402, 429):
                return 'daily_limit'
        except (httpx.HTTPError, ValueError):
            pass
        return 'failed'


class GoogleIdentity:
    def __init__(self, client_id):
        self.client_id = client_id
        # Fixed trusted endpoint; never follow an ID-token supplied jku/x5u URL.
        self.keys = PyJWKClient('https://www.googleapis.com/oauth2/v3/certs', cache_keys=True, lifespan=300, timeout=5)

    def verify(self, credential, nonce):
        try:
            if not self.client_id or len(credential) > 6000:
                raise ValueError()
            header = jwt.get_unverified_header(credential)
            if header.get('alg') != 'RS256' or not header.get('kid'):
                raise ValueError()
            key = self.keys.get_signing_key_from_jwt(credential).key
            claims = jwt.decode(credential, key, algorithms=['RS256'], audience=self.client_id,
                issuer=['accounts.google.com', 'https://accounts.google.com'], leeway=30,
                options={'require': ['iss', 'aud', 'exp', 'iat', 'sub', 'nonce', 'email']})
            if claims.get('azp', self.client_id) != self.client_id or claims.get('aud') != self.client_id:
                raise ValueError()
            if not secrets.compare_digest(str(claims['nonce']), nonce):
                raise ValueError()
            if not isinstance(claims['sub'], str) or not 1 <= len(claims['sub']) <= 255:
                raise ValueError()
            email = email_address(claims['email'])
            authoritative = claims.get('email_verified') is True and (email.endswith('@gmail.com') or bool(claims.get('hd')))
            return {'subject': claims['sub'], 'email': email, 'authoritative': authoritative,
                    'name': str(claims.get('name', ''))[:150]}
        except jwt.PyJWKClientConnectionError:
            raise ApiError(503, 'GOOGLE_UNAVAILABLE', 'Google sign-in is temporarily unavailable. Please try again.') from None
        except (jwt.PyJWTError, ValueError, TypeError, KeyError):
            raise ApiError(401, 'INVALID_GOOGLE_TOKEN', 'Google sign-in could not be verified. Try again.') from None
