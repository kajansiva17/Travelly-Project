from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from app.config import get_settings
from app.main import create_app
from app.sessions import SessionStore


@pytest.fixture
def boundary_client():
    settings=get_settings()
    store=SessionStore(settings.redis_url,prefix='travelly-http-test:'+uuid4().hex+':')
    assert store.client.ping()
    with TestClient(create_app(settings,store=store)) as client:
        yield client
    keys=list(store.client.scan_iter(store.prefix+'*'))
    if keys:store.client.delete(*keys)


@pytest.mark.parametrize('body,status', [('{',400),('{"x":1,"x":2}',400),('[]',422),('NaN',400),('x'*8193,413)])
def test_http_json_boundary(boundary_client,body,status):
    response=boundary_client.post('/api/v1/auth/register',content=body,headers={'Content-Type':'application/json'})
    assert response.status_code==status
    assert set(response.json())=={'code','message','field_errors','trace_id'}
    assert response.headers['Cache-Control']=='no-store'


def test_extra_fields_never_echo_password(boundary_client):
    secret='a long private password'
    response=boundary_client.post('/api/v1/auth/register',json={'full_name':'Test','email':'test@example.com','password':secret,'role_code':'ADMIN'})
    assert response.status_code==422 and secret not in response.text


def test_missing_access_wrong_content_type_and_rate_limit(boundary_client):
    assert boundary_client.get('/api/v1/users/me').status_code==401
    assert boundary_client.post('/api/v1/auth/login',content='text').status_code==415
    for _ in range(10):response=boundary_client.post('/api/v1/auth/register',json={})
    response=boundary_client.post('/api/v1/auth/register',json={})
    assert response.status_code==429 and int(response.headers['Retry-After'])>0


def test_cors_allows_only_configured_origins_and_covers_errors(boundary_client):
    response=boundary_client.get('/api/v1/users/me',headers={'Origin':'http://127.0.0.1:5173'})
    assert response.status_code==401
    assert response.headers['Access-Control-Allow-Origin']=='http://127.0.0.1:5173'
    response=boundary_client.get('/api/v1/users/me',headers={'Origin':'https://untrusted.example'})
    assert 'Access-Control-Allow-Origin' not in response.headers
