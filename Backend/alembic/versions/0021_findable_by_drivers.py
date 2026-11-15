# Owner decision 15 Nov 2026: Drivers can search for an Owner by name or full number plate; an Owner can switch this off.
from alembic import op
from sqlalchemy import Boolean, Column, text

revision = '0021_findable_by_drivers'
down_revision = '0020_owner_driver_requests'
branch_labels = depends_on = None


def upgrade():
    op.add_column('users', Column('findable_by_drivers', Boolean, nullable=False, server_default=text('true')))


def downgrade():
    op.drop_column('users', 'findable_by_drivers')
