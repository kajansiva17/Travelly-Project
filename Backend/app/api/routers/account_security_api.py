"""Settings, Account security (continued): two-step verification and closing the account.

Owner decisions (14 November 2026). Same endpoints for every role. See docs/03-API/03SV-TRAVELLY-TWO-STEP-AND-ACCOUNT-CLOSURE.md.
"""
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional
from fastapi import APIRouter, Depends, Request
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.routers.api import current, session_meta, touch
from app.core import session_cookie
from app.core.errors import ApiError
from app.core.security import issue_tokens, verify_password
from app.dependencies.database import get_db
from app.models import User
from app.schemas import RequestModel
from app.services import account_closure, two_factor

router = APIRouter(prefix='/api/v1', tags=['Account security'])
logger = logging.getLogger('travelly.audit')
CHALLENGE_MINUTES = 5


def locked(db, user_id):
    return db.scalar(select(User).where(User.id == user_id).with_for_update().execution_options(populate_existing=True))


def second_factor(request, row, code):
    """Check an authenticator code or a backup code. Returns a function that records the use, or raises. Wrong tries are limited."""
    store, settings = request.app.state.store, request.app.state.settings
    lock = 'two-factor:' + str(row.id)
    store.check_lock(lock)
    secret = two_factor.unseal(settings, row.totp_secret) if row.totp_secret else None
    step = two_factor.check(secret, code, row.totp_last_step) if secret else None
    if step is not None:
        store.clear_failures(lock)
        return lambda: setattr(row, 'totp_last_step', step)
    left = two_factor.use_backup_code(settings, row.totp_backup_codes, code)
    if left is not None:
        store.clear_failures(lock)
        return lambda: setattr(row, 'totp_backup_codes', left)
    store.failure(lock)
    raise ApiError(422, 'TWO_FACTOR_CODE_WRONG', 'That code is not correct.', [{'field': 'code', 'message': 'Not correct or already used.'}])


def check_password(request, row, password):
    """Re-confirm the password (accounts that have one). Wrong tries are limited."""
    if not row.password_hash:
        return
    store = request.app.state.store
    lock = 'account-confirm:' + str(row.id)
    store.check_lock(lock)
    if not password or not verify_password(password, row.password_hash):
        store.failure(lock)
        raise ApiError(422, 'CURRENT_PASSWORD_WRONG', 'The current password is not correct.', [{'field': 'password', 'message': 'Not correct.'}])
    store.clear_failures(lock)


def reactivate(user):
    """Signing in to a deactivated account brings it back and cancels a pending delete request."""
    if user.account_status == 'DEACTIVATED':
        user.account_status, user.deletion_requested_at = 'ACTIVE', None


def start_session(request, db, user, remember=False):
    reactivate(user)
    user.failed_login_count, user.locked_until, user.last_login_at = 0, None, datetime.now(timezone.utc)
    touch(user); db.commit()
    tokens, sid, expires = issue_tokens(user.id, request.app.state.settings, auth_version=user.auth_version, remember=remember)
    request.app.state.store.create(sid, user.id, tokens['refresh_token'], expires, session_meta(request))
    session_cookie.keep(request, tokens, remember)
    return tokens


def challenge_for(request, user, remember=False):
    token = request.app.state.auth_state.issue('login-2fa', {'uid': str(user.id), 'remember': bool(remember)}, ttl=CHALLENGE_MINUTES * 60)
    return {'status': 'two_factor_required', 'challenge': token, 'expires_in': CHALLENGE_MINUTES * 60,
            'message': 'Enter the 6-digit code from your authenticator app, or a backup code.'}


# ----------------------------------------------------------------------------- two-step verification

class CodeBody(RequestModel):
    code: str = Field(min_length=6, max_length=20)


class ConfirmBody(RequestModel):
    password: Optional[str] = Field(default=None, max_length=128)
    code: str = Field(min_length=6, max_length=20)


class LoginCode(RequestModel):
    challenge: str = Field(min_length=30, max_length=100)
    code: str = Field(min_length=6, max_length=20)


def status_out(row):
    return {'enabled': row.totp_enabled_at is not None, 'enabled_at': row.totp_enabled_at.isoformat() if row.totp_enabled_at else None,
            'backup_codes_left': len(row.totp_backup_codes or []) if row.totp_enabled_at else 0}


@router.get('/users/me/2fa')
def two_factor_status(user=Depends(current)):
    return status_out(user)


@router.post('/users/me/2fa/setup')
def two_factor_setup(request: Request, user=Depends(current), db: Session = Depends(get_db)):
    row = locked(db, user.id)
    if row.totp_enabled_at:
        raise ApiError(409, 'TWO_FACTOR_ALREADY_ON', 'Two-step verification is already on.')
    secret = two_factor.new_secret()
    row.totp_secret = two_factor.seal(request.app.state.settings, secret)
    touch(row); db.commit()
    return {'secret': secret, 'otpauth_uri': two_factor.otpauth_uri(secret, str(row.email or row.phone_e164)), 'issuer': 'Travelly',
            'message': 'Add this account in your authenticator app, then enter the 6-digit code to turn it on.'}


