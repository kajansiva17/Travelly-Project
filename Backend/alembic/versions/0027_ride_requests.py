# Owner decision 23 Nov 2026: "Book now" (PickMe-style). A Passenger picks an online vehicle near them and the person sending that vehicle's
# location (Driver, or the Owner who drives) accepts within 90 seconds. Accepting creates the confirmed booking and trip.
from alembic import op
from sqlalchemy import CHAR, CheckConstraint, Column, DateTime, ForeignKey, Numeric, SmallInteger, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = '0027_ride_requests'
down_revision = '0026_vehicle_live_online'
branch_labels = depends_on = None


def upgrade():
    op.create_table('ride_requests',
        Column('id', UUID(as_uuid=True), nullable=False, server_default=text('gen_random_uuid()'), primary_key=True),
        Column('created_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
        Column('passenger_user_id', UUID(as_uuid=True), ForeignKey('users.id', name='fk_ride_requests_passenger', ondelete='RESTRICT'), nullable=False),
        Column('vehicle_id', UUID(as_uuid=True), ForeignKey('vehicles.id', name='fk_ride_requests_vehicle', ondelete='RESTRICT'), nullable=False),
        Column('operator_user_id', UUID(as_uuid=True), ForeignKey('users.id', name='fk_ride_requests_operator', ondelete='RESTRICT'), nullable=False),
        Column('service_type_id', UUID(as_uuid=True), ForeignKey('service_types.id', name='fk_ride_requests_service', ondelete='RESTRICT'), nullable=False),
        Column('pickup', JSONB, nullable=False),
        Column('destination', JSONB, nullable=False),
        Column('passenger_count', SmallInteger, nullable=False),
        Column('fare', Numeric(12, 2), nullable=False),
        Column('currency', CHAR(3), nullable=False, server_default=text("'LKR'")),
        Column('status', String(10), nullable=False, server_default=text("'OFFERED'")),
        Column('expires_at', DateTime(timezone=True), nullable=False),
        Column('responded_at', DateTime(timezone=True), nullable=True),
        Column('booking_id', UUID(as_uuid=True), ForeignKey('bookings.id', name='fk_ride_requests_booking', ondelete='RESTRICT'), nullable=True),
        CheckConstraint("status IN ('OFFERED','ACCEPTED','DECLINED','EXPIRED','CANCELLED')", name='ck_ride_requests_status'),
        CheckConstraint('fare>0', name='ck_ride_requests_fare'),
        CheckConstraint('passenger_count>0', name='ck_ride_requests_passengers'),
        CheckConstraint("status<>'ACCEPTED' OR booking_id IS NOT NULL", name='ck_ride_requests_booking'))
    # One open request per Passenger and one per vehicle at a time.
    op.create_index('uq_ride_requests_passenger_open', 'ride_requests', ['passenger_user_id'], unique=True, postgresql_where=text("status='OFFERED'"))
    op.create_index('uq_ride_requests_vehicle_open', 'ride_requests', ['vehicle_id'], unique=True, postgresql_where=text("status='OFFERED'"))
    op.create_index('ix_ride_requests_operator', 'ride_requests', ['operator_user_id', 'created_at'])


def downgrade():
    op.drop_index('ix_ride_requests_operator', table_name='ride_requests')
    op.drop_index('uq_ride_requests_vehicle_open', table_name='ride_requests')
    op.drop_index('uq_ride_requests_passenger_open', table_name='ride_requests')
    op.drop_table('ride_requests')
