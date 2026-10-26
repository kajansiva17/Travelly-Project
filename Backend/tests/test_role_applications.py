from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, select

from app.api import require_role
from app.errors import ApiError
from app.models import User, UserRole
from conftest import bearer, signed_in


PATH = '/api/v1/users/me/role-requests'


@pytest.mark.parametrize('codes', [('OWNER',), ('DRIVER',), ('OWNER', 'DRIVER')])
def test_independent_applications_keep_passenger_and_contact_state(client, passenger, codes):
    user, tokens = signed_in(client, passenger)
    for code in codes:
        response = client.post(PATH, json={'role_code': code}, headers=bearer(tokens))
        assert response.status_code == 201
        assert response.json()['approval_status'] == 'PENDING'
        assert response.json()['role_code'] == code
        assert not {'user_id', 'approved_by', 'role_profile', 'created_by'} & response.json().keys()
    profile = client.get('/api/v1/users/me', headers=bearer(tokens)).json()
    assert profile['id'] == user['id'] and profile['approved_roles'] == ['PASSENGER']
    assert profile['account_status'] == 'ACTIVE'
    assert profile['email_verified_at'] is not None and profile['phone_verified_at'] is None
    roles = client.get('/api/v1/users/me/roles', headers=bearer(tokens)).json()['items']
    assert len(roles) == len(codes) + 1


@pytest.mark.parametrize('extra', [
    {'approval_status': 'APPROVED'}, {'approval_status': 'REJECTED'},
    {'approval_status': 'SUSPENDED'}, {'approved_by': str(uuid4())},
    {'user_id': str(uuid4())}, {'role_profile': {'approved': True}},
    {'supporting_document_ids': [str(uuid4())]},
])
def test_applicant_cannot_control_review_or_attach_unimplemented_documents(client, passenger, extra):
    _, tokens = signed_in(client, passenger)
    response = client.post(PATH, json={'role_code': 'OWNER', **extra}, headers=bearer(tokens))
    assert response.status_code == 422
    roles = client.get('/api/v1/users/me/roles', headers=bearer(tokens)).json()['items']
    assert [role['role_code'] for role in roles] == ['PASSENGER']


def test_concurrent_duplicate_application_creates_only_one_membership(client, passenger):
    user, tokens = signed_in(client, passenger)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: client.post(PATH, json={'role_code': 'OWNER'}, headers=bearer(tokens)), range(2)))
    assert sorted(response.status_code for response in responses) == [201, 409]
    loser = next(response for response in responses if response.status_code == 409)
    assert loser.json()['code'] == 'ROLE_ALREADY_REQUESTED'
    with client.app.state.sessions() as db:
        roles = db.scalars(select(UserRole).where(UserRole.user_id == UUID(user['id']))).all()
        assert sorted(role.role_code for role in roles) == ['OWNER', 'PASSENGER']


def test_rejected_resubmission_keeps_identity_and_resets_decision_fields(client, passenger, caplog):
    _, tokens = signed_in(client, passenger)
    initial = client.post(PATH, json={'role_code': 'DRIVER'}, headers=bearer(tokens)).json()
    with client.app.state.sessions() as db:
        role = db.get(UserRole, UUID(initial['id']))
        role.approval_status = 'REJECTED'
        role.rejection_reason = 'Private test review reason'
        role.version += 1
        db.commit()
        previous_version, previous_request, created_at = role.version, role.requested_at, role.created_at
    with caplog.at_level('INFO', logger='travelly.audit'):
        response = client.post(PATH, json={'role_code': 'DRIVER'}, headers=bearer(tokens))
    result = response.json()
    assert response.status_code == 201 and result['id'] == initial['id']
    assert result['approval_status'] == 'PENDING' and result['version'] == previous_version + 1
    assert all(result[field] is None for field in ['approved_at', 'rejection_reason', 'suspended_at', 'suspension_reason'])
    with client.app.state.sessions() as db:
        role = db.get(UserRole, UUID(initial['id']))
        assert role.requested_at > previous_request and role.created_at == created_at
        assert role.approved_by is None and role.updated_by == role.user_id
    assert 'role_resubmitted' in caplog.text
    assert 'Private test review reason' not in caplog.text


def test_approved_and_suspended_roles_cannot_resubmit_or_reinstate(client, passenger):
    user, tokens = signed_in(client, passenger)
    for code in ['OWNER', 'DRIVER']:
        assert client.post(PATH, json={'role_code': code}, headers=bearer(tokens)).status_code == 201
    with client.app.state.sessions() as db:
        # Privileged fixture only; there is no public approval API.
        admin = User(public_user_reference='USR-' + uuid4().hex[:16].upper(), full_name='Review Fixture', email=f'{uuid4().hex}@example.com', password_hash='not-a-login-hash')
        db.add(admin)
        db.flush()
        roles = db.scalars(select(UserRole).where(UserRole.user_id == UUID(user['id']))).all()
        for role in roles:
            if role.role_code == 'OWNER':
                role.approval_status = 'APPROVED'
                role.approved_at = datetime.now(timezone.utc)
                role.approved_by = admin.id
            elif role.role_code == 'DRIVER':
                role.approval_status = 'SUSPENDED'
                role.suspended_at = datetime.now(timezone.utc)
                role.suspension_reason = 'Authorized review required'
        db.commit()
        person = db.get(User, UUID(user['id']))
        require_role(db, person, 'PASSENGER')
        require_role(db, person, 'OWNER')
        with pytest.raises(ApiError) as denied:
            require_role(db, person, 'DRIVER')
        assert denied.value.status == 403
        with pytest.raises(ApiError):
            require_role(db, person, 'ADMIN')
    for code in ['OWNER', 'DRIVER']:
        response = client.post(PATH, json={'role_code': code}, headers=bearer(tokens))
        assert response.status_code == 409 and response.json()['code'] == 'ROLE_ALREADY_REQUESTED'
    assert client.get('/api/v1/users/me', headers=bearer(tokens)).json()['approved_roles'] == ['OWNER', 'PASSENGER']


def test_application_authentication_own_record_access_and_passenger_guard(client, passenger):
    assert client.post(PATH, json={'role_code': 'OWNER'}).status_code == 401
    user, tokens = signed_in(client, passenger)
    assert client.post(PATH, json={'role_code': 'OWNER'}, headers=bearer(tokens)).status_code == 201
    other = {**passenger, 'email': f'{uuid4().hex}@example.com', 'phone_e164': '+9477' + str(uuid4().int % 10000000).zfill(7)}
    _, other_tokens = signed_in(client, other)
    assert [role['role_code'] for role in client.get('/api/v1/users/me/roles', headers=bearer(other_tokens)).json()['items']] == ['PASSENGER']
    with client.app.state.sessions() as db:
        # Corrupt membership fixture: fail closed instead of repairing it from a request.
        db.execute(delete(UserRole).where(UserRole.user_id == UUID(user['id']), UserRole.role_code == 'PASSENGER'))
        db.commit()
    response = client.post(PATH, json={'role_code': 'DRIVER'}, headers=bearer(tokens))
    assert response.status_code == 403 and response.json()['code'] == 'ROLE_NOT_APPROVED'


@pytest.mark.parametrize('status', ['SUSPENDED', 'BLOCKED', 'CLOSED'])
def test_restricted_account_cannot_apply(client, passenger, status):
    user, tokens = signed_in(client, passenger)
    with client.app.state.sessions() as db:
        db.get(User, UUID(user['id'])).account_status = status
        db.commit()
    assert client.post(PATH, json={'role_code': 'OWNER'}, headers=bearer(tokens)).status_code == 403
