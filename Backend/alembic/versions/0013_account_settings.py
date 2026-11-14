# Owner decision 14 Nov 2026 (Settings: notification preferences): one JSONB column on users, {'muted': [types]}.
from alembic import op
from sqlalchemy import Column, text
from sqlalchemy.dialects.postgresql import JSONB

revision = '0013_account_settings'
down_revision = '0012_social'
branch_labels = depends_on = None


def upgrade():
    op.add_column('users', Column('notification_preferences', JSONB, nullable=False, server_default=text("'{}'::jsonb")))
    op.create_check_constraint('ck_users_notification_preferences', 'users', text("jsonb_typeof(notification_preferences) = 'object'"))


def downgrade():
    op.drop_constraint('ck_users_notification_preferences', 'users')
    op.drop_column('users', 'notification_preferences')
