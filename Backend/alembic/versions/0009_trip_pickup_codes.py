# Pickup verification at the start of a private-hire trip, chosen by the project owner (10 November 2026).
# The Passenger shows a QR code; if it will not scan, the Driver types the six-digit number printed under it.
# No new table: four columns on the existing trips row, so the approved 20-table catalogue is unchanged.
# The code itself is never stored. It is derived from the application secret and the version below, so the
# Passenger can open it again at any time and a new code can be issued by moving the version on.
from alembic import op
from sqlalchemy import Column, DateTime, Integer, text

revision = '0009_trip_pickup_codes'
down_revision = '0008_ticket_hold_default'
branch_labels = depends_on = None


def upgrade():
    op.add_column('trips', Column('pickup_code_version', Integer, nullable=False, server_default=text('0')))
    op.add_column('trips', Column('pickup_code_issued_at', DateTime(timezone=True), nullable=True))
    op.add_column('trips', Column('pickup_verified_at', DateTime(timezone=True), nullable=True))
    op.add_column('trips', Column('pickup_failed_attempts', Integer, nullable=False, server_default=text('0')))
    op.create_check_constraint('ck_trips_20', 'trips', 'pickup_code_version>=0')
    op.create_check_constraint('ck_trips_21', 'trips', 'pickup_failed_attempts>=0')
    # A trip can only be marked verified against a code that was actually issued.
    op.create_check_constraint('ck_trips_22', 'trips', 'pickup_verified_at IS NULL OR pickup_code_version>0')


def downgrade():
    op.drop_constraint('ck_trips_22', 'trips', type_='check')
    op.drop_constraint('ck_trips_21', 'trips', type_='check')
    op.drop_constraint('ck_trips_20', 'trips', type_='check')
    for name in ('pickup_failed_attempts', 'pickup_verified_at', 'pickup_code_issued_at', 'pickup_code_version'):
        op.drop_column('trips', name)
