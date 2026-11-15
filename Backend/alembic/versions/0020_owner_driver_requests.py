# Owner decision 15 Nov 2026: a Driver can ask an Owner (by the Owner's Travelly reference) to be listed in My drivers,
# and an Owner can invite a Driver by reference. The Driver or Owner accepts or declines. Still no permanent relationship:
# either side can remove the link, and every trip still needs the licence check and the Driver's acceptance.
from alembic import op
from sqlalchemy import Column, String, text

revision = '0020_owner_driver_requests'
down_revision = '0019_owner_drivers'
branch_labels = depends_on = None


def upgrade():
    op.add_column('owner_drivers', Column('status', String(12), nullable=False, server_default=text("'ACTIVE'")))
    op.add_column('owner_drivers', Column('initiated_by', String(6), nullable=False, server_default=text("'OWNER'")))


def downgrade():
    op.drop_column('owner_drivers', 'initiated_by')
    op.drop_column('owner_drivers', 'status')
