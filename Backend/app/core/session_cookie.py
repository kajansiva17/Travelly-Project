"""Keep the refresh token in an HttpOnly cookie so a page reload does not sign the person out.

Browser scripts never see this cookie (HttpOnly), it is only sent to the auth endpoints (Path) and only from the
Travelly site itself (SameSite=Strict). The access token stays in page memory as before. Endpoints only mark what
should happen (request.state.session_cookie); the HTTP boundary middleware writes or clears the cookie.
"""
NAME = 'travelly_session'
PATH = '/api/v1/auth'


def keep(request, tokens, remember=False):
    """Set the cookie. Without "remember me" it is a browser-session cookie (survives reloads, not a browser restart)."""
    request.state.session_cookie = ('set', tokens['refresh_token'], tokens['refresh_expires_in'] if remember else None)


def forget(request):
    request.state.session_cookie = ('clear',)


def read(request):
    return request.cookies.get(NAME)


def apply(request, response, settings):
    action = getattr(request.state, 'session_cookie', None)
    if action is None:
        return
    secure = settings.environment == 'production' or settings.frontend_url.startswith('https://')
    if action[0] == 'set':
        response.set_cookie(NAME, action[1], max_age=action[2], path=PATH, httponly=True, secure=secure, samesite='strict')
    else:
        response.delete_cookie(NAME, path=PATH, httponly=True, secure=secure, samesite='strict')
