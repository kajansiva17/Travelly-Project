"""ORM mapping for the PRD `social_posts` and `social_interactions` tables (+ view_count, owner decision 13 Nov 2026).
DDL and CHECK constraints live in migration 0012_social."""
from sqlalchemy import Column, DateTime, Integer, Numeric, SmallInteger, String, Table, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from app.models import Base


def common():
    return [Column('id', UUID(as_uuid=True), nullable=False, server_default=text('gen_random_uuid()'), primary_key=True),
            Column('created_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
            Column('updated_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
            Column('created_by', UUID(as_uuid=True), nullable=True),
            Column('updated_by', UUID(as_uuid=True), nullable=True),
            Column('version', Integer, nullable=False, server_default=text('1'))]


social_posts_table = Table('social_posts', Base.metadata, *common(),
    Column('author_user_id', UUID(as_uuid=True), nullable=False),
    Column('post_type', String(8), nullable=False),
    Column('media_url', Text, nullable=True),
    Column('thumbnail_url', Text, nullable=True),
    Column('caption', Text, nullable=True),
    Column('hashtags', JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    Column('location_name', String(150), nullable=True),
    Column('latitude', Numeric(9, 6), nullable=True),
    Column('longitude', Numeric(9, 6), nullable=True),
    Column('linked_vehicle_id', UUID(as_uuid=True), nullable=True),
    Column('linked_route_id', UUID(as_uuid=True), nullable=True),
    Column('linked_scheduled_trip_id', UUID(as_uuid=True), nullable=True),
    Column('visibility', String(12), nullable=False, server_default=text("'PRIVATE'")),
    Column('moderation_status', String(9), nullable=False, server_default=text("'PENDING'")),
    Column('published_at', DateTime(timezone=True), nullable=True),
    Column('duration_seconds', Integer, nullable=True),
    Column('denormalized_like_count', Integer, nullable=False, server_default=text('0')),
    Column('comment_count', Integer, nullable=False, server_default=text('0')),
    Column('share_count', Integer, nullable=False, server_default=text('0')),
    Column('view_count', Integer, nullable=False, server_default=text('0')),
)

social_interactions_table = Table('social_interactions', Base.metadata, *common(),
    Column('actor_user_id', UUID(as_uuid=True), nullable=False),
    Column('post_id', UUID(as_uuid=True), nullable=True),
    Column('target_user_id', UUID(as_uuid=True), nullable=True),
    Column('interaction_type', String(12), nullable=False),
    Column('comment_text', Text, nullable=True),
    Column('rating', SmallInteger, nullable=True),
    Column('report_reason', Text, nullable=True),
    Column('interaction_status', String(12), nullable=False, server_default=text("'ACTIVE'")),
    Column('parent_interaction_id', UUID(as_uuid=True), nullable=True),
    Column('interaction_metadata', JSONB, nullable=False, server_default=text("'{}'::jsonb")),
)


class SocialPost(Base):
    __table__ = social_posts_table


class SocialInteraction(Base):
    __table__ = social_interactions_table
