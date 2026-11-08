# Planned rate tables, generated from the frozen 02C dictionary.
from sqlalchemy import Table, Column, CheckConstraint, ForeignKey, Index, UniqueConstraint, text
from sqlalchemy import String, Text, Integer, SmallInteger, BigInteger, Boolean, Date, DateTime, Numeric, CHAR
from sqlalchemy.dialects.postgresql import UUID, CITEXT, JSONB
from app.models import Base
import app.models.review_models as review_models  # register vehicles before resolving rate FKs

service_types_table = Table('service_types', Base.metadata,
    Column('id', UUID(as_uuid=True), nullable=False, server_default=text('gen_random_uuid()'), primary_key=True),
    Column('created_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
    Column('updated_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
    Column('created_by', UUID(as_uuid=True), ForeignKey('users.id', name='fk_service_types_created_by', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('updated_by', UUID(as_uuid=True), ForeignKey('users.id', name='fk_service_types_updated_by', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('version', Integer, nullable=False, server_default=text('1')),
    Column('code', CITEXT, nullable=False),
    Column('name', String(100), nullable=False),
    Column('description', Text, nullable=True),
    Column('category', String(16), nullable=False),
    Column('is_active', Boolean, nullable=False, server_default=text('false')),
    Column('display_order', Integer, nullable=False, server_default=text('0')),
    Column('default_pricing_basis', String(16), nullable=False),
    Column('settings', JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    CheckConstraint('version>=1', name='ck_service_types_01'),
    CheckConstraint('updated_at>=created_at', name='ck_service_types_02'),
    CheckConstraint('name=btrim(name) AND char_length(name)>0', name='ck_service_types_03'),
    CheckConstraint("category IN ('PRIVATE_HIRE','TICKET_HIRE','RENTAL')", name='ck_service_types_04'),
    CheckConstraint('display_order>=0', name='ck_service_types_05'),
    CheckConstraint("default_pricing_basis IN ('FIXED','DISTANCE','TIME','PER_SEAT','OWNER_QUOTE')", name='ck_service_types_06'),
    CheckConstraint("jsonb_typeof(settings)='object'", name='ck_service_types_07'),
    UniqueConstraint('code', name='uq_service_types_01'),
)
Index('ix_service_types_01', service_types_table.c.category, service_types_table.c.is_active)
Index('ix_service_types_02', service_types_table.c.display_order)
Index('ix_service_types_created_by', service_types_table.c.created_by, postgresql_where=text('created_by IS NOT NULL'))
Index('ix_service_types_updated_by', service_types_table.c.updated_by, postgresql_where=text('updated_by IS NOT NULL'))
service_types_table.primary_key.name = 'pk_service_types'

vehicle_services_table = Table('vehicle_services', Base.metadata,
    Column('id', UUID(as_uuid=True), nullable=False, server_default=text('gen_random_uuid()'), primary_key=True),
    Column('created_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
    Column('updated_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
    Column('created_by', UUID(as_uuid=True), ForeignKey('users.id', name='fk_vehicle_services_created_by', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('updated_by', UUID(as_uuid=True), ForeignKey('users.id', name='fk_vehicle_services_updated_by', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('version', Integer, nullable=False, server_default=text('1')),
    Column('vehicle_id', UUID(as_uuid=True), ForeignKey('vehicles.id', name='fk_vehicle_services_vehicle_id', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=False),
    Column('service_type_id', UUID(as_uuid=True), ForeignKey('service_types.id', name='fk_vehicle_services_service_type_id', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=False),
    Column('is_enabled', Boolean, nullable=False, server_default=text('false')),
    Column('pricing_basis', String(16), nullable=False),
    Column('base_price', Numeric(12,2), nullable=True),
    Column('price_per_km', Numeric(12,2), nullable=True),
    Column('price_per_hour', Numeric(12,2), nullable=True),
    Column('currency', CHAR(3), nullable=False),
    Column('minimum_hire_hours', Numeric(8,2), nullable=True),
    Column('minimum_hire_km', Numeric(10,2), nullable=True),
    Column('available_from', Date, nullable=True),
    Column('available_until', Date, nullable=True),
    Column('owner_terms', JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    CheckConstraint('available_from IS NULL OR available_until IS NULL OR available_until>=available_from', name='ck_vehicle_services_01'),
    CheckConstraint('version>=1', name='ck_vehicle_services_02'),
    CheckConstraint('updated_at>=created_at', name='ck_vehicle_services_03'),
    CheckConstraint("pricing_basis IN ('FIXED','DISTANCE','TIME','PER_SEAT','OWNER_QUOTE')", name='ck_vehicle_services_04'),
    CheckConstraint('base_price>=0', name='ck_vehicle_services_05'),
    CheckConstraint('price_per_km>=0', name='ck_vehicle_services_06'),
    CheckConstraint('price_per_hour>=0', name='ck_vehicle_services_07'),
    CheckConstraint("currency ~ '^[A-Z]{3}$'", name='ck_vehicle_services_08'),
    CheckConstraint('minimum_hire_hours>=0', name='ck_vehicle_services_09'),
    CheckConstraint('minimum_hire_km>=0', name='ck_vehicle_services_10'),
    CheckConstraint("jsonb_typeof(owner_terms)='object'", name='ck_vehicle_services_11'),
    UniqueConstraint('vehicle_id', 'service_type_id', name='uq_vehicle_services_01'),
)
Index('ix_vehicle_services_01', vehicle_services_table.c.service_type_id, vehicle_services_table.c.is_enabled)
Index('ix_vehicle_services_02', vehicle_services_table.c.vehicle_id)
Index('ix_vehicle_services_created_by', vehicle_services_table.c.created_by, postgresql_where=text('created_by IS NOT NULL'))
Index('ix_vehicle_services_updated_by', vehicle_services_table.c.updated_by, postgresql_where=text('updated_by IS NOT NULL'))
vehicle_services_table.primary_key.name = 'pk_vehicle_services'

class ServiceType(Base):
    __table__ = service_types_table

class VehicleService(Base):
    __table__ = vehicle_services_table

