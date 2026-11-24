import logging
import secrets
import time
from datetime import datetime, timezone, timedelta
from uuid import UUID
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.dependencies.database import get_db
from app.core.errors import ApiError, unauthorized
from app.models import User, UserRole
from app.schemas import RegisterRequest, LoginRequest, RefreshRequest, RoleRequest, UserResponse, RoleResponse, RolesResponse, TokenResponse
from app.schemas.profile import ProfileUpdate
from app.core.security import hasher, verify_password, DUMMY_HASH, decode_token, issue_tokens
from app.core import session_cookie

router = APIRouter(prefix='/api/v1')
logger = logging.getLogger('travelly.audit')


def session_meta(request: Request) -> dict:
    """What the sessions list shows: a device label and a coarse address."""
    agent = (request.headers.get('user-agent') or '')[:300]
    low = agent.lower()
    system = next((name for key, name in (
        ('windows', 'Windows'), ('android', 'Android'), ('iphone', 'iPhone'),
        ('ipad', 'iPad'), ('mac os', 'Mac'), ('linux', 'Linux')) if key in low), None)
    browser = next((name for key, name in (
        ('edg/', 'Edge'), ('opr/', 'Opera'), ('chrome/', 'Chrome'),
        ('firefox/', 'Firefox'), ('safari/', 'Safari')) if key in low), None)
    forwarded = request.headers.get('x-forwarded-for', '')
    host = forwarded.split(',')[0].strip() if forwarded else (request.client.host if request.client else '')
    parts = host.split('.')
    hint = '.'.join(parts[:2]) + '.x.x' if len(parts) == 4 else (host.split(':')[0] + ':x' if ':' in host else '')
    return {'device': ' on '.join(value for value in (browser, system) if value) or 'Unknown device', 'ip_hint': hint}


def touch(row):
    # PostgreSQL and the Windows clock can differ by sub-millisecond precision.
    # Never move an audit timestamp behind its persisted creation/update time.
    row.updated_at = max(datetime.now(timezone.utc), row.created_at, row.updated_at)
    row.version += 1


def allowed_account(user):
    if user is None or user.account_status not in ('PENDING_VERIFICATION', 'ACTIVE'):
        raise ApiError(403, 'ACCOUNT_RESTRICTED', 'This account is not available for this action.')


def current(request: Request, db: Session = Depends(get_db)):
    header = request.headers.get('authorization', '')
    scheme, _, token = header.partition(' ')
    if scheme.lower() != 'bearer' or not token or len(token) > 2048:
        raise unauthorized()
    claims = decode_token(token, request.app.state.settings)
    store = request.app.state.store
    store.get(claims['sid'], claims['sub'])
    request.state.auth_claims = claims
    path = request.url.path
    if path.startswith(('/api/v1/admin/', '/api/v1/documents')):
        group, limit, seconds = ('files', 30, 60) if path.endswith('/file') else ('review', 30, 60) if request.method == 'PATCH' else ('upload', 10, 900) if request.method == 'POST' else ('metadata', 120, 60)
        store.rate(group + '-session:' + claims['sid'], limit, seconds)
    else:
        store.rate('profile-session:' + claims['sid'], 120, 60)
    user = db.get(User, UUID(claims['sub']))
    allowed_account(user)
    if claims.get('av', 0) != user.auth_version:
        raise unauthorized()
    if user.email_login_required and not user.email_verified_at:
        raise ApiError(403, 'EMAIL_VERIFICATION_REQUIRED', 'Verify your email before signing in.')
    return user


def require_role(db, user, role):
    allowed_account(user)
    if not db.scalar(select(UserRole.id).where(UserRole.user_id == user.id, UserRole.role_code == role, UserRole.approval_status == 'APPROVED')):
        raise ApiError(403, 'ROLE_NOT_APPROVED', 'An approved role is required.')


def profile(db, user):
    roles = db.scalars(select(UserRole.role_code).where(UserRole.user_id == user.id, UserRole.approval_status == 'APPROVED').order_by(UserRole.role_code)).all()
    data = {name: getattr(user, name) for name in UserResponse.model_fields if name != 'approved_roles'}
    return UserResponse(**data, approved_roles=list(roles))


