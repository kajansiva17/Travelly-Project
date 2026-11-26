# A reported departure problem records who finds the passengers another journey: the Owner or Travelly.
from alembic import op
from sqlalchemy import Column, String

revision = '0041_departure_arrangement'
down_revision = '0040_admin_notes'
branch_labels = depends_on = None


def upgrade():
    op.add_column('scheduled_trips', Column('arrangement', String(10), nullable=True))
    op.create_check_constraint('ck_scheduled_trips_arrangement', 'scheduled_trips', "arrangement IS NULL OR arrangement IN ('OWNER','TRAVELLY')")


def downgrade():
    op.drop_constraint('ck_scheduled_trips_arrangement', 'scheduled_trips', type_='check')
    op.drop_column('scheduled_trips', 'arrangement')
