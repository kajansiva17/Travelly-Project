# The link status names DRIVER_REQUESTED (16) and OWNER_INVITED (13) are longer than the 12 characters made in 0020.
from alembic import op
from sqlalchemy import String

revision = '0022_owner_driver_status_length'
down_revision = '0021_findable_by_drivers'
branch_labels = depends_on = None


def upgrade():
    op.alter_column('owner_drivers', 'status', type_=String(20), existing_nullable=False)


def downgrade():
    op.alter_column('owner_drivers', 'status', type_=String(12), existing_nullable=False)
