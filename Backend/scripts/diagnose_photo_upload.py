"""Find out why Owner vehicle photo upload says "The review service is temporarily unavailable".

Run from the Backend folder (read-only apart from one tiny test photo it creates and removes again):
    ..\\.venv\\Scripts\\python.exe scripts\\diagnose_photo_upload.py

It prints OK or FAIL for each thing a photo upload needs, using the application's own code.
No passwords or secrets are printed.
"""
import io
import sys
import tempfile
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

failures = []


def step(name, action):
    try:
        result = action()
        print(f'OK    {name}' + (f' -> {result}' if result else ''))
        return result
    except BaseException as error:  # noqa: BLE001 - this is a diagnostic tool
        text = getattr(error, 'message', None) or str(error) or type(error).__name__
        print(f'FAIL  {name} -> {type(error).__name__}: {text}')
        traceback.print_exc(limit=4)
        failures.append(name)
        return None


holder = {}


def load():
    from app.core.config import get_settings
    holder['settings'] = get_settings()
    return 'loaded'


step('Load settings from .env', load)
settings = holder.get('settings')
if settings is None:
    sys.exit(1)

print()
print('VEHICLE_PHOTO_ROOT   =', settings.vehicle_photo_root)
print('PRIVATE_DOCUMENT_ROOT =', settings.private_document_root)
print('REVIEW_AUDIT_ROOT    =', settings.review_audit_root)
print('REVIEW_AUDIT_ENDPOINT =', settings.review_audit_endpoint)
print()

from app.services.vehicle_media import VehiclePhotos  # noqa: E402

photos = VehiclePhotos(settings)
root = step('Photo folder is configured, exists and is private', lambda: str(photos.root()))
if root:
    def writable():
        probe = Path(root) / ('probe-' + 'x' * 8)
        probe.write_bytes(b'ok')
        probe.unlink()
        return 'can write and delete'
    step('Photo folder is writable', writable)

step('Pillow (image library) is installed', lambda: __import__('PIL').__version__)


def upload_a_test_photo():
    from PIL import Image
    buffer = io.BytesIO()
    Image.new('RGB', (640, 400), (120, 160, 90)).save(buffer, format='PNG')
    buffer.seek(0)

    class Upload:
        filename = 'diagnostic.png'
        content_type = 'image/png'
        file = buffer

    variants = photos.place(Upload)
    for variant in variants.values():  # remove the test files again
        (Path(photos.root()) / variant['key']).unlink(missing_ok=True)
    return f'{len(variants)} sizes written and removed'


if root:
    step('Photo is normalized and stored (same code as the upload)', upload_a_test_photo)

if settings.review_audit_endpoint:
    def audit_key():
        size = len(settings.review_audit_auth_file.read_bytes())
        if size != 32:
            raise ValueError(f'key file is {size} bytes, expected 32')
        return 'key file is readable (32 bytes)'

    step('Review writer key file', audit_key)

    def writer():
        from app.dependencies.database import make_engine
        from app.services.review_audit import AuditJournal
        with AuditJournal(settings, make_engine(settings.database_url)).coordinated():
            return 'connected to the review writer'

    step('Review writer is running and accepts the web app', writer)
else:
    print('SKIP  Review writer (REVIEW_AUDIT_ENDPOINT is not set)')

print()
print('Everything a photo upload needs is working.' if not failures else 'Failed: ' + '; '.join(failures))
