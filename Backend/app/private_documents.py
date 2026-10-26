import hashlib
import json
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path
from uuid import UUID, uuid4
from sqlalchemy import select, text
from .errors import ApiError
from .private_infrastructure import private_root, file_lock, durable_move, sync_directory, unavailable
from .review_models import Document

MAX_FILE = 10 * 1024**2
MAX_MULTIPART = MAX_FILE + 64 * 1024
DOCUMENT_TYPES = ('NIC', 'PASSPORT', 'DRIVING_LICENCE', 'BUSINESS_REGISTRATION', 'OWNER_AUTHORISATION',
                  'BANK_PROOF', 'VEHICLE_REGISTRATION', 'REVENUE_LICENCE', 'INSURANCE', 'EMISSION', 'FITNESS', 'ROUTE_PERMIT')
DOCUMENT_STATES = ('DRAFT', 'SUBMITTED', 'UNDER_REVIEW', 'APPROVED', 'REJECTED', 'NEEDS_CORRECTION', 'EXPIRED', 'SUPERSEDED')
SUMMARY = ('id', 'user_id', 'vehicle_id', 'document_type', 'issuing_country', 'issue_date', 'expiry_date',
           'status', 'submitted_at', 'verified_at', 'rejection_reason', 'superseded_document_id', 'version')


def invalid_file():
    return ApiError(422, 'VALIDATION_ERROR', 'Request validation failed.',
                    [{'field': 'file', 'code': 'invalid_file', 'message': 'Use a valid PDF, JPEG or PNG file with a safe filename.'}])


def safe_filename(value):
    if not value or len(value) > 255 or value != value.strip() or value.endswith('.') or re.search(r'[\\/:\x00-\x1f\x7f]', value) or any(unicodedata.category(c) == 'Cc' for c in value):
        raise invalid_file()
    if value.split('.')[0].rstrip(' .').upper() in {'CON', 'PRN', 'AUX', 'NUL', *('COM' + str(i) for i in range(1, 10)), *('LPT' + str(i) for i in range(1, 10))}:
        raise invalid_file()
    return value


def document_summary(row):
    return {name: getattr(row, name) for name in SUMMARY}


def document_detail(row):
    return {**document_summary(row), **{name: getattr(row, name) for name in
            ('document_number', 'original_file_name', 'mime_type', 'file_size_bytes', 'verified_by')},
            'secure_file_url': f'/api/v1/documents/{row.id}/file'}


class PrivateDocuments:
    def __init__(self, settings):
        self.settings = settings

    def root(self):
        return private_root(self.settings.private_document_root)

    def path(self, key):
        if not re.fullmatch(r'[0-9a-f]{32}', key):
            raise unavailable()
        path = self.root() / key
        if path.exists() and (path.is_symlink() or getattr(path.lstat(), 'st_file_attributes', 0) & 0x400):
            raise unavailable()
        return path

    def recover(self, db):
        """Must hold upload.lock. Never delete until a successful reference query proves orphanhood."""
        referenced = set(db.scalars(select(Document.storage_key)).all())
        unresolved = set()
        for marker in self.root().glob('*.pending'):
            key = marker.stem
            if not re.fullmatch(r'[0-9a-f]{32}', key) or marker.is_symlink() or getattr(marker.lstat(), 'st_file_attributes', 0) & 0x400 or marker.stat().st_size > 2048:
                raise unavailable()
            event = json.loads(marker.read_text(encoding='utf-8'))
            if set(event) != {'database_identity', 'postgres_xid8'} or event['database_identity'] != self.identity(db):
                raise unavailable()
            outcome = db.scalar(text('SELECT pg_xact_status(CAST(:xid AS xid8))'), {'xid': event['postgres_xid8']})
            if outcome == 'committed' and key in referenced:
                marker.unlink()
            elif outcome == 'aborted' and key not in referenced:
                self.path(key).unlink(missing_ok=True); marker.unlink()
            else:
                # A SELECT with no visible row is never proof that an uncertain COMMIT aborted.
                unresolved.add(key)
        if unresolved:
            raise unavailable()
        for path in self.root().iterdir():
            if re.fullmatch(r'[0-9a-f]{32}(\.staging)?', path.name) and path.name not in referenced:
                if path.is_file() and not path.is_symlink() and not getattr(path.lstat(), 'st_file_attributes', 0) & 0x400:
                    path.unlink()

    def identity(self, db):
        if not self.settings.review_database_identity: raise unavailable()
        return [self.settings.review_database_identity, *db.execute(text("SELECT current_database(), current_schema(), oid::text FROM pg_database WHERE datname=current_database()")).one()]

    def mark_transaction(self, key, db):
        marker = self.root() / (key + '.pending')
        event = {'database_identity': self.identity(db), 'postgres_xid8': str(db.scalar(text('SELECT pg_current_xact_id()::text')))}
        with marker.open('x', encoding='utf-8') as stream:
            json.dump(event, stream); stream.flush(); os.fsync(stream.fileno())
        sync_directory(marker.parent)

    def finish_transaction(self, key):
        # A leftover committed marker is safe and reconciled on the next maintenance pass.
        try:
            (self.root() / (key + '.pending')).unlink()
            sync_directory(self.root())
        except OSError:
            pass

    def place(self, upload):
        name = safe_filename(upload.filename)
        mime = upload.content_type
        if Path(name).suffix.lower() not in {'application/pdf': ('.pdf',), 'image/jpeg': ('.jpg', '.jpeg'), 'image/png': ('.png',)}.get(mime, ()):
            raise invalid_file()
        key = uuid4().hex
        staging = self.root() / (key + '.staging')
        digest, size = hashlib.sha256(), 0
        try:
            with staging.open('xb') as target:
                while chunk := upload.file.read(65536):
                    size += len(chunk)
                    if size > MAX_FILE:
                        raise ApiError(413, 'REQUEST_TOO_LARGE', 'The file exceeds 10 MiB.',
                                       [{'field': 'file', 'code': 'file_too_large',
                                         'message': 'Choose a file no larger than 10 MiB (10,485,760 bytes).'}])
                    digest.update(chunk); target.write(chunk)
                target.flush(); os.fsync(target.fileno())
            if not size:
                raise invalid_file()
            try:
                result = subprocess.run([sys.executable, '-m', 'app.validate_document', str(staging), mime],
                                        cwd=Path(__file__).parents[1], timeout=6, capture_output=True,
                                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            except subprocess.TimeoutExpired:
                raise invalid_file() from None
            if result.returncode == 2:
                raise unavailable()
            if result.returncode:
                raise invalid_file()
            durable_move(staging, self.path(key))
            return dict(storage_key=key, original_file_name=name, mime_type=mime, file_size_bytes=size,
                        file_checksum=digest.hexdigest())
        finally:
            if staging.exists():
                staging.unlink()

    def open_verified(self, row):
        try:
            stream = self.path(row.storage_key).open('rb')
            digest = hashlib.sha256()
            size = 0
            while chunk := stream.read(65536):
                size += len(chunk); digest.update(chunk)
                if size > row.file_size_bytes:
                    stream.close(); raise unavailable()
            if size != row.file_size_bytes or digest.hexdigest() != row.file_checksum:
                stream.close(); raise unavailable()
            stream.seek(0)
            return stream
        except (OSError, ValueError):
            raise unavailable() from None
