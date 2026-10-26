"""Create only Travelly users and user_roles, snapshot of the frozen Auth schema."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision = '0001_auth'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.execute('CREATE EXTENSION IF NOT EXISTS citext WITH SCHEMA public')
    op.create_table('users',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('public_user_reference', sa.String(length=20), nullable=False),
    sa.Column('email', postgresql.CITEXT(), nullable=True),
    sa.Column('phone_e164', sa.String(length=20), nullable=True),
    sa.Column('password_hash', sa.Text(), nullable=False),
    sa.Column('full_name', sa.String(length=150), nullable=False),
    sa.Column('display_name', sa.String(length=100), nullable=True),
    sa.Column('profile_image_url', sa.Text(), nullable=True),
    sa.Column('preferred_language', sa.String(length=2), server_default='en', nullable=False),
    sa.Column('timezone', sa.String(length=64), server_default='Asia/Colombo', nullable=False),
    sa.Column('account_status', sa.String(length=24), server_default='PENDING_VERIFICATION', nullable=False),
    sa.Column('email_verified_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('phone_verified_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('failed_login_count', sa.Integer(), server_default='0', nullable=False),
    sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.Column('version', sa.Integer(), server_default='1', nullable=False),
    sa.CheckConstraint("account_status <> 'ACTIVE' OR email_verified_at IS NOT NULL OR phone_verified_at IS NOT NULL", name='ck_users_activation'),
    sa.CheckConstraint("account_status IN ('PENDING_VERIFICATION','ACTIVE','SUSPENDED','BLOCKED','CLOSED')", name='ck_users_account_status'),
    sa.CheckConstraint("email IS NULL OR (email::text = lower(btrim(email::text)) AND char_length(email::text) BETWEEN 3 AND 254 AND email::text !~ '[[:space:]]')", name='ck_users_email'),
    sa.CheckConstraint("phone_e164 IS NULL OR phone_e164 ~ '^[+][1-9][0-9]{7,14}$'", name='ck_users_phone'),
    sa.CheckConstraint("preferred_language IN ('en','ta','si')", name='ck_users_language'),
    sa.CheckConstraint("public_user_reference ~ '^USR-[0-9A-F]{16}$'", name='ck_users_reference'),
    sa.CheckConstraint("timezone = 'Asia/Colombo'", name='ck_users_timezone'),
    sa.CheckConstraint('char_length(password_hash) > 0', name='ck_users_password_hash'),
    sa.CheckConstraint('display_name IS NULL OR (display_name = btrim(display_name) AND char_length(display_name) BETWEEN 1 AND 100)', name='ck_users_display_name'),
    sa.CheckConstraint('email IS NOT NULL OR phone_e164 IS NOT NULL', name='ck_users_contact'),
    sa.CheckConstraint('email_verified_at IS NULL OR email IS NOT NULL', name='ck_users_verified_email'),
    sa.CheckConstraint('failed_login_count >= 0', name='ck_users_failures'),
    sa.CheckConstraint('full_name = btrim(full_name) AND char_length(full_name) BETWEEN 1 AND 150', name='ck_users_full_name'),
    sa.CheckConstraint('phone_verified_at IS NULL OR phone_e164 IS NOT NULL', name='ck_users_verified_phone'),
    sa.CheckConstraint('updated_at >= created_at', name='ck_users_timestamps'),
    sa.CheckConstraint('version >= 1', name='ck_users_version'),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], name='fk_users_created_by', onupdate='RESTRICT', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['updated_by'], ['users.id'], name='fk_users_updated_by', onupdate='RESTRICT', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name='pk_users'),
    sa.UniqueConstraint('email', name='uq_users_email'),
    sa.UniqueConstraint('phone_e164', name='uq_users_phone'),
    sa.UniqueConstraint('public_user_reference', name='uq_users_public_reference'),
    comment='Shared identity; contact verification is independent of role approval.'
    )
    op.create_index('ix_users_account_status', 'users', ['account_status'], unique=False)
    op.create_index('ix_users_created_at', 'users', ['created_at'], unique=False)
    op.create_index('ix_users_created_by', 'users', ['created_by'], unique=False, postgresql_where=sa.text('created_by IS NOT NULL'))
    op.create_index('ix_users_updated_by', 'users', ['updated_by'], unique=False, postgresql_where=sa.text('updated_by IS NOT NULL'))
    op.create_table('user_roles',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('role_code', sa.String(length=9), nullable=False),
    sa.Column('approval_status', sa.String(length=9), server_default='PENDING', nullable=False),
    sa.Column('requested_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('approved_by', sa.UUID(), nullable=True),
    sa.Column('rejection_reason', sa.Text(), nullable=True),
    sa.Column('suspended_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('suspension_reason', sa.Text(), nullable=True),
    sa.Column('role_profile', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.Column('version', sa.Integer(), server_default='1', nullable=False),
    sa.CheckConstraint("approval_status <> 'APPROVED' OR approved_at IS NOT NULL", name='ck_user_roles_approved'),
    sa.CheckConstraint("approval_status <> 'APPROVED' OR role_code IN ('PASSENGER','ADMIN') OR approved_by IS NOT NULL", name='ck_user_roles_reviewer'),
    sa.CheckConstraint("approval_status <> 'REJECTED' OR (rejection_reason IS NOT NULL AND char_length(btrim(rejection_reason)) BETWEEN 1 AND 2000)", name='ck_user_roles_rejected'),
    sa.CheckConstraint("approval_status <> 'SUSPENDED' OR (suspended_at IS NOT NULL AND suspension_reason IS NOT NULL AND char_length(btrim(suspension_reason)) BETWEEN 1 AND 2000)", name='ck_user_roles_suspended'),
    sa.CheckConstraint("approval_status IN ('PENDING','APPROVED','REJECTED','SUSPENDED')", name='ck_user_roles_approval'),
    sa.CheckConstraint("jsonb_typeof(role_profile) = 'object'", name='ck_user_roles_profile'),
    sa.CheckConstraint("role_code IN ('PASSENGER','OWNER','DRIVER','ADMIN')", name='ck_user_roles_code'),
    sa.CheckConstraint('updated_at >= created_at AND requested_at >= created_at AND (approved_at IS NULL OR approved_at >= requested_at) AND (suspended_at IS NULL OR suspended_at >= requested_at)', name='ck_user_roles_timestamps'),
    sa.CheckConstraint('version >= 1', name='ck_user_roles_version'),
    sa.ForeignKeyConstraint(['approved_by'], ['users.id'], name='fk_user_roles_approved_by', onupdate='RESTRICT', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], name='fk_user_roles_created_by', onupdate='RESTRICT', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['updated_by'], ['users.id'], name='fk_user_roles_updated_by', onupdate='RESTRICT', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_user_roles_user', onupdate='RESTRICT', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name='pk_user_roles'),
    sa.UniqueConstraint('user_id', 'role_code', name='uq_user_roles_user_role')
    )
    op.create_index('ix_user_roles_approved_by', 'user_roles', ['approved_by'], unique=False, postgresql_where=sa.text('approved_by IS NOT NULL'))
    op.create_index('ix_user_roles_created_by', 'user_roles', ['created_by'], unique=False, postgresql_where=sa.text('created_by IS NOT NULL'))
    op.create_index('ix_user_roles_role_approval', 'user_roles', ['role_code', 'approval_status'], unique=False)
    op.create_index('ix_user_roles_updated_by', 'user_roles', ['updated_by'], unique=False, postgresql_where=sa.text('updated_by IS NOT NULL'))


def downgrade():
    op.drop_table('user_roles')
    op.drop_table('users')
    # CITEXT is shared database infrastructure; never drop the extension here.
