"""Accepted email verification, Google account completion/linking and recovery."""
import secrets
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, Request
from pydantic import Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .api import current, allowed_account, profile, touch
from .database import get_db
from .errors import ApiError, unauthorized
from .models import User, UserRole
from .schemas import RequestModel, email_address, phone_number, clean_text, new_password
from .security import hasher, verify_password, issue_tokens

router = APIRouter(prefix='/api/v1', tags=['Auth extension'])
DELIVERY = {
    'captured': 'Development email captured locally. No message was sent to an inbox.',
    'provider_accepted': 'The email provider accepted the message. Check your inbox and spam folder; delivery is not yet confirmed.',
    'failed': 'We could not submit the email. Your account is saved; please try Resend later.',
    'daily_limit': 'The email sending limit has been reached. Your account is saved; please try again later.',
    'not_sent': 'Verify your email before signing in. Use your existing link or request another one.',
}


class Ticket(RequestModel):
    ticket: str = Field(min_length=30, max_length=100)


class LinkToken(RequestModel):
    token: str = Field(min_length=30, max_length=100)


class GoogleToken(RequestModel):
    credential: str = Field(min_length=1, max_length=6000)
    challenge: str = Field(min_length=30, max_length=100)


class GoogleLink(GoogleToken):
    confirm: Literal[True]
    current_password: str | None = Field(default=None, max_length=128)

    @field_validator('confirm', mode='before')
    @classmethod
    def confirm_true(cls, value):
        if value is not True: raise ValueError()
        return value


class GoogleComplete(Ticket):
    full_name: str = Field(min_length=1, max_length=150)
    phone_e164: str
    preferred_language: Literal['en', 'ta', 'si'] = 'en'
    accept_terms: Literal[True]

    @field_validator('accept_terms', mode='before')
    @classmethod
    def terms_true(cls, value):
        if value is not True: raise ValueError()
        return value

    @field_validator('full_name')
    @classmethod
    def name(cls, value):
        value = clean_text(value.strip())
        if not value: raise ValueError()
        return value

    @field_validator('phone_e164')
    @classmethod
    def phone(cls, value): return phone_number(value)


class EmailRequest(RequestModel):
    email: str
    @field_validator('email')
    @classmethod
    def email_valid(cls, value): return email_address(value)


class ResetPassword(LinkToken):
    password: str
    @field_validator('password')
    @classmethod
    def password_valid(cls, value): return new_password(value)


def bound(user):
    return {'uid': str(user.id), 'email': str(user.email), 'av': user.auth_version}


def verification_result(request, user, send=False):
    state = request.app.state.auth_state
    ticket = state.issue('resend', bound(user), ttl=86400)
    delivery = send_link(request, user, 'verify') if send else 'not_sent'
    return {'status': 'verification_required', 'verification_required': True,
            'verification_ticket': ticket, 'email_delivery': delivery, 'message': DELIVERY[delivery]}


def send_link(request, user, purpose):
    store, state = request.app.state.store, request.app.state.auth_state
    store.rate('email-minute:' + purpose + ':' + str(user.id), 1, 60)
    store.rate('email-hour:' + purpose + ':' + str(user.id), 5, 3600)
    token = state.issue(purpose, bound(user), subject=user.id)
    result = request.app.state.mailer.send(str(user.email), token, purpose)
    if result not in ('captured', 'provider_accepted'):
        state.discard(purpose, token)
    return result


def invalid_link():
    return ApiError(400, 'INVALID_OR_EXPIRED_LINK', 'This link is invalid, expired or already used. Request a new link.')


def linked_user(db, record):
    if not record: raise invalid_link()
    user = db.scalar(select(User).where(User.id == UUID(record['uid'])).with_for_update())
    if not user or str(user.email) != record['email'] or user.auth_version != record['av']:
        raise invalid_link()
    return user


@router.post('/auth/email/resend')
def resend(body: Ticket, request: Request, db: Session = Depends(get_db)):
    user = linked_user(db, request.app.state.auth_state.read('resend', body.ticket))
    allowed_account(user)
    if user.email_verified_at:
        return {'status': 'verified', 'message': 'Your email is already verified. You can sign in.'}
    delivery = send_link(request, user, 'verify')
    return {'status': 'verification_required', 'email_delivery': delivery, 'message': DELIVERY[delivery]}


