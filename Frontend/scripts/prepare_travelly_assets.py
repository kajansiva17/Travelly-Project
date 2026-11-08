"""Create production derivatives; reference screenshots never enter public/."""
import json
import sys
import zipfile
from pathlib import Path
from PIL import Image

root = Path(__file__).resolve().parents[2]
source = root / '.tools' / 'travelly-redesign' / 'source'
output = root / 'Frontend' / 'public' / 'images' / 'travelly'
metadata = root / 'Frontend' / 'src' / 'assets' / 'travelly'
manifest_path = metadata / 'manifest.json'
manifest = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else {}
with zipfile.ZipFile(sys.argv[1]) as archive:
    for entry in archive.infolist():
        relative = Path(entry.filename).relative_to('travelly-landing-assets')
        if '..' in relative.parts or relative.is_absolute():
            raise ValueError('Invalid archive path')
        if relative.name in ('README.md', 'prompts.json'):
            metadata.mkdir(parents=True, exist_ok=True)
            (metadata / relative.name).write_bytes(archive.read(entry))
        if relative.suffix != '.png' or relative.parts[0] == 'references':
            continue
        if len(sys.argv) > 2 and relative.as_posix() != sys.argv[2]:
            continue
        original = source / relative
        original.parent.mkdir(parents=True, exist_ok=True)
        original.write_bytes(archive.read(entry))
        with Image.open(original) as image:
            image = image.convert('RGBA')
            if relative.parts[0] in ('branding', 'icons', 'vehicles'):
                # The logo has near-transparent generation noise far beyond its
                # visible lockup. Ignore that padding, retaining the visible mark.
                alpha = image.getchannel('A')
                box = alpha.point(lambda a: 255 if a > 16 else 0).getbbox() if relative.parts[0] == 'branding' else alpha.getbbox()
                if box:
                    image = image.crop(box)
            widths = {'heroes': [768, 1280, 1920], 'branding': [480, 960], 'destinations': [480, 960], 'vehicles': [400, 800]}.get(relative.parts[0], [320, 640])
            variants = []
            for width in widths:
                resized = image.copy()
                resized.thumbnail((width, width * 2), Image.Resampling.LANCZOS)
                path = output / relative.parent / f'{relative.stem}-{width}.webp'
                path.parent.mkdir(parents=True, exist_ok=True)
                resized.save(path, 'WEBP', quality=86, method=6)
                variants.append({'src': '/images/travelly/' + path.relative_to(output).as_posix(), 'width': resized.width, 'height': resized.height, 'bytes': path.stat().st_size})
            manifest[relative.as_posix()] = variants
(metadata / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print(f'Prepared {len(manifest)} assets; {sum(v["bytes"] for a in manifest.values() for v in a):,} production bytes. Reference images excluded.')
