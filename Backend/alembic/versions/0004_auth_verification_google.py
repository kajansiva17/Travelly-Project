"""Email verification transition and the existing planned Google identity pair."""
from alembic import op
import sqlalchemy as sa

revision = '0004_auth_verification_google'
down_revision = '0003_review_documents'
branch_labels = depends_on = None


def upgrade():
    op.add_column('users', sa.Column('external_auth_provider', sa.String(40), nullable=True))
    op.add_column('users', sa.Column('external_auth_subject', sa.String(255), nullable=True))
    # Backfill legacy accounts false, then default new accounts true. No date heuristic.
    op.add_column('users', sa.Column('email_login_required', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.alter_column('users', 'email_login_required', server_default=sa.true())
    op.add_column('users', sa.Column('auth_version', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('terms_accepted_at', sa.DateTime(timezone=True), nullable=True))
    op.alter_column('users', 'password_hash', nullable=True)
    op.create_unique_constraint('uq_users_external_identity', 'users', ['external_auth_provider', 'external_auth_subject'])
    op.create_check_constraint('ck_users_provider_pair', 'users', "(external_auth_provider IS NULL AND external_auth_subject IS NULL) OR (external_auth_provider IS NOT NULL AND external_auth_provider = 'GOOGLE' AND external_auth_subject IS NOT NULL AND char_length(external_auth_subject) BETWEEN 1 AND 255)")
    op.create_check_constraint('ck_users_auth_method', 'users', 'password_hash IS NOT NULL OR external_auth_provider IS NOT NULL')
    op.create_check_constraint('ck_users_auth_version', 'users', 'auth_version >= 0')


def downgrade():
    # Never destroy provider identity or grandfathering state as an automatic rollback.
    raise RuntimeError('Auth data requires an explicit recovery plan; automatic downgrade is not supported.')
