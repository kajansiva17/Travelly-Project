# Support chat (migration 0031): a ticket is a chat thread between one person and the Travelly Admins.
from sqlalchemy import Table, Column, CheckConstraint, ForeignKey, Index, text
from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from app.models import Base

support_tickets_table = Table('support_tickets', Base.metadata,
    Column('id', UUID(as_uuid=True), nullable=False, server_default=text('gen_random_uuid()'), primary_key=True),
    Column('created_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id', name='fk_support_tickets_user', ondelete='RESTRICT'), nullable=False),
    Column('workspace_role', String(10), nullable=False),
    Column('category', String(12), nullable=False),
    Column('subject', String(120), nullable=False),
    Column('booking_id', UUID(as_uuid=True), ForeignKey('bookings.id', name='fk_support_tickets_booking', ondelete='RESTRICT'), nullable=True),
    Column('status', String(12), nullable=False, server_default=text("'OPEN'")),
    Column('last_message_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
    Column('user_unread', Boolean, nullable=False, server_default=text('false')),
    Column('admin_unread', Boolean, nullable=False, server_default=text('true')),
    CheckConstraint("workspace_role IN ('PASSENGER','OWNER','DRIVER')", name='ck_support_tickets_role'),
    CheckConstraint("category IN ('PAYMENT','BOOKING','VEHICLE','DRIVER','REFUND','ACCOUNT','APP','OTHER')", name='ck_support_tickets_category'),
    CheckConstraint("status IN ('OPEN','IN_PROGRESS','RESOLVED','CLOSED')", name='ck_support_tickets_status'),
    CheckConstraint('subject=btrim(subject) AND char_length(subject)>0', name='ck_support_tickets_subject'),
    Index('ix_support_tickets_user', 'user_id', 'last_message_at'),
    Index('ix_support_tickets_inbox', 'status', 'last_message_at'))

support_messages_table = Table('support_messages', Base.metadata,
    Column('id', UUID(as_uuid=True), nullable=False, server_default=text('gen_random_uuid()'), primary_key=True),
    Column('created_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
    Column('ticket_id', UUID(as_uuid=True), ForeignKey('support_tickets.id', name='fk_support_messages_ticket', ondelete='CASCADE'), nullable=False),
    Column('sender_user_id', UUID(as_uuid=True), ForeignKey('users.id', name='fk_support_messages_sender', ondelete='RESTRICT'), nullable=False),
    Column('from_admin', Boolean, nullable=False, server_default=text('false')),
    Column('body', Text, nullable=False),
    CheckConstraint('char_length(body) BETWEEN 1 AND 2000', name='ck_support_messages_body'),
    Index('ix_support_messages_ticket', 'ticket_id', 'created_at'))


class SupportTicket(Base):
    __table__ = support_tickets_table


class SupportMessage(Base):
    __table__ = support_messages_table
