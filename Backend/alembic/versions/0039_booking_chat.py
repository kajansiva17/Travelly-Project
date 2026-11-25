# Booking chat: the people on a confirmed booking (Passenger, Owner, assigned Driver) can write to each other until the trip ends.
# Notifications accept a CHAT type so the others are told about a new message (the text is never put in the notice).
from alembic import op
from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = '0039_booking_chat'
down_revision = '0038_ride_request_groups'
branch_labels = depends_on = None

OLD = "notification_type IN ('BOOKING_REQUEST','BOOKING_CONFIRMED','DRIVER_ASSIGNMENT','RECONFIRMATION','PAYMENT','REFUND','REPLACEMENT','MAINTENANCE_DUE','DOCUMENT_EXPIRY','ROAD_ALERT','ADMIN_ACTION','REVIEW')"
NEW = "notification_type IN ('BOOKING_REQUEST','BOOKING_CONFIRMED','DRIVER_ASSIGNMENT','RECONFIRMATION','PAYMENT','REFUND','REPLACEMENT','MAINTENANCE_DUE','DOCUMENT_EXPIRY','ROAD_ALERT','ADMIN_ACTION','REVIEW','CHAT')"


def upgrade():
    op.create_table('booking_messages',
        Column('id', UUID(as_uuid=True), nullable=False, server_default=text('gen_random_uuid()'), primary_key=True),
        Column('created_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
        Column('booking_id', UUID(as_uuid=True), ForeignKey('bookings.id', name='fk_booking_messages_booking', ondelete='RESTRICT'), nullable=False),
        Column('sender_user_id', UUID(as_uuid=True), ForeignKey('users.id', name='fk_booking_messages_sender', ondelete='RESTRICT'), nullable=False),
        Column('body', Text, nullable=False),
        Column('read_by', JSONB, nullable=False, server_default=text("'[]'::jsonb")),
        CheckConstraint('char_length(body) BETWEEN 1 AND 500', name='ck_booking_messages_body'),
        CheckConstraint("jsonb_typeof(read_by)='array'", name='ck_booking_messages_read_by'))
    op.create_index('ix_booking_messages_booking', 'booking_messages', ['booking_id', 'created_at'])
    op.drop_constraint('ck_notifications_03', 'notifications', type_='check')
    op.create_check_constraint('ck_notifications_03', 'notifications', NEW)


def downgrade():
    op.execute("DELETE FROM notifications WHERE notification_type = 'CHAT'")
    op.drop_constraint('ck_notifications_03', 'notifications', type_='check')
    op.create_check_constraint('ck_notifications_03', 'notifications', OLD)
    op.drop_index('ix_booking_messages_booking', table_name='booking_messages')
    op.drop_table('booking_messages')
