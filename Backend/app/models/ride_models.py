# Book now requests (migration 0027): one Passenger asks one or more online vehicles at once (one group, migration 0038); the first operator to accept gets the trip.
from sqlalchemy import Table, Column, CheckConstraint, ForeignKey, Index, text
from sqlalchemy import String, DateTime, Numeric, CHAR, SmallInteger, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.models import Base

ride_requests_table = Table('ride_requests', Base.metadata,
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
    Column('group_id', UUID(as_uuid=True), nullable=True),
    Column('booking_id', UUID(as_uuid=True), ForeignKey('bookings.id', name='fk_ride_requests_booking', ondelete='RESTRICT'), nullable=True),
    Column('round_trip', Boolean, nullable=False, server_default=text('false')),
    CheckConstraint("status IN ('OFFERED','ACCEPTED','DECLINED','EXPIRED','CANCELLED')", name='ck_ride_requests_status'),
    CheckConstraint('fare>0', name='ck_ride_requests_fare'),
    CheckConstraint('passenger_count>0', name='ck_ride_requests_passengers'),
    CheckConstraint("status<>'ACCEPTED' OR booking_id IS NOT NULL", name='ck_ride_requests_booking'),
    Index('ix_ride_requests_group', 'group_id'),
    Index('ix_ride_requests_passenger_open', 'passenger_user_id', postgresql_where=text("status='OFFERED'")),
    Index('uq_ride_requests_vehicle_open', 'vehicle_id', unique=True, postgresql_where=text("status='OFFERED'")),
    Index('ix_ride_requests_operator', 'operator_user_id', 'created_at'))


class RideRequest(Base):
    __table__ = ride_requests_table
