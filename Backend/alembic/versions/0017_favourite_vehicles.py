# Owner decision 15 Nov 2026 (sidebar): a Passenger can keep favourite vehicles and hire one quickly.
# A favourite is only a bookmark: it changes no booking, price or availability. Removing it deletes just the bookmark.
from alembic import op
from sqlalchemy import Column, DateTime, ForeignKey, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID

revision = '0017_favourite_vehicles'
down_revision = '0016_booking_history'
branch_labels = depends_on = None


def upgrade():
    op.create_table('favourite_vehicles',
        Column('id', UUID(as_uuid=True), nullable=False, server_default=text('gen_random_uuid()'), primary_key=True),
        Column('user_id', UUID(as_uuid=True), ForeignKey('users.id', name='fk_favourite_vehicles_user_id', ondelete='CASCADE'), nullable=False),
        Column('vehicle_id', UUID(as_uuid=True), ForeignKey('vehicles.id', name='fk_favourite_vehicles_vehicle_id', ondelete='CASCADE'), nullable=False),
        Column('created_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
        UniqueConstraint('user_id', 'vehicle_id', name='uq_favourite_vehicles_user_vehicle'))
    op.create_index('ix_favourite_vehicles_user', 'favourite_vehicles', ['user_id', 'created_at'])


def downgrade():
    op.drop_index('ix_favourite_vehicles_user', table_name='favourite_vehicles')
    op.drop_table('favourite_vehicles')