@router.post('/auth/register', status_code=201, tags=['Auth'])
def register(body: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    encoded = hasher.hash(body.password)
    for _ in range(3):
        try:
            need_verify = request.app.state.settings.require_email_verification
            user = User(public_user_reference='USR-' + secrets.token_hex(8).upper(), password_hash=encoded,
                        full_name=body.full_name, email=body.email, phone_e164=body.phone_e164,
                        preferred_language=body.preferred_language, email_login_required=need_verify,
                        email_verified_at=None if need_verify else datetime.now(timezone.utc),
                        account_status='PENDING_VERIFICATION' if need_verify else 'ACTIVE',
                        terms_accepted_at=datetime.now(timezone.utc))
            db.add(user)
            db.flush()
            db.add(UserRole(user_id=user.id, role_code='PASSENGER', approval_status='APPROVED',
                            requested_at=user.created_at, approved_at=user.created_at))
            db.commit()
            logger.info('registration user=%s trace=%s', user.id, request.state.trace_id)
            from app.api.routers.auth_extension import verification_result
            return {**profile(db, user).model_dump(), **verification_result(request, user, send=True, journey=body.journey, sign_in=True)}
        except IntegrityError as exc:
            db.rollback()
            constraint = getattr(getattr(exc.orig, 'diag', None), 'constraint_name', '')
            if constraint == 'uq_users_public_reference':
                continue
            if constraint in ('uq_users_email', 'uq_users_phone'):
                field = 'email' if constraint == 'uq_users_email' else 'phone_e164'
                message = 'This email is already registered. Sign in or use password recovery.' if field == 'email' else 'This mobile number is already registered. Sign in to your existing account.'
                raise ApiError(409, 'CONTACT_ALREADY_REGISTERED', message, [{'field': field, 'code': 'duplicate', 'message': message}]) from None
            raise
    raise ApiError(500, 'INTERNAL_ERROR', 'Unable to create an account. Please try again.')


@router.post('/auth/login', tags=['Auth'])
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    store, settings = request.app.state.store, request.app.state.settings
    store.check_lock(body.identifier)
    column = User.email if '@' in body.identifier else User.phone_e164
    user = db.scalar(select(User).where(column == body.identifier).with_for_update())
    now = datetime.now(timezone.utc)
    # Recheck after the database lock to serialize concurrent attempts for one account.
    store.check_lock(body.identifier)
    if user and user.locked_until and user.locked_until > now:
        store.limited((user.locked_until - now).total_seconds())
    valid = verify_password(body.password, user.password_hash if user else DUMMY_HASH)
    if not valid or not user or user.account_status not in ('ACTIVE', 'PENDING_VERIFICATION', 'DEACTIVATED'):
        count = store.failure(body.identifier)
        if user:
            user.failed_login_count = count
            if count >= 5:
                user.locked_until = now + timedelta(minutes=15)
            touch(user)
            db.commit()
        if count >= 5:
            store.limited(900)
        raise ApiError(401, 'INVALID_CREDENTIALS', 'Invalid credentials or account unavailable.', headers={'WWW-Authenticate': 'Bearer'})
    if user.email_login_required and not user.email_verified_at:
        store.clear_failures(body.identifier)
        from app.api.routers.auth_extension import verification_result
        return verification_result(request, user, journey=body.journey, sign_in=True)
    if user.totp_enabled_at:
        from app.api.routers.account_security_api import challenge_for
        user.failed_login_count, user.locked_until = 0, None
        touch(user)
        db.commit()
        store.clear_failures(body.identifier)
        return challenge_for(request, user, body.remember_me)
    from app.api.routers.account_security_api import reactivate
    welcome = reactivate(user)
    user.failed_login_count, user.locked_until, user.last_login_at = 0, None, now
    if hasher.check_needs_rehash(user.password_hash):
        user.password_hash = hasher.hash(body.password)
    touch(user)
    db.commit()
    store.clear_failures(body.identifier)
    tokens, sid, expires = issue_tokens(user.id, settings, auth_version=user.auth_version, remember=body.remember_me)
    store.create(sid, user.id, tokens['refresh_token'], expires, session_meta(request))
    session_cookie.keep(request, tokens, body.remember_me)
    logger.info('login user=%s session=%s trace=%s', user.id, sid, request.state.trace_id)
    return {**tokens, **welcome}


@router.post('/auth/refresh', response_model=TokenResponse, tags=['Auth'])
def refresh(body: RefreshRequest, request: Request, db: Session = Depends(get_db)):
    token = body.refresh_token or session_cookie.read(request)
    try:
        if not token:
            raise unauthorized('INVALID_REFRESH_TOKEN')
        return renew(token, request, db)
    except ApiError as exc:
        # A refused token's cookie is cleared so the browser stops offering it. Busy (429) or unavailable (503)
        # answers keep it, so a short outage does not sign anyone out.
        if exc.status in (401, 403):
            session_cookie.forget(request)
        raise


def renew(token, request, db):
    store, settings = request.app.state.store, request.app.state.settings
    claims = decode_token(token, settings, 'refresh')
    try:
        record = store.get(claims['sid'], claims['sub'])
    except ApiError:
        raise unauthorized('INVALID_REFRESH_TOKEN') from None
    store.rate('refresh-session:' + claims['sid'], 20, 60)
    user = db.get(User, UUID(claims['sub']))
    if user is None or user.account_status not in ('ACTIVE', 'PENDING_VERIFICATION'):
        store.revoke(claims['sid'])
        raise ApiError(403, 'ACCOUNT_RESTRICTED', 'This account is not available for this action.')
    if claims.get('av', 0) != user.auth_version or (user.email_login_required and not user.email_verified_at):
        store.revoke(claims['sid'])
        raise unauthorized('INVALID_REFRESH_TOKEN')
    remember = bool(claims.get('rm'))
    tokens, _, _ = issue_tokens(user.id, settings, claims['sid'], int(record['exp']), auth_version=user.auth_version, remember=remember)
    store.rotate(claims['sid'], user.id, token, tokens['refresh_token'])
    session_cookie.keep(request, tokens, remember)
    return tokens


@router.post('/auth/logout', status_code=204, tags=['Auth'])
def logout(body: RefreshRequest, request: Request):
    header = request.headers.get('authorization', '')
    scheme, _, token = header.partition(' ')
    if scheme.lower() != 'bearer' or not token:
        raise unauthorized()
    session_cookie.forget(request)
    claims = decode_token(token, request.app.state.settings)
    refresh_token = body.refresh_token or session_cookie.read(request)
    if not refresh_token:
        raise unauthorized('INVALID_SESSION')
    refresh_claims = decode_token(refresh_token, request.app.state.settings, 'refresh')
    if (claims['sid'], claims['sub']) != (refresh_claims['sid'], refresh_claims['sub']):
        raise unauthorized('INVALID_SESSION')
    request.app.state.store.logout(claims['sid'], claims['sub'], refresh_token)
    logger.info('logout user=%s session=%s trace=%s', claims['sub'], claims['sid'], request.state.trace_id)
    return Response(status_code=204)


@router.get('/users/me', response_model=UserResponse, tags=['Users'])
def me(user: User = Depends(current), db: Session = Depends(get_db)):
    return profile(db, user)


@router.patch('/users/me', response_model=UserResponse, tags=['Users'])
def update_profile(body: ProfileUpdate, request: Request, user: User = Depends(current), db: Session = Depends(get_db)):
    from app.services.profile_image import normalize_avatar
    # Any user with at least one approved role may edit their own profile (name, mobile, photo).
    user = db.scalar(select(User).where(User.id == user.id).with_for_update().execution_options(populate_existing=True))
    allowed_account(user)
    if not db.scalar(select(UserRole.id).where(UserRole.user_id == user.id, UserRole.approval_status == 'APPROVED')):
        raise ApiError(403, 'ROLE_NOT_APPROVED', 'An approved role is required.')
    if request.state.auth_claims.get('av', 0) != user.auth_version:
        raise unauthorized()
    request.app.state.store.get(request.state.auth_claims['sid'], str(user.id))
    if body.version != user.version:
        raise ApiError(409, 'PROFILE_CHANGED', 'Your profile changed. Reload your profile before saving again.')
    if body.phone_e164 != user.phone_e164:
        # A changed number must never inherit verification from the old number.
        # Preserve the existing ACTIVE-account constraint and security workflows.
        if user.account_status == 'ACTIVE' and not user.email_verified_at:
            raise ApiError(409, 'EMAIL_VERIFICATION_REQUIRED', 'Verify your email in Settings before changing your mobile number.')
        user.phone_verified_at = None
    # Unchanged legacy public-safe image URLs are retained; new values must be raster uploads.
    avatar = user.profile_image_url if body.profile_image_url == user.profile_image_url else normalize_avatar(body.profile_image_url)
    user.full_name, user.phone_e164, user.profile_image_url = body.full_name, body.phone_e164, avatar
    user.updated_by = user.id
    touch(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if getattr(getattr(exc.orig, 'diag', None), 'constraint_name', '') == 'uq_users_phone':
            raise ApiError(409, 'CONTACT_ALREADY_REGISTERED', 'This mobile number is already registered.', [{'field':'phone_e164','code':'duplicate','message':'This mobile number is already registered.'}]) from None
        raise
    return profile(db, user)


@router.get('/users/me/roles', response_model=RolesResponse, tags=['Roles'])
def my_roles(user: User = Depends(current), db: Session = Depends(get_db)):
    rows = db.scalars(select(UserRole).where(UserRole.user_id == user.id).order_by(UserRole.role_code)).all()
    return RolesResponse(items=[RoleResponse.model_validate(row) for row in rows])


@router.post('/users/me/role-requests', status_code=201, response_model=RoleResponse, tags=['Roles'])
def apply_role(body: RoleRequest, request: Request, user: User = Depends(current), db: Session = Depends(get_db)):
    from app.services.review_audit import decision_evidence
    user_id = user.id
    try:
        # A first PENDING request has no destructive history mutation and keeps its existing Auth boundary.
        return _apply_role(body, request, user, db, decision_evidence, history_guard=False)
    except _HistoryRequired:
        db.rollback()  # release identity locks BEFORE acquiring the cross-worker coordinator
        with request.app.state.audit.coordinated():
            return _apply_role(body, request, db.get(User, user_id), db, decision_evidence, history_guard=True)


class _HistoryRequired(Exception):
    pass


def _apply_role(body, request, user, db, decision_evidence, history_guard):
    # Lock the identity, including when no membership exists, to avoid duplicate applications.
    user = db.scalar(select(User).where(User.id == user.id).with_for_update().execution_options(populate_existing=True))
    # Recheck eligibility after the lock, including a restriction that committed
    # while this request waited. Applications require retained Passenger access.
    require_role(db, user, 'PASSENGER')
    claims = request.state.auth_claims
    if claims.get('av', 0) != user.auth_version: raise unauthorized()
    request.app.state.store.get(claims['sid'], claims['sub'])
    row = db.scalar(select(UserRole).where(UserRole.user_id == user.id, UserRole.role_code == body.role_code))
    if row and row.approval_status != 'REJECTED':
        raise ApiError(409, 'ROLE_ALREADY_REQUESTED', 'This role is already requested, approved or suspended.')
    if row:
        if not history_guard:
            raise _HistoryRequired()
        evidence, old_version = decision_evidence(row), row.version
        logger.info('role_resubmitted user=%s role=%s prior_status=%s trace=%s', user.id, row.role_code, row.approval_status, request.state.trace_id)
        row.approval_status, row.requested_at = 'PENDING', datetime.now(timezone.utc)
        row.approved_at = row.approved_by = row.rejection_reason = row.suspended_at = row.suspension_reason = None
        touch(row)
        row.updated_by = user.id
        result = RoleResponse.model_validate(row)
        request.app.state.audit.commit(db, actor=user.id,
            target={'resource': 'user_roles', 'id': str(row.id), 'applicant': str(user.id), 'role': row.role_code},
            previous_status='REJECTED', new_status='PENDING', previous_version=old_version, new_version=row.version,
            full_reason=evidence['rejection_reason'], previous_decision_evidence=evidence, trace_id=request.state.trace_id)
        return result
    else:
        row = UserRole(user_id=user.id, role_code=body.role_code, approval_status='PENDING', created_by=user.id)
        db.add(row)
    db.commit()
    logger.info('role_requested user=%s role=%s trace=%s', user.id, row.role_code, request.state.trace_id)
    return RoleResponse.model_validate(row)
