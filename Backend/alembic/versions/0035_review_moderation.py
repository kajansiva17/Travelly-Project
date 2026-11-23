# Review extras: the Admin can hide a review (hidden reviews drop out of every average and out of the Owner's list), and the
# notifications table accepts a REVIEW type so Owners, Drivers and Passengers can be told about reviews and replies.
from alembic import op
from sqlalchemy import Column, DateTime, Text

revision = '0035_review_moderation'
down_revision = '0034_wait_prompt_report'
branch_labels = depends_on = None

OLD = "notification_type IN ('BOOKING_REQUEST','BOOKING_CONFIRMED','DRIVER_ASSIGNMENT','RECONFIRMATION','PAYMENT','REFUND','REPLACEMENT','MAINTENANCE_DUE','DOCUMENT_EXPIRY','ROAD_ALERT','ADMIN_ACTION')"
NEW = "notification_type IN ('BOOKING_REQUEST','BOOKING_CONFIRMED','DRIVER_ASSIGNMENT','RECONFIRMATION','PAYMENT','REFUND','REPLACEMENT','MAINTENANCE_DUE','DOCUMENT_EXPIRY','ROAD_ALERT','ADMIN_ACTION','REVIEW')"


def upgrade():
    op.add_column('trip_reviews', Column('hidden_at', DateTime(timezone=True), nullable=True))
    op.add_column('trip_reviews', Column('hidden_note', Text, nullable=True))
    op.create_check_constraint('ck_trip_reviews_hidden', 'trip_reviews',
                               '(hidden_at IS NULL) = (hidden_note IS NULL) AND (hidden_note IS NULL OR char_length(hidden_note) BETWEEN 1 AND 300)')
    op.drop_constraint('ck_notifications_03', 'notifications', type_='check')
    op.create_check_constraint('ck_notifications_03', 'notifications', NEW)


def downgrade():
    op.execute("DELETE FROM notifications WHERE notification_type = 'REVIEW'")
    op.drop_constraint('ck_notifications_03', 'notifications', type_='check')
    op.create_check_constraint('ck_notifications_03', 'notifications', OLD)
    op.drop_constraint('ck_trip_reviews_hidden', 'trip_reviews', type_='check')
    op.drop_column('trip_reviews', 'hidden_note')
    op.drop_column('trip_reviews', 'hidden_at')
