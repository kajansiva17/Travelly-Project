import io
import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from uuid import UUID, uuid4
import pytest
from PIL import Image
from sqlalchemy import select, text, inspect
from app.models import User, UserRole
from app.review_models import Document, Vehicle
from app.review_operator import provision
from app.private_documents import safe_filename, MAX_FILE, MAX_MULTIPART
from app.errors import ApiError
from conftest import signed_in, bearer


@pytest.fixture
def review_case(client, passenger):
    person, tokens = signed_in(client, passenger)
    email = uuid4().hex + '@example.com'
    with client.app.state.sessions() as db:
        user = db.get(User, UUID(person['id']))
        admin = User(public_user_reference='USR-' + uuid4().hex[:16].upper(), full_name='Review Admin', email=email, password_hash=user.password_hash, email_login_required=False)
        db.add(admin); db.flush()
        db.add(UserRole(user_id=admin.id, role_code='PASSENGER', approval_status='APPROVED', approved_at=admin.created_at))
        db.commit(); admin_id = admin.id
        assert 'created' in provision(db, client.app.state.audit, admin_id, 'isolated-test-operator', str(uuid4()))
    login = client.post('/api/v1/auth/login', json={'identifier': email, 'password': passenger['password']})
    assert login.status_code == 200
    roles = {}
    for code in ('OWNER', 'DRIVER'):
        result = client.post('/api/v1/users/me/role-requests', json={'role_code': code}, headers=bearer(tokens))
        assert result.status_code == 201
        roles[code] = result.json()
    return dict(person=person, owner=bearer(tokens), admin=bearer(login.json()), admin_id=admin_id, roles=roles)


def png():
    target = io.BytesIO(); Image.new('RGB', (24, 24), 'white').save(target, 'PNG'); return target.getvalue()


def upload(client, c, kind='NIC', **metadata):
    data = dict(owner_type='USER', owner_id=c['person']['id'], document_type=kind, **metadata)
    return client.post('/api/v1/documents', data=data, files={'file': ('evidence.png', png(), 'image/png')}, headers=c['owner'])


def doc_review(client, c, doc, decision, reason=None):
    result = client.patch(f"/api/v1/admin/documents/{doc['id']}/review", json={'decision': decision, 'version': doc['version'], 'reason': reason}, headers=c['admin'])
    assert result.status_code == 200, result.text
    return result.json()


def verified(client, c, kind, **metadata):
    r = upload(client, c, kind, **metadata); assert r.status_code == 201, r.text
    d = doc_review(client, c, r.json(), 'UNDER_REVIEW')
    return doc_review(client, c, d, 'APPROVED')


def role_review(client, c, role, decision, reason=None):
    return client.patch(f"/api/v1/admin/role-requests/{role['id']}/review", json={'decision': decision, 'version': role['version'], 'reason': reason}, headers=c['admin'])


def test_queue_authorization_filters_allowlists_and_self_exclusion(client, review_case):
    c = review_case
    assert client.get('/api/v1/admin/role-requests').status_code == 401
    assert client.get('/api/v1/admin/role-requests', headers=c['owner']).json()['code'] == 'ADMIN_REQUIRED'
    r = client.get('/api/v1/admin/role-requests', headers=c['admin']); assert r.status_code == 200
    data = r.json(); assert set(data) == {'items', 'page', 'page_size', 'total', 'has_next'} and data['total'] == 2
    assert set(data['items'][0]) == {'id', 'role_code', 'approval_status', 'requested_at', 'version', 'applicant'}
    for query, total in [('role_code=OWNER', 1), ('status=REJECTED', 0), ('q=%25', 0), ('page=50', 2)]:
        result = client.get('/api/v1/admin/role-requests?' + query, headers=c['admin'])
        assert result.status_code == 200 and result.json()['total'] == total
    for query in ['page=0', 'page_size=101', 'status=UNDER_REVIEW', 'status=PENDING&status=APPROVED', 'extra=x', 'q=%00', 'role_code=PASSENGER']:
        assert client.get('/api/v1/admin/role-requests?' + query, headers=c['admin']).status_code == 422
    own = client.post('/api/v1/users/me/role-requests', json={'role_code': 'OWNER'}, headers=c['admin']).json()
    assert client.get('/api/v1/admin/role-requests', headers=c['admin']).json()['total'] == 2
    assert client.get('/api/v1/admin/role-requests/' + own['id'], headers=c['admin']).json()['code'] == 'REVIEW_FORBIDDEN'
    assert role_review(client, c, own, 'REJECTED', 'No self rejection').json()['code'] == 'REVIEW_FORBIDDEN'
    assert client.get('/api/v1/admin/role-requests/' + str(uuid4()), headers=c['admin']).status_code == 404


