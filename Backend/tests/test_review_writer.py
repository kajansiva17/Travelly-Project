import os
import secrets
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4, UUID
from sqlalchemy import text
from app.review_audit import AuditJournal
from app.models import UserRole
from test_admin_review import review_case, role_review


def test_isolated_writer_acknowledges_without_runtime_history_access(client, review_case, tmp_path, monkeypatch):
    c = review_case
    offline = client.app.state.audit
    auth = tmp_path / 'ipc.key'; auth.write_bytes(secrets.token_bytes(32))
    endpoint = '\\\\.\\pipe\\TravellyReviewAudit-' + uuid4().hex if os.name == 'nt' else str(tmp_path / 'audit.sock')
    settings = client.app.state.settings.model_copy(update={'review_audit_endpoint': endpoint, 'review_audit_auth_file': auth})
    with client.app.state.engine.connect() as db: schema = db.scalar(text('select current_schema()'))
    env = {**os.environ, 'REVIEW_AUDIT_ENDPOINT': endpoint, 'REVIEW_AUDIT_AUTH_FILE': str(auth),
           'REVIEW_AUDIT_ROOT': str(settings.review_audit_root), 'REVIEW_DATABASE_IDENTITY': settings.review_database_identity, 'TEST_SCHEMA': schema}
    script = '''
import os
from app.config import get_settings
from app.database import make_engine
from app.review_audit import FileAuditJournal
from app.review_writer import serve
s=get_settings();e=make_engine(s.database_url,connect_args={'options':'-csearch_path='+os.environ['TEST_SCHEMA']+',public'})
serve(s,FileAuditJournal(s,e))
'''
    process = subprocess.Popen([sys.executable, '-c', script], cwd=Path(__file__).parents[1], env=env,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    remote = AuditJournal(settings, client.app.state.engine)
    try:
        for _ in range(40):
            try:
                with remote.coordinated(): pass
                break
            except Exception: time.sleep(.1)
        else: raise AssertionError('Isolated writer did not start')
        client.app.state.audit = remote
        def no_file_access(*args): raise AssertionError('Web identity must not read/write history files')
        monkeypatch.setattr(remote, 'root', no_file_access)
        result = role_review(client, c, c['roles']['OWNER'], 'REJECTED', 'Full reason through restricted IPC.')
        assert result.status_code == 200, result.text
        records, _, _ = offline.records()
        assert records[-1]['outcome'] == 'committed' and records[-1]['full_reason'] == 'Full reason through restricted IPC.'
        process.kill(); process.wait(timeout=5)
        # Writer outage prevents the next decision; no direct-file fallback.
        result = role_review(client, c, c['roles']['DRIVER'], 'REJECTED', 'Will not commit.')
        assert result.status_code == 503
        with client.app.state.sessions() as db: assert db.get(UserRole, UUID(c['roles']['DRIVER']['id'])).approval_status == 'PENDING'
    finally:
        if process.poll() is None: process.kill(); process.wait(timeout=5)
        client.app.state.audit = offline
