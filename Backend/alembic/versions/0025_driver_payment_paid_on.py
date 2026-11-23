# The day the Owner actually paid the Driver. An Owner may pay days after the trip, so this is not the day it was recorded.
from alembic import op
from sqlalchemy import Column, Date, text

revision = '0025_driver_payment_paid_on'
down_revision = '0024_driver_payments'
branch_labels = depends_on = None


def upgrade():
    op.add_column('driver_payments', Column('paid_on', Date, nullable=False, server_default=text('CURRENT_DATE')))
    op.execute('UPDATE driver_payments SET paid_on = owner_recorded_at::date')


def downgrade():
    op.drop_column('driver_payments', 'paid_on')
