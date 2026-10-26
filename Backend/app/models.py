import uuid
from datetime import datetime
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import CITEXT, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    public_user_reference: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[str | None] = mapped_column(CITEXT, nullable=True)
    phone_e164: Mapped[str | None] = mapped_column(String(20), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_auth_provider: Mapped[str | None] = mapped_column(String(40))
    external_auth_subject: Mapped[str | None] = mapped_column(String(255))
    email_login_required: Mapped[bool] = mapped_column(Boolean, server_default=text('true'))
    auth_version: Mapped[int] = mapped_column(Integer, server_default='0')
    terms_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100))
    profile_image_url: Mapped[str | None] = mapped_column(Text)
    preferred_language: Mapped[str] = mapped_column(String(2), server_default='en')
    timezone: Mapped[str] = mapped_column(String(64), server_default='Asia/Colombo')
    account_status: Mapped[str] = mapped_column(String(24), server_default='PENDING_VERIFICATION')
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    phone_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_login_count: Mapped[int] = mapped_column(Integer, server_default='0')
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text('now()'))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text('now()'))
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', name='fk_users_created_by', ondelete='RESTRICT', onupdate='RESTRICT'))
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', name='fk_users_updated_by', ondelete='RESTRICT', onupdate='RESTRICT'))
    version: Mapped[int] = mapped_column(Integer, server_default='1')
    __table_args__ = (
        UniqueConstraint('public_user_reference', name='uq_users_public_reference'),
        UniqueConstraint('email', name='uq_users_email'), UniqueConstraint('phone_e164', name='uq_users_phone'),
        UniqueConstraint('external_auth_provider', 'external_auth_subject', name='uq_users_external_identity'),
        CheckConstraint("(external_auth_provider IS NULL AND external_auth_subject IS NULL) OR (external_auth_provider IS NOT NULL AND external_auth_provider = 'GOOGLE' AND external_auth_subject IS NOT NULL AND char_length(external_auth_subject) BETWEEN 1 AND 255)", name='ck_users_provider_pair'),
        CheckConstraint('password_hash IS NOT NULL OR external_auth_provider IS NOT NULL', name='ck_users_auth_method'),
        CheckConstraint('auth_version >= 0', name='ck_users_auth_version'),
        CheckConstraint("public_user_reference ~ '^USR-[0-9A-F]{16}$'", name='ck_users_reference'),
        CheckConstraint('email IS NOT NULL OR phone_e164 IS NOT NULL', name='ck_users_contact'),
        CheckConstraint("email IS NULL OR (email::text = lower(btrim(email::text)) AND char_length(email::text) BETWEEN 3 AND 254 AND email::text !~ '[[:space:]]')", name='ck_users_email'),
        CheckConstraint("phone_e164 IS NULL OR phone_e164 ~ '^[+][1-9][0-9]{1,14}$'", name='ck_users_phone'),
        CheckConstraint('char_length(password_hash) > 0', name='ck_users_password_hash'),
        CheckConstraint('full_name = btrim(full_name) AND char_length(full_name) BETWEEN 1 AND 150', name='ck_users_full_name'),
        CheckConstraint('display_name IS NULL OR (display_name = btrim(display_name) AND char_length(display_name) BETWEEN 1 AND 100)', name='ck_users_display_name'),
        CheckConstraint("preferred_language IN ('en','ta','si')", name='ck_users_language'),
        CheckConstraint("timezone = 'Asia/Colombo'", name='ck_users_timezone'),
        CheckConstraint("account_status IN ('PENDING_VERIFICATION','ACTIVE','SUSPENDED','BLOCKED','CLOSED')", name='ck_users_account_status'),
        CheckConstraint('email_verified_at IS NULL OR email IS NOT NULL', name='ck_users_verified_email'),
        CheckConstraint('phone_verified_at IS NULL OR phone_e164 IS NOT NULL', name='ck_users_verified_phone'),
        CheckConstraint("account_status <> 'ACTIVE' OR email_verified_at IS NOT NULL OR phone_verified_at IS NOT NULL", name='ck_users_activation'),
        CheckConstraint('failed_login_count >= 0', name='ck_users_failures'),
        CheckConstraint('version >= 1', name='ck_users_version'),
        CheckConstraint('updated_at >= created_at', name='ck_users_timestamps'),
        Index('ix_users_account_status', 'account_status'), Index('ix_users_created_at', 'created_at'),
        Index('ix_users_created_by', 'created_by', postgresql_where=text('created_by IS NOT NULL')),
        Index('ix_users_updated_by', 'updated_by', postgresql_where=text('updated_by IS NOT NULL')),
        {'comment': 'Shared identity; contact verification is independent of role approval.'},
    )


