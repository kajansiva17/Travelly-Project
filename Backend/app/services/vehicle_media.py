"""Separate moderated photo store. No static mount; no private document reuse."""
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path
from uuid import uuid4
from app.core.errors import ApiError
from app.services.private_documents import MAX_FILE, safe_filename
from app.core.private_infrastructure import private_root, durable_move, unavailable


class VehiclePhotos:
    def __init__(self,settings):self.settings=settings
    def root(self):
        root=private_root(self.settings.vehicle_photo_root)
        for other in (self.settings.private_document_root,self.settings.review_audit_root):
            if other:
                other=Path(other).absolute()
                if root.is_relative_to(other) or other.is_relative_to(root):raise unavailable()
        return root
    def path(self,key):
        if not re.fullmatch(r'[0-9a-f]{32}\.(480|960|1600)',key):raise unavailable()
        path=self.root()/key
        if path.exists() and (path.is_symlink() or getattr(path.lstat(),'st_file_attributes',0)&0x400):raise unavailable()
        return path
    def place(self,upload):
        from PIL import Image
        name=safe_filename(upload.filename);mime=upload.content_type
        if Path(name).suffix.lower() not in {'image/jpeg':('.jpg','.jpeg'),'image/png':('.png',)}.get(mime,()):
            raise ApiError(422,'INVALID_PHOTO','Use a genuine JPEG or PNG photo; PDF, SVG and animated files are not public photos.')
        root=self.root();key=uuid4().hex;source=root/(key+'.source');prefix=root/(key+'.normalized')
        try:
            size=0
            with source.open('xb') as stream:
                while chunk:=upload.file.read(65536):
                    size+=len(chunk)
                    if size>MAX_FILE:raise ApiError(413,'PHOTO_TOO_LARGE','Choose a JPEG or PNG no larger than 10 MiB.')
                    stream.write(chunk)
                stream.flush();os.fsync(stream.fileno())
            if not size:raise ApiError(422,'INVALID_PHOTO','Choose a non-empty JPEG or PNG photo.')
            try: result=subprocess.run([sys.executable,'-m','app.services.normalize_vehicle_photo',str(source),mime,str(prefix)],
                cwd=Path(__file__).parents[2],timeout=8,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            except subprocess.TimeoutExpired:raise ApiError(422,'INVALID_PHOTO','The photo cannot be processed safely.') from None
            if result.returncode==2:raise unavailable()
            if result.returncode:raise ApiError(422,'INVALID_PHOTO','Use a valid JPEG or PNG photo within the 20-megapixel processing limit.')
            variants={}
            for width in (480,960,1600):
                staging=Path(str(prefix)+'.'+str(width));data=staging.read_bytes()
                with Image.open(staging) as image:w,h=image.size
                with staging.open('r+b') as stream:stream.flush();os.fsync(stream.fileno())
                target=key+'.'+str(width);durable_move(staging,self.path(target))
                variants[str(width)]={'key':target,'width':w,'height':h,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
            return variants
        finally:
            source.unlink(missing_ok=True)
            for width in (480,960,1600):Path(str(prefix)+'.'+str(width)).unlink(missing_ok=True)
    def open(self,variant):
        try:
            data=self.path(variant['key']).read_bytes()
            if len(data)!=variant['bytes'] or hashlib.sha256(data).hexdigest()!=variant['sha256']:raise unavailable()
            return data
        except (OSError,KeyError):raise unavailable() from None
