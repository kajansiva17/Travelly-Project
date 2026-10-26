from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from uuid import UUID
import pytest
from sqlalchemy import select, text, inspect
from sqlalchemy.exc import IntegrityError
from app.api import require_role
from app.errors import ApiError
from app.models import User, UserRole
from app.security import decode_token
from conftest import signed_in, bearer, captured_token


def test_register_login_profile_logout_journey(client, passenger):
    user,tokens=signed_in(client,passenger)
    assert user['approved_roles']==['PASSENGER'] and user['account_status']=='PENDING_VERIFICATION'
    assert user['email_verified_at'] is None and user['phone_verified_at'] is None
    profile=client.get('/api/v1/users/me',headers=bearer(tokens))
    assert profile.status_code==200 and profile.json()['id']==user['id']
    assert profile.json()['created_at'].endswith('Z')
    assert profile.json()['updated_at'].endswith('Z')
    assert not {'password_hash','failed_login_count','locked_until','created_by'} & profile.json().keys()
    roles=client.get('/api/v1/users/me/roles',headers=bearer(tokens)).json()['items']
    assert len(roles)==1 and roles[0]['role_code']=='PASSENGER' and roles[0]['approval_status']=='APPROVED'
    assert client.post('/api/v1/auth/logout',json={'refresh_token':tokens['refresh_token']},headers=bearer(tokens)).status_code==204
    assert client.get('/api/v1/users/me',headers=bearer(tokens)).status_code==401
    assert client.post('/api/v1/auth/refresh',json={'refresh_token':tokens['refresh_token']}).status_code==401
    assert client.post('/api/v1/auth/logout',json={'refresh_token':tokens['refresh_token']},headers=bearer(tokens)).status_code==204


@pytest.mark.parametrize('length,valid', [(11, False), (12, True), (128, True), (129, False)])
def test_password_length_api_contract(client, passenger, length, valid):
    password = 'Aa1!' + 'p' * (length - 4)
    response = client.post('/api/v1/auth/register', json={**passenger, 'password': password})
    if valid:
        assert response.status_code == 201
        assert client.post('/api/v1/auth/email/verify', json={'token': captured_token(client)}).status_code == 200
        assert client.post('/api/v1/auth/login', json={'identifier': passenger['email'], 'password': password}).status_code == 200
    else:
        assert response.status_code == 422 and password not in response.text
        message = 'Use at least 12 characters.' if length < 12 else 'Use at most 128 characters.'
        assert response.json()['field_errors'] == [{'field': 'password', 'code': 'string_too_short' if length < 12 else 'string_too_long', 'message': message}]


def test_required_contacts_and_case_insensitive_email(client, passenger):
    for field in ('email', 'phone_e164'):
        assert client.post('/api/v1/auth/register', json={**passenger, field: None}).status_code == 422
    data = {**passenger, 'email': '  TEST@example.com  '}
    assert client.post('/api/v1/auth/register', json=data).status_code == 201
    assert client.post('/api/v1/auth/register', json={**data, 'email': 'test@EXAMPLE.COM'}).status_code == 409


def test_concurrent_registration_is_atomic(client, passenger):
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:client.post('/api/v1/auth/register',json=passenger).status_code,range(2)))
    assert sorted(results)==[201,409]
    with client.app.state.sessions() as db:
        assert len(db.scalars(select(User)).all())==1 and len(db.scalars(select(UserRole)).all())==1


@pytest.mark.parametrize('extra',[{'role_code':'ADMIN'},{'account_status':'ACTIVE'},{'email_verified_at':'2026-01-01T00:00:00Z'}])
def test_registration_cannot_grant_privileges(client, passenger, extra):
    r=client.post('/api/v1/auth/register',json={**passenger,**extra})
    assert r.status_code==422 and passenger['password'] not in r.text


