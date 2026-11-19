# Owner decision 15 Nov 2026: an Owner can remove a vehicle from the fleet list and bring it back.
# Archive only, never deleted: the vehicle, its bookings, payments and history stay (PRD).
from alembic import op
from sqlalchemy import Column, DateTime

revision = '0018_vehicle_removed'
down_revision = '0017_favourite_vehicles'
branch_labels = depends_on = None


def upgrade():
    op.add_column('vehicles', Column('archived_at', DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column('vehicles', 'archived_at')
