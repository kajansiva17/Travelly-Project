# Owner decision 15 Nov 2026 (Ticket > Your departures): a finished departure can be taken off the Owner's list.
# It is archived, never deleted: the row, its bookings and payments stay as history (PRD: history must not be overwritten).
from alembic import op
from sqlalchemy import Column, DateTime

revision = '0015_departure_history'
down_revision = '0014_two_factor_and_closure'
branch_labels = depends_on = None


def upgrade():
    op.add_column('scheduled_trips', Column('archived_at', DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column('scheduled_trips', 'archived_at')
