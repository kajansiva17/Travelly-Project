# Owner decision 15 Nov 2026 (Bookings page): a finished booking can be taken off a person's own list.
# Hidden, never deleted: the booking, its payments and its history stay (PRD). Owner and Passenger hide separately.
from alembic import op
from sqlalchemy import Column, DateTime

revision = '0016_booking_history'
down_revision = '0015_departure_history'
branch_labels = depends_on = None


def upgrade():
    op.add_column('bookings', Column('owner_hidden_at', DateTime(timezone=True), nullable=True))
    op.add_column('bookings', Column('passenger_hidden_at', DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column('bookings', 'passenger_hidden_at')
    op.drop_column('bookings', 'owner_hidden_at')