def test_private_upload_stream_ownership_and_revocation(client, review_case):
    c = review_case
    result = upload(client, c); assert result.status_code == 201, result.text
    doc = result.json(); assert doc['status'] == 'SUBMITTED' and not {'storage_key', 'file_checksum'} & doc.keys()
    path = doc['secure_file_url']
    assert path == f"/api/v1/documents/{doc['id']}/file"
    for headers in (c['admin'], c['owner']):
        stream = client.get(path, headers=headers)
        assert stream.status_code == 200 and stream.content == png()
        assert stream.headers['content-type'] == 'image/png' and stream.headers['cache-control'] == 'no-store'
        assert stream.headers['x-content-type-options'] == 'nosniff'
    with client.app.state.sessions() as db:
        role = db.scalar(select(UserRole).where(UserRole.user_id == c['admin_id'], UserRole.role_code == 'ADMIN'))
        role.approval_status = 'SUSPENDED'; role.suspended_at = datetime.now(timezone.utc); role.suspension_reason = 'Fixture revocation'; db.commit()
    assert client.get(path, headers=c['admin']).status_code == 404
    assert client.get('/api/v1/admin/role-requests', headers=c['admin']).status_code == 403
    assert client.get(path).status_code == 401
    assert client.get(path + '?token=anything', headers=c['owner']).status_code == 422
    assert client.get('/api/v1/documents?user_id=' + str(c['admin_id']), headers=c['owner']).status_code == 404


def test_owner_approval_driver_rejection_suspension_and_workspace(client, review_case):
    c = review_case; owner, driver = c['roles']['OWNER'], c['roles']['DRIVER']
    assert role_review(client, c, owner, 'APPROVED').json()['code'] == 'REQUIRED_EVIDENCE_NOT_VERIFIED'
    verified(client, c, 'NIC'); verified(client, c, 'OWNER_AUTHORISATION')
    approved = role_review(client, c, owner, 'APPROVED'); assert approved.status_code == 200, approved.text
    assert approved.json()['version'] == owner['version'] + 1
    assert client.get('/api/v1/users/me', headers=c['owner']).json()['approved_roles'] == ['OWNER', 'PASSENGER']
    rejected = role_review(client, c, driver, 'REJECTED', 'Please replace the incomplete licence evidence.')
    assert rejected.status_code == 200 and rejected.json()['rejection_reason'].startswith('Please replace')
    suspended = role_review(client, c, approved.json(), 'SUSPENDED', 'Required evidence is no longer valid.')
    assert suspended.status_code == 200 and suspended.json()['approved_at'] == approved.json()['approved_at']
    profile = client.get('/api/v1/users/me', headers=c['owner']).json()
    assert profile['approved_roles'] == ['PASSENGER'] and profile['email_verified_at'] is not None
    assert role_review(client, c, owner, 'REJECTED', 'Stale').json()['code'] == 'VERSION_CONFLICT'
    assert client.post('/api/v1/users/me/role-requests', json={'role_code': 'OWNER'}, headers=c['owner']).status_code == 409


