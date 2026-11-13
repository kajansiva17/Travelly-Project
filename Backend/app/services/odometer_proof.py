"""Odometer photo proof (owner decision 13 Nov 2026).

At trip start and finish the operator types the odometer reading AND takes a live photo of it in the app:
1. `session`  - the app asks for a one-time capture code (10 minutes, one photo). There is no gallery upload: the photo
                must come from the in-app camera together with that code, the time and the GPS position.
2. `photo`    - the photo is checked, shrunk and stripped of metadata, read by Gemini, and compared with the typed
                number:
                MATCH      read within the tolerance (default 1 km)            -> may continue
                MISMATCH   read clearly differs                                 -> fix the number or retake; blocked
                UNREADABLE Gemini could not read it (dark, blurred)             -> retake; after 3 tries may continue
                           with the typed number, flagged "photo not readable"
                NOT_CHECKED no reader (no Gemini key, daily cap, error)         -> may continue; photo kept as proof
3. start / complete then require a fresh proof for exactly the number sent (`ODOMETER_PROOF_REQUIRED`).

Always: the start reading cannot be below the vehicle's last known odometer, the end reading cannot be below the start
reading, and the start photo must be taken near the private-hire pickup point.

Storage: no PRD table or column. Files live under the odometer photo root as <trip_id>/<STAGE>.jpg plus a small
<STAGE>.json. The photo and the GPS position are deleted `odometer_photo_keep_days` (7) after the trip ends (or after
a cancelled trip's photo was taken); the typed/read numbers stay in the JSON and the readings stay in `trips`.
"""
import base64
import io
import json
import math
import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from app.core.errors import ApiError
from app.core.private_infrastructure import unavailable

STAGES = ('START', 'END')
CODE_SECONDS = 600
PROOF_FRESH_MINUTES = 30
MAX_PHOTO = 8 * 1024 * 1024


# --------------------------------------------------------------------------------------------------- storage

def root(settings):
    value = settings.odometer_photo_root
    if value is None:
        if not settings.private_document_root:
            raise unavailable()
        value = Path(settings.private_document_root).absolute().parent / 'odometer-photos'
    folder = Path(value).absolute()
    repository = Path(__file__).resolve().parents[3]
    if folder.is_relative_to(repository) or repository.is_relative_to(folder):
        raise unavailable()
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def files(settings, trip_id, stage):
    folder = root(settings) / str(trip_id)
    return folder, folder / f'{stage}.jpg', folder / f'{stage}.json'


def read_record(settings, trip_id, stage):
    _, _, meta = files(settings, trip_id, stage)
    if not meta.exists():
        return None
    try:
        return json.loads(meta.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def write_record(settings, trip_id, stage, record, photo_bytes=None):
    folder, photo, meta = files(settings, trip_id, stage)
    folder.mkdir(parents=True, exist_ok=True)
    if photo_bytes is not None:
        temp = photo.with_suffix('.tmp')
        temp.write_bytes(photo_bytes)
        temp.replace(photo)
    temp = meta.with_suffix('.jsontmp')
    temp.write_text(json.dumps(record), encoding='utf-8')
    temp.replace(meta)


# --------------------------------------------------------------------------------------------------- capture code

def new_code(store, trip_id, user_id, stage):
    code = secrets.token_urlsafe(24)
    payload = json.dumps({'trip_id': str(trip_id), 'user_id': str(user_id), 'stage': stage})
    store.client.set(store.key('odometer-code:' + code), payload, ex=CODE_SECONDS)
    return code, datetime.now(timezone.utc) + timedelta(seconds=CODE_SECONDS)


def use_code(store, code, trip_id, user_id, stage):
    """One photo per code: the code is removed as it is used."""
    raw = store.client.getdel(store.key('odometer-code:' + code)) if code else None
    if not raw:
        raise ApiError(409, 'CAPTURE_CODE_INVALID', 'The camera session expired. Open the camera again and take a new photo.')
    data = json.loads(raw)
    if data != {'trip_id': str(trip_id), 'user_id': str(user_id), 'stage': stage}:
        raise ApiError(409, 'CAPTURE_CODE_INVALID', 'The camera session expired. Open the camera again and take a new photo.')


# --------------------------------------------------------------------------------------------------- photo

def clean_photo(upload):
    """Accept one real JPEG/PNG up to 8 MiB; return a re-encoded JPEG (max 1600 px, no EXIF or other metadata)."""
    from PIL import Image, ImageOps, UnidentifiedImageError
    if upload.content_type not in ('image/jpeg', 'image/png'):
        raise ApiError(422, 'INVALID_PHOTO', 'Take the photo with the Travelly camera (JPEG or PNG).')
    data = upload.file.read(MAX_PHOTO + 1)
    if len(data) > MAX_PHOTO:
        raise ApiError(413, 'PHOTO_TOO_LARGE', 'The photo is larger than 8 MiB.')
    try:
        with Image.open(io.BytesIO(data)) as probe:
            probe.verify()
        with Image.open(io.BytesIO(data)) as image:
            if getattr(image, 'n_frames', 1) != 1:
                raise ApiError(422, 'INVALID_PHOTO', 'Use a still photo.')
            image = ImageOps.exif_transpose(image).convert('RGB')
            image.thumbnail((1600, 1600))
            out = io.BytesIO()
            image.save(out, 'JPEG', quality=85)
            return out.getvalue()
    except ApiError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise ApiError(422, 'INVALID_PHOTO', 'The photo could not be read. Take it again.') from None


READ_SCHEMA = {'type': 'OBJECT', 'properties': {'readable': {'type': 'BOOLEAN'}, 'odometer_km': {'type': 'NUMBER'}},
               'required': ['readable']}
READ_PROMPT = ('This is a photo of a vehicle dashboard. Read the TOTAL odometer (ODO): the distance the vehicle has run in '
               'its life. Ignore the trip meters (TRIP, A, B), speed, fuel, clock and range. If the total odometer is not '
               'clearly visible and readable, return readable false. Otherwise return readable true and odometer_km as a '
               'number (kilometres; a tenth digit only if the display shows one).')


def read_odometer(settings, store, jpeg):
    """Gemini reads the odometer. Returns (km or None, engine): engine 'gemini' or None when no reader was available."""
    import httpx
    from app.services import ai_assist
    if not ai_assist.gemini_allowed(store, settings):
        return None, None
    try:
        data = ai_assist.gemini_image(settings, READ_PROMPT, READ_SCHEMA, base64.b64encode(jpeg).decode('ascii'))
    except (httpx.HTTPError, KeyError, IndexError, ValueError, TypeError):
        return None, None
    if not data.get('readable') or data.get('odometer_km') is None:
        return None, 'gemini'
    try:
        value = Decimal(str(data['odometer_km'])).quantize(Decimal('0.1'))
    except (InvalidOperation, ValueError):
        return None, 'gemini'
    return (value if value >= 0 else None), 'gemini'


def distance_km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(a))