class UserRole(Base):
    __tablename__ = 'user_roles'
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', name='fk_user_roles_user', ondelete='RESTRICT', onupdate='RESTRICT'))
    role_code: Mapped[str] = mapped_column(String(9))
    approval_status: Mapped[str] = mapped_column(String(9), server_default='PENDING')
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text('now()'))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', name='fk_user_roles_approved_by', ondelete='RESTRICT', onupdate='RESTRICT'))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    suspended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    suspension_reason: Mapped[str | None] = mapped_column(Text)
    role_profile: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text('now()'))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text('now()'))
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', name='fk_user_roles_created_by', ondelete='RESTRICT', onupdate='RESTRICT'))
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', name='fk_user_roles_updated_by', ondelete='RESTRICT', onupdate='RESTRICT'))
    version: Mapped[int] = mapped_column(Integer, server_default='1')
    __table_args__ = (
        UniqueConstraint('user_id', 'role_code', name='uq_user_roles_user_role'),
        CheckConstraint("role_code IN ('PASSENGER','OWNER','DRIVER','ADMIN')", name='ck_user_roles_code'),
        CheckConstraint("approval_status IN ('PENDING','APPROVED','REJECTED','SUSPENDED')", name='ck_user_roles_approval'),
        CheckConstraint("approval_status <> 'APPROVED' OR approved_at IS NOT NULL", name='ck_user_roles_approved'),
        CheckConstraint("approval_status <> 'APPROVED' OR role_code IN ('PASSENGER','ADMIN') OR approved_by IS NOT NULL", name='ck_user_roles_reviewer'),
        CheckConstraint("approval_status <> 'REJECTED' OR (rejection_reason IS NOT NULL AND char_length(btrim(rejection_reason)) BETWEEN 1 AND 2000)", name='ck_user_roles_rejected'),
        CheckConstraint("approval_status <> 'SUSPENDED' OR (suspended_at IS NOT NULL AND suspension_reason IS NOT NULL AND char_length(btrim(suspension_reason)) BETWEEN 1 AND 2000)", name='ck_user_roles_suspended'),
        CheckConstraint("jsonb_typeof(role_profile) = 'object'", name='ck_user_roles_profile'),
        CheckConstraint('version >= 1', name='ck_user_roles_version'),
        CheckConstraint('updated_at >= created_at AND requested_at >= created_at AND (approved_at IS NULL OR approved_at >= requested_at) AND (suspended_at IS NULL OR suspended_at >= requested_at)', name='ck_user_roles_timestamps'),
        Index('ix_user_roles_role_approval', 'role_code', 'approval_status'),
        Index('ix_user_roles_approved_by', 'approved_by', postgresql_where=text('approved_by IS NOT NULL')),
        Index('ix_user_roles_created_by', 'created_by', postgresql_where=text('created_by IS NOT NULL')),
        Index('ix_user_roles_updated_by', 'updated_by', postgresql_where=text('updated_by IS NOT NULL')),
    )


User.__table__.primary_key.name = 'pk_users'
UserRole.__table__.primary_key.name = 'pk_user_roles'