def test_driver_licence_issuer_expiry_and_identity_alternative(client, review_case):
    c = review_case; role = c['roles']['DRIVER']
    verified(client, c, 'PASSPORT', expiry_date='2030-12-31')
    verified(client, c, 'DRIVING_LICENCE', issuing_country='GB', expiry_date='2030-12-31')
    assert role_review(client, c, role, 'APPROVED').status_code == 409
    verified(client, c, 'DRIVING_LICENCE', issuing_country='LK')
    assert role_review(client, c, role, 'APPROVED').status_code == 409
    verified(client, c, 'DRIVING_LICENCE', issuing_country='LK', expiry_date='2020-01-01')
    assert role_review(client, c, role, 'APPROVED').status_code == 409
    verified(client, c, 'DRIVING_LICENCE', issuing_country='LK', expiry_date='2030-12-31')
    assert role_review(client, c, role, 'APPROVED').status_code == 200


@pytest.mark.parametrize('ownership,kind', [('self', 'VEHICLE_REGISTRATION'),
                                         ('individual', 'OWNER_AUTHORISATION'),
                                         ('company', 'OWNER_AUTHORISATION')])
def test_frozen_owner_evidence_cases(client, review_case, ownership, kind):
    # Case is review guidance, not a new client-authoritative field or account type.
    c = review_case
    verified(client, c, 'NIC')
    assert role_review(client, c, c['roles']['OWNER'], 'APPROVED').status_code == 409
    verified(client, c, kind)
    assert role_review(client, c, c['roles']['OWNER'], 'APPROVED').status_code == 200


def test_each_application_document_upload_accepts_absent_optional_metadata(client, review_case):
    for kind in ('NIC', 'PASSPORT', 'DRIVING_LICENCE', 'VEHICLE_REGISTRATION', 'OWNER_AUTHORISATION'):
        result = upload(client, review_case, kind)
        assert result.status_code == 201, result.text
        data = result.json()
        for field in ('document_number', 'issuing_country', 'issue_date', 'expiry_date'):
            assert data[field] is None


def test_correction_replacement_retains_history_and_pending_role(client, review_case):
    c = review_case
    first = upload(client, c).json()
    reviewing = doc_review(client, c, first, 'UNDER_REVIEW')
    corrected = doc_review(client, c, reviewing, 'NEEDS_CORRECTION', 'Both sides must be readable.')
    roles = client.get('/api/v1/users/me/roles', headers=c['owner']).json()['items']
    assert next(r for r in roles if r['role_code'] == 'OWNER')['approval_status'] == 'PENDING'
    replacement = upload(client, c).json()
    assert replacement['superseded_document_id'] == first['id']
    old = client.get('/api/v1/documents/' + first['id'], headers=c['owner']).json()
    assert old['rejection_reason'] == 'Both sides must be readable.'
    assert client.get(old['secure_file_url'], headers=c['owner']).status_code == 200
    detail = client.get('/api/v1/admin/role-requests/' + c['roles']['OWNER']['id'], headers=c['admin']).json()
    assert [d['id'] for d in detail['documents']] == [replacement['id']]
    records, _, _ = client.app.state.audit.records()
    assert any(r.get('full_reason') == corrected['rejection_reason'] and r['outcome'] == 'committed' for r in records)


