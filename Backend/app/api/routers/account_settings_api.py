"""Settings, Account security: the person's own sessions, password change and notification preferences.

Owner decisions (14 November 2026). Every role uses the same endpoints (they belong to the user, not to a workspace).
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request
from pydantic import Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.routers.api import current, session_meta, touch
from app.core import session_cookie
from app.core.errors import ApiError
from app.core.security import hasher, issue_tokens, verify_password
from app.dependencies.database import get_db
from app.models import User
from app.schemas import RequestModel, new_password

router = APIRouter(prefix='/api/v1', tags=['Account settings'])

# Only these can be turned off. Everything about bookings, money, trips, refunds, replacements and Admin actions always arrives.
OPTIONAL_NOTIFICATIONS = ('ROAD_ALERT', 'MAINTENANCE_DUE')
ALL_NOTIFICATIONS = ('BOOKING_REQUEST', 'BOOKING_CONFIRMED', 'DRIVER_ASSIGNMENT', 'RECONFIRMATION', 'PAYMENT', 'REFUND', 'REPLACEMENT',
                     'MAINTENANCE_DUE', 'DOCUMENT_EXPIRY', 'ROAD_ALERT', 'ADMIN_ACTION')


def muted_types(user):
    return [t for t in (user.notification_preferences or {}).get('muted', []) if t in OPTIONAL_NOTIFICATIONS]


# ----------------------------------------------------------------------------- sessions

def session_out(sid, data, current_sid):
    when = lambda v: datetime.fromtimestamp(int(v), timezone.utc).isoformat() if v else None
    return {'id': sid, 'current': sid == current_sid, 'device': data.get('device') or 'Unknown device', 'ip_hint': data.get('ip_hint') or None,
            'signed_in_at': when(data.get('created')), 'last_active_at': when(data.get('last') or data.get('created'))}


@router.get('/users/me/sessions')
def my_sessions(request: Request, user=Depends(current)):
    here = request.state.auth_claims['sid']
    live = request.app.state.store.sessions_of(user.id)
    items = [session_out(sid, data, here) for sid, data in live.items()]
    items.sort(key=lambda i: i['last_active_at'] or '', reverse=True)     # newest first, then this device on top
    items.sort(key=lambda i: not i['current'])
    return {'items': items[:50]}


@router.delete('/users/me/sessions/{session_id}', status_code=204)
def end_session(session_id: str, request: Request, user=Depends(current)):
    store = request.app.state.store
    if session_id == request.state.auth_claims['sid']:
        raise ApiError(409, 'USE_LOGOUT_FOR_THIS_DEVICE', 'Use Log out to leave this device.')
    if session_id not in store.sessions_of(user.id):
        raise ApiError(404, 'SESSION_NOT_FOUND', 'That session is not signed in any more.')
    store.revoke(session_id)


@router.post('/users/me/sessions/revoke-others')
def end_other_sessions(request: Request, user=Depends(current)):
    store, here = request.app.state.store, request.state.auth_claims['sid']
    others = [sid for sid in store.sessions_of(user.id) if sid != here]
    for sid in others:
        store.revoke(sid)
    return {'signed_out': len(others)}


# ----------------------------------------------------------------------------- password

class ChangePassword(RequestModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(max_length=128)

    @field_validator('new_password')
    @classmethod
    def valid(cls, value):
        return new_password(value)


@router.post('/users/me/password')
def change_password(body: ChangePassword, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    store, settings = request.app.state.store, request.app.state.settings
    lock = 'change-password:' + str(user.id)
    store.check_lock(lock)
    row = db.scalar(select(User).where(User.id == user.id).with_for_update().execution_options(populate_existing=True))
    if not row.password_hash:
        raise ApiError(409, 'NO_PASSWORD_SET', 'This account signs in with Google. Use "Reset password using a verified email" to set a password.')
    if not verify_password(body.current_password, row.password_hash):
        store.failure(lock)
        raise ApiError(422, 'CURRENT_PASSWORD_WRONG', 'The current password is not correct.',
                       [{'field': 'current_password', 'message': 'Not correct.'}])
    if verify_password(body.new_password, row.password_hash):
        raise ApiError(422, 'PASSWORD_UNCHANGED', 'Choose a password different from the current one.',
                       [{'field': 'new_password', 'message': 'Same as the current password.'}])
    store.clear_failures(lock)
    row.password_hash = hasher.hash(body.new_password)
    row.auth_version += 1                      # every older access and refresh token stops working
    touch(row); db.commit()
    for sid in store.sessions_of(row.id):
        store.revoke(sid)
    remember = bool(request.state.auth_claims.get('rm'))
    tokens, sid, expires = issue_tokens(row.id, settings, auth_version=row.auth_version, remember=remember)
    store.create(sid, row.id, tokens['refresh_token'], expires, session_meta(request))   # this device stays signed in
    session_cookie.keep(request, tokens, remember)
    return {**tokens, 'message': 'Your password has been changed. Other devices were signed out.'}


# ----------------------------------------------------------------------------- notification preferences

class NotificationPreferences(RequestModel):
    muted: list[str] = Field(max_length=20)


def preferences_out(user):
    muted = muted_types(user)
    return {'items': [{'notification_type': t, 'can_turn_off': t in OPTIONAL_NOTIFICATIONS, 'enabled': t not in muted} for t in ALL_NOTIFICATIONS]}


@router.get('/users/me/notification-preferences')
def get_notification_preferences(user=Depends(current)):
    return preferences_out(user)


@router.put('/users/me/notification-preferences')
def set_notification_preferences(body: NotificationPreferences, user=Depends(current), db: Session = Depends(get_db)):
    bad = sorted(set(body.muted) - set(OPTIONAL_NOTIFICATIONS))
    if bad:
        raise ApiError(422, 'NOTIFICATION_CANNOT_BE_TURNED_OFF', 'These notifications are always sent: ' + ', '.join(bad) + '.',
                       [{'field': 'muted', 'message': 'Cannot be turned off: ' + ', '.join(bad)}])
    row = db.scalar(select(User).where(User.id == user.id).with_for_update().execution_options(populate_existing=True))
    row.notification_preferences = {**(row.notification_preferences or {}), 'muted': sorted(set(body.muted))}
    touch(row); db.commit()
    return preferences_out(row)
