# Several replacement offers can wait for one departure at once: each offer points back at the departure it would replace.
from alembic import op
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID

revision = '0042_departure_offers'
down_revision = '0041_departure_arrangement'
branch_labels = depends_on = None


def upgrade():
    op.add_column('scheduled_trips', Column('offer_for_scheduled_trip_id', UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_scheduled_trips_offer_for', 'scheduled_trips', 'scheduled_trips', ['offer_for_scheduled_trip_id'], ['id'], ondelete='RESTRICT')
    op.execute("UPDATE scheduled_trips o SET offer_for_scheduled_trip_id = t.id FROM scheduled_trips t WHERE t.replacement_scheduled_trip_id = o.id")
    op.create_index('ix_scheduled_trips_offer_for', 'scheduled_trips', ['offer_for_scheduled_trip_id'])


def downgrade():
    op.drop_index('ix_scheduled_trips_offer_for', table_name='scheduled_trips')
    op.drop_constraint('fk_scheduled_trips_offer_for', 'scheduled_trips', type_='foreignkey')
    op.drop_column('scheduled_trips', 'offer_for_scheduled_trip_id')
