from datetime import datetime
from typing import Literal
from uuid import UUID
import unicodedata
import re
import phonenumbers
from email_validator import validate_email, EmailNotValidError
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MIN_PASSWORD_LENGTH = 12


def clean_text(value):
    if any(unicodedata.category(c).startswith('C') for c in value):
        raise ValueError('Control characters are not allowed.')
    return value


def email_address(value):
    value = value.strip().lower()
    if not 3 <= len(value) <= 254 or any(c.isspace() for c in value):
        raise ValueError('Enter a valid email address.')
    try:
        return validate_email(value, check_deliverability=False).normalized.lower()
    except EmailNotValidError:
        raise ValueError('Enter a valid email address.') from None


def password_requirements(value):
    failures = []
    if len(value) < 12: failures.append('Use at least 12 characters.')
    if len(value) > 128: failures.append('Use at most 128 characters.')
    if not any(unicodedata.category(c) == 'Lu' for c in value): failures.append('Add an uppercase letter.')
    if not any(unicodedata.category(c) == 'Ll' for c in value): failures.append('Add a lowercase letter.')
    if not any(unicodedata.category(c) == 'Nd' for c in value): failures.append('Add a number.')
    if not any(unicodedata.category(c)[0] in ('P', 'S') for c in value): failures.append('Add a symbol.')
    if any(c.isspace() for c in value): failures.append('Remove all whitespace.')
    if any(unicodedata.category(c).startswith('C') for c in value): failures.append('Remove control characters.')
    return failures


def new_password(value):
    if password_requirements(value):
        raise ValueError('Password requirements not met.')
    return value


def phone_number(value):
    value = clean_text(value).strip()
    if not value.startswith('+'):
        raise ValueError('Include the international country code, for example +94.')
    try:
        if not re.fullmatch(r'\+[0-9 ()-]+', value):
            raise ValueError()
        digits = re.sub(r'[^0-9]', '', value)
        if len(digits) > 15:
            raise ValueError()
        phone = phonenumbers.parse(value, None)
        normalized = phonenumbers.format_number(phone, phonenumbers.PhoneNumberFormat.E164)
        # Only display separators may be removed. Never silently repair a
        # repeated calling code, national trunk prefix, extension or suffix.
        if phone.extension or not phonenumbers.is_valid_number(phone) or normalized != '+' + digits:
            raise ValueError()
        return normalized
    except (ValueError, phonenumbers.NumberParseException):
        raise ValueError('Enter a valid international phone number.') from None


class RequestModel(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class RegisterRequest(RequestModel):
    full_name: str = Field(min_length=1, max_length=150)
    email: str
    phone_e164: str
    accept_terms: Literal[True]
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=128)
    preferred_language: Literal['en', 'ta', 'si'] = 'en'

    @field_validator('accept_terms', mode='before')
    @classmethod
    def terms_true(cls, value):
        if value is not True: raise ValueError()
        return value

    @field_validator('full_name', mode='before')
    @classmethod
    def name(cls, v):
        return clean_text(v.strip()) if isinstance(v, str) else v

    @field_validator('email')
    @classmethod
    def email_valid(cls, v):
        return email_address(v) if v is not None else v

    @field_validator('phone_e164')
    @classmethod
    def phone_valid(cls, v):
        return phone_number(v) if v is not None else v

    @field_validator('password')
    @classmethod
    def password_valid(cls, v):
        return new_password(v)

    @model_validator(mode='after')
    def contact(self):
        if self.email is None and self.phone_e164 is None:
            raise ValueError('Provide an email address or international phone number.')
        return self


class LoginRequest(RequestModel):
    identifier: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=128)

    @field_validator('identifier')
    @classmethod
    def identifier_valid(cls, v):
        return email_address(v) if '@' in v else phone_number(v)


class RefreshRequest(RequestModel):
    refresh_token: str = Field(min_length=1, max_length=2048)


class RoleRequest(RequestModel):
    role_code: Literal['OWNER', 'DRIVER']
    # The document module is excluded. Never pretend supplied IDs were verified.
    supporting_document_ids: list[UUID] = Field(default_factory=list, max_length=0)


class ResponseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserResponse(ResponseModel):
    id: UUID
    public_user_reference: str
    full_name: str
    display_name: str | None
    profile_image_url: str | None
    email: str | None
    phone_e164: str | None
    preferred_language: str
    timezone: str
    account_status: str
    email_verified_at: datetime | None
    phone_verified_at: datetime | None
    approved_roles: list[str]
    created_at: datetime
    updated_at: datetime
    version: int


class RoleResponse(ResponseModel):
    id: UUID
    role_code: str
    approval_status: str
    requested_at: datetime
    approved_at: datetime | None
    rejection_reason: str | None
    suspended_at: datetime | None
    suspension_reason: str | None
    version: int


class RolesResponse(BaseModel):
    items: list[RoleResponse]


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = 'bearer'
    expires_in: int
    refresh_expires_in: int
