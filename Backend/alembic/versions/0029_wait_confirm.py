# Owner decision 23 Nov 2026: a Book now return that finishes without "Return started" is still charged fairly. The place where the waiting started is
# remembered so the vehicle moving away ends the waiting by itself; at finish the Driver confirms the waited minutes (never more than the timer showed),
# or adds them when the timer was never started. wait_source says who ended it: DRIVER, GPS or MANUAL.
from alembic import op
from sqlalchemy import Column, Numeric, String

revision = '0029_wait_confirm'
down_revision = '0028_return_waiting'
branch_labels = depends_on = None


def upgrade():
    op.add_column('trips', Column('wait_latitude', Numeric(9, 6), nullable=True))
    op.add_column('trips', Column('wait_longitude', Numeric(9, 6), nullable=True))
    op.add_column('trips', Column('wait_confirmed_minutes', Numeric(8, 1), nullable=True))
    op.add_column('trips', Column('wait_source', String(8), nullable=True))
    op.create_check_constraint('ck_trips_24', 'trips', 'wait_confirmed_minutes IS NULL OR wait_confirmed_minutes>=0')
    op.create_check_constraint('ck_trips_25', 'trips', "wait_source IS NULL OR wait_source IN ('DRIVER','GPS','MANUAL')")


def downgrade():
    op.drop_constraint('ck_trips_25', 'trips', type_='check')
    op.drop_constraint('ck_trips_24', 'trips', type_='check')
    for name in ('wait_source', 'wait_confirmed_minutes', 'wait_longitude', 'wait_latitude'):
        op.drop_column('trips', name)