def judge(typed, read, engine, tries_unreadable, settings):
    if engine is None:
        return 'NOT_CHECKED', True
    if read is None:
        return 'UNREADABLE', tries_unreadable >= settings.odometer_unreadable_tries
    if abs(read - typed) <= Decimal(str(settings.odometer_match_tolerance_km)):
        return 'MATCH', True
    return 'MISMATCH', False


# --------------------------------------------------------------------------------------------------- rules used by trips

def require_proof(settings, trip, stage, km, now=None):
    """Called by start / complete: a fresh accepted photo for exactly this reading."""
    if not settings.odometer_photo_required:
        return
    record = read_record(settings, trip.id, stage)
    now = now or datetime.now(timezone.utc)
    word = 'start' if stage == 'START' else 'finish'
    if not record or not record.get('can_continue') or Decimal(record['typed_km']) != Decimal(str(km)) \
            or datetime.fromisoformat(record['taken_at']) < now - timedelta(minutes=PROOF_FRESH_MINUTES):
        raise ApiError(409, 'ODOMETER_PROOF_REQUIRED',
                       f'Take a live photo of the odometer and enter the same reading before you {word} the trip.')


def below_last(vehicle, km):
    if vehicle is not None and vehicle.current_odometer_km is not None and Decimal(str(km)) < vehicle.current_odometer_km:
        raise ApiError(422, 'ODOMETER_BELOW_LAST',
                       f'The reading is lower than this vehicle’s last recorded odometer ({vehicle.current_odometer_km} km). Check it again.')


# --------------------------------------------------------------------------------------------------- clean-up

def expired(trip, record, now, keep_days):
    keep = timedelta(days=keep_days)
    if trip.actual_end_at is not None:
        return now >= trip.actual_end_at + keep
    if trip.status == 'CANCELLED' and record and record.get('taken_at'):
        return now >= datetime.fromisoformat(record['taken_at']) + keep
    return False


def forget_photo(settings, trip, now=None):
    """Delete the photos and positions once kept long enough. Returns how many photos were deleted."""
    now = now or datetime.now(timezone.utc)
    deleted = 0
    for stage in STAGES:
        record = read_record(settings, trip.id, stage)
        _, photo, _ = files(settings, trip.id, stage)
        if record is None or not expired(trip, record, now, settings.odometer_photo_keep_days):
            continue
        if photo.exists():
            photo.unlink()
            deleted += 1
        if record.get('photo_available') or 'latitude' in record:
            record.update({'photo_available': False, 'photo_deleted_at': now.isoformat()})
            record.pop('latitude', None); record.pop('longitude', None); record.pop('accuracy_m', None)
            write_record(settings, trip.id, stage, record)
    return deleted
