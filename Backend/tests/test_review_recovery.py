"""Real PostgreSQL and filesystem fault/crash tests; never run against live application rows."""
import io
import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import UUID, uuid4
import pytest
from starlette.datastructures import UploadFile, Headers
from sqlalchemy import text, select
from app.models import UserRole
from app.errors import ApiError
from app.private_documents import MAX_FILE, MAX_MULTIPART
from test_admin_review import review_case, png, upload, role_review


@pytest.mark.parametrize('phase,expected', [('before_intent', 'PENDING'), ('after_intent', 'PENDING'), ('after_commit', 'REJECTED')])
def test_process_exit_at_commit_boundaries(client, review_case, phase, expected):
    c = review_case; journal = client.app.state.audit; role = c['roles']['OWNER']
    with client.app.state.engine.connect() as db: schema = db.scalar(text('select current_schema()'))
    script = '''
import os
from uuid import UUID
from sqlalchemy import select
from app.config import get_settings
from app.database import make_engine, session_factory
from app.review_audit import AuditJournal, decision_evidence
from app.models import UserRole
from app.api import touch
s=get_settings(); e=make_engine(s.database_url,connect_args={'options':'-csearch_path='+os.environ['TEST_SCHEMA']+',public'})
j=AuditJournal(s,e); original=j.append; phase=os.environ['TEST_PHASE']
def append(event):
 if phase=='before_intent' and event['outcome']=='intent': os._exit(71)
 if phase=='after_commit' and event['outcome']=='committed': os._exit(71)
 result=original(event)
 if phase=='after_intent' and event['outcome']=='intent': os._exit(71)
 return result
j.append=append
with j.coordinated(), session_factory(e)() as db:
 row=db.scalar(select(UserRole).where(UserRole.id==UUID(os.environ['TEST_ROLE'])).with_for_update())
 evidence=decision_evidence(row); row.approval_status='REJECTED';row.rejection_reason='Full crash-test reason.';touch(row)
 j.commit(db,actor=os.environ['TEST_ACTOR'],target={'resource':'user_roles','id':str(row.id),'applicant':str(row.user_id),'role':row.role_code},previous_status='PENDING',new_status='REJECTED',previous_version=1,new_version=2,full_reason=row.rejection_reason,previous_decision_evidence=evidence,trace_id=os.environ['TEST_TRACE'])
'''
    env = {**os.environ, 'TEST_SCHEMA': schema, 'TEST_PHASE': phase, 'TEST_ROLE': role['id'], 'TEST_ACTOR': str(c['admin_id']), 'TEST_TRACE': str(uuid4()),
           'PRIVATE_DOCUMENT_ROOT': str(client.app.state.settings.private_document_root), 'REVIEW_AUDIT_ROOT': str(journal.root()),
           'REVIEW_DATABASE_IDENTITY': client.app.state.settings.review_database_identity, 'REVIEW_AUDIT_ENDPOINT': ''}
    process = subprocess.run([sys.executable, '-c', script], cwd=Path(__file__).parents[1], env=env, capture_output=True, timeout=20)
    assert process.returncode == 71  # intentionally killed, no graceful Python cleanup
    with journal.coordinated(): pass
    with client.app.state.sessions() as db: assert db.get(UserRole, UUID(role['id'])).approval_status == expected
    records, _, _ = journal.records()
    events = [r for r in records if r.get('target', {}).get('id') == role['id']]
    assert len(events) == (0 if phase == 'before_intent' else 2)
    if events:
        assert events[-1]['outcome'] == ('committed' if expected == 'REJECTED' else 'aborted')
        assert events[0]['full_reason'] == 'Full crash-test reason.'


def test_uncertain_intent_fsync_rolls_back_then_reconciles_aborted(client, review_case, monkeypatch):
    c = review_case; journal = client.app.state.audit
    original = os.fsync
    def fail(fd): raise OSError('injected uncertain durable acknowledgement')
    with monkeypatch.context() as patch:
        patch.setattr('app.review_audit.os.fsync', fail)
        result = role_review(client, c, c['roles']['OWNER'], 'REJECTED', 'No committed change.')
        assert result.status_code == 503
    with journal.coordinated(): pass
    records, _, _ = journal.records()
    assert records[-1]['outcome'] == 'aborted'
    with client.app.state.sessions() as db:
        row = db.get(UserRole, UUID(c['roles']['OWNER']['id']))
        assert row.approval_status == 'PENDING' and row.version == 1 and row.rejection_reason is None


def test_unresolved_inprogress_null_and_restore_identity_fail_closed(client, review_case, monkeypatch):
    c = review_case; journal = client.app.state.audit
    with client.app.state.sessions() as db:
        xid = db.scalar(text('SELECT pg_current_xact_id()::text'))
        journal.append(dict(correlation_id=str(uuid4()), actor=str(c['admin_id']), target={'resource': 'user_roles', 'id': c['roles']['OWNER']['id']},
                            previous_status='PENDING', new_status='REJECTED', previous_version=1, new_version=2,
                            full_reason='Uncommitted test intent', previous_decision_evidence={}, trace_id=str(uuid4()),
                            postgres_xid8=xid, database_identity=journal.identity(db), outcome='intent'))
        with pytest.raises(ApiError):
            with journal.coordinated(): pass
        db.rollback()
    with monkeypatch.context() as patch:
        patch.setattr(journal, 'transaction_status', lambda *args: None)
        assert role_review(client, c, c['roles']['OWNER'], 'REJECTED', 'Will not change').status_code == 503
    with monkeypatch.context() as patch:
        patch.setattr(journal, 'identity', lambda db: ['unrelated-restored-database'])
        assert role_review(client, c, c['roles']['OWNER'], 'REJECTED', 'Will not change').status_code == 503
    with journal.coordinated(): pass


