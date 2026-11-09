# Ticket seat inventory from the frozen 02C dictionary (tables 10, 12 and 13).
# Uses only tables already in the approved 20-table catalogue; no new application entity.
from alembic import op
from sqlalchemy import MetaData, Table, Column, CheckConstraint, ForeignKey, Index, UniqueConstraint, text
from sqlalchemy import String, Text, Integer, SmallInteger, Boolean, DateTime, Numeric
from sqlalchemy.dialects.postgresql import UUID, CITEXT, JSONB


class Snapshot:
    metadata = MetaData()


Base = Snapshot
for target in ('users', 'vehicles', 'bookings', 'scheduled_trips', 'route_stops'):
    Table(target, Base.metadata, Column('id', UUID(as_uuid=True), primary_key=True))


def audit_columns(table):
    return [
        Column('id', UUID(as_uuid=True), nullable=False, server_default=text('gen_random_uuid()'), primary_key=True),
        Column('created_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
        Column('updated_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
        Column('created_by', UUID(as_uuid=True), ForeignKey('users.id', name=f'fk_{table}_created_by', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
        Column('updated_by', UUID(as_uuid=True), ForeignKey('users.id', name=f'fk_{table}_updated_by', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
        Column('version', Integer, nullable=False, server_default=text('1')),
    ]


def fk(table, column, target, ondelete='RESTRICT', nullable=False):
    return Column(column, UUID(as_uuid=True), ForeignKey(f'{target}.id', name=f'fk_{table}_{column}', ondelete=ondelete, onupdate='RESTRICT', deferrable=False), nullable=nullable)


vehicle_seats_table = Table('vehicle_seats', Base.metadata,
    *audit_columns('vehicle_seats'),
    fk('vehicle_seats', 'vehicle_id', 'vehicles'),
    Column('layout_version', Integer, nullable=False, server_default=text('1')),
    Column('seat_code', String(12), nullable=False),
    Column('row_number', SmallInteger, nullable=False),
    Column('column_number', SmallInteger, nullable=False),
    Column('deck_number', SmallInteger, nullable=False, server_default=text('1')),
    Column('seat_type', String(12), nullable=False, server_default=text("'STANDARD'")),
    Column('is_active', Boolean, nullable=False, server_default=text('true')),
    Column('is_bookable', Boolean, nullable=False, server_default=text('true')),
    Column('display_metadata', JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    CheckConstraint('version>=1', name='ck_vehicle_seats_01'),
    CheckConstraint('updated_at>=created_at', name='ck_vehicle_seats_02'),
    CheckConstraint('layout_version>0', name='ck_vehicle_seats_03'),
    CheckConstraint('seat_code=btrim(seat_code) AND char_length(seat_code)>0', name='ck_vehicle_seats_04'),
    CheckConstraint('row_number>=0', name='ck_vehicle_seats_05'),
    CheckConstraint('column_number>=0', name='ck_vehicle_seats_06'),
    CheckConstraint('deck_number>0', name='ck_vehicle_seats_07'),
    CheckConstraint("seat_type IN ('STANDARD','WINDOW','AISLE','PREMIUM','ACCESSIBLE','CREW')", name='ck_vehicle_seats_08'),
    CheckConstraint("jsonb_typeof(display_metadata)='object'", name='ck_vehicle_seats_09'),
    UniqueConstraint('vehicle_id', 'layout_version', 'seat_code', name='uq_vehicle_seats_01'),
    UniqueConstraint('vehicle_id', 'layout_version', 'deck_number', 'row_number', 'column_number', name='uq_vehicle_seats_02'),
)
Index('ix_vehicle_seats_01', vehicle_seats_table.c.vehicle_id, vehicle_seats_table.c.layout_version, vehicle_seats_table.c.is_active)
Index('ix_vehicle_seats_created_by', vehicle_seats_table.c.created_by, postgresql_where=text('created_by IS NOT NULL'))
Index('ix_vehicle_seats_updated_by', vehicle_seats_table.c.updated_by, postgresql_where=text('updated_by IS NOT NULL'))
vehicle_seats_table.primary_key.name = 'pk_vehicle_seats'

scheduled_trip_seats_table = Table('scheduled_trip_seats', Base.metadata,
    *audit_columns('scheduled_trip_seats'),
    fk('scheduled_trip_seats', 'scheduled_trip_id', 'scheduled_trips', ondelete='CASCADE'),
    fk('scheduled_trip_seats', 'vehicle_seat_id', 'vehicle_seats'),
    Column('seat_status', String(9), nullable=False, server_default=text("'AVAILABLE'")),
    fk('scheduled_trip_seats', 'held_by_booking_id', 'bookings', nullable=True),
    Column('hold_expires_at', DateTime(timezone=True), nullable=True),
    fk('scheduled_trip_seats', 'booked_booking_id', 'bookings', nullable=True),
    Column('fare_override', Numeric(12, 2), nullable=True),
    CheckConstraint("seat_status<>'HELD' OR (held_by_booking_id IS NOT NULL AND hold_expires_at IS NOT NULL)", name='ck_scheduled_trip_seats_01'),
    CheckConstraint("seat_status<>'BOOKED' OR booked_booking_id IS NOT NULL", name='ck_scheduled_trip_seats_02'),
    CheckConstraint("seat_status<>'AVAILABLE' OR (held_by_booking_id IS NULL AND hold_expires_at IS NULL AND booked_booking_id IS NULL)", name='ck_scheduled_trip_seats_03'),
    CheckConstraint("seat_status<>'HELD' OR booked_booking_id IS NULL", name='ck_scheduled_trip_seats_04'),
    CheckConstraint('version>=1', name='ck_scheduled_trip_seats_05'),
    CheckConstraint('updated_at>=created_at', name='ck_scheduled_trip_seats_06'),
    CheckConstraint("seat_status IN ('AVAILABLE','HELD','BOOKED','BLOCKED')", name='ck_scheduled_trip_seats_07'),
    CheckConstraint('fare_override>=0', name='ck_scheduled_trip_seats_08'),
    UniqueConstraint('scheduled_trip_id', 'vehicle_seat_id', name='uq_scheduled_trip_seats_01'),
)
Index('ix_scheduled_trip_seats_01', scheduled_trip_seats_table.c.scheduled_trip_id, scheduled_trip_seats_table.c.seat_status)
Index('ix_scheduled_trip_seats_02', scheduled_trip_seats_table.c.hold_expires_at, postgresql_where=text("seat_status='HELD'"))
Index('ix_scheduled_trip_seats_created_by', scheduled_trip_seats_table.c.created_by, postgresql_where=text('created_by IS NOT NULL'))
Index('ix_scheduled_trip_seats_updated_by', scheduled_trip_seats_table.c.updated_by, postgresql_where=text('updated_by IS NOT NULL'))
scheduled_trip_seats_table.primary_key.name = 'pk_scheduled_trip_seats'

booking_travellers_table = Table('booking_travellers', Base.metadata,
    *audit_columns('booking_travellers'),
    fk('booking_travellers', 'booking_id', 'bookings'),
    fk('booking_travellers', 'linked_user_id', 'users', nullable=True),
    Column('full_name', String(150), nullable=False),
    Column('contact_phone', String(20), nullable=True),
    Column('contact_email', CITEXT, nullable=True),
    Column('age_category', String(30), nullable=True),
    Column('is_primary', Boolean, nullable=False, server_default=text('false')),
    Column('identity_reference', String(100), nullable=True),
    fk('booking_travellers', 'scheduled_trip_seat_id', 'scheduled_trip_seats', nullable=True),
    fk('booking_travellers', 'boarding_stop_id', 'route_stops', nullable=True),
    fk('booking_travellers', 'dropoff_stop_id', 'route_stops', nullable=True),
    Column('special_assistance', Text, nullable=True),
    Column('traveller_status', String(12), nullable=False, server_default=text("'ACTIVE'")),
    CheckConstraint('version>=1', name='ck_booking_travellers_01'),
    CheckConstraint('updated_at>=created_at', name='ck_booking_travellers_02'),
    CheckConstraint('full_name=btrim(full_name) AND char_length(full_name)>0', name='ck_booking_travellers_03'),
    CheckConstraint('contact_phone=btrim(contact_phone) AND char_length(contact_phone)>0', name='ck_booking_travellers_04'),
    CheckConstraint('age_category=btrim(age_category) AND char_length(age_category)>0', name='ck_booking_travellers_05'),
    CheckConstraint('identity_reference=btrim(identity_reference) AND char_length(identity_reference)>0', name='ck_booking_travellers_06'),
    CheckConstraint("traveller_status IN ('ACTIVE','MOVED','CANCELLED','BOARDED','COMPLETED')", name='ck_booking_travellers_07'),
)
Index('ix_booking_travellers_01', booking_travellers_table.c.booking_id)
Index('ix_booking_travellers_02', booking_travellers_table.c.booking_id, unique=True, postgresql_where=text('is_primary'))
Index('ix_booking_travellers_03', booking_travellers_table.c.scheduled_trip_seat_id, unique=True,
      postgresql_where=text("scheduled_trip_seat_id IS NOT NULL AND traveller_status IN ('ACTIVE','BOARDED')"))
Index('ix_booking_travellers_created_by', booking_travellers_table.c.created_by, postgresql_where=text('created_by IS NOT NULL'))
Index('ix_booking_travellers_updated_by', booking_travellers_table.c.updated_by, postgresql_where=text('updated_by IS NOT NULL'))
booking_travellers_table.primary_key.name = 'pk_booking_travellers'

revision = '0007_ticket_seat_inventory'
down_revision = '0006_private_hire_pricing'
branch_labels = depends_on = None


def upgrade():
    bind = op.get_bind()
    vehicle_seats_table.create(bind)
    scheduled_trip_seats_table.create(bind)
    booking_travellers_table.create(bind)
    # One active service type is required so a scheduled departure can reference it.
    op.execute(
        "INSERT INTO service_types (code, name, description, category, is_active, display_order, default_pricing_basis) "
        "VALUES ('TICKET_HIRE', 'Scheduled ticket', 'Route and airport Ticket Hire with numbered seats', 'TICKET_HIRE', true, 100, 'PER_SEAT') "
        "ON CONFLICT (code) DO NOTHING"
    )


def downgrade():
    raise RuntimeError('Ticket seat inventory holds booking history; use an explicit preservation/recovery plan.')
