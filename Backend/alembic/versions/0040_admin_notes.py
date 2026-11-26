# Admin notes: the Admin writes down exceptional cases (and can edit or delete them), optionally tied to one booking or departure.
from alembic import op
from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import UUID

revision = '0040_admin_notes'
down_revision = '0039_booking_chat'
branch_labels = depends_on = None


def upgrade():
    op.create_table('admin_notes',
        Column('id', UUID(as_uuid=True), nullable=False, server_default=text('gen_random_uuid()'), primary_key=True),
        Column('created_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
        Column('created_by', UUID(as_uuid=True), ForeignKey('users.id', name='fk_admin_notes_created_by', ondelete='RESTRICT'), nullable=False),
        Column('updated_at', DateTime(timezone=True), nullable=True),
        Column('updated_by', UUID(as_uuid=True), ForeignKey('users.id', name='fk_admin_notes_updated_by', ondelete='RESTRICT'), nullable=True),
        Column('deleted_at', DateTime(timezone=True), nullable=True),
        Column('deleted_by', UUID(as_uuid=True), ForeignKey('users.id', name='fk_admin_notes_deleted_by', ondelete='RESTRICT'), nullable=True),
        Column('summary', String(300), nullable=False),
        Column('details', Text, nullable=False),
        Column('booking_id', UUID(as_uuid=True), ForeignKey('bookings.id', name='fk_admin_notes_booking', ondelete='RESTRICT'), nullable=True),
        Column('scheduled_trip_id', UUID(as_uuid=True), ForeignKey('scheduled_trips.id', name='fk_admin_notes_departure', ondelete='RESTRICT'), nullable=True),
        CheckConstraint('char_length(summary) BETWEEN 1 AND 300', name='ck_admin_notes_summary'),
        CheckConstraint('char_length(details) BETWEEN 1 AND 5000', name='ck_admin_notes_details'),
        CheckConstraint('booking_id IS NULL OR scheduled_trip_id IS NULL', name='ck_admin_notes_one_link'))
    op.create_index('ix_admin_notes_created', 'admin_notes', ['created_at'])


def downgrade():
    op.drop_index('ix_admin_notes_created', table_name='admin_notes')
    op.drop_table('admin_notes')
