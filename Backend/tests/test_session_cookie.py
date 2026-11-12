"""Staying signed in across page reloads: the refresh token travels in an HttpOnly cookie (owner decision 12 Nov)."""
from app.core.security import decode_token
from conftest import signed_in, bearer

COOKIE = 'travelly_session'


def set_cookie_header(response):
    return '; '.join(v for k, v in response.headers.multi_items() if k.lower() == 'set-cookie')


def login(client, passenger, **extra):
    return client.post('/api/v1/auth/login', json={'identifier': passenger['email'], 'password': passenger['password'], **extra})


def test_login_sets_an_httponly_session_cookie_and_a_reload_restores_the_session(client, passenger):
    signed_in(client, passenger)
    client.cookies.clear()
    first = login(client, passenger)
    header = set_cookie_header(first)
    assert COOKIE + '=' in header and 'HttpOnly' in header and 'Path=/api/v1/auth' in header
    assert 'samesite=strict' in header.lower() and 'Max-Age' not in header  # browser-session cookie without "remember me"
    # A page reload: the app has no tokens in memory and asks with an empty body.
    restored = client.post('/api/v1/auth/refresh', json={})
    assert restored.status_code == 200, restored.text
    assert client.get('/api/v1/users/me', headers=bearer(restored.json())).status_code == 200
    # The cookie rotated with the token, so a second reload works too.
    assert client.post('/api/v1/auth/refresh', json={}).status_code == 200


def test_remember_me_keeps_the_cookie_after_a_browser_restart(client, passenger):
    signed_in(client, passenger)
    remembered = login(client, passenger, remember_me=True)
    assert 'Max-Age=' in set_cookie_header(remembered)
    assert decode_token(remembered.json()['refresh_token'], client.app.state.settings, 'refresh')['rm'] is True
    renewed = client.post('/api/v1/auth/refresh', json={})
    assert renewed.status_code == 200 and 'Max-Age=' in set_cookie_header(renewed)


def test_logout_clears_the_cookie_and_the_session_cannot_be_restored(client, passenger):
    signed_in(client, passenger)
    tokens = login(client, passenger).json()
    out = client.post('/api/v1/auth/logout', json={}, headers=bearer(tokens))
    assert out.status_code == 204
    assert COOKIE + '=""' in set_cookie_header(out) or 'Max-Age=0' in set_cookie_header(out)
    assert client.post('/api/v1/auth/refresh', json={}).status_code == 401
    assert client.get('/api/v1/users/me', headers=bearer(tokens)).status_code == 401


def test_without_a_cookie_or_token_refresh_is_refused(client, passenger):
    client.cookies.clear()
    refused = client.post('/api/v1/auth/refresh', json={})
    assert refused.status_code == 401 and refused.json()['code'] == 'INVALID_REFRESH_TOKEN'


def test_a_replayed_cookie_is_refused_and_cleared(client, passenger):
    signed_in(client, passenger)
    login(client, passenger)
    stale = client.cookies.get(COOKIE)
    assert client.post('/api/v1/auth/refresh', json={}).status_code == 200
    client.cookies.clear()
    client.cookies.set(COOKIE, stale, path='/api/v1/auth')
    replay = client.post('/api/v1/auth/refresh', json={})
    cleared = set_cookie_header(replay)
    assert replay.status_code == 401 and ('Max-Age=0' in cleared or COOKIE + '=""' in cleared)