@router.post('/users/me/2fa/enable')
def two_factor_enable(body: CodeBody, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    settings, store = request.app.state.settings, request.app.state.store
    row = locked(db, user.id)
    if row.totp_enabled_at:
        raise ApiError(409, 'TWO_FACTOR_ALREADY_ON', 'Two-step verification is already on.')
    if not row.totp_secret:
        raise ApiError(409, 'TWO_FACTOR_SETUP_REQUIRED', 'Start the setup first.')
    lock = 'two-factor:' + str(row.id)
    store.check_lock(lock)
    step = two_factor.check(two_factor.unseal(settings, row.totp_secret) or '', body.code)
    if step is None:
        store.failure(lock)
        raise ApiError(422, 'TWO_FACTOR_CODE_WRONG', 'That code is not correct.', [{'field': 'code', 'message': 'Not correct. Check the time on your phone.'}])
    store.clear_failures(lock)
    shown, hashes = two_factor.new_backup_codes(settings)
    row.totp_enabled_at, row.totp_last_step, row.totp_backup_codes = datetime.now(timezone.utc), step, hashes
    touch(row); db.commit()
    logger.info('two-factor on user=%s trace=%s', row.id, request.state.trace_id)
    return {**status_out(row), 'backup_codes': shown, 'message': 'Two-step verification is on. Keep these backup codes safe; each works once and they are not shown again.'}


@router.post('/users/me/2fa/disable')
def two_factor_disable(body: ConfirmBody, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    row = locked(db, user.id)
    if not row.totp_enabled_at:
        raise ApiError(409, 'TWO_FACTOR_NOT_ON', 'Two-step verification is not on.')
    check_password(request, row, body.password)
    used = second_factor(request, row, body.code)
    used()
    row.totp_secret, row.totp_enabled_at, row.totp_backup_codes, row.totp_last_step = None, None, [], None
    touch(row); db.commit()
    logger.info('two-factor off user=%s trace=%s', row.id, request.state.trace_id)
    return status_out(row)


@router.post('/users/me/2fa/backup-codes')
def new_backup_codes(body: ConfirmBody, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    row = locked(db, user.id)
    if not row.totp_enabled_at:
        raise ApiError(409, 'TWO_FACTOR_NOT_ON', 'Two-step verification is not on.')
    check_password(request, row, body.password)
    second_factor(request, row, body.code)()
    shown, hashes = two_factor.new_backup_codes(request.app.state.settings)
    row.totp_backup_codes = hashes
    touch(row); db.commit()
    return {**status_out(row), 'backup_codes': shown, 'message': 'New backup codes. The old ones no longer work.'}


@router.post('/auth/2fa')
def sign_in_with_code(body: LoginCode, request: Request, db: Session = Depends(get_db)):
    """The second step of signing in, after /auth/login or Google sign-in returned status two_factor_required."""
    data = request.app.state.auth_state.read('login-2fa', body.challenge)
    if not data:
        raise ApiError(401, 'TWO_FACTOR_CHALLENGE_EXPIRED', 'This sign-in step expired. Sign in again.')
    row = locked(db, data['uid'])
    if row is None or row.account_status not in ('ACTIVE', 'PENDING_VERIFICATION', 'DEACTIVATED') or not row.totp_enabled_at:
        raise ApiError(401, 'TWO_FACTOR_CHALLENGE_EXPIRED', 'This sign-in step expired. Sign in again.')
    second_factor(request, row, body.code)()
    if not request.app.state.auth_state.read('login-2fa', body.challenge, consume=True):
        raise ApiError(401, 'TWO_FACTOR_CHALLENGE_EXPIRED', 'This sign-in step expired. Sign in again.')
    return start_session(request, db, row, data.get('remember', False))


# ----------------------------------------------------------------------------- close the account

class CloseAccount(RequestModel):
    confirm: Literal[True]
    password: Optional[str] = Field(default=None, max_length=128)
    code: Optional[str] = Field(default=None, min_length=6, max_length=20)


@router.get('/users/me/account-closure')
def closure_status(user=Depends(current), db: Session = Depends(get_db)):
    found = account_closure.blockers(db, user.id)
    return {'can_close': not found, 'blockers': found, 'delete_after_days': account_closure.DELETE_AFTER_DAYS}


def close(request, db, user, body, delete):
    row = locked(db, user.id)
    check_password(request, row, body.password)
    if row.totp_enabled_at:
        if not body.code:
            raise ApiError(422, 'TWO_FACTOR_CODE_REQUIRED', 'Enter your authenticator code.', [{'field': 'code', 'message': 'Required.'}])
        used = second_factor(request, row, body.code)
        used()
    found = account_closure.blockers(db, row.id)
    if found:
        db.rollback()
        raise ApiError(409, 'ACCOUNT_HAS_OPEN_ITEMS', 'Finish or settle these first: ' + ' '.join(b['message'] for b in found),
                       [{'field': b['code'], 'message': b['message']} for b in found])
    row.account_status = 'DEACTIVATED'
    row.deletion_requested_at = datetime.now(timezone.utc) if delete else None
    row.auth_version += 1                       # every token of this person stops working
    touch(row); db.commit()
    for sid in request.app.state.store.sessions_of(row.id):
        request.app.state.store.revoke(sid)
    session_cookie.forget(request)
    logger.info('account %s user=%s trace=%s', 'delete-request' if delete else 'deactivated', row.id, request.state.trace_id)
    return row


@router.post('/users/me/deactivate')
def deactivate(body: CloseAccount, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    close(request, db, user, body, delete=False)
    return {'status': 'DEACTIVATED', 'message': 'Your account is deactivated. Sign in again any time to bring it back.'}


@router.post('/users/me/delete-request')
def delete_request(body: CloseAccount, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    row = close(request, db, user, body, delete=True)
    after = row.deletion_requested_at + timedelta(days=account_closure.DELETE_AFTER_DAYS)
    return {'status': 'DEACTIVATED', 'delete_after': after.isoformat(),
            'message': f'Your account is deactivated and will be deleted in {account_closure.DELETE_AFTER_DAYS} days. Sign in before then to cancel.'}
