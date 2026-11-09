import hashlib,io
from pathlib import Path
from uuid import uuid4
from PIL import Image
from app.core.errors import ApiError
from app.core.private_infrastructure import private_root,durable_move,unavailable

ALLOWED={'image/jpeg':'JPEG','image/png':'PNG','application/pdf':None}
MAX_BYTES=10*1024*1024
MAX_DIMENSION=8000
def invalid(message='Use a JPEG, PNG, or PDF evidence file no larger than 10 MiB.'):
 return ApiError(422,'UNSUPPORTED_MEDIA',message)
class OperationalMedia:
 def __init__(self,settings):self.settings=settings
 def root(self):return private_root(self.settings.operational_media_root)
 def path(self,key):
  if len(key)!=32 or any(c not in '0123456789abcdef' for c in key):raise unavailable()
  return self.root()/key
 def place(self,upload):
  mime=(upload.content_type or '').lower()
  if mime not in ALLOWED:raise invalid()
  raw=upload.file.read(MAX_BYTES+1)
  if not raw or len(raw)>MAX_BYTES:raise invalid('Evidence must be between 1 byte and 10 MiB.')
  if mime=='application/pdf':
   if not raw.startswith(b'%PDF-'):raise invalid()
   clean=raw
  else:
   try:
    image=Image.open(io.BytesIO(raw));image.verify();image=Image.open(io.BytesIO(raw))
    if image.width>MAX_DIMENSION or image.height>MAX_DIMENSION:raise invalid('Image dimensions exceed 8000 pixels.')
    if mime=='image/jpeg' and image.mode not in ('RGB','L'):image=image.convert('RGB')
    out=io.BytesIO();image.save(out,format=ALLOWED[mime]);clean=out.getvalue()
   except ApiError:raise
   except Exception:raise invalid() from None
  key=uuid4().hex;staging=self.root()/(key+'.staging')
  try:
   with staging.open('xb') as f:f.write(clean);f.flush()
   durable_move(staging,self.path(key))
  finally:
   if staging.exists():staging.unlink()
  return key,mime,len(clean),hashlib.sha256(clean).hexdigest()
 def open(self,row):
  try:
   path=self.path(row.storage_key)
   raw=path.read_bytes()
   if len(raw)!=row.byte_size or hashlib.sha256(raw).hexdigest()!=row.sha256:raise unavailable()
   return raw
  except OSError:raise unavailable() from None
