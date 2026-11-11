"""ORM mapping for the approved PRD `payments` table.

DDL, CHECK and UNIQUE constraints live in migration 0010_payments; this mapping only reads and writes rows.
Refund, reallocation, additional charge and Owner payout are new rows linked through original_payment_id.
"""
from sqlalchemy import CHAR, Column, DateTime, Integer, Numeric, String, Table, Text, text
from sqlalchemy.dialects.postgresql import UUID
from app.models import Base

payments_table = Table('payments', Base.metadata,
    Column('id', UUID(as_uuid=True), nullable=False, server_default=text('gen_random_uuid()'), primary_key=True),
    Column('created_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
    Column('updated_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
    Column('created_by', UUID(as_uuid=True), nullable=True),
    Column('updated_by', UUID(as_uuid=True), nullable=True),
    Column('version', Integer, nullable=False, server_default=text('1')),
    Column('payment_reference', String(30), nullable=False),
    Column('booking_id', UUID(as_uuid=True), nullable=False),
    Column('original_payment_id', UUID(as_uuid=True), nullable=True),
    Column('payee_owner_user_id', UUID(as_uuid=True), nullable=True),
    Column('transaction_type', String(20), nullable=False),
    Column('payment_method', String(12), nullable=False),
    Column('provider_name', String(100), nullable=True),
    Column('provider_reference', String(200), nullable=True),
    Column('idempotency_key', String(100), nullable=False),
    Column('amount', Numeric(12, 2), nullable=False),
    Column('commission_amount', Numeric(12, 2), nullable=True),
    Column('owner_net_amount', Numeric(12, 2), nullable=True),
    Column('currency', CHAR(3), nullable=False),
    Column('status', String(32), nullable=False, server_default=text("'PENDING'")),
    Column('owner_settlement_status', String(32), nullable=True),
    Column('authorized_at', DateTime(timezone=True), nullable=True),
    Column('captured_at', DateTime(timezone=True), nullable=True),
    Column('refunded_at', DateTime(timezone=True), nullable=True),
    Column('owner_payable_at', DateTime(timezone=True), nullable=True),
    Column('owner_paid_at', DateTime(timezone=True), nullable=True),
    Column('failure_code', String(100), nullable=True),
    Column('failure_message', Text, nullable=True),
)


class Payment(Base):
    __table__ = payments_table
