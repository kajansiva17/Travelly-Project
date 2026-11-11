# The approved PRD `payments` table (data dictionary, table 17 of 20), exactly as specified: columns, named checks,
# unique constraints and indexes. No other table is added. Payment decisions by the project owner (11 November 2026):
# no advance for private hire, the gateway fee comes out of the Owner's share, commission is an Admin percentage per
# service type, Sandbox now and PayHere later. Those settings live in service_types.settings, not here.
from alembic import op
from sqlalchemy import CHAR, Column, DateTime, ForeignKey, Integer, Numeric, PrimaryKeyConstraint, String, Text, text
from sqlalchemy.dialects.postgresql import UUID

revision = '0010_payments'
down_revision = '0009_trip_pickup_codes'
branch_labels = depends_on = None


def fk(column, target):
    return ForeignKey(target, name=f'fk_payments_{column}', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False)


def upgrade():
    op.create_table(
        'payments',
        Column('id', UUID(as_uuid=True), nullable=False, server_default=text('gen_random_uuid()')),
        Column('created_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
        Column('updated_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
        Column('created_by', UUID(as_uuid=True), fk('created_by', 'users.id'), nullable=True),
        Column('updated_by', UUID(as_uuid=True), fk('updated_by', 'users.id'), nullable=True),
        Column('version', Integer, nullable=False, server_default=text('1')),
        Column('payment_reference', String(30), nullable=False),
        Column('booking_id', UUID(as_uuid=True), fk('booking_id', 'bookings.id'), nullable=False),
        Column('original_payment_id', UUID(as_uuid=True), fk('original_payment_id', 'payments.id'), nullable=True),
        Column('payee_owner_user_id', UUID(as_uuid=True), fk('payee_owner_user_id', 'users.id'), nullable=True),
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
        # The primary key is declared with the table so the self-reference (original_payment_id) can point at it.
        PrimaryKeyConstraint('id', name='pk_payments'),
    )
    checks = {
        'ck_payments_01': 'original_payment_id IS NULL OR original_payment_id<>id',
        'ck_payments_02': 'commission_amount IS NULL OR commission_amount<=amount',
        'ck_payments_03': 'owner_net_amount IS NULL OR owner_net_amount<=amount',
        'ck_payments_04': 'version>=1',
        'ck_payments_05': 'updated_at>=created_at',
        'ck_payments_06': 'payment_reference=btrim(payment_reference) AND char_length(payment_reference)>0',
        'ck_payments_07': "transaction_type IN ('PAYMENT','REALLOCATION','ADDITIONAL_CHARGE','PARTIAL_REFUND','FULL_REFUND','OWNER_PAYOUT')",
        'ck_payments_08': "payment_method IN ('CARD','BANK','MOBILE','CASH','SANDBOX')",
        'ck_payments_09': 'provider_name=btrim(provider_name) AND char_length(provider_name)>0',
        'ck_payments_10': 'provider_reference=btrim(provider_reference) AND char_length(provider_reference)>0',
        'ck_payments_11': 'idempotency_key=btrim(idempotency_key) AND char_length(idempotency_key)>0',
        'ck_payments_12': 'amount>=0',
        'ck_payments_13': 'commission_amount>=0',
        'ck_payments_14': 'owner_net_amount>=0',
        'ck_payments_15': "currency ~ '^[A-Z]{3}$'",
        'ck_payments_16': "status IN ('PENDING','PROCESSING','PAID','CASH_AWAITING_CONFIRMATION','FAILED','REFUNDED','PARTIALLY_REFUNDED')",
        'ck_payments_17': 'owner_settlement_status=btrim(owner_settlement_status) AND char_length(owner_settlement_status)>0',
        'ck_payments_18': 'failure_code=btrim(failure_code) AND char_length(failure_code)>0',
    }
    for name, condition in checks.items():
        op.create_check_constraint(name, 'payments', condition)
    op.create_unique_constraint('uq_payments_01', 'payments', ['payment_reference'])
    op.create_unique_constraint('uq_payments_02', 'payments', ['idempotency_key'])
    op.create_index('ix_payments_01', 'payments', ['booking_id', 'created_at'])
    op.create_index('ix_payments_02', 'payments', ['provider_reference'])
    op.create_index('ix_payments_03', 'payments', ['payee_owner_user_id', 'owner_settlement_status'])
    op.create_index('ix_payments_created_by', 'payments', ['created_by'], postgresql_where=text('created_by IS NOT NULL'))
    op.create_index('ix_payments_updated_by', 'payments', ['updated_by'], postgresql_where=text('updated_by IS NOT NULL'))


def downgrade():
    op.drop_table('payments')