def test_exact_file_and_multipart_byte_boundaries_and_false_content_length(client, review_case):
    c = review_case; storage = client.app.state.documents
    # The image is decoded without alteration; trailing original bytes remain intact.
    content = png(); content += b'\x00' * (MAX_FILE - len(content))
    file = UploadFile(io.BytesIO(content), filename='boundary.png', headers=Headers({'content-type': 'image/png'}))
    metadata = storage.place(file)
    assert metadata['file_size_bytes'] == MAX_FILE
    with pytest.raises(ApiError) as oversized:
        storage.place(UploadFile(io.BytesIO(content + b'x'), filename='boundary.png', headers=Headers({'content-type': 'image/png'})))
    assert oversized.value.status == 413
    # Streamed chunks enforce actual bytes, ignoring a forged short length.
    def chunks():
        for _ in range(11): yield b'x' * 1024**2
    result = client.post('/api/v1/documents', content=chunks(), headers={**c['owner'], 'Content-Type': 'multipart/form-data; boundary=x', 'Content-Length': '1'})
    assert result.status_code == 413
    # Exactly the whole-request boundary reaches multipart validation; +1 fails the boundary.
    for size, status in [(MAX_MULTIPART, 422), (MAX_MULTIPART + 1, 413)]:
        r = client.post('/api/v1/documents', content=b'x' * size, headers={**c['owner'], 'Content-Type': 'multipart/form-data; boundary=x'})
        assert r.status_code == status


def test_missing_referenced_file_and_symlink_escape_fail_closed(client, review_case, tmp_path):
    c = review_case; result = upload(client, c); assert result.status_code == 201
    with client.app.state.sessions() as db:
        from app.review_models import Document
        doc = db.get(Document, UUID(result.json()['id']))
        file = client.app.state.documents.path(doc.storage_key)
    file.unlink()
    assert client.get(result.json()['secure_file_url'], headers=c['owner']).status_code == 503
    target = tmp_path / 'unrelated'; target.write_bytes(b'do not disclose')
    try: file.symlink_to(target)
    except OSError:
        # Windows junctions have the same reparse bit; unit-check the mandatory guard without requiring symlink privilege.
        class Reparse:
            st_file_attributes = 0x400
            st_mode = 0
        from unittest.mock import patch
        with patch.object(type(file), 'exists', return_value=True), patch.object(type(file), 'is_symlink', return_value=False), patch.object(type(file), 'lstat', return_value=Reparse()):
            with pytest.raises(ApiError): client.app.state.documents.path(file.name)
    else:
        assert client.get(result.json()['secure_file_url'], headers=c['owner']).status_code == 503


def test_upload_unknown_transaction_retains_bytes_until_abort_is_proven(client, review_case):
    from app.private_infrastructure import file_lock
    c = review_case; storage = client.app.state.documents
    key = uuid4().hex; storage.path(key).write_bytes(png())
    with client.app.state.sessions() as upload_db:
        storage.mark_transaction(key, upload_db)
        with file_lock(storage.root() / 'upload.lock'), client.app.state.sessions() as recovery_db:
            with pytest.raises(ApiError): storage.recover(recovery_db)
        assert storage.path(key).exists()  # no visible row is insufficient proof
        upload_db.rollback()
    with file_lock(storage.root() / 'upload.lock'), client.app.state.sessions() as recovery_db:
        storage.recover(recovery_db)
    assert not storage.path(key).exists()


def test_valid_pdf_jpeg_encrypted_pdf_and_missing_validator(client, review_case, monkeypatch):
    from pypdf import PdfWriter
    from PIL import Image
    c = review_case; fields = {'owner_type': 'USER', 'owner_id': c['person']['id'], 'document_type': 'NIC'}
    image = io.BytesIO(); Image.new('RGB', (24, 24), 'white').save(image, 'JPEG')
    writer = PdfWriter(); writer.add_blank_page(width=100, height=100)
    pdf = io.BytesIO(); writer.write(pdf)
    for filename, data, mime in [('valid.jpg', image.getvalue(), 'image/jpeg'), ('valid.pdf', pdf.getvalue(), 'application/pdf')]:
        result = client.post('/api/v1/documents', data=fields, files={'file': (filename, data, mime)}, headers=c['owner'])
        assert result.status_code == 201, result.text
        assert client.get(result.json()['secure_file_url'], headers=c['owner']).content == data
    writer.encrypt('not-a-shared-password'); encrypted = io.BytesIO(); writer.write(encrypted)
    assert client.post('/api/v1/documents', data=fields, files={'file': ('encrypted.pdf', encrypted.getvalue(), 'application/pdf')}, headers=c['owner']).status_code == 422
    class MissingValidator:
        returncode = 2
    monkeypatch.setattr('app.private_documents.subprocess.run', lambda *a, **k: MissingValidator())
    assert upload(client, c).status_code == 503