@router.post('/users/me/email-verification')
def request_verification(request: Request, user=Depends(current)):
    if user.email_verified_at:
        return {'status': 'verified', 'message': 'Your email is already verified.'}
    if not user.email:
        raise ApiError(409, 'EMAIL_NOT_AVAILABLE', 'This account has no email address. Email recovery and verification are unavailable.')
    return verification_result(request, user, send=True)


@router.post('/auth/email/verify')
def verify_email(body: LinkToken, request: Request, db: Session = Depends(get_db)):
    state = request.app.state.auth_state
    user = linked_user(db, state.read('verify', body.token))
    allowed_account(user)
    if user.email_verified_at or not state.read('verify', body.token, consume=True): raise invalid_link()
    user.email_verified_at = datetime.now(timezone.utc)
    if user.account_status == 'PENDING_VERIFICATION': user.account_status = 'ACTIVE'
    touch(user); db.commit()
    return {'status': 'verified', 'message': 'Your email is verified. You can now sign in.'}


@router.post('/auth/password/forgot', status_code=202)
def forgot_password(body: EmailRequest, request: Request, db: Session = Depends(get_db)):
    # The same response for absent/unverified/restricted users, recipient throttles and provider failures.
    response = {'message': 'If this email belongs to an eligible account with a verified email, we will attempt to send a reset link. Delivery is not guaranteed. Check your inbox and spam folder.'}
    store = request.app.state.store
    try:
        store.rate('forgot-email:' + body.email, 3, 3600)
        user = db.scalar(select(User).where(User.email == body.email))
        if user and user.email_verified_at and user.account_status in ('ACTIVE', 'PENDING_VERIFICATION'):
            send_link(request, user, 'reset')
    except ApiError:
        pass
    return response


@router.post('/auth/password/reset')
def reset_password(body: ResetPassword, request: Request, db: Session = Depends(get_db)):
    state = request.app.state.auth_state
    encoded = hasher.hash(body.password)
    user = linked_user(db, state.read('reset', body.token))
    allowed_account(user)
    if not user.email_verified_at or not state.read('reset', body.token, consume=True): raise invalid_link()
    user.password_hash = encoded
    user.auth_version += 1
    user.failed_login_count, user.locked_until = 0, None
    touch(user); db.commit()
    for identifier in (user.email, user.phone_e164):
        if identifier: request.app.state.store.clear_failures(str(identifier))
    return {'message': 'Your password has been changed and previous sessions have been signed out. Sign in again.'}


def challenge(request, user=None):
    settings = request.app.state.settings
    if not settings.google_client_id:
        raise ApiError(503, 'GOOGLE_NOT_CONFIGURED', 'Google sign-in is not configured yet. Use email and password for now.')
    nonce = secrets.token_urlsafe(32)
    data = {'nonce': nonce, 'uid': str(user.id) if user else None,
            'sid': request.state.auth_claims['sid'] if user else None}
    token = request.app.state.auth_state.issue('google-challenge', data, ttl=300)
    return {'challenge': token, 'nonce': nonce, 'client_id': settings.google_client_id}


@router.post('/auth/google/challenge')
def sign_in_challenge(request: Request): return challenge(request)


@router.post('/users/me/google/challenge')
def link_challenge(request: Request, user=Depends(current)): return challenge(request, user)


def google_identity(body, request, user=None):
    state = request.app.state.auth_state
    data = state.read('google-challenge', body.challenge)
    uid, sid = (str(user.id), request.state.auth_claims['sid']) if user else (None, None)
    if not data or (data['uid'], data['sid']) != (uid, sid):
        raise ApiError(401, 'INVALID_GOOGLE_CHALLENGE', 'Start Google sign-in again.')
    result = request.app.state.google.verify(body.credential, data['nonce'])
    if not state.read('google-challenge', body.challenge, consume=True):
        raise ApiError(401, 'INVALID_GOOGLE_CHALLENGE', 'Start Google sign-in again.')
    return result