def test_audit_failure_prevents_role_document_and_resubmission_commit(client, review_case, monkeypatch):
    c = review_case; journal = client.app.state.audit
    doc = upload(client, c).json(); role = c['roles']['OWNER']
    original = journal.append
    def fail(event): raise OSError('injected disk failure')
    monkeypatch.setattr(journal, 'append', fail)
    r = role_review(client, c, role, 'REJECTED', 'Full reason must survive.')
    assert r.status_code == 503 and r.json()['code'] == 'REVIEW_DEPENDENCY_UNAVAILABLE'
    r = client.patch(f"/api/v1/admin/documents/{doc['id']}/review", json={'decision': 'UNDER_REVIEW', 'version': 1}, headers=c['admin'])
    assert r.status_code == 503
    with client.app.state.sessions() as db:
        assert db.get(UserRole, UUID(role['id'])).approval_status == 'PENDING'
        assert db.get(Document, UUID(doc['id'])).status == 'SUBMITTED'
    monkeypatch.setattr(journal, 'append', original)
    rejected = role_review(client, c, role, 'REJECTED', 'Full reason must survive.').json()
    monkeypatch.setattr(journal, 'append', fail)
    assert client.post('/api/v1/users/me/role-requests', json={'role_code': 'OWNER'}, headers=c['owner']).status_code == 503
    with client.app.state.sessions() as db:
        row = db.get(UserRole, UUID(role['id']))
        assert row.rejection_reason == rejected['rejection_reason'] and row.version == rejected['version']
    monkeypatch.setattr(journal, 'append', original)
    assert client.post('/api/v1/users/me/role-requests', json={'role_code': 'OWNER'}, headers=c['owner']).status_code == 201
    records, _, _ = journal.records()
    assert any(r.get('previous_decision_evidence', {}).get('rejection_reason') == rejected['rejection_reason'] and r['outcome'] == 'committed' for r in records)


def test_concurrent_review_is_one_commit_one_version_conflict(client, review_case):
    c = review_case; role = c['roles']['DRIVER']
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: role_review(client, c, role, 'REJECTED', 'Please correct your evidence.'), range(2)))
    assert sorted(r.status_code for r in results) == [200, 409]
    records, _, _ = client.app.state.audit.records()
    assert len([r for r in records if r['outcome'] == 'committed' and r['target']['id'] == role['id']]) == 1


def test_decision_strict_json_boundary_errors_and_no_self_document_review(client, review_case):
    c = review_case; path = '/api/v1/admin/role-requests/' + c['roles']['OWNER']['id'] + '/review'
    for body in [{'decision': 'APPROVED', 'version': True}, {'decision': 'REJECTED', 'version': 1, 'reason': ' '},
                 {'decision': 'REJECTED', 'version': 1, 'reason': 'x' * 2001}, {'decision': 'APPROVED', 'version': 1, 'reason': 'note'},
                 {'decision': 'PENDING', 'version': 1}, {'decision': 'REJECTED', 'version': 1, 'reason': 'valid', 'approved_by': str(c['admin_id'])}]:
        assert client.patch(path, json=body, headers=c['admin']).status_code == 422
    assert client.patch(path, content='{"decision":"REJECTED","decision":"APPROVED","version":1}', headers={**c['admin'], 'Content-Type': 'application/json'}).status_code == 400
    assert client.patch(path, content='x' * 8193, headers={**c['admin'], 'Content-Type': 'application/json'}).status_code == 413
    assert client.patch(path, content='{}', headers=c['admin']).status_code == 415
    own_c = {**c, 'person': {'id': str(c['admin_id'])}, 'owner': c['admin']}
    own = upload(client, own_c).json()
    assert client.get(own['secure_file_url'], headers=c['admin']).status_code == 200
    result = client.patch('/api/v1/admin/documents/' + own['id'] + '/review', json={'decision': 'UNDER_REVIEW', 'version': 1}, headers=c['admin'])
    assert result.json()['code'] == 'REVIEW_FORBIDDEN'


@pytest.mark.parametrize('name', ['../x.png', 'C:\\x.png', 'x:stream.png', 'CON.png', 'lpt1.jpg', 'evil\r\n.png', 'x.png.', ' x.png'])
def test_safe_display_filename(name):
    with pytest.raises(ApiError): safe_filename(name)