def test_bad_json_limits_and_unknown_queries(client, passenger):
    for body in ['{', '{"email":"a","email":"b"}']:
        assert client.post('/api/v1/auth/register',content=body,headers={'Content-Type':'application/json'}).status_code==400
    assert client.post('/api/v1/auth/register',content='x').status_code==415
    assert client.post('/api/v1/auth/register',content='x'*8193,headers={'Content-Type':'application/json'}).status_code==413
    assert client.post('/api/v1/auth/register',json={**passenger,'email':None}).status_code==422
    user,tokens=signed_in(client,passenger)
    assert client.get('/api/v1/users/me?other_user=1',headers=bearer(tokens)).status_code==422


def test_invalid_login_generic_and_fifth_failure_locks(client, passenger):
    user,tokens=signed_in(client,passenger)
    data={'identifier':passenger['email'],'password':'not the password'}
    invalid=client.post('/api/v1/auth/login',json=data)
    unknown=client.post('/api/v1/auth/login',json={**data,'identifier':'unknown@example.com'})
    assert invalid.status_code==unknown.status_code==401
    assert invalid.json()['message']==unknown.json()['message']
    for _ in range(3):assert client.post('/api/v1/auth/login',json=data).status_code==401
    locked=client.post('/api/v1/auth/login',json=data)
    assert locked.status_code==429 and int(locked.headers['Retry-After'])>0
    assert client.post('/api/v1/auth/login',json={**data,'password':passenger['password']}).status_code==429
    with client.app.state.sessions() as db:
        stored=db.get(User,UUID(user['id']))
        assert stored.failed_login_count==5 and stored.locked_until is not None


def test_refresh_rotation_and_replay_revokes_family(client, passenger):
    user,tokens=signed_in(client,passenger)
    refreshed=client.post('/api/v1/auth/refresh',json={'refresh_token':tokens['refresh_token']})
    assert refreshed.status_code==200
    new=refreshed.json()
    assert new['access_token']!=tokens['access_token'] and new['refresh_token']!=tokens['refresh_token']
    old_claims=decode_token(tokens['refresh_token'],client.app.state.settings,'refresh')
    new_claims=decode_token(new['refresh_token'],client.app.state.settings,'refresh')
    assert old_claims['exp']==new_claims['exp']
    assert client.get('/api/v1/users/me',headers=bearer(new)).status_code==200
    assert client.post('/api/v1/auth/refresh',json={'refresh_token':tokens['refresh_token']}).status_code==401
    assert client.get('/api/v1/users/me',headers=bearer(new)).status_code==401


def test_concurrent_refresh_has_one_success_then_revocation(client, passenger):
    _,tokens=signed_in(client,passenger)
    with ThreadPoolExecutor(max_workers=2) as pool:
        result=list(pool.map(lambda _:client.post('/api/v1/auth/refresh',json={'refresh_token':tokens['refresh_token']}),range(2)))
    assert sorted(r.status_code for r in result)==[200,401]
    winner=next(r.json() for r in result if r.status_code==200)
    assert client.get('/api/v1/users/me',headers=bearer(winner)).status_code==401


def test_logout_mismatch_and_other_device_independence(client, passenger):
    _,one=signed_in(client,passenger)
    two=client.post('/api/v1/auth/login',json={'identifier':passenger['email'],'password':passenger['password']}).json()
    assert client.post('/api/v1/auth/logout',json={'refresh_token':two['refresh_token']},headers=bearer(one)).status_code==401
    assert client.post('/api/v1/auth/logout',json={'refresh_token':one['refresh_token']},headers=bearer(one)).status_code==204
    assert client.get('/api/v1/users/me',headers=bearer(two)).status_code==200


@pytest.mark.parametrize('status',['SUSPENDED','BLOCKED','CLOSED'])
def test_account_restriction_and_logout(client, passenger, status):
    user,tokens=signed_in(client,passenger)
    with client.app.state.sessions() as db:
        db.get(User,UUID(user['id'])).account_status=status; db.commit()
    assert client.get('/api/v1/users/me',headers=bearer(tokens)).status_code==403
    assert client.post('/api/v1/auth/login',json={'identifier':passenger['email'],'password':passenger['password']}).status_code==401
    assert client.post('/api/v1/auth/logout',json={'refresh_token':tokens['refresh_token']},headers=bearer(tokens)).status_code==204


