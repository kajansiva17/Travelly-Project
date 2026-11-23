# Passenger saved places (migration 0030).
from sqlalchemy import Table, Column, CheckConstraint, ForeignKey, Index, text, func
from sqlalchemy import String, DateTime, Numeric
from sqlalchemy.dialects.postgresql import UUID
from app.models import Base

saved_places_table = Table('saved_places', Base.metadata,
    Column('id', UUID(as_uuid=True), nullable=False, server_default=text('gen_random_uuid()'), primary_key=True),
    Column('created_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id', name='fk_saved_places_user', ondelete='CASCADE'), nullable=False),
    Column('name', String(30), nullable=False),
    Column('place_label', String(200), nullable=False),
    Column('latitude', Numeric(9, 6), nullable=False),
    Column('longitude', Numeric(9, 6), nullable=False),
    CheckConstraint('name=btrim(name) AND char_length(name)>0', name='ck_saved_places_name'),
    CheckConstraint('latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180', name='ck_saved_places_position'))
Index('uq_saved_places_name', saved_places_table.c.user_id, func.lower(saved_places_table.c.name), unique=True)


class SavedPlace(Base):
    __table__ = saved_places_table
