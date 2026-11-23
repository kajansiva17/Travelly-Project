# Trip reviews (migration 0032): one review per finished trip, written by the Passenger, answered once by the Owner.
from sqlalchemy import Table, Column, CheckConstraint, ForeignKey, Index, UniqueConstraint, text
from sqlalchemy import DateTime, SmallInteger, Text
from sqlalchemy.dialects.postgresql import UUID
from app.models import Base

trip_reviews_table = Table('trip_reviews', Base.metadata,
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
    Column('edited_at', DateTime(timezone=True), nullable=True),
    Column('hidden_at', DateTime(timezone=True), nullable=True),
    Column('hidden_note', Text, nullable=True),
    UniqueConstraint('trip_id', name='uq_trip_reviews_trip'),
    CheckConstraint('rating BETWEEN 1 AND 5', name='ck_trip_reviews_rating'),
    CheckConstraint('driver_rating IS NULL OR (driver_user_id IS NOT NULL AND driver_rating BETWEEN 1 AND 5)', name='ck_trip_reviews_driver_rating'),
    CheckConstraint('comment IS NULL OR char_length(comment) BETWEEN 1 AND 500', name='ck_trip_reviews_comment'),
    CheckConstraint('(reply IS NULL) = (replied_at IS NULL) AND (reply IS NULL OR char_length(reply) BETWEEN 1 AND 300)', name='ck_trip_reviews_reply'),
    CheckConstraint('(hidden_at IS NULL) = (hidden_note IS NULL) AND (hidden_note IS NULL OR char_length(hidden_note) BETWEEN 1 AND 300)', name='ck_trip_reviews_hidden'),
    Index('ix_trip_reviews_owner', 'owner_user_id', 'created_at'))


class TripReview(Base):
    __table__ = trip_reviews_table
