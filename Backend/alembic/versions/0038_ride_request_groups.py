# Book now to many vehicles at once: the requests of one ask share a group_id; the first operator to accept gets the trip and the rest are cancelled.
from alembic import op
from sqlalchemy import Column, text
from sqlalchemy.dialects.postgresql import UUID

revision = '0038_ride_request_groups'
down_revision = '0037_vehicle_profile_image'
branch_labels = depends_on = None


def upgrade():
    op.add_column('ride_requests', Column('group_id', UUID(as_uuid=True), nullable=True))
    op.create_index('ix_ride_requests_group', 'ride_requests', ['group_id'])
    op.drop_index('uq_ride_requests_passenger_open', table_name='ride_requests')
    op.create_index('ix_ride_requests_passenger_open', 'ride_requests', ['passenger_user_id'], postgresql_where=text("status='OFFERED'"))


def downgrade():
    op.drop_index('ix_ride_requests_passenger_open', table_name='ride_requests')
    op.create_index('uq_ride_requests_passenger_open', 'ride_requests', ['passenger_user_id'], unique=True, postgresql_where=text("status='OFFERED'"))
    op.drop_index('ix_ride_requests_group', table_name='ride_requests')
    op.drop_column('ride_requests', 'group_id')
