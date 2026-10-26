import hashlib
import secrets
import time
from uuid import UUID, uuid4
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from .errors import unauthorized

hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=1, hash_len=32, salt_len=16)
DUMMY_HASH = hasher.hash(secrets.token_urlsafe(24))


def verify_password(password, encoded):
    try:
        result = hasher.verify(encoded or DUMMY_HASH, password)
        return bool(encoded) and result
    except (VerificationError, InvalidHashError):
        return False


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def decode_token(token, settings, kind='access'):
    try:
        header = jwt.get_unverified_header(token)
        if header.get('typ') != 'JWT' or header.get('alg') != 'HS256':
            raise ValueError()
        data = jwt.decode(token, settings.jwt_secret if kind == 'access' else settings.jwt_refresh_secret,
                          algorithms=['HS256'], audience='travelly-web' if kind == 'access' else 'travelly-refresh',
                          issuer='travelly-api', leeway=30,
                          options={'require': ['sub', 'sid', 'jti', 'iat', 'exp', 'token_type']})
        if data['token_type'] != kind:
            raise ValueError()
        for field in ('sub', 'sid', 'jti'):
            UUID(data[field])
        return data
    except (jwt.PyJWTError, ValueError, TypeError, KeyError):
        raise unauthorized('INVALID_REFRESH_TOKEN' if kind == 'refresh' else 'UNAUTHENTICATED') from None


def issue_tokens(user_id, settings, sid=None, expires=None, auth_version=0):
    now = int(time.time())
    sid = sid or str(uuid4())
    expires = expires or now + 604800
    access_exp = min(now + 900, expires)
    def encode(kind, exp, key, audience):
        return jwt.encode({'sub': str(user_id), 'sid': sid, 'jti': str(uuid4()), 'iat': now, 'exp': exp,
                           'iss': 'travelly-api', 'aud': audience, 'token_type': kind, 'av': auth_version}, key, algorithm='HS256', headers={'typ': 'JWT'})
    response = {'access_token': encode('access', access_exp, settings.jwt_secret, 'travelly-web'),
                'refresh_token': encode('refresh', expires, settings.jwt_refresh_secret, 'travelly-refresh'),
                'token_type': 'bearer', 'expires_in': access_exp - now, 'refresh_expires_in': expires - now}
    return response, sid, expires