def test_upload_invalid_content_parts_sizes_and_orphan_cleanup(client, review_case):
    c = review_case; fields = dict(owner_type='USER', owner_id=c['person']['id'], document_type='NIC')
    for filename, content, mime in [('x.png', b'<html>no</html>', 'image/png'), ('x.pdf', b'%PDF-broken', 'application/pdf'), ('x.jpg', png(), 'image/jpeg'), ('x.png', b'', 'image/png')]:
        assert client.post('/api/v1/documents', data=fields, files={'file': (filename, content, mime)}, headers=c['owner']).status_code == 422
    assert client.post('/api/v1/documents', json=fields, headers=c['owner']).status_code == 415
    assert client.post('/api/v1/documents', data={**fields, 'status': 'APPROVED'}, files={'file': ('x.png', png(), 'image/png')}, headers=c['owner']).status_code == 422
    assert client.post('/api/v1/documents', data=fields, files=[('file', ('x.png', png(), 'image/png')), ('file', ('y.png', png(), 'image/png'))], headers=c['owner']).status_code == 422
    # Clear only this isolated test's upload counters before testing further independent boundary cases.
    store = client.app.state.store
    for key in list(store.client.scan_iter(store.prefix + '*')):
        if 'upload' in key: store.client.delete(key)
    oversized = client.post('/api/v1/documents', data=fields, files={'file': ('x.png', b'x' * (MAX_FILE + 1), 'image/png')}, headers=c['owner'])
    assert oversized.status_code == 413
    assert oversized.json()['field_errors'][0]['field'] == 'file'
    assert '10,485,760 bytes' in oversized.json()['field_errors'][0]['message']
    good = upload(client, c); assert good.status_code == 201
    storage = client.app.state.documents
    orphan = storage.root() / uuid4().hex; orphan.write_bytes(b'unreferenced')
    staging = storage.root() / (uuid4().hex + '.staging'); staging.write_bytes(b'crashed upload')
    from app.private_infrastructure import file_lock
    with file_lock(storage.root() / 'upload.lock'), client.app.state.sessions() as db: storage.recover(db)
    assert not orphan.exists() and not staging.exists()
    assert client.get(good.json()['secure_file_url'], headers=c['owner']).status_code == 200


def test_terminal_failure_has_no_false_rollback_and_recovers(client, review_case, monkeypatch):
    c = review_case; journal = client.app.state.audit; original = journal.append
    def terminal_failure(event):
        if event['outcome'] == 'committed': raise OSError('terminal outage')
        return original(event)
    monkeypatch.setattr(journal, 'append', terminal_failure)
    result = role_review(client, c, c['roles']['DRIVER'], 'REJECTED', 'Durable complete reason.')
    assert result.status_code == 500 and result.json()['message'] == 'The decision outcome could not be confirmed. Refresh before retrying.'
    with client.app.state.sessions() as db: assert db.get(UserRole, UUID(c['roles']['DRIVER']['id'])).approval_status == 'REJECTED'
    # Further mutations blocked until the journal can reconcile the committed xid8.
    assert role_review(client, c, c['roles']['OWNER'], 'REJECTED', 'another decision').status_code == 503
    monkeypatch.setattr(journal, 'append', original)
    with journal.coordinated(): pass
    assert role_review(client, c, c['roles']['DRIVER'], 'REJECTED', 'retry').json()['code'] == 'VERSION_CONFLICT'


def test_torn_journal_blocks_mutation_and_preserves_bytes(client, review_case):
    c = review_case; path = client.app.state.audit.root() / 'events.journal'
    with path.open('ab') as stream: stream.write(b'{torn'); stream.flush(); os.fsync(stream.fileno())
    before = path.read_bytes()
    assert role_review(client, c, c['roles']['OWNER'], 'REJECTED', 'Will not commit').status_code == 503
    assert path.read_bytes() == before


