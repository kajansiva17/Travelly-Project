# What an Owner paid a Driver for one completed trip (migration 0024). Separate from `payments`, which is Passenger money.
from sqlalchemy import Table, Column, CheckConstraint, ForeignKey, Index, text
from sqlalchemy import String, DateTime, Numeric, CHAR
from sqlalchemy.dialects.postgresql import UUID
from app.models import Base

driver_payments_table = Table('driver_payments', Base.metadata,
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
    CheckConstraint('owner_user_id<>driver_user_id', name='ck_driver_payments_people'),
    Index('uq_driver_payments_trip_live', 'trip_id', unique=True, postgresql_where=text("status<>'DECLINED'")),
    Index('ix_driver_payments_owner', 'owner_user_id', 'created_at'),
    Index('ix_driver_payments_driver', 'driver_user_id', 'created_at'))


class DriverPayment(Base):
    __table__ = driver_payments_table
