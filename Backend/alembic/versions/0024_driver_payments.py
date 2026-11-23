# Owner decision 23 Nov 2026: an Owner records what they paid the Driver for a completed trip, in cash or online. Cash needs the Driver's
# confirmation too; an online payment is recorded with its reference. Both people see it in their reports.
from alembic import op
from sqlalchemy import CHAR, CheckConstraint, Column, DateTime, ForeignKey, Numeric, String, text
from sqlalchemy.dialects.postgresql import UUID

revision = '0024_driver_payments'
down_revision = '0023_vehicle_hire_location'
branch_labels = depends_on = None


def upgrade():
    op.create_table('driver_payments',
        Column('id', UUID(as_uuid=True), nullable=False, server_default=text('gen_random_uuid()'), primary_key=True),
        Column('created_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
        Column('updated_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
        Column('trip_id', UUID(as_uuid=True), ForeignKey('trips.id', name='fk_driver_payments_trip_id', ondelete='RESTRICT'), nullable=False),
        Column('owner_user_id', UUID(as_uuid=True), ForeignKey('users.id', name='fk_driver_payments_owner_user_id', ondelete='RESTRICT'), nullable=False),
        Column('driver_user_id', UUID(as_uuid=True), ForeignKey('users.id', name='fk_driver_payments_driver_user_id', ondelete='RESTRICT'), nullable=False),
        Column('amount', Numeric(12, 2), nullable=False),
        Column('currency', CHAR(3), nullable=False, server_default=text("'LKR'")),
        Column('method', String(6), nullable=False),
        Column('reference', String(80), nullable=True),
        Column('status', String(16), nullable=False, server_default=text("'PENDING_DRIVER'")),
        Column('owner_recorded_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
        Column('driver_confirmed_at', DateTime(timezone=True), nullable=True),
        Column('driver_note', String(300), nullable=True),
        CheckConstraint('amount>0', name='ck_driver_payments_amount'),
        CheckConstraint("method IN ('CASH','ONLINE')", name='ck_driver_payments_method'),
        CheckConstraint("status IN ('PENDING_DRIVER','CONFIRMED','DECLINED')", name='ck_driver_payments_status'),
        CheckConstraint("method<>'ONLINE' OR reference IS NOT NULL", name='ck_driver_payments_reference'),
        CheckConstraint("status<>'CONFIRMED' OR method='ONLINE' OR driver_confirmed_at IS NOT NULL", name='ck_driver_payments_confirmed'),
        CheckConstraint('owner_user_id<>driver_user_id', name='ck_driver_payments_people'))
    # One live payment per trip; a declined one can be recorded again.
    op.create_index('uq_driver_payments_trip_live', 'driver_payments', ['trip_id'], unique=True, postgresql_where=text("status<>'DECLINED'"))
    op.create_index('ix_driver_payments_owner', 'driver_payments', ['owner_user_id', 'created_at'])
    op.create_index('ix_driver_payments_driver', 'driver_payments', ['driver_user_id', 'created_at'])


def downgrade():
    op.drop_index('ix_driver_payments_driver', table_name='driver_payments')
    op.drop_index('ix_driver_payments_owner', table_name='driver_payments')
    op.drop_index('uq_driver_payments_trip_live', table_name='driver_payments')
    op.drop_table('driver_payments')