def test_controlled_provisioning_is_idempotent_and_no_public_admin_grant(client, review_case):
    c = review_case
    with client.app.state.sessions() as db:
        assert 'unchanged' in provision(db, client.app.state.audit, c['admin_id'], 'test-operator', str(uuid4()))
        role = db.scalar(select(UserRole).where(UserRole.user_id == c['admin_id'], UserRole.role_code == 'ADMIN'))
        role.approval_status = 'REJECTED'; role.rejection_reason = 'Fixture operator revocation'; db.commit()
        assert 'REJECTED (unchanged)' in provision(db, client.app.state.audit, c['admin_id'], 'test-operator', str(uuid4()))
    assert client.post('/api/v1/users/me/role-requests', json={'role_code': 'ADMIN'}, headers=c['owner']).status_code == 422


def test_physical_dictionary_exact_review_columns_constraints_and_no_2pc(client):
    with client.app.state.engine.connect() as db:
        schema = db.scalar(text('select current_schema()'))
        assert db.scalar(text('SHOW max_prepared_transactions')) == '0'
        assert db.scalar(text('SHOW fsync')) == 'on'
        xid = db.scalar(text('SELECT pg_current_xact_id()::text'))
        assert db.scalar(text('SELECT pg_xact_status(CAST(:x AS xid8))'), {'x': xid}) == 'in progress'
    inspector = inspect(client.app.state.engine)
    for cls in (Vehicle, Document):
        name = cls.__table__.name
        actual = {c['name']: c for c in inspector.get_columns(name, schema=schema)}
        assert set(actual) == set(cls.__table__.c.keys())
        assert all(actual[c.name]['nullable'] == c.nullable for c in cls.__table__.c)
        assert {c['name'] for c in inspector.get_check_constraints(name, schema=schema)} == {c.name for c in cls.__table__.constraints if c.__class__.__name__ == 'CheckConstraint'}


def test_review_rate_limits_unauthorized_decisions_and_protected_vehicle_owner(client, review_case):
    c = review_case; role = c['roles']['OWNER']
    path = '/api/v1/admin/role-requests/' + role['id'] + '/review'
    body = {'decision': 'REJECTED', 'version': 1, 'reason': 'Unauthorized change'}
    assert client.patch(path, json=body, headers=c['owner']).json()['code'] == 'ADMIN_REQUIRED'
    with client.app.state.sessions() as db:
        vehicle = Vehicle(public_vehicle_reference='V-' + uuid4().hex[:16], registration_number='TEST-' + uuid4().hex[:6], owner_user_id=UUID(c['person']['id']))
        db.add(vehicle); db.commit(); vehicle_id = str(vehicle.id)
    result = client.post('/api/v1/documents', data={'owner_type': 'VEHICLE', 'owner_id': vehicle_id, 'document_type': 'VEHICLE_REGISTRATION'}, files={'file': ('x.png', png(), 'image/png')}, headers=c['owner'])
    assert result.status_code == 201 and result.json()['user_id'] is None
    assert client.get(result.json()['secure_file_url'], headers=c['owner']).status_code == 200
    for _ in range(30): client.patch(path, json=body, headers=c['admin'])
    limited = client.patch(path, json=body, headers=c['admin'])
    assert limited.status_code == 429 and int(limited.headers['retry-after']) > 0


def test_controlled_admin_revocation_and_live_openapi_contract(client, review_case):
    from app.review_operator import revoke
    from app.review_audit import FileAuditJournal
    from pathlib import Path
    c = review_case
    with client.app.state.sessions() as db:
        assert 'suspended' in revoke(db, client.app.state.audit, c['admin_id'], 'test-operator', 'Controlled operator revocation.', str(uuid4()))
    assert client.get('/api/v1/admin/role-requests', headers=c['admin']).status_code == 403
    assert client.get('/api/v1/users/me', headers=c['admin']).json()['approved_roles'] == ['PASSENGER']
    source = json.loads((Path(__file__).parents[2] / 'docs/03-API/03C-TRAVELLY-ADMIN-REVIEW-OPENAPI.json').read_text())
    live = client.get('/openapi.json').json()
    for path, operations in source['paths'].items():
        for method, operation in operations.items(): assert live['paths'][path][method] == operation
