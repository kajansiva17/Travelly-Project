# Booking chat (migration 0039): short text messages between the people on one booking.
from sqlalchemy import Table, Column, CheckConstraint, ForeignKey, Index, text
from sqlalchemy import DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from app.models import Base

booking_messages_table = Table('booking_messages', Base.metadata,
    Column('id', UUID(as_uuid=True), nullable=False, server_default=text('gen_random_uuid()'), primary_key=True),
    Column('created_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
    Column('booking_id', UUID(as_uuid=True), ForeignKey('bookings.id', name='fk_booking_messages_booking', ondelete='RESTRICT'), nullable=False),
    Column('sender_user_id', UUID(as_uuid=True), ForeignKey('users.id', name='fk_booking_messages_sender', ondelete='RESTRICT'), nullable=False),
    Column('body', Text, nullable=False),
    Column('read_by', JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    CheckConstraint('char_length(body) BETWEEN 1 AND 500', name='ck_booking_messages_body'),
    CheckConstraint("jsonb_typeof(read_by)='array'", name='ck_booking_messages_read_by'),
    Index('ix_booking_messages_booking', 'booking_id', 'created_at'))


class BookingMessage(Base):
    __table__ = booking_messages_table
