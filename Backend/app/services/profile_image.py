import base64
import binascii
import io
import warnings
from PIL import Image, ImageOps, UnidentifiedImageError
from app.core.errors import ApiError


def normalize_avatar(value, size=256):
    """Persist only a bounded, metadata-free raster data URL in the existing column."""
    if value is None:
        return None
    try:
        header, encoded = value.split(',', 1)
        if header not in ('data:image/jpeg;base64', 'data:image/png;base64', 'data:image/webp;base64'):
            raise ValueError()
        raw = base64.b64decode(encoded, validate=True)
        if len(raw) > 1_048_576:
            raise ValueError()
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as source:
                if source.format not in ('JPEG', 'PNG', 'WEBP') or source.width * source.height > 16_000_000:
                    raise ValueError()
                source.load()
                image = ImageOps.exif_transpose(source)
                image.thumbnail((size, size))
                # A fresh image strips EXIF, comments, ICC and other embedded metadata.
                clean = Image.new('RGB', image.size, 'white')
                rgba = image.convert('RGBA')
                clean.paste(rgba, mask=rgba.getchannel('A'))
                output = io.BytesIO()
                clean.save(output, format='JPEG', quality=80, optimize=True)
        return 'data:image/jpeg;base64,' + base64.b64encode(output.getvalue()).decode('ascii')
    except (ValueError, binascii.Error, UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ApiError(422, 'INVALID_PROFILE_IMAGE', 'Choose a JPEG, PNG or WebP image up to 1 MB and 16 megapixels.') from None
