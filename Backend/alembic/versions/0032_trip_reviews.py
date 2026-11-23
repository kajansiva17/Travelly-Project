# Trip reviews: after a finished trip the Passenger rates it once (vehicle and service, optionally the Driver) and may write a comment;
# the Owner of the vehicle reads the reviews and may reply once.
from alembic import op
from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, SmallInteger, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID

revision = '0032_trip_reviews'
down_revision = '0031_support_chat'
branch_labels = depends_on = None


def upgrade():
    op.create_table('trip_reviews',
        Column('id', UUID(as_uuid=True), nullable=False, server_default=text('gen_random_uuid()'), primary_key=True),
        Column('created_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
        Column('trip_id', UUID(as_uuid=True), ForeignKey('trips.id', name='fk_trip_reviews_trip', ondelete='RESTRICT'), nullable=False),
        Column('booking_id', UUID(as_uuid=True), ForeignKey('bookings.id', name='fk_trip_reviews_booking', ondelete='RESTRICT'), nullable=False),
        Column('vehicle_id', UUID(as_uuid=True), ForeignKey('vehicles.id', name='fk_trip_reviews_vehicle', ondelete='RESTRICT'), nullable=False),
        Column('passenger_user_id', UUID(as_uuid=True), ForeignKey('users.id', name='fk_trip_reviews_passenger', ondelete='RESTRICT'), nullable=False),
        Column('owner_user_id', UUID(as_uuid=True), ForeignKey('users.id', name='fk_trip_reviews_owner', ondelete='RESTRICT'), nullable=False),
        Column('driver_user_id', UUID(as_uuid=True), ForeignKey('users.id', name='fk_trip_reviews_driver', ondelete='RESTRICT'), nullable=True),
        Column('rating', SmallInteger, nullable=False),
        Column('driver_rating', SmallInteger, nullable=True),
        Column('comment', Text, nullable=True),
        Column('reply', Text, nullable=True),
        Column('replied_at', DateTime(timezone=True), nullable=True),
        UniqueConstraint('trip_id', name='uq_trip_reviews_trip'),
        CheckConstraint('rating BETWEEN 1 AND 5', name='ck_trip_reviews_rating'),
        CheckConstraint('driver_rating IS NULL OR (driver_user_id IS NOT NULL AND driver_rating BETWEEN 1 AND 5)', name='ck_trip_reviews_driver_rating'),
        CheckConstraint('comment IS NULL OR char_length(comment) BETWEEN 1 AND 500', name='ck_trip_reviews_comment'),
        CheckConstraint('(reply IS NULL) = (replied_at IS NULL) AND (reply IS NULL OR char_length(reply) BETWEEN 1 AND 300)', name='ck_trip_reviews_reply'))
    op.create_index('ix_trip_reviews_owner', 'trip_reviews', ['owner_user_id', 'created_at'])


def downgrade():
    op.drop_table('trip_reviews')
