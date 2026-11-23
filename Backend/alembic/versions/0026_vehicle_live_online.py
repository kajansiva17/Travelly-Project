# Owner decision 23 Nov 2026: "Go online" like Uber. The Driver (or a self-driving Owner) sends the vehicle's GPS from their phone, so the
# 15-minute location rule is met automatically and nobody types a location. Adds who is sending (live_online_user_id), since when, and the
# Owner's per-vehicle instant-booking switch (default OFF).
from alembic import op
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID

revision = '0026_vehicle_live_online'
down_revision = '0025_driver_payment_paid_on'
branch_labels = depends_on = None


def upgrade():
    op.add_column('vehicles', Column('live_online_user_id', UUID(as_uuid=True),
                                     ForeignKey('users.id', name='fk_vehicles_live_online_user_id', ondelete='RESTRICT', onupdate='RESTRICT'), nullable=True))
    op.add_column('vehicles', Column('live_online_since', DateTime(timezone=True), nullable=True))
    op.add_column('vehicles', Column('instant_booking', Boolean, nullable=False, server_default=text('false')))
    op.create_check_constraint('ck_vehicles_live_online', 'vehicles', '(live_online_user_id IS NULL) = (live_online_since IS NULL)')
    op.create_index('ix_vehicles_live_online', 'vehicles', ['live_online_user_id'], postgresql_where=text('live_online_user_id IS NOT NULL'))


def downgrade():
    op.drop_index('ix_vehicles_live_online', table_name='vehicles')
    op.drop_constraint('ck_vehicles_live_online', 'vehicles', type_='check')
    op.drop_column('vehicles', 'instant_booking')
    op.drop_column('vehicles', 'live_online_since')
    op.drop_column('vehicles', 'live_online_user_id')
