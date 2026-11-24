# Vehicle profile picture: set by the Owner at any time (no Admin approval); Admin can take it down with a reason.
from alembic import op
from sqlalchemy import Column, String, Text

revision = '0037_vehicle_profile_image'
down_revision = '0036_vehicle_display_name'
branch_labels = depends_on = None


def upgrade():
    op.add_column('vehicles', Column('profile_image_url', Text, nullable=True))
    op.add_column('vehicles', Column('profile_image_note', String(500), nullable=True))


def downgrade():
    op.drop_column('vehicles', 'profile_image_note')
    op.drop_column('vehicles', 'profile_image_url')
