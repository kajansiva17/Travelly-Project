"""Two-step verification with an authenticator app (owner decision 14 Nov 2026): TOTP (RFC 6238), 6 digits, 30 seconds.

No new dependency: the code is the standard HMAC-SHA1 one-time password. The secret is stored encrypted (Fernet, key derived
from the application secret); backup codes are stored only as keyed hashes and each works once.
"""
import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote
from cryptography.fernet import Fernet, InvalidToken

STEP, DIGITS, WINDOW = 30, 6, 1
BACKUP_COUNT = 10
ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'   # no look-alike characters


def _fernet(settings):
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(b'travelly-2fa-v1|' + settings.jwt_secret.encode()).digest()))


def new_secret():
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip('=')


def seal(settings, secret):
    return _fernet(settings).encrypt(secret.encode()).decode()


def unseal(settings, sealed):
    try:
        return _fernet(settings).decrypt(sealed.encode()).decode()
    except (InvalidToken, ValueError):
        return None


def code_at(secret, step):
    key = base64.b32decode(secret + '=' * (-len(secret) % 8))
    digest = hmac.new(key, struct.pack('>Q', step), hashlib.sha1).digest()
    offset = digest[-1] & 15
    return str((struct.unpack('>I', digest[offset:offset + 4])[0] & 0x7fffffff) % 10 ** DIGITS).zfill(DIGITS)


def check(secret, code, last_step=None, now=None):
    """The matching time step, or None. A step that was already used is refused, so one code cannot be replayed."""
    code = (code or '').strip().replace(' ', '')
    if len(code) != DIGITS or not code.isdigit():
        return None
    current = int((now if now is not None else time.time()) // STEP)
    for step in range(current - WINDOW, current + WINDOW + 1):
        if hmac.compare_digest(code_at(secret, step), code) and (last_step is None or step > last_step):
            return step
    return None


def otpauth_uri(secret, account):
    return f'otpauth://totp/Travelly:{quote(account)}?secret={secret}&issuer=Travelly&algorithm=SHA1&digits={DIGITS}&period={STEP}'


def _backup_hash(settings, code):
    return hmac.new(settings.jwt_secret.encode(), b'backup|' + code.replace('-', '').upper().encode(), hashlib.sha256).hexdigest()


def new_backup_codes(settings):
    """(codes to show once, hashes to store)."""
    codes = [''.join(secrets.choice(ALPHABET) for _ in range(10)) for _ in range(BACKUP_COUNT)]
    shown = [c[:5] + '-' + c[5:] for c in codes]
    return shown, [_backup_hash(settings, c) for c in codes]


def use_backup_code(settings, stored, code):
    """The stored list without the used code, or None when the code is not one of them."""
    wanted = _backup_hash(settings, code or '')
    for item in stored or []:
        if hmac.compare_digest(item, wanted):
            return [x for x in stored if x != item]
    return None
