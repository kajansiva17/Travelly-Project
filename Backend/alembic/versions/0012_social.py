# The approved PRD `social_posts` and `social_interactions` tables (data dictionary tables 18 and 19): columns, named
# checks and indexes as specified. Owner decision 13 Nov 2026 adds one column, social_posts.view_count (with
# ck_social_posts_14), because the Reels screens show views and the PRD table has no view counter. With this migration
# all 20 PRD tables exist.
from alembic import op
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, PrimaryKeyConstraint, SmallInteger, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = '0012_social'
down_revision = '0011_road_alerts'
branch_labels = depends_on = None


def fk(table, column, target):
    return ForeignKey(target, name=f'fk_{table}_{column}', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False)


def common(table):
    return [
        Column('id', UUID(as_uuid=True), nullable=False, server_default=text('gen_random_uuid()')),
        Column('created_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
        Column('updated_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
        Column('created_by', UUID(as_uuid=True), fk(table, 'created_by', 'users.id'), nullable=True),
        Column('updated_by', UUID(as_uuid=True), fk(table, 'updated_by', 'users.id'), nullable=True),
        Column('version', Integer, nullable=False, server_default=text('1')),
    ]


def upgrade():
    t = 'social_posts'
    op.create_table(t, *common(t),
        Column('author_user_id', UUID(as_uuid=True), fk(t, 'author_user_id', 'users.id'), nullable=False),
        Column('post_type', String(8), nullable=False),
        Column('media_url', Text, nullable=True),
        Column('thumbnail_url', Text, nullable=True),
        Column('caption', Text, nullable=True),
        Column('hashtags', JSONB, nullable=False, server_default=text("'[]'::jsonb")),
        Column('location_name', String(150), nullable=True),
        Column('latitude', Numeric(9, 6), nullable=True),
        Column('longitude', Numeric(9, 6), nullable=True),
        Column('linked_vehicle_id', UUID(as_uuid=True), fk(t, 'linked_vehicle_id', 'vehicles.id'), nullable=True),
        Column('linked_route_id', UUID(as_uuid=True), fk(t, 'linked_route_id', 'routes.id'), nullable=True),
        Column('linked_scheduled_trip_id', UUID(as_uuid=True), fk(t, 'linked_scheduled_trip_id', 'scheduled_trips.id'), nullable=True),
        Column('visibility', String(12), nullable=False, server_default=text("'PRIVATE'")),
        Column('moderation_status', String(9), nullable=False, server_default=text("'PENDING'")),
        Column('published_at', DateTime(timezone=True), nullable=True),
        Column('duration_seconds', Integer, nullable=True),
        Column('denormalized_like_count', Integer, nullable=False, server_default=text('0')),
        Column('comment_count', Integer, nullable=False, server_default=text('0')),
        Column('share_count', Integer, nullable=False, server_default=text('0')),
        Column('view_count', Integer, nullable=False, server_default=text('0')),   # owner decision 13 Nov 2026
        PrimaryKeyConstraint('id', name='pk_social_posts'),
    )
    for name, condition in {
        'ck_social_posts_01': 'version>=1',
        'ck_social_posts_02': 'updated_at>=created_at',
        'ck_social_posts_03': "post_type IN ('REEL','PHOTO','REVIEW')",
        'ck_social_posts_04': "jsonb_typeof(hashtags)='array'",
        'ck_social_posts_05': 'location_name=btrim(location_name) AND char_length(location_name)>0',
        'ck_social_posts_06': 'latitude BETWEEN -90 AND 90',
        'ck_social_posts_07': 'longitude BETWEEN -180 AND 180',
        'ck_social_posts_08': "visibility IN ('PUBLIC','FOLLOWERS','PRIVATE')",
        'ck_social_posts_09': "moderation_status IN ('PENDING','APPROVED','REJECTED','HIDDEN')",
        'ck_social_posts_10': 'duration_seconds>=0',
        'ck_social_posts_11': 'denormalized_like_count>=0',
        'ck_social_posts_12': 'comment_count>=0',
        'ck_social_posts_13': 'share_count>=0',
        'ck_social_posts_14': 'view_count>=0',
    }.items():
        op.create_check_constraint(name, t, condition)
    op.create_index('ix_social_posts_01', t, ['moderation_status', 'published_at'])
    op.create_index('ix_social_posts_02', t, ['author_user_id', 'published_at'])
    op.create_index('ix_social_posts_created_by', t, ['created_by'], postgresql_where=text('created_by IS NOT NULL'))
    op.create_index('ix_social_posts_updated_by', t, ['updated_by'], postgresql_where=text('updated_by IS NOT NULL'))

    t = 'social_interactions'
    op.create_table(t, *common(t),
        Column('actor_user_id', UUID(as_uuid=True), fk(t, 'actor_user_id', 'users.id'), nullable=False),
        Column('post_id', UUID(as_uuid=True), fk(t, 'post_id', 'social_posts.id'), nullable=True),
        Column('target_user_id', UUID(as_uuid=True), fk(t, 'target_user_id', 'users.id'), nullable=True),
        Column('interaction_type', String(12), nullable=False),
        Column('comment_text', Text, nullable=True),
        Column('rating', SmallInteger, nullable=True),
        Column('report_reason', Text, nullable=True),
        Column('interaction_status', String(12), nullable=False, server_default=text("'ACTIVE'")),
        Column('parent_interaction_id', UUID(as_uuid=True), fk(t, 'parent_interaction_id', 'social_interactions.id'), nullable=True),
        Column('interaction_metadata', JSONB, nullable=False, server_default=text("'{}'::jsonb")),
        PrimaryKeyConstraint('id', name='pk_social_interactions'),
    )
    for name, condition in {
        'ck_social_interactions_01': "(interaction_type='FOLLOW' AND target_user_id IS NOT NULL AND post_id IS NULL) OR "
                                     "(interaction_type<>'FOLLOW' AND post_id IS NOT NULL AND target_user_id IS NULL)",
        'ck_social_interactions_02': 'rating IS NULL OR rating BETWEEN 1 AND 5',
        'ck_social_interactions_03': "interaction_type<>'RATING' OR rating IS NOT NULL",
        'ck_social_interactions_04': "parent_interaction_id IS NULL OR (parent_interaction_id<>id AND interaction_type='COMMENT')",
        'ck_social_interactions_05': 'version>=1',
        'ck_social_interactions_06': 'updated_at>=created_at',
        'ck_social_interactions_07': "interaction_type IN ('LIKE','COMMENT','SAVE','SHARE','FOLLOW','REPORT','RATING')",
        'ck_social_interactions_08': "interaction_status IN ('ACTIVE','REMOVED','UNDER_REVIEW','RESOLVED')",
        'ck_social_interactions_09': "jsonb_typeof(interaction_metadata)='object'",
    }.items():
        op.create_check_constraint(name, t, condition)
    op.create_index('ix_social_interactions_01', t, ['post_id', 'interaction_type', 'interaction_status'])
    op.create_index('ix_social_interactions_02', t, ['actor_user_id', 'post_id', 'interaction_type'], unique=True,
                    postgresql_where=text("interaction_status='ACTIVE' AND interaction_type IN ('LIKE','SAVE')"))
    op.create_index('ix_social_interactions_03', t, ['actor_user_id', 'target_user_id'], unique=True,
                    postgresql_where=text("interaction_status='ACTIVE' AND interaction_type='FOLLOW'"))
    op.create_index('ix_social_interactions_04', t, ['parent_interaction_id'])
    op.create_index('ix_social_interactions_created_by', t, ['created_by'], postgresql_where=text('created_by IS NOT NULL'))
    op.create_index('ix_social_interactions_updated_by', t, ['updated_by'], postgresql_where=text('updated_by IS NOT NULL'))


def downgrade():
    op.drop_table('social_interactions')
    op.drop_table('social_posts')
