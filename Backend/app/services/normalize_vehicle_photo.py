"""Disposable bounded decoder; public derivatives contain no source metadata."""
import sys
from pathlib import Path
from app.services.validate_document import validate


def normalize(source, mime, prefix):
    validate(source, mime)
    from PIL import Image, ImageOps
    with Image.open(source) as original:
        if getattr(original,'n_frames',1)!=1:raise ValueError()
        image = ImageOps.exif_transpose(original).convert('RGB')
        for width in (480,960,1600):
            variant=image.copy();variant.thumbnail((width,width*2),Image.Resampling.LANCZOS)
            # A fresh pixel image drops EXIF, ICC, comments and embedded metadata.
            clean=Image.new('RGB',variant.size);clean.paste(variant)
            clean.save(str(prefix)+'.'+str(width),format='JPEG',quality=85,optimize=False)


if __name__=='__main__':
    try: normalize(*sys.argv[1:])
    except (ImportError,RuntimeError):sys.exit(2)
    except Exception:sys.exit(1)
