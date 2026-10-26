# Frozen 02C physical definitions; no operational vehicle endpoints.
from sqlalchemy import Table, Column, CheckConstraint, ForeignKey, Index, UniqueConstraint, text
from sqlalchemy import String, Text, Integer, SmallInteger, BigInteger, Boolean, Date, DateTime, Numeric, CHAR
from sqlalchemy.dialects.postgresql import UUID, CITEXT, JSONB
from sqlalchemy import MetaData
class Snapshot:
    metadata = MetaData()
Base = Snapshot
Table("users", Base.metadata, Column("id", UUID(as_uuid=True), primary_key=True))

vehicles_table = Table('vehicles', Base.metadata,
    Column('id', UUID(as_uuid=True), nullable=False, server_default=text('gen_random_uuid()'), primary_key=True),
    Column('created_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
    Column('updated_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
    Column('created_by', UUID(as_uuid=True), ForeignKey('users.id', name='fk_vehicles_created_by', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('updated_by', UUID(as_uuid=True), ForeignKey('users.id', name='fk_vehicles_updated_by', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('version', Integer, nullable=False, server_default=text('1')),
    Column('public_vehicle_reference', String(20), nullable=False),
    Column('owner_user_id', UUID(as_uuid=True), ForeignKey('users.id', name='fk_vehicles_owner_user_id', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=False),
    Column('default_driver_user_id', UUID(as_uuid=True), ForeignKey('users.id', name='fk_vehicles_default_driver_user_id', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('registration_number', CITEXT, nullable=False),
    Column('vehicle_type_code', String(60), nullable=True),
    Column('make', String(80), nullable=True),
    Column('model', String(80), nullable=True),
    Column('manufacture_year', SmallInteger, nullable=True),
    Column('colour', String(40), nullable=True),
    Column('power_type', String(4), nullable=True),
    Column('engine_fuel_type', String(6), nullable=True),
    Column('seat_capacity', SmallInteger, nullable=True),
    Column('large_luggage_capacity', SmallInteger, nullable=True),
    Column('small_luggage_capacity', SmallInteger, nullable=True),
    Column('current_odometer_km', Numeric(12,1), nullable=True),
    Column('odometer_updated_at', DateTime(timezone=True), nullable=True),
    Column('transmission_type', String(40), nullable=True),
    Column('air_conditioned', Boolean, nullable=True),
    Column('description', Text, nullable=True),
    Column('media', JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    Column('verification_status', String(9), nullable=False, server_default=text("'DRAFT'")),
    Column('availability_status', String(20), nullable=False, server_default=text("'DRAFT'")),
    Column('is_published', Boolean, nullable=False, server_default=text('false')),
    Column('approved_by', UUID(as_uuid=True), ForeignKey('users.id', name='fk_vehicles_approved_by', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('approved_at', DateTime(timezone=True), nullable=True),
    CheckConstraint('char_length(btrim(registration_number::text)) BETWEEN 1 AND 40', name='ck_vehicles_01'),
    CheckConstraint("power_type IS DISTINCT FROM 'BEV' OR engine_fuel_type IS NULL", name='ck_vehicles_02'),
    CheckConstraint("power_type IS NULL OR power_type='BEV' OR engine_fuel_type IS NOT NULL", name='ck_vehicles_03'),
    CheckConstraint("NOT is_published OR verification_status='APPROVED'", name='ck_vehicles_04'),
    CheckConstraint("verification_status<>'APPROVED' OR (approved_by IS NOT NULL AND approved_at IS NOT NULL)", name='ck_vehicles_05'),
    CheckConstraint('version>=1', name='ck_vehicles_06'),
    CheckConstraint('updated_at>=created_at', name='ck_vehicles_07'),
    CheckConstraint('public_vehicle_reference=btrim(public_vehicle_reference) AND char_length(public_vehicle_reference)>0', name='ck_vehicles_08'),
    CheckConstraint('vehicle_type_code=btrim(vehicle_type_code) AND char_length(vehicle_type_code)>0', name='ck_vehicles_09'),
    CheckConstraint('make=btrim(make) AND char_length(make)>0', name='ck_vehicles_10'),
    CheckConstraint('model=btrim(model) AND char_length(model)>0', name='ck_vehicles_11'),
    CheckConstraint('manufacture_year>0', name='ck_vehicles_12'),
    CheckConstraint('colour=btrim(colour) AND char_length(colour)>0', name='ck_vehicles_13'),
    CheckConstraint("power_type IN ('ICE','MHEV','HEV','PHEV','BEV')", name='ck_vehicles_14'),
    CheckConstraint("engine_fuel_type IN ('PETROL','DIESEL')", name='ck_vehicles_15'),
    CheckConstraint('seat_capacity>=0', name='ck_vehicles_16'),
    CheckConstraint('large_luggage_capacity>=0', name='ck_vehicles_17'),
    CheckConstraint('small_luggage_capacity>=0', name='ck_vehicles_18'),
    CheckConstraint('current_odometer_km>=0', name='ck_vehicles_19'),
    CheckConstraint('transmission_type=btrim(transmission_type) AND char_length(transmission_type)>0', name='ck_vehicles_20'),
    CheckConstraint("jsonb_typeof(media)='array'", name='ck_vehicles_21'),
    CheckConstraint("verification_status IN ('DRAFT','SUBMITTED','APPROVED','REJECTED','SUSPENDED')", name='ck_vehicles_22'),
    CheckConstraint("availability_status IN ('DRAFT','PENDING_VERIFICATION','ACTIVE','BOOKED','ON_TRIP','MAINTENANCE','SUSPENDED','INACTIVE')", name='ck_vehicles_23'),
    UniqueConstraint('public_vehicle_reference', name='uq_vehicles_01'),
    UniqueConstraint('registration_number', name='uq_vehicles_02'),
)
Index('ix_vehicles_01', vehicles_table.c.owner_user_id)
Index('ix_vehicles_02', vehicles_table.c.verification_status, vehicles_table.c.is_published, vehicles_table.c.availability_status)
Index('ix_vehicles_03', vehicles_table.c.vehicle_type_code)
Index('ix_vehicles_04', vehicles_table.c.availability_status)
Index('ix_vehicles_created_by', vehicles_table.c.created_by, postgresql_where=text('created_by IS NOT NULL'))
Index('ix_vehicles_updated_by', vehicles_table.c.updated_by, postgresql_where=text('updated_by IS NOT NULL'))
vehicles_table.primary_key.name = 'pk_vehicles'

documents_table = Table('documents', Base.metadata,
    Column('id', UUID(as_uuid=True), nullable=False, server_default=text('gen_random_uuid()'), primary_key=True),
    Column('created_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
    Column('updated_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
    Column('created_by', UUID(as_uuid=True), ForeignKey('users.id', name='fk_documents_created_by', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('updated_by', UUID(as_uuid=True), ForeignKey('users.id', name='fk_documents_updated_by', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('version', Integer, nullable=False, server_default=text('1')),
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id', name='fk_documents_user_id', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('vehicle_id', UUID(as_uuid=True), ForeignKey('vehicles.id', name='fk_documents_vehicle_id', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('document_type', String(60), nullable=False),
    Column('document_number', String(100), nullable=True),
    Column('issuing_country', CHAR(2), nullable=True),
    Column('issue_date', Date, nullable=True),
    Column('expiry_date', Date, nullable=True),
    Column('storage_key', Text, nullable=False),
    Column('secure_file_url', Text, nullable=True),
    Column('original_file_name', String(255), nullable=False),
    Column('mime_type', String(100), nullable=False),
    Column('file_size_bytes', BigInteger, nullable=False),
    Column('file_checksum', CHAR(64), nullable=False),
    Column('status', String(20), nullable=False, server_default=text("'DRAFT'")),
    Column('submitted_at', DateTime(timezone=True), nullable=True),
    Column('verified_by', UUID(as_uuid=True), ForeignKey('users.id', name='fk_documents_verified_by', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('verified_at', DateTime(timezone=True), nullable=True),
    Column('rejection_reason', Text, nullable=True),
    Column('superseded_document_id', UUID(as_uuid=True), ForeignKey('documents.id', name='fk_documents_superseded_document_id', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    CheckConstraint('(user_id IS NOT NULL)::int + (vehicle_id IS NOT NULL)::int = 1', name='ck_documents_01'),
    CheckConstraint("issuing_country IS NULL OR issuing_country ~ '^[A-Z]{2}$'", name='ck_documents_02'),
    CheckConstraint('issue_date IS NULL OR expiry_date IS NULL OR expiry_date>=issue_date', name='ck_documents_03'),
    CheckConstraint("secure_file_url IS NULL OR secure_file_url='/api/v1/documents/'||id::text||'/file'", name='ck_documents_04'),
    CheckConstraint('char_length(storage_key) BETWEEN 1 AND 200', name='ck_documents_05'),
    CheckConstraint("mime_type IN ('application/pdf','image/jpeg','image/png')", name='ck_documents_06'),
    CheckConstraint('file_size_bytes BETWEEN 1 AND 10485760', name='ck_documents_07'),
    CheckConstraint("file_checksum ~ '^[0-9a-f]{64}$'", name='ck_documents_08'),
    CheckConstraint('superseded_document_id IS NULL OR superseded_document_id<>id', name='ck_documents_09'),
    CheckConstraint("status NOT IN ('APPROVED','REJECTED','NEEDS_CORRECTION') OR (verified_by IS NOT NULL AND verified_at IS NOT NULL)", name='ck_documents_10'),
    CheckConstraint("status NOT IN ('REJECTED','NEEDS_CORRECTION') OR (rejection_reason IS NOT NULL AND char_length(btrim(rejection_reason)) BETWEEN 1 AND 2000)", name='ck_documents_11'),
    CheckConstraint("status='DRAFT' OR submitted_at IS NOT NULL", name='ck_documents_12'),
    CheckConstraint('version>=1', name='ck_documents_13'),
    CheckConstraint('updated_at>=created_at', name='ck_documents_14'),
    CheckConstraint("document_type IN ('NIC','PASSPORT','DRIVING_LICENCE','BUSINESS_REGISTRATION','OWNER_AUTHORISATION','BANK_PROOF','VEHICLE_REGISTRATION','REVENUE_LICENCE','INSURANCE','EMISSION','FITNESS','ROUTE_PERMIT')", name='ck_documents_15'),
    CheckConstraint('document_number=btrim(document_number) AND char_length(document_number)>0', name='ck_documents_16'),
    CheckConstraint('original_file_name=btrim(original_file_name) AND char_length(original_file_name)>0', name='ck_documents_17'),
    CheckConstraint('mime_type=btrim(mime_type) AND char_length(mime_type)>0', name='ck_documents_18'),
    CheckConstraint("status IN ('DRAFT','SUBMITTED','UNDER_REVIEW','APPROVED','REJECTED','NEEDS_CORRECTION','EXPIRED','SUPERSEDED')", name='ck_documents_19'),
    UniqueConstraint('storage_key', name='uq_documents_01'),
)
Index('ix_documents_01', documents_table.c.user_id, documents_table.c.document_type, documents_table.c.status)
Index('ix_documents_02', documents_table.c.vehicle_id, documents_table.c.document_type, documents_table.c.status)
Index('ix_documents_03', documents_table.c.expiry_date, documents_table.c.status)
Index('ix_documents_04', documents_table.c.superseded_document_id)
Index('ix_documents_created_by', documents_table.c.created_by, postgresql_where=text('created_by IS NOT NULL'))
Index('ix_documents_updated_by', documents_table.c.updated_by, postgresql_where=text('updated_by IS NOT NULL'))
documents_table.primary_key.name = 'pk_documents'

from alembic import op
revision = '0003_review_documents'
down_revision = '0002_international_phone'
branch_labels = None
depends_on = None

def upgrade():
    vehicles_table.create(op.get_bind())
    documents_table.create(op.get_bind())

def downgrade():
    # Explicit downgrade only; PostgreSQL refuses deletion with external FK references.
    documents_table.drop(op.get_bind())
    vehicles_table.drop(op.get_bind())

