"""ORM mappings for the approved seat-inventory tables (vehicle_seats, scheduled_trip_seats, booking_travellers).

DDL, CHECK and UNIQUE constraints live in migration 0007_ticket_seat_inventory; these mappings only read/write rows.
"""
from sqlalchemy import Table, Column, Boolean, DateTime, Integer, Numeric, SmallInteger, String, Text, text
from sqlalchemy.dialects.postgresql import CITEXT, JSONB, UUID
from app.models import Base


def audit():
    return [
        Column('id', UUID(as_uuid=True), nullable=False, server_default=text('gen_random_uuid()'), primary_key=True),
        Column('created_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
        Column('updated_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
        Column('created_by', UUID(as_uuid=True), nullable=True),
        Column('updated_by', UUID(as_uuid=True), nullable=True),
        Column('version', Integer, nullable=False, server_default=text('1')),
    ]


vehicle_seats_table = Table('vehicle_seats', Base.metadata, *audit(),
    Column('vehicle_id', UUID(as_uuid=True), nullable=False),
    Column('layout_version', Integer, nullable=False, server_default=text('1')),
    Column('seat_code', String(12), nullable=False),
    Column('row_number', SmallInteger, nullable=False),
    Column('column_number', SmallInteger, nullable=False),
    Column('deck_number', SmallInteger, nullable=False, server_default=text('1')),
    Column('seat_type', String(12), nullable=False, server_default=text("'STANDARD'")),
    Column('is_active', Boolean, nullable=False, server_default=text('true')),
    Column('is_bookable', Boolean, nullable=False, server_default=text('true')),
    Column('display_metadata', JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    extend_existing=True)

scheduled_trip_seats_table = Table('scheduled_trip_seats', Base.metadata, *audit(),
    Column('scheduled_trip_id', UUID(as_uuid=True), nullable=False),
    Column('vehicle_seat_id', UUID(as_uuid=True), nullable=False),
    Column('seat_status', String(9), nullable=False, server_default=text("'AVAILABLE'")),
    Column('held_by_booking_id', UUID(as_uuid=True), nullable=True),
    Column('hold_expires_at', DateTime(timezone=True), nullable=True),
    Column('booked_booking_id', UUID(as_uuid=True), nullable=True),
    Column('fare_override', Numeric(12, 2), nullable=True),
    extend_existing=True)

booking_travellers_table = Table('booking_travellers', Base.metadata, *audit(),
    Column('booking_id', UUID(as_uuid=True), nullable=False),
    Column('linked_user_id', UUID(as_uuid=True), nullable=True),
    Column('full_name', String(150), nullable=False),
    Column('contact_phone', String(20), nullable=True),
    Column('contact_email', CITEXT, nullable=True),
    Column('age_category', String(30), nullable=True),
    Column('is_primary', Boolean, nullable=False, server_default=text('false')),
    Column('identity_reference', String(100), nullable=True),
    Column('scheduled_trip_seat_id', UUID(as_uuid=True), nullable=True),
    Column('boarding_stop_id', UUID(as_uuid=True), nullable=True),
    Column('dropoff_stop_id', UUID(as_uuid=True), nullable=True),
    Column('special_assistance', Text, nullable=True),
    Column('traveller_status', String(12), nullable=False, server_default=text("'ACTIVE'")),
    extend_existing=True)


class VehicleSeat(Base):
    __table__ = vehicle_seats_table


class ScheduledTripSeat(Base):
    __table__ = scheduled_trip_seats_table


class BookingTraveller(Base):
    __table__ = booking_travellers_table
