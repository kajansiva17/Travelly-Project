"""Check that the PayHere Refund API credentials in Backend/.env work, without printing them.

Run from the project folder:
    .venv\\Scripts\\python.exe Backend\\scripts\\check_payhere_refund_api.py
It asks PayHere for an access token (no refund is made) and prints only yes/no answers.
"""
import os
import sys
from pathlib import Path

backend = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend))
os.chdir(backend)  # so Backend/.env is read

from app.core.config import get_settings  # noqa: E402
from app.services import payhere_refunds  # noqa: E402

settings = get_settings()
print('PAYHERE_APP_ID set:    ', bool(settings.payhere_app_id.strip()))
print('PAYHERE_APP_SECRET set:', bool(settings.payhere_app_secret.strip()))
print('PayHere mode:          ', settings.payhere_mode)
if not payhere_refunds.configured(settings):
    sys.exit('Add PAYHERE_APP_ID and PAYHERE_APP_SECRET to Backend/.env, then run this again.')
try:
    payhere_refunds.access_token(settings)
    print('PayHere accepted the credentials: YES - refunds will go through the Refund API.')
except Exception as exc:  # noqa: BLE001 - show the reason, never the secret
    print('PayHere accepted the credentials: NO -', str(exc).replace(settings.payhere_app_secret, '***'))