def test_role_applications_are_pending_and_independent(client, passenger):
    user,tokens=signed_in(client,passenger)
    for role in ['OWNER','DRIVER']:
        r=client.post('/api/v1/users/me/role-requests',json={'role_code':role},headers=bearer(tokens))
        assert r.status_code==201 and r.json()['approval_status']=='PENDING'
        assert client.post('/api/v1/users/me/role-requests',json={'role_code':role},headers=bearer(tokens)).status_code==409
    assert client.post('/api/v1/users/me/role-requests',json={'role_code':'ADMIN'},headers=bearer(tokens)).status_code==422
    assert client.get('/api/v1/users/me',headers=bearer(tokens)).json()['approved_roles']==['PASSENGER']
    with client.app.state.sessions() as db:
        driver=db.scalar(select(UserRole).where(UserRole.user_id==UUID(user['id']),UserRole.role_code=='DRIVER'))
        driver.approval_status='REJECTED';driver.rejection_reason='Licence review pending';db.commit()
    r=client.post('/api/v1/users/me/role-requests',json={'role_code':'DRIVER'},headers=bearer(tokens))
    assert r.status_code==201 and r.json()['approval_status']=='PENDING' and r.json()['rejection_reason'] is None


def test_suspended_driver_does_not_remove_passenger(client, passenger):
    user,tokens=signed_in(client,passenger)
    with client.app.state.sessions() as db:
        driver=UserRole(user_id=UUID(user['id']),role_code='DRIVER',approval_status='PENDING')
        db.add(driver);db.flush()
        driver.approval_status='SUSPENDED';driver.suspended_at=max(datetime.now(timezone.utc),driver.requested_at);driver.suspension_reason='Review required';db.commit()
        person=db.get(User,UUID(user['id']))
        require_role(db,person,'PASSENGER')
        with pytest.raises(ApiError):require_role(db,person,'DRIVER')
    assert client.get('/api/v1/users/me',headers=bearer(tokens)).json()['approved_roles']==['PASSENGER']
    assert {r['approval_status'] for r in client.get('/api/v1/users/me/roles',headers=bearer(tokens)).json()['items']}=={'APPROVED','SUSPENDED'}


def test_sessions_fail_closed_and_bad_bearers(client, passenger, monkeypatch):
    _,tokens=signed_in(client,passenger)
    assert client.get('/api/v1/users/me').status_code==401
    assert client.get('/api/v1/users/me',headers={'Authorization':'Bearer '+tokens['refresh_token']}).status_code==401
    import redis
    def unavailable(*args,**kwargs):raise redis.ConnectionError()
    monkeypatch.setattr(client.app.state.store.client,'eval',unavailable)
    r=client.get('/api/v1/users/me',headers=bearer(tokens))
    assert r.status_code==503 and r.json()['code']=='AUTH_DEPENDENCY_UNAVAILABLE'


def test_schema_has_only_auth_tables_and_enforces_constraints(client):
    engine=client.app.state.engine
    with engine.connect() as c:
        schema=c.scalar(text('select current_schema()'))
    assert set(inspect(engine).get_table_names(schema=schema))=={'users','user_roles','vehicles','documents','alembic_version'}
    with client.app.state.sessions() as db:
        db.add(User(public_user_reference='USR-0123456789ABCDEF',full_name='No contact',password_hash='hash'))
        with pytest.raises(IntegrityError):db.commit()
        db.rollback()


def test_atomic_registration_rolls_back_failed_membership(client, passenger, monkeypatch):
    from sqlalchemy.orm import Session
    original=Session.add
    def fail_role(self,instance,*args,**kwargs):
        if isinstance(instance,UserRole):raise IntegrityError('membership failure',None,Exception())
        return original(self,instance,*args,**kwargs)
    monkeypatch.setattr(Session,'add',fail_role)
    assert client.post('/api/v1/auth/register',json=passenger).status_code==503
    with client.app.state.sessions() as db:
        assert db.scalar(select(User).where(User.email==passenger['email'])) is None
