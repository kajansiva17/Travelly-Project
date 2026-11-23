# Owner decision 23 Nov 2026 (Book now return): when the vehicle leaves the waiting spot the Driver is asked whether the waiting is over, and the waiting
# clock stops at the moment it left until he answers (wait_moved_at). A Passenger may report the waiting charge once after the trip (reason optional);
# the report never blocks payment. The Owner keeps the charge or lowers it.
from alembic import op
from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID

revision = '0034_wait_prompt_report'
down_revision = '0033_review_edited'
branch_labels = depends_on = None


def upgrade():
    op.add_column('trips', Column('wait_moved_at', DateTime(timezone=True), nullable=True))
    op.create_table('waiting_charge_reports',
        Column('id', UUID(as_uuid=True), nullable=False, server_default=text('gen_random_uuid()'), primary_key=True),
        Column('created_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
        Column('trip_id', UUID(as_uuid=True), ForeignKey('trips.id', name='fk_wcr_trip', ondelete='RESTRICT'), nullable=False),
        Column('booking_id', UUID(as_uuid=True), ForeignKey('bookings.id', name='fk_wcr_booking', ondelete='RESTRICT'), nullable=False),
        Column('passenger_user_id', UUID(as_uuid=True), ForeignKey('users.id', name='fk_wcr_passenger', ondelete='RESTRICT'), nullable=False),
        Column('owner_user_id', UUID(as_uuid=True), ForeignKey('users.id', name='fk_wcr_owner', ondelete='RESTRICT'), nullable=False),
        Column('reason', Text, nullable=True),
        Column('charge', Numeric(12, 2), nullable=False),
        Column('status', String(8), nullable=False, server_default=text("'OPEN'")),
        Column('new_charge', Numeric(12, 2), nullable=True),
        Column('refund_due', Numeric(12, 2), nullable=True),
        Column('owner_note', Text, nullable=True),
        Column('resolved_at', DateTime(timezone=True), nullable=True),
        UniqueConstraint('trip_id', name='uq_wcr_trip'),
        CheckConstraint("status IN ('OPEN','KEPT','REDUCED')", name='ck_wcr_status'),
        CheckConstraint('reason IS NULL OR char_length(reason) BETWEEN 1 AND 300', name='ck_wcr_reason'),
        CheckConstraint('owner_note IS NULL OR char_length(owner_note) BETWEEN 1 AND 300', name='ck_wcr_note'),
        CheckConstraint('charge>0', name='ck_wcr_charge'),
        CheckConstraint("(status='REDUCED') = (new_charge IS NOT NULL) AND (new_charge IS NULL OR (new_charge>=0 AND new_charge<charge))", name='ck_wcr_new_charge'),
        CheckConstraint("(status='OPEN') = (resolved_at IS NULL)", name='ck_wcr_resolved'))
    op.create_index('ix_wcr_owner', 'waiting_charge_reports', ['owner_user_id', 'created_at'])


def downgrade():
    op.drop_table('waiting_charge_reports')
    op.drop_column('trips', 'wait_moved_at')
