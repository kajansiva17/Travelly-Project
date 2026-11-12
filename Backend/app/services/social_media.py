"""Travel Reels media files (PRD: "Media outside DB, no private document links").

Files live under the social media root (default <PRIVATE_DOCUMENT_ROOT>/../social-media) as <post_id>/media.<ext> and
<post_id>/thumb.jpg. They are served only through the API:
- an APPROVED PUBLIC post's media is open to everyone;
- any other post's media needs a signed link (1 hour) that the API gives only to people allowed to see the post.
Videos are stored as sent (no transcoding); photos and thumbnails are re-encoded to JPEG (max 1600 px, no metadata).
"""
import hashlib
import hmac
import io
import time
from pathlib import Path
from app.core.errors import ApiError
from app.core.private_infrastructure import unavailable

VIDEO_TYPES = {'video/mp4': '.mp4', 'video/quicktime': '.mov', 'video/webm': '.webm'}
IMAGE_TYPES = ('image/jpeg', 'image/png')
LINK_SECONDS = 3600


def root(settings):
    value = settings.social_media_root
    if value is None:
        if not settings.private_document_root:
            raise unavailable()
        value = Path(settings.private_document_root).absolute().parent / 'social-media'
    folder = Path(value).absolute()
    repository = Path(__file__).resolve().parents[3]
    if folder.is_relative_to(repository) or repository.is_relative_to(folder):
        raise unavailable()
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def folder(settings, post_id):
    return root(settings) / str(post_id)


def media_file(settings, post_id):
    found = sorted(folder(settings, post_id).glob('media.*'))
    return found[0] if found else None


def thumb_file(settings, post_id):
    path = folder(settings, post_id) / 'thumb.jpg'
    return path if path.exists() else None


def read_limited(upload, limit, too_big):
    data = upload.file.read(limit + 1)
    if len(data) > limit:
        raise ApiError(413, 'MEDIA_TOO_LARGE', too_big)
    return data


def clean_image(upload, limit=10 * 1024 * 1024):
    from PIL import Image, ImageOps, UnidentifiedImageError
    if upload.content_type not in IMAGE_TYPES:
        raise ApiError(422, 'INVALID_MEDIA', 'Use a JPEG or PNG photo.')
    data = read_limited(upload, limit, 'Choose a photo no larger than 10 MB.')
    try:
        with Image.open(io.BytesIO(data)) as probe:
            probe.verify()
        with Image.open(io.BytesIO(data)) as image:
            if getattr(image, 'n_frames', 1) != 1:
                raise ApiError(422, 'INVALID_MEDIA', 'Use a still photo.')
            image = ImageOps.exif_transpose(image).convert('RGB')
            image.thumbnail((1600, 1600))
            out = io.BytesIO()
            image.save(out, 'JPEG', quality=85)
            return out.getvalue()
    except ApiError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise ApiError(422, 'INVALID_MEDIA', 'The photo could not be read.') from None


def check_video(upload, limit_mb):
    if upload.content_type not in VIDEO_TYPES:
        raise ApiError(422, 'INVALID_MEDIA', 'Use an MP4, MOV or WebM video.')
    data = read_limited(upload, limit_mb * 1024 * 1024, f'Choose a video no larger than {limit_mb} MB.')
    mp4_like = len(data) > 12 and data[4:8] == b'ftyp'
    webm = data[:4] == b'\x1a\x45\xdf\xa3'
    if not (mp4_like or webm):
        raise ApiError(422, 'INVALID_MEDIA', 'The file is not a playable video.')
    return data, VIDEO_TYPES[upload.content_type]


def save(settings, post_id, media=None, media_ext=None, thumb=None):
    target = folder(settings, post_id)
    target.mkdir(parents=True, exist_ok=True)
    if media is not None:
        (target / f'media{media_ext}').write_bytes(media)
    if thumb is not None:
        (target / 'thumb.jpg').write_bytes(thumb)


def remove(settings, post_id):
    target = folder(settings, post_id)
    if target.exists():
        for child in target.iterdir():
            child.unlink()
        target.rmdir()


def sign(settings, post_id, kind, now=None):
    expires = int(now or time.time()) + LINK_SECONDS
    mac = hmac.new(settings.jwt_secret.encode(), f'{post_id}:{kind}:{expires}'.encode(), hashlib.sha256).hexdigest()[:32]
    return f'{expires}.{mac}'


def signed(settings, post_id, kind, token):
    try:
        expires, mac = token.split('.', 1)
        if int(expires) < time.time():
            return False
    except (AttributeError, ValueError):
        return False
    good = hmac.new(settings.jwt_secret.encode(), f'{post_id}:{kind}:{expires}'.encode(), hashlib.sha256).hexdigest()[:32]
    return hmac.compare_digest(good, mac)
