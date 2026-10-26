"""Align only the existing phone CHECK with the accepted international rule.

No table, column, uniqueness constraint or role/account state is added/changed.
Country-specific number validity remains an application-level check.
"""
from alembic import op

revision = '0002_international_phone'
down_revision = '0001_auth'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint('ck_users_phone', 'users', type_='check')
    op.create_check_constraint('ck_users_phone', 'users',
                               "phone_e164 IS NULL OR phone_e164 ~ '^[+][1-9][0-9]{1,14}$'")


def downgrade():
    # PostgreSQL will safely reject the old constraint if valid shorter foreign
    # numbers exist. Never delete or truncate those users to force a downgrade.
    op.drop_constraint('ck_users_phone', 'users', type_='check')
    op.create_check_constraint('ck_users_phone', 'users',
                               "phone_e164 IS NULL OR phone_e164 ~ '^[+][1-9][0-9]{7,14}$'")
