"""Pickup verification codes for a private-hire trip.

The Passenger shows a QR code at pickup; if it will not scan, the Driver types the six-digit
number printed under it. Neither value is stored: both are derived from the application secret
and the trip's pickup_code_version, so the Passenger can open the same code again at any time,
and issuing a new one is simply moving the version on.
"""
import base64
import hashlib
import hmac
from app.core.config import get_settings

PIN_DIGITS = 6
MAX_ATTEMPTS = 5


def _mac(trip_id, version, kind):
    key = get_settings().jwt_secret.encode()
    return hmac.new(key, f'{kind}:{trip_id}:{version}'.encode(), hashlib.sha256).digest()


def pin_for(trip_id, version):
    """The six digits printed under the QR code."""
    return str(int.from_bytes(_mac(trip_id, version, 'pin')[:8], 'big') % 10 ** PIN_DIGITS).zfill(PIN_DIGITS)


def token_for(trip_id, version):
    """The value inside the QR code."""
    return base64.urlsafe_b64encode(_mac(trip_id, version, 'qr')).decode().rstrip('=')


def same(given, expected):
    """Constant-time comparison; a wrong length must not answer faster than a wrong value."""
    return hmac.compare_digest(str(given or '').strip(), expected)
