# The approved PRD `road_alerts` table (data dictionary, table 20 of 20), exactly as specified: columns, named checks
# and indexes. No other table is added. Road safety only: no stored geospatial point column (bounded coordinate
# indexes and distance calculation), no GPS history. Owner decisions 12 Nov 2026: per-type expiry, 15 km relevance,
# confirm/deny by nearby Drivers, button and voice input with Driver confirmation.
from alembic import op
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, PrimaryKeyConstraint, String, Text, text
from sqlalchemy.dialects.postgresql import UUID

revision = '0011_road_alerts'
down_revision = '0010_payments'
branch_labels = depends_on = None


def fk(column, target):
    return ForeignKey(target, name=f'fk_road_alerts_{column}', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False)


def upgrade():
    op.create_table(
        'road_alerts',
        Column('id', UUID(as_uuid=True), nullable=False, server_default=text('gen_random_uuid()')),
        Column('created_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
        Column('updated_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
        Column('created_by', UUID(as_uuid=True), fk('created_by', 'users.id'), nullable=True),
        Column('updated_by', UUID(as_uuid=True), fk('updated_by', 'users.id'), nullable=True),
        Column('version', Integer, nullable=False, server_default=text('1')),
        Column('reporter_user_id', UUID(as_uuid=True), fk('reporter_user_id', 'users.id'), nullable=False),
        Column('trip_id', UUID(as_uuid=True), fk('trip_id', 'trips.id'), nullable=True),
        Column('alert_type', String(20), nullable=False),
        Column('latitude', Numeric(9, 6), nullable=False),
        Column('longitude', Numeric(9, 6), nullable=False),
        Column('travel_direction_degrees', Numeric(6, 3), nullable=True),
        Column('description', Text, nullable=True),
        Column('source_input', String(8), nullable=False),
        Column('status', String(12), nullable=False, server_default=text("'UNCONFIRMED'")),
        Column('confidence_score', Numeric(5, 4), nullable=True),
        Column('confirmation_count', Integer, nullable=False, server_default=text('0')),
        Column('denial_count', Integer, nullable=False, server_default=text('0')),
        Column('reported_at', DateTime(timezone=True), nullable=False),
        Column('verified_at', DateTime(timezone=True), nullable=True),
        Column('expires_at', DateTime(timezone=True), nullable=False),
        Column('moderated_by_user_id', UUID(as_uuid=True), fk('moderated_by_user_id', 'users.id'), nullable=True),
        Column('moderation_reason', Text, nullable=True),
        PrimaryKeyConstraint('id', name='pk_road_alerts'),
    )
    checks = {
        'ck_road_alerts_01': 'travel_direction_degrees IS NULL OR (travel_direction_degrees>=0 AND travel_direction_degrees<360)',
        'ck_road_alerts_02': 'confidence_score IS NULL OR confidence_score BETWEEN 0 AND 1',
        'ck_road_alerts_03': 'expires_at>reported_at',
        'ck_road_alerts_04': 'version>=1',
        'ck_road_alerts_05': 'updated_at>=created_at',
        'ck_road_alerts_06': "alert_type IN ('POLICE_PRESENCE','SPEED_CHECK','ACCIDENT','ROADBLOCK','ROAD_HAZARD')",
        'ck_road_alerts_07': 'latitude BETWEEN -90 AND 90',
        'ck_road_alerts_08': 'longitude BETWEEN -180 AND 180',
        'ck_road_alerts_09': "source_input IN ('BUTTON','VOICE')",
        'ck_road_alerts_10': "status IN ('ACTIVE','UNCONFIRMED','VERIFIED','EXPIRED','REJECTED','REMOVED')",
        'ck_road_alerts_11': 'confirmation_count>=0',
        'ck_road_alerts_12': 'denial_count>=0',
    }
    for name, condition in checks.items():
        op.create_check_constraint(name, 'road_alerts', condition)
    op.create_index('ix_road_alerts_01', 'road_alerts', ['status', 'expires_at'])
    op.create_index('ix_road_alerts_02', 'road_alerts', ['trip_id'])
    op.create_index('ix_road_alerts_03', 'road_alerts', ['reporter_user_id'])
    op.create_index('ix_road_alerts_04', 'road_alerts', ['latitude', 'longitude'])
    op.create_index('ix_road_alerts_created_by', 'road_alerts', ['created_by'], postgresql_where=text('created_by IS NOT NULL'))
    op.create_index('ix_road_alerts_updated_by', 'road_alerts', ['updated_by'], postgresql_where=text('updated_by IS NOT NULL'))


def downgrade():
    op.drop_table('road_alerts')
