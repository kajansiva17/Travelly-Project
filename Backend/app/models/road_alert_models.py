"""ORM mapping for the approved PRD `road_alerts` table. DDL and CHECK constraints live in migration 0011_road_alerts."""
from sqlalchemy import Column, DateTime, Integer, Numeric, String, Table, Text, text
from sqlalchemy.dialects.postgresql import UUID
from app.models import Base

road_alerts_table = Table('road_alerts', Base.metadata,
    Column('id', UUID(as_uuid=True), nullable=False, server_default=text('gen_random_uuid()'), primary_key=True),
    Column('created_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
    Column('updated_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
    Column('created_by', UUID(as_uuid=True), nullable=True),
    Column('updated_by', UUID(as_uuid=True), nullable=True),
    Column('version', Integer, nullable=False, server_default=text('1')),
    Column('reporter_user_id', UUID(as_uuid=True), nullable=False),
    Column('trip_id', UUID(as_uuid=True), nullable=True),
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
    Column('moderated_by_user_id', UUID(as_uuid=True), nullable=True),
    Column('moderation_reason', Text, nullable=True),
)


class RoadAlert(Base):
    __table__ = road_alerts_table
