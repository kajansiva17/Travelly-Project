# Passenger saved places (sidebar > Saved Places): a few named places (Home, Work ...) the person picks with one tap when booking.
# Only the label and coordinates are stored; a fresh signed location proof is made each time the list is read.
from alembic import op
from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Numeric, String, text
from sqlalchemy.dialects.postgresql import UUID

revision = '0030_saved_places'
down_revision = '0029_wait_confirm'
branch_labels = depends_on = None


def upgrade():
    op.create_table('saved_places',
        Column('id', UUID(as_uuid=True), nullable=False, server_default=text('gen_random_uuid()'), primary_key=True),
        Column('created_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
        Column('user_id', UUID(as_uuid=True), ForeignKey('users.id', name='fk_saved_places_user', ondelete='CASCADE'), nullable=False),
        Column('name', String(30), nullable=False),
        Column('place_label', String(200), nullable=False),
        Column('latitude', Numeric(9, 6), nullable=False),
        Column('longitude', Numeric(9, 6), nullable=False),
        CheckConstraint('name=btrim(name) AND char_length(name)>0', name='ck_saved_places_name'),
        CheckConstraint('latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180', name='ck_saved_places_position'))
    op.create_index('uq_saved_places_name', 'saved_places', [text('user_id'), text('lower(name)')], unique=True)


def downgrade():
    op.drop_index('uq_saved_places_name', table_name='saved_places')
    op.drop_table('saved_places')
