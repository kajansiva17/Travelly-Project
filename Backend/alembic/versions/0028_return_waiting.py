# Owner decision 23 Nov 2026: Book now can be a return trip. The Passenger does not choose a waiting time; the Driver records when the waiting at the
# destination starts and ends, and the waiting beyond the Owner's free minutes is charged by the minute actually waited, added to the total at completion.
from alembic import op
from sqlalchemy import Boolean, Column, DateTime, text

revision = '0028_return_waiting'
down_revision = '0027_ride_requests'
branch_labels = depends_on = None


def upgrade():
    op.add_column('ride_requests', Column('round_trip', Boolean, nullable=False, server_default=text('false')))
    op.add_column('trips', Column('wait_started_at', DateTime(timezone=True), nullable=True))
    op.add_column('trips', Column('wait_ended_at', DateTime(timezone=True), nullable=True))
    op.create_check_constraint('ck_trips_23', 'trips', 'wait_ended_at IS NULL OR (wait_started_at IS NOT NULL AND wait_ended_at>=wait_started_at)')


def downgrade():
    op.drop_constraint('ck_trips_23', 'trips', type_='check')
    op.drop_column('trips', 'wait_ended_at')
    op.drop_column('trips', 'wait_started_at')
    op.drop_column('ride_requests', 'round_trip')
