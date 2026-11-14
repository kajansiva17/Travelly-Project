# Owner decisions 14 Nov 2026 (Settings): two-step verification (authenticator app) and account deactivate / delete request.
# users gets the 2FA columns, deletion_requested_at, and account_status gains DEACTIVATED (the person can come back by signing in).
from alembic import op
from sqlalchemy import Column, DateTime, Integer, Text, text
from sqlalchemy.dialects.postgresql import JSONB

revision = '0014_two_factor_and_closure'
down_revision = '0013_account_settings'
branch_labels = depends_on = None

OLD = "account_status IN ('PENDING_VERIFICATION','ACTIVE','SUSPENDED','BLOCKED','CLOSED')"
NEW = "account_status IN ('PENDING_VERIFICATION','ACTIVE','SUSPENDED','BLOCKED','CLOSED','DEACTIVATED')"


def upgrade():
    op.add_column('users', Column('totp_secret', Text, nullable=True))
    op.add_column('users', Column('totp_enabled_at', DateTime(timezone=True), nullable=True))
    op.add_column('users', Column('totp_backup_codes', JSONB, nullable=False, server_default=text("'[]'::jsonb")))
    op.add_column('users', Column('totp_last_step', Integer, nullable=True))
    op.add_column('users', Column('deletion_requested_at', DateTime(timezone=True), nullable=True))
    op.drop_constraint('ck_users_account_status', 'users')
    op.create_check_constraint('ck_users_account_status', 'users', text(NEW))
    op.create_check_constraint('ck_users_totp_backup_codes', 'users', text("jsonb_typeof(totp_backup_codes) = 'array'"))


def downgrade():
    op.drop_constraint('ck_users_totp_backup_codes', 'users')
    op.drop_constraint('ck_users_account_status', 'users')
    op.create_check_constraint('ck_users_account_status', 'users', text(OLD))
    for name in ('deletion_requested_at', 'totp_last_step', 'totp_backup_codes', 'totp_enabled_at', 'totp_secret'):
        op.drop_column('users', name)
