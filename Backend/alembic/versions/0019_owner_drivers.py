# Owner decision 15 Nov 2026: "My drivers" is the Owner's own saved list of Drivers (a bookmark only, not a relationship).
from alembic import op
from sqlalchemy import Column, DateTime, ForeignKey, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID

revision = '0019_owner_drivers'
down_revision = '0018_vehicle_removed'
branch_labels = depends_on = None


def upgrade():
    op.create_table('owner_drivers',
        Column('id', UUID(as_uuid=True), nullable=False, server_default=text('gen_random_uuid()'), primary_key=True),
        Column('owner_user_id', UUID(as_uuid=True), ForeignKey('users.id', name='fk_owner_drivers_owner_user_id', ondelete='CASCADE'), nullable=False),
        Column('driver_user_id', UUID(as_uuid=True), ForeignKey('users.id', name='fk_owner_drivers_driver_user_id', ondelete='CASCADE'), nullable=False),
        Column('nickname', String(60), nullable=True),
        Column('created_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
        UniqueConstraint('owner_user_id', 'driver_user_id', name='uq_owner_drivers_owner_driver'))
    op.create_index('ix_owner_drivers_owner', 'owner_drivers', ['owner_user_id', 'created_at'])


def downgrade():
    op.drop_index('ix_owner_drivers_owner', table_name='owner_drivers')
    op.drop_table('owner_drivers')