def session_for(request, db, user):
    allowed_account(user)
    if user.email_login_required and not user.email_verified_at:
        return verification_result(request, user)
    user.last_login_at = datetime.now(timezone.utc); touch(user); db.commit()
    tokens, sid, expires = issue_tokens(user.id, request.app.state.settings, auth_version=user.auth_version)
    request.app.state.store.create(sid, user.id, tokens['refresh_token'], expires)
    return tokens


@router.post('/auth/google')
def google_sign_in(body: GoogleToken, request: Request, db: Session = Depends(get_db)):
    identity = google_identity(body, request)
    user = db.scalar(select(User).where(User.external_auth_provider == 'GOOGLE', User.external_auth_subject == identity['subject']).with_for_update())
    if user:
        return session_for(request, db, user)
    if db.scalar(select(User.id).where(User.email == identity['email'])):
        return {'status': 'link_required', 'message': 'A Travelly account already uses this email. Sign in using its existing method, then connect Google in Profile. If you cannot sign in, use verified-email password recovery.'}
    ticket = request.app.state.auth_state.issue('google-complete', identity, ttl=600)
    return {'status': 'completion_required', 'ticket': ticket, 'email': identity['email'], 'full_name': identity['name']}


@router.post('/auth/google/complete', status_code=201)
def google_complete(body: GoogleComplete, request: Request, db: Session = Depends(get_db)):
    state = request.app.state.auth_state
    identity = state.read('google-complete', body.ticket, consume=True)
    if not identity: raise invalid_link()
    now = datetime.now(timezone.utc)
    user = User(public_user_reference='USR-' + secrets.token_hex(8).upper(), full_name=body.full_name,
        email=identity['email'], phone_e164=body.phone_e164, preferred_language=body.preferred_language,
        password_hash=None, external_auth_provider='GOOGLE', external_auth_subject=identity['subject'],
        email_login_required=True, terms_accepted_at=now,
        email_verified_at=now if identity['authoritative'] else None,
        account_status='ACTIVE' if identity['authoritative'] else 'PENDING_VERIFICATION')
    try:
        db.add(user); db.flush()
        db.add(UserRole(user_id=user.id, role_code='PASSENGER', approval_status='APPROVED', approved_at=user.created_at))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ApiError(409, 'CONTACT_ALREADY_REGISTERED', 'This email, phone or Google identity is already registered. Sign in to your existing account; no accounts were linked.') from None
    if not user.email_verified_at:
        return verification_result(request, user, send=True)
    return session_for(request, db, user)


@router.get('/users/me/auth-methods')
def methods(user=Depends(current)):
    return {'password': bool(user.password_hash), 'google': user.external_auth_provider == 'GOOGLE', 'email_verified': bool(user.email_verified_at)}


@router.post('/users/me/google')
def connect_google(body: GoogleLink, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    request.app.state.store.rate('google-link:' + str(user.id), 5, 900)
    user = db.scalar(select(User).where(User.id == user.id).with_for_update().execution_options(populate_existing=True))
    allowed_account(user)
    if request.state.auth_claims.get('av', 0) != user.auth_version: raise unauthorized()
    if user.password_hash and not verify_password(body.current_password or '', user.password_hash):
        raise ApiError(400, 'PASSWORD_CONFIRMATION_FAILED', 'Your current password could not be confirmed.')
    identity = google_identity(body, request, user)
    if user.external_auth_subject and user.external_auth_subject != identity['subject']:
        raise ApiError(409, 'GOOGLE_ALREADY_LINKED', 'This Travelly account already has a different Google account connected.')
    existing = db.scalar(select(User.id).where(User.external_auth_provider == 'GOOGLE', User.external_auth_subject == identity['subject']))
    if existing and existing != user.id:
        raise ApiError(409, 'GOOGLE_ALREADY_LINKED', 'This Google identity is already connected to another account.')
    user.external_auth_provider, user.external_auth_subject = 'GOOGLE', identity['subject']
    touch(user)
    try: db.commit()
    except IntegrityError:
        db.rollback()
        raise ApiError(409, 'GOOGLE_ALREADY_LINKED', 'This Google identity is already connected to another account.') from None
    return {'message': 'Google is connected to this same Travelly account. Your roles and records are unchanged.'}
