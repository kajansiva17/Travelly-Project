# Owner-chosen vehicle name: shown to the Owner and to Passengers instead of the make/model/registration text.
from alembic import op
from sqlalchemy import Column, String

revision = '0036_vehicle_display_name'
down_revision = '0035_review_moderation'
branch_labels = depends_on = None


def upgrade():
    op.add_column('vehicles', Column('display_name', String(80), nullable=True))


def downgrade():
    op.drop_column('vehicles', 'display_name')
