from concurrent.futures import ThreadPoolExecutor
from uuid import UUID

import pytest
from sqlalchemy import select

from app.models import User, UserRole
from conftest import bearer, captured_token


@pytest.mark.parametrize('supplied,canonical', [
    ('+94 77 123 4567', '+94771234567'),
    ('+44 (7400) 123-456', '+447400123456'),
    ('+1 (202) 555-0123', '+12025550123'),
    ('+6907290', '+6907290'),  # Valid short Tokelau example; no eight-digit floor.
])
def test_international_registration_is_normalized_and_unverified(client, passenger, supplied, canonical):
    response = client.post('/api/v1/auth/register', json={**passenger, 'phone_e164': supplied})
    assert response.status_code == 201, response.text
    user = response.json()
    assert user['phone_e164'] == canonical
    assert user['account_status'] == 'PENDING_VERIFICATION'
    assert user['phone_verified_at'] is None and user['email_verified_at'] is None
    assert user['approved_roles'] == ['PASSENGER']
    with client.app.state.sessions() as db:
        assert db.get(User, UUID(user['id'])).phone_e164 == canonical
        roles = db.scalars(select(UserRole).where(UserRole.user_id == UUID(user['id']))).all()
        assert [(r.role_code, r.approval_status) for r in roles] == [('PASSENGER', 'APPROVED')]
    assert client.post('/api/v1/auth/email/verify', json={'token': captured_token(client)}).status_code == 200
    login = client.post('/api/v1/auth/login', json={'identifier': canonical, 'password': passenger['password']})
    assert login.status_code == 200
    profile = client.get('/api/v1/users/me', headers=bearer(login.json()))
    assert profile.json()['id'] == user['id'] and profile.json()['phone_verified_at'] is None


@pytest.mark.parametrize('number', [
    '+9991234567', '+94', '+9477', '0771234567', '',
    '+940771234567', '+9494771234567', '+4474001234567890',
    '+94771234567 ext 123', '+94771234567abc', '+94771234567\n',
])
def test_invalid_phone_cannot_be_discarded_even_with_valid_email(client, passenger, number):
    response = client.post('/api/v1/auth/register', json={**passenger, 'phone_e164': number})
    assert response.status_code == 422
    assert response.json()['code'] == 'VALIDATION_ERROR'
    assert response.json()['field_errors'][0]['field'] == 'phone_e164'
    assert 'valid international mobile number' in response.json()['field_errors'][0]['message']
    with client.app.state.sessions() as db:
        assert db.scalar(select(User).where(User.email == passenger['email'])) is None


def test_foreign_duplicate_normalization_is_atomic(client, passenger):
    numbers = ['+44 7400 123456', '+447400123456']
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda n: client.post('/api/v1/auth/register',
            json={**passenger, 'phone_e164': n}), numbers))
    assert sorted(r.status_code for r in responses) == [201, 409]
    conflict = next(r.json() for r in responses if r.status_code == 409)
    assert conflict['code'] == 'CONTACT_ALREADY_REGISTERED'
    assert 'already registered' in conflict['message']
    assert conflict['field_errors'][0]['field'] in ('email', 'phone_e164')
    with client.app.state.sessions() as db:
        assert len(db.scalars(select(User)).all()) == 1
        assert len(db.scalars(select(UserRole)).all()) == 1
