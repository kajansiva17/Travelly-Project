# Existing planned operational FK slice; no new application entity.
from sqlalchemy import Table, Column, CheckConstraint, ForeignKey, Index, UniqueConstraint, text
from sqlalchemy import String, Text, Integer, SmallInteger, BigInteger, Boolean, Date, DateTime, Numeric, CHAR
from sqlalchemy.dialects.postgresql import UUID, CITEXT, JSONB
from sqlalchemy.types import UserDefinedType
from sqlalchemy.dialects.postgresql.base import ischema_names
from app.models import Base
import app.models.rate_models as rate_models
class RouteGeometry(UserDefinedType):
    cache_ok = True
    def __init__(self, *args, **kwargs): pass
    def get_col_spec(self, **kwargs): return 'geometry(LineString,4326)'
ischema_names['geometry'] = RouteGeometry

routes_table = Table('routes', Base.metadata,
    Column('id', UUID(as_uuid=True), nullable=False, server_default=text('gen_random_uuid()'), primary_key=True),
    Column('created_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
    Column('updated_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
    Column('created_by', UUID(as_uuid=True), ForeignKey('users.id', name='fk_routes_created_by', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('updated_by', UUID(as_uuid=True), ForeignKey('users.id', name='fk_routes_updated_by', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('version', Integer, nullable=False, server_default=text('1')),
    Column('route_code', CITEXT, nullable=False),
    Column('route_name', String(150), nullable=False),
    Column('origin_name', String(150), nullable=False),
    Column('destination_name', String(150), nullable=False),
    Column('origin_latitude', Numeric(9,6), nullable=True),
    Column('origin_longitude', Numeric(9,6), nullable=True),
    Column('destination_latitude', Numeric(9,6), nullable=True),
    Column('destination_longitude', Numeric(9,6), nullable=True),
    Column('estimated_distance_km', Numeric(12,3), nullable=True),
    Column('estimated_duration_minutes', Integer, nullable=True),
    Column('status', String(8), nullable=False, server_default=text("'DRAFT'")),
    Column('created_by_owner_id', UUID(as_uuid=True), ForeignKey('users.id', name='fk_routes_created_by_owner_id', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('approved_by', UUID(as_uuid=True), ForeignKey('users.id', name='fk_routes_approved_by', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('approved_at', DateTime(timezone=True), nullable=True),
    Column('route_geometry', RouteGeometry(), nullable=True),
    Column('route_settings', JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    CheckConstraint("status<>'ACTIVE' OR (approved_by IS NOT NULL AND approved_at IS NOT NULL)", name='ck_routes_01'),
    CheckConstraint('version>=1', name='ck_routes_02'),
    CheckConstraint('updated_at>=created_at', name='ck_routes_03'),
    CheckConstraint('route_name=btrim(route_name) AND char_length(route_name)>0', name='ck_routes_04'),
    CheckConstraint('origin_name=btrim(origin_name) AND char_length(origin_name)>0', name='ck_routes_05'),
    CheckConstraint('destination_name=btrim(destination_name) AND char_length(destination_name)>0', name='ck_routes_06'),
    CheckConstraint('origin_latitude BETWEEN -90 AND 90', name='ck_routes_07'),
    CheckConstraint('origin_longitude BETWEEN -180 AND 180', name='ck_routes_08'),
    CheckConstraint('destination_latitude BETWEEN -90 AND 90', name='ck_routes_09'),
    CheckConstraint('destination_longitude BETWEEN -180 AND 180', name='ck_routes_10'),
    CheckConstraint('estimated_distance_km>=0', name='ck_routes_11'),
    CheckConstraint('estimated_duration_minutes>=0', name='ck_routes_12'),
    CheckConstraint("status IN ('DRAFT','ACTIVE','INACTIVE')", name='ck_routes_13'),
    CheckConstraint("jsonb_typeof(route_settings)='object'", name='ck_routes_14'),
    UniqueConstraint('route_code', name='uq_routes_01'),
)
Index('ix_routes_01', routes_table.c.origin_name, routes_table.c.destination_name, routes_table.c.status)
Index('ix_routes_02', routes_table.c.created_by_owner_id)
Index('ix_routes_03', routes_table.c.route_geometry, postgresql_using='gist')
Index('ix_routes_created_by', routes_table.c.created_by, postgresql_where=text('created_by IS NOT NULL'))
Index('ix_routes_updated_by', routes_table.c.updated_by, postgresql_where=text('updated_by IS NOT NULL'))
routes_table.primary_key.name = 'pk_routes'

route_stops_table = Table('route_stops', Base.metadata,
    Column('id', UUID(as_uuid=True), nullable=False, server_default=text('gen_random_uuid()'), primary_key=True),
    Column('created_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
    Column('updated_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
    Column('created_by', UUID(as_uuid=True), ForeignKey('users.id', name='fk_route_stops_created_by', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('updated_by', UUID(as_uuid=True), ForeignKey('users.id', name='fk_route_stops_updated_by', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('version', Integer, nullable=False, server_default=text('1')),
    Column('route_id', UUID(as_uuid=True), ForeignKey('routes.id', name='fk_route_stops_route_id', ondelete='CASCADE', onupdate='RESTRICT', deferrable=False), nullable=False),
    Column('stop_order', SmallInteger, nullable=False),
    Column('stop_code', String(30), nullable=True),
    Column('stop_name', String(150), nullable=False),
    Column('latitude', Numeric(9,6), nullable=False),
    Column('longitude', Numeric(9,6), nullable=False),
    Column('pickup_allowed', Boolean, nullable=False, server_default=text('true')),
    Column('dropoff_allowed', Boolean, nullable=False, server_default=text('true')),
    Column('scheduled_offset_minutes', Integer, nullable=False, server_default=text('0')),
    Column('is_active', Boolean, nullable=False, server_default=text('true')),
    CheckConstraint('version>=1', name='ck_route_stops_01'),
    CheckConstraint('updated_at>=created_at', name='ck_route_stops_02'),
    CheckConstraint('stop_order>=0', name='ck_route_stops_03'),
    CheckConstraint('stop_code=btrim(stop_code) AND char_length(stop_code)>0', name='ck_route_stops_04'),
    CheckConstraint('stop_name=btrim(stop_name) AND char_length(stop_name)>0', name='ck_route_stops_05'),
    CheckConstraint('latitude BETWEEN -90 AND 90', name='ck_route_stops_06'),
    CheckConstraint('longitude BETWEEN -180 AND 180', name='ck_route_stops_07'),
    CheckConstraint('scheduled_offset_minutes>=0', name='ck_route_stops_08'),
    UniqueConstraint('route_id', 'stop_order', name='uq_route_stops_01'),
    UniqueConstraint('route_id', 'stop_code', name='uq_route_stops_02'),
)
Index('ix_route_stops_01', route_stops_table.c.route_id, route_stops_table.c.is_active)
Index('ix_route_stops_created_by', route_stops_table.c.created_by, postgresql_where=text('created_by IS NOT NULL'))
Index('ix_route_stops_updated_by', route_stops_table.c.updated_by, postgresql_where=text('updated_by IS NOT NULL'))
route_stops_table.primary_key.name = 'pk_route_stops'

scheduled_trips_table = Table('scheduled_trips', Base.metadata,
    Column('id', UUID(as_uuid=True), nullable=False, server_default=text('gen_random_uuid()'), primary_key=True),
    Column('created_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
    Column('updated_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
    Column('created_by', UUID(as_uuid=True), ForeignKey('users.id', name='fk_scheduled_trips_created_by', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('updated_by', UUID(as_uuid=True), ForeignKey('users.id', name='fk_scheduled_trips_updated_by', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('version', Integer, nullable=False, server_default=text('1')),
    Column('departure_reference', String(24), nullable=False),
    Column('owner_user_id', UUID(as_uuid=True), ForeignKey('users.id', name='fk_scheduled_trips_owner_user_id', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=False),
    Column('service_type_id', UUID(as_uuid=True), ForeignKey('service_types.id', name='fk_scheduled_trips_service_type_id', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=False),
    Column('route_id', UUID(as_uuid=True), ForeignKey('routes.id', name='fk_scheduled_trips_route_id', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=False),
    Column('original_vehicle_id', UUID(as_uuid=True), ForeignKey('vehicles.id', name='fk_scheduled_trips_original_vehicle_id', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=False),
    Column('current_vehicle_id', UUID(as_uuid=True), ForeignKey('vehicles.id', name='fk_scheduled_trips_current_vehicle_id', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=False),
    Column('operator_driver_user_id', UUID(as_uuid=True), ForeignKey('users.id', name='fk_scheduled_trips_operator_driver_user_id', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('departure_at', DateTime(timezone=True), nullable=False),
    Column('estimated_arrival_at', DateTime(timezone=True), nullable=False),
    Column('booking_cutoff_at', DateTime(timezone=True), nullable=False),
    Column('fare_per_seat', Numeric(12,2), nullable=False),
    Column('currency', CHAR(3), nullable=False),
    Column('fulfilment_policy', String(48), nullable=False),
    Column('minimum_confirmed_seats', SmallInteger, nullable=True),
    Column('decision_deadline', DateTime(timezone=True), nullable=True),
    Column('accepted_time_window_minutes', Integer, nullable=False, server_default=text('0')),
    Column('accepted_replacement_terms', JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    Column('status', String(20), nullable=False, server_default=text("'DRAFT'")),
    Column('replacement_status', String(24), nullable=False, server_default=text("'NOT_REQUIRED'")),
    Column('replacement_scheduled_trip_id', UUID(as_uuid=True), ForeignKey('scheduled_trips.id', name='fk_scheduled_trips_replacement_scheduled_trip_id', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('final_operating_owner_user_id', UUID(as_uuid=True), ForeignKey('users.id', name='fk_scheduled_trips_final_operating_owner_user_id', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('committed_at', DateTime(timezone=True), nullable=True),
    Column('cancellation_reason', Text, nullable=True),
    Column('archived_at', DateTime(timezone=True), nullable=True),
    CheckConstraint('estimated_arrival_at>departure_at', name='ck_scheduled_trips_01'),
    CheckConstraint('booking_cutoff_at<=departure_at', name='ck_scheduled_trips_02'),
    CheckConstraint('decision_deadline IS NULL OR decision_deadline<=departure_at', name='ck_scheduled_trips_03'),
    CheckConstraint("fulfilment_policy<>'FIXED_GUARANTEED' OR minimum_confirmed_seats IS NULL", name='ck_scheduled_trips_04'),
    CheckConstraint("fulfilment_policy<>'MINIMUM_SEATS_WITH_PROTECTED_FULFILMENT' OR (minimum_confirmed_seats IS NOT NULL AND minimum_confirmed_seats>0 AND decision_deadline IS NOT NULL)", name='ck_scheduled_trips_05'),
    CheckConstraint('replacement_scheduled_trip_id IS NULL OR replacement_scheduled_trip_id<>id', name='ck_scheduled_trips_06'),
    CheckConstraint('version>=1', name='ck_scheduled_trips_07'),
    CheckConstraint('updated_at>=created_at', name='ck_scheduled_trips_08'),
    CheckConstraint('departure_reference=btrim(departure_reference) AND char_length(departure_reference)>0', name='ck_scheduled_trips_09'),
    CheckConstraint('fare_per_seat>=0', name='ck_scheduled_trips_10'),
    CheckConstraint("currency ~ '^[A-Z]{3}$'", name='ck_scheduled_trips_11'),
    CheckConstraint("fulfilment_policy IN ('FIXED_GUARANTEED','MINIMUM_SEATS_WITH_PROTECTED_FULFILMENT')", name='ck_scheduled_trips_12'),
    CheckConstraint('minimum_confirmed_seats>=0', name='ck_scheduled_trips_13'),
    CheckConstraint('accepted_time_window_minutes>=0', name='ck_scheduled_trips_14'),
    CheckConstraint("jsonb_typeof(accepted_replacement_terms)='object'", name='ck_scheduled_trips_15'),
    CheckConstraint("status IN ('DRAFT','PUBLISHED','BOOKING_OPEN','DECISION_REQUIRED','COMMITTED','READY','IN_PROGRESS','COMPLETED','CANCELLED','DISRUPTED')", name='ck_scheduled_trips_16'),
    CheckConstraint("replacement_status IN ('NOT_REQUIRED','OWNER_ALTERNATIVE','PLATFORM_SHORTLISTED','AWAITING_OTHER_OWNER','APPROVED','REJECTED','FAILED')", name='ck_scheduled_trips_17'),
    UniqueConstraint('departure_reference', name='uq_scheduled_trips_01'),
)
Index('ix_scheduled_trips_01', scheduled_trips_table.c.route_id, scheduled_trips_table.c.departure_at, scheduled_trips_table.c.status)
Index('ix_scheduled_trips_02', scheduled_trips_table.c.current_vehicle_id, scheduled_trips_table.c.departure_at)
Index('ix_scheduled_trips_03', scheduled_trips_table.c.owner_user_id, scheduled_trips_table.c.status)
Index('ix_scheduled_trips_04', scheduled_trips_table.c.decision_deadline, scheduled_trips_table.c.status)
Index('ix_scheduled_trips_created_by', scheduled_trips_table.c.created_by, postgresql_where=text('created_by IS NOT NULL'))
Index('ix_scheduled_trips_updated_by', scheduled_trips_table.c.updated_by, postgresql_where=text('updated_by IS NOT NULL'))
scheduled_trips_table.primary_key.name = 'pk_scheduled_trips'

bookings_table = Table('bookings', Base.metadata,
    Column('id', UUID(as_uuid=True), nullable=False, server_default=text('gen_random_uuid()'), primary_key=True),
    Column('created_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
    Column('updated_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
    Column('created_by', UUID(as_uuid=True), ForeignKey('users.id', name='fk_bookings_created_by', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('updated_by', UUID(as_uuid=True), ForeignKey('users.id', name='fk_bookings_updated_by', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('version', Integer, nullable=False, server_default=text('1')),
    Column('booking_reference', String(24), nullable=False),
    Column('passenger_user_id', UUID(as_uuid=True), ForeignKey('users.id', name='fk_bookings_passenger_user_id', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=False),
    Column('booking_type', String(16), nullable=False),
    Column('service_type_id', UUID(as_uuid=True), ForeignKey('service_types.id', name='fk_bookings_service_type_id', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=False),
    Column('requested_owner_user_id', UUID(as_uuid=True), ForeignKey('users.id', name='fk_bookings_requested_owner_user_id', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('owner_user_id', UUID(as_uuid=True), ForeignKey('users.id', name='fk_bookings_owner_user_id', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('vehicle_id', UUID(as_uuid=True), ForeignKey('vehicles.id', name='fk_bookings_vehicle_id', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('original_scheduled_trip_id', UUID(as_uuid=True), ForeignKey('scheduled_trips.id', name='fk_bookings_original_scheduled_trip_id', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('current_scheduled_trip_id', UUID(as_uuid=True), ForeignKey('scheduled_trips.id', name='fk_bookings_current_scheduled_trip_id', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('origin_text', Text, nullable=True),
    Column('destination_text', Text, nullable=True),
    Column('origin_stop_id', UUID(as_uuid=True), ForeignKey('route_stops.id', name='fk_bookings_origin_stop_id', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('destination_stop_id', UUID(as_uuid=True), ForeignKey('route_stops.id', name='fk_bookings_destination_stop_id', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('start_at', DateTime(timezone=True), nullable=False),
    Column('end_at', DateTime(timezone=True), nullable=False),
    Column('passenger_count', SmallInteger, nullable=False),
    Column('large_luggage_count', SmallInteger, nullable=False, server_default=text('0')),
    Column('small_luggage_count', SmallInteger, nullable=False, server_default=text('0')),
    Column('special_requirements', Text, nullable=True),
    Column('status', String(24), nullable=False, server_default=text("'REQUESTED'")),
    Column('assurance_type', String(24), nullable=False),
    Column('protected_terms_snapshot', JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    Column('quoted_amount', Numeric(12,2), nullable=True),
    Column('discount_amount', Numeric(12,2), nullable=False, server_default=text('0')),
    Column('total_amount', Numeric(12,2), nullable=True),
    Column('currency', CHAR(3), nullable=False),
    Column('payment_status_snapshot', String(32), nullable=True),
    Column('owner_hidden_at', DateTime(timezone=True), nullable=True),
    Column('passenger_hidden_at', DateTime(timezone=True), nullable=True),
    Column('cancelled_by_user_id', UUID(as_uuid=True), ForeignKey('users.id', name='fk_bookings_cancelled_by_user_id', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('cancelled_at', DateTime(timezone=True), nullable=True),
    Column('cancellation_reason', Text, nullable=True),
    Column('cancellation_policy_snapshot', JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    Column('idempotency_key', String(80), nullable=True),
    Column('accepted_at', DateTime(timezone=True), nullable=True),
    Column('confirmed_at', DateTime(timezone=True), nullable=True),
    Column('itinerary_snapshot', JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    CheckConstraint("jsonb_typeof(itinerary_snapshot)='object'", name='ck_bookings_itinerary_snapshot_json'),
    Column('price_snapshot', JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    CheckConstraint("jsonb_typeof(price_snapshot)='object'", name='ck_bookings_price_snapshot_json'),
    Column('pending_change', JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    CheckConstraint("jsonb_typeof(pending_change)='object'", name='ck_bookings_pending_change_json'),
    Column('accepted_quote_digest', CHAR(64), nullable=True),
    Column('vehicle_committed', Boolean, nullable=False, server_default=text('false')),
    CheckConstraint("accepted_quote_digest IS NULL OR accepted_quote_digest ~ '^[0-9a-f]{64}$'", name='ck_bookings_quote_digest'),
    CheckConstraint('end_at>start_at', name='ck_bookings_01'),
    CheckConstraint('discount_amount=0 OR quoted_amount IS NOT NULL', name='ck_bookings_02'),
    CheckConstraint('quoted_amount IS NULL OR discount_amount<=quoted_amount', name='ck_bookings_03'),
    CheckConstraint("booking_type<>'TICKET_HIRE' OR (original_scheduled_trip_id IS NOT NULL AND current_scheduled_trip_id IS NOT NULL)", name='ck_bookings_04'),
    CheckConstraint('version>=1', name='ck_bookings_05'),
    CheckConstraint('updated_at>=created_at', name='ck_bookings_06'),
    CheckConstraint('booking_reference=btrim(booking_reference) AND char_length(booking_reference)>0', name='ck_bookings_07'),
    CheckConstraint("booking_type IN ('PRIVATE_HIRE','TICKET_HIRE','RENTAL')", name='ck_bookings_08'),
    CheckConstraint('passenger_count>0', name='ck_bookings_09'),
    CheckConstraint('large_luggage_count>=0', name='ck_bookings_10'),
    CheckConstraint('small_luggage_count>=0', name='ck_bookings_11'),
    CheckConstraint("status IN ('REQUESTED','AWAITING_DRIVER','OWNER_ACTION_REQUIRED','CONFIRMED','IN_PROGRESS','COMPLETED','REJECTED','CANCELLED')", name='ck_bookings_12'),
    CheckConstraint("assurance_type IN ('STANDARD_HIRE','FIXED_DEPARTURE','TRAVELLY_PROTECTED')", name='ck_bookings_13'),
    CheckConstraint("jsonb_typeof(protected_terms_snapshot)='object'", name='ck_bookings_14'),
    CheckConstraint('quoted_amount>=0', name='ck_bookings_15'),
    CheckConstraint('discount_amount>=0', name='ck_bookings_16'),
    CheckConstraint('total_amount>=0', name='ck_bookings_17'),
    CheckConstraint("currency ~ '^[A-Z]{3}$'", name='ck_bookings_18'),
    CheckConstraint("payment_status_snapshot IN ('PENDING','PROCESSING','PAID','CASH_AWAITING_CONFIRMATION','FAILED','REFUNDED','PARTIALLY_REFUNDED')", name='ck_bookings_19'),
    CheckConstraint("jsonb_typeof(cancellation_policy_snapshot)='object'", name='ck_bookings_20'),
    CheckConstraint('idempotency_key=btrim(idempotency_key) AND char_length(idempotency_key)>0', name='ck_bookings_21'),
    UniqueConstraint('booking_reference', name='uq_bookings_01'),
    UniqueConstraint('idempotency_key', name='uq_bookings_02'),
)
Index('ix_bookings_01', bookings_table.c.passenger_user_id, bookings_table.c.status, bookings_table.c.created_at.desc())
Index('ix_bookings_02', bookings_table.c.owner_user_id, bookings_table.c.status, bookings_table.c.start_at)
Index('ix_bookings_03', bookings_table.c.vehicle_id, bookings_table.c.start_at, bookings_table.c.end_at)
Index('ix_bookings_04', bookings_table.c.current_scheduled_trip_id, bookings_table.c.status)
Index('ix_bookings_05', bookings_table.c.service_type_id, bookings_table.c.start_at)
Index('ix_bookings_created_by', bookings_table.c.created_by, postgresql_where=text('created_by IS NOT NULL'))
Index('ix_bookings_updated_by', bookings_table.c.updated_by, postgresql_where=text('updated_by IS NOT NULL'))
bookings_table.primary_key.name = 'pk_bookings'

trips_table = Table('trips', Base.metadata,
    Column('id', UUID(as_uuid=True), nullable=False, server_default=text('gen_random_uuid()'), primary_key=True),
    Column('created_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
    Column('updated_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
    Column('created_by', UUID(as_uuid=True), ForeignKey('users.id', name='fk_trips_created_by', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('updated_by', UUID(as_uuid=True), ForeignKey('users.id', name='fk_trips_updated_by', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('version', Integer, nullable=False, server_default=text('1')),
    Column('trip_reference', String(24), nullable=False),
    Column('booking_id', UUID(as_uuid=True), ForeignKey('bookings.id', name='fk_trips_booking_id', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('scheduled_trip_id', UUID(as_uuid=True), ForeignKey('scheduled_trips.id', name='fk_trips_scheduled_trip_id', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('vehicle_id', UUID(as_uuid=True), ForeignKey('vehicles.id', name='fk_trips_vehicle_id', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=False),
    Column('operating_owner_user_id', UUID(as_uuid=True), ForeignKey('users.id', name='fk_trips_operating_owner_user_id', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=False),
    Column('driver_user_id', UUID(as_uuid=True), ForeignKey('users.id', name='fk_trips_driver_user_id', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('assignment_type', String(20), nullable=True),
    Column('assignment_status', String(12), nullable=False, server_default=text("'PENDING'")),
    Column('status', String(24), nullable=False, server_default=text("'READY'")),
    Column('scheduled_start_at', DateTime(timezone=True), nullable=False),
    Column('scheduled_end_at', DateTime(timezone=True), nullable=False),
    Column('actual_start_at', DateTime(timezone=True), nullable=True),
    Column('actual_end_at', DateTime(timezone=True), nullable=True),
    Column('start_odometer_km', Numeric(12,1), nullable=True),
    Column('end_odometer_km', Numeric(12,1), nullable=True),
    Column('calculated_distance_km', Numeric(12,1), nullable=True),
    Column('tracking_status', String(8), nullable=False, server_default=text("'OFF'")),
    Column('current_latitude', Numeric(9,6), nullable=True),
    Column('current_longitude', Numeric(9,6), nullable=True),
    Column('location_accuracy_m', Numeric(10,2), nullable=True),
    Column('current_speed_kph', Numeric(8,2), nullable=True),
    Column('location_updated_at', DateTime(timezone=True), nullable=True),
    Column('breakdown_details', Text, nullable=True),
    Column('completion_notes', Text, nullable=True),
    Column('pickup_code_version', Integer, nullable=False, server_default=text('0')),
    Column('pickup_code_issued_at', DateTime(timezone=True), nullable=True),
    Column('pickup_verified_at', DateTime(timezone=True), nullable=True),
    Column('pickup_failed_attempts', Integer, nullable=False, server_default=text('0')),
    Column('wait_started_at', DateTime(timezone=True), nullable=True),
    Column('wait_ended_at', DateTime(timezone=True), nullable=True),
    Column('wait_latitude', Numeric(9,6), nullable=True),
    Column('wait_longitude', Numeric(9,6), nullable=True),
    Column('wait_confirmed_minutes', Numeric(8,1), nullable=True),
    Column('wait_source', String(8), nullable=True),
    Column('wait_moved_at', DateTime(timezone=True), nullable=True),
    CheckConstraint('wait_confirmed_minutes IS NULL OR wait_confirmed_minutes>=0', name='ck_trips_24'),
    CheckConstraint("wait_source IS NULL OR wait_source IN ('DRIVER','GPS','MANUAL')", name='ck_trips_25'),
    CheckConstraint('wait_ended_at IS NULL OR (wait_started_at IS NOT NULL AND wait_ended_at>=wait_started_at)', name='ck_trips_23'),
    CheckConstraint('booking_id IS NOT NULL OR scheduled_trip_id IS NOT NULL', name='ck_trips_01'),
    CheckConstraint('pickup_code_version>=0', name='ck_trips_20'),
    CheckConstraint('pickup_failed_attempts>=0', name='ck_trips_21'),
    CheckConstraint('pickup_verified_at IS NULL OR pickup_code_version>0', name='ck_trips_22'),
    CheckConstraint('scheduled_end_at>scheduled_start_at', name='ck_trips_02'),
    CheckConstraint('actual_start_at IS NULL OR actual_end_at IS NULL OR actual_end_at>=actual_start_at', name='ck_trips_03'),
    CheckConstraint('start_odometer_km IS NULL OR end_odometer_km IS NULL OR end_odometer_km>=start_odometer_km', name='ck_trips_04'),
    CheckConstraint("tracking_status NOT IN ('ACTIVE','STALE') OR status IN ('IN_PROGRESS','BREAKDOWN','ASSISTANCE_REQUIRED')", name='ck_trips_05'),
    CheckConstraint('version>=1', name='ck_trips_06'),
    CheckConstraint('updated_at>=created_at', name='ck_trips_07'),
    CheckConstraint('trip_reference=btrim(trip_reference) AND char_length(trip_reference)>0', name='ck_trips_08'),
    CheckConstraint("assignment_type IN ('OWNER_SELF_DRIVE','EXTERNAL_DRIVER')", name='ck_trips_09'),
    CheckConstraint("assignment_status IN ('NOT_REQUIRED','PENDING','ACCEPTED','REJECTED','CANCELLED')", name='ck_trips_10'),
    CheckConstraint("status IN ('READY','IN_PROGRESS','BREAKDOWN','ASSISTANCE_REQUIRED','COMPLETED','CANCELLED')", name='ck_trips_11'),
    CheckConstraint('start_odometer_km>=0', name='ck_trips_12'),
    CheckConstraint('end_odometer_km>=0', name='ck_trips_13'),
    CheckConstraint('calculated_distance_km>=0', name='ck_trips_14'),
    CheckConstraint("tracking_status IN ('OFF','ACTIVE','STALE','ENDED')", name='ck_trips_15'),
    CheckConstraint('current_latitude BETWEEN -90 AND 90', name='ck_trips_16'),
    CheckConstraint('current_longitude BETWEEN -180 AND 180', name='ck_trips_17'),
    CheckConstraint('location_accuracy_m>=0', name='ck_trips_18'),
    CheckConstraint('current_speed_kph>=0', name='ck_trips_19'),
    UniqueConstraint('trip_reference', name='uq_trips_01'),
)
Index('ix_trips_01', trips_table.c.driver_user_id, trips_table.c.status, trips_table.c.scheduled_start_at)
Index('ix_trips_02', trips_table.c.operating_owner_user_id, trips_table.c.status, trips_table.c.scheduled_start_at)
Index('ix_trips_03', trips_table.c.vehicle_id, trips_table.c.scheduled_start_at)
Index('ix_trips_04', trips_table.c.status, postgresql_where=text("tracking_status IN ('ACTIVE','STALE')"))
Index('ix_trips_created_by', trips_table.c.created_by, postgresql_where=text('created_by IS NOT NULL'))
Index('ix_trips_updated_by', trips_table.c.updated_by, postgresql_where=text('updated_by IS NOT NULL'))
trips_table.primary_key.name = 'pk_trips'

vehicle_records_table = Table('vehicle_records', Base.metadata,
    Column('id', UUID(as_uuid=True), nullable=False, server_default=text('gen_random_uuid()'), primary_key=True),
    Column('created_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
    Column('updated_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
    Column('created_by', UUID(as_uuid=True), ForeignKey('users.id', name='fk_vehicle_records_created_by', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('updated_by', UUID(as_uuid=True), ForeignKey('users.id', name='fk_vehicle_records_updated_by', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('version', Integer, nullable=False, server_default=text('1')),
    Column('vehicle_id', UUID(as_uuid=True), ForeignKey('vehicles.id', name='fk_vehicle_records_vehicle_id', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=False),
    Column('trip_id', UUID(as_uuid=True), ForeignKey('trips.id', name='fk_vehicle_records_trip_id', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('recorded_by_user_id', UUID(as_uuid=True), ForeignKey('users.id', name='fk_vehicle_records_recorded_by_user_id', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=False),
    Column('record_type', String(32), nullable=False),
    Column('recorded_at', DateTime(timezone=True), nullable=False),
    Column('odometer_km', Numeric(12,1), nullable=True),
    Column('start_at', DateTime(timezone=True), nullable=True),
    Column('end_at', DateTime(timezone=True), nullable=True),
    Column('start_odometer_km', Numeric(12,1), nullable=True),
    Column('end_odometer_km', Numeric(12,1), nullable=True),
    Column('amount', Numeric(12,2), nullable=True),
    Column('currency', CHAR(3), nullable=True),
    Column('quantity', Numeric(12,3), nullable=True),
    Column('unit', String(20), nullable=True),
    Column('fuel_type', String(30), nullable=True),
    Column('fuel_grade_product', String(100), nullable=True),
    Column('charging_kwh', Numeric(12,3), nullable=True),
    Column('next_due_odometer_km', Numeric(12,1), nullable=True),
    Column('genuine_calendar_due_date', Date, nullable=True),
    Column('service_provider', String(150), nullable=True),
    Column('receipt_url', Text, nullable=True),
    Column('notes', Text, nullable=True),
    Column('approval_status', String(24), nullable=True),
    CheckConstraint('start_at IS NULL OR end_at IS NULL OR end_at>start_at', name='ck_vehicle_records_01'),
    CheckConstraint('start_odometer_km IS NULL OR end_odometer_km IS NULL OR end_odometer_km>=start_odometer_km', name='ck_vehicle_records_02'),
    CheckConstraint("record_type<>'AVAILABILITY_BLOCK' OR (start_at IS NOT NULL AND end_at IS NOT NULL)", name='ck_vehicle_records_03'),
    CheckConstraint("record_type<>'FUEL_PURCHASE' OR (fuel_grade_product IS NOT NULL AND quantity IS NOT NULL AND amount IS NOT NULL)", name='ck_vehicle_records_04'),
    CheckConstraint("record_type<>'EV_CHARGING' OR amount IS NOT NULL", name='ck_vehicle_records_05'),
    CheckConstraint('version>=1', name='ck_vehicle_records_06'),
    CheckConstraint('updated_at>=created_at', name='ck_vehicle_records_07'),
    CheckConstraint("record_type IN ('OIL_CHANGE','OIL_FILTER_CHANGE','TYRE_CHANGE','TYRE_ROTATION','WHEEL_ALIGNMENT','WHEEL_BALANCING','GENERAL_SERVICE','BRAKE_SERVICE','BATTERY_SERVICE','REPAIR','FUEL_PURCHASE','EV_CHARGING','PERSONAL_EXTRA_USE','ODOMETER_UPDATE','AVAILABILITY_BLOCK')", name='ck_vehicle_records_08'),
    CheckConstraint('odometer_km>=0', name='ck_vehicle_records_09'),
    CheckConstraint('start_odometer_km>=0', name='ck_vehicle_records_10'),
    CheckConstraint('end_odometer_km>=0', name='ck_vehicle_records_11'),
    CheckConstraint('amount>=0', name='ck_vehicle_records_12'),
    CheckConstraint("currency ~ '^[A-Z]{3}$'", name='ck_vehicle_records_13'),
    CheckConstraint('quantity>=0', name='ck_vehicle_records_14'),
    CheckConstraint('unit=btrim(unit) AND char_length(unit)>0', name='ck_vehicle_records_15'),
    CheckConstraint('fuel_type=btrim(fuel_type) AND char_length(fuel_type)>0', name='ck_vehicle_records_16'),
    CheckConstraint('fuel_grade_product=btrim(fuel_grade_product) AND char_length(fuel_grade_product)>0', name='ck_vehicle_records_17'),
    CheckConstraint('charging_kwh>=0', name='ck_vehicle_records_18'),
    CheckConstraint('next_due_odometer_km>=0', name='ck_vehicle_records_19'),
    CheckConstraint('service_provider=btrim(service_provider) AND char_length(service_provider)>0', name='ck_vehicle_records_20'),
    CheckConstraint('approval_status=btrim(approval_status) AND char_length(approval_status)>0', name='ck_vehicle_records_21'),
)
Index('ix_vehicle_records_01', vehicle_records_table.c.vehicle_id, vehicle_records_table.c.record_type, vehicle_records_table.c.recorded_at.desc())
Index('ix_vehicle_records_02', vehicle_records_table.c.vehicle_id, vehicle_records_table.c.start_at, vehicle_records_table.c.end_at)
Index('ix_vehicle_records_03', vehicle_records_table.c.trip_id)
Index('ix_vehicle_records_created_by', vehicle_records_table.c.created_by, postgresql_where=text('created_by IS NOT NULL'))
Index('ix_vehicle_records_updated_by', vehicle_records_table.c.updated_by, postgresql_where=text('updated_by IS NOT NULL'))
vehicle_records_table.primary_key.name = 'pk_vehicle_records'

notifications_table = Table('notifications', Base.metadata,
    Column('id', UUID(as_uuid=True), nullable=False, server_default=text('gen_random_uuid()'), primary_key=True),
    Column('created_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
    Column('updated_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
    Column('created_by', UUID(as_uuid=True), ForeignKey('users.id', name='fk_notifications_created_by', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('updated_by', UUID(as_uuid=True), ForeignKey('users.id', name='fk_notifications_updated_by', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('version', Integer, nullable=False, server_default=text('1')),
    Column('recipient_user_id', UUID(as_uuid=True), ForeignKey('users.id', name='fk_notifications_recipient_user_id', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=False),
    Column('booking_id', UUID(as_uuid=True), ForeignKey('bookings.id', name='fk_notifications_booking_id', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('scheduled_trip_id', UUID(as_uuid=True), ForeignKey('scheduled_trips.id', name='fk_notifications_scheduled_trip_id', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('trip_id', UUID(as_uuid=True), ForeignKey('trips.id', name='fk_notifications_trip_id', ondelete='RESTRICT', onupdate='RESTRICT', deferrable=False), nullable=True),
    Column('notification_type', String(24), nullable=False),
    Column('channel', String(8), nullable=False),
    Column('title', String(200), nullable=False),
    Column('body', Text, nullable=False),
    Column('action_required', Boolean, nullable=False, server_default=text('false')),
    Column('action_payload', JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    Column('status', String(12), nullable=False, server_default=text("'QUEUED'")),
    Column('sent_at', DateTime(timezone=True), nullable=True),
    Column('delivered_at', DateTime(timezone=True), nullable=True),
    Column('read_at', DateTime(timezone=True), nullable=True),
    Column('response_code', String(40), nullable=True),
    Column('response_value', Text, nullable=True),
    Column('responded_at', DateTime(timezone=True), nullable=True),
    Column('expires_at', DateTime(timezone=True), nullable=True),
    Column('retry_count', Integer, nullable=False, server_default=text('0')),
    CheckConstraint('version>=1', name='ck_notifications_01'),
    CheckConstraint('updated_at>=created_at', name='ck_notifications_02'),
    CheckConstraint("notification_type IN ('BOOKING_REQUEST','BOOKING_CONFIRMED','DRIVER_ASSIGNMENT','RECONFIRMATION','PAYMENT','REFUND','REPLACEMENT','MAINTENANCE_DUE','DOCUMENT_EXPIRY','ROAD_ALERT','ADMIN_ACTION','REVIEW','CHAT')", name='ck_notifications_03'),
    CheckConstraint("channel IN ('IN_APP','EMAIL')", name='ck_notifications_04'),
    CheckConstraint('title=btrim(title) AND char_length(title)>0', name='ck_notifications_05'),
    CheckConstraint("jsonb_typeof(action_payload)='object'", name='ck_notifications_06'),
    CheckConstraint("status IN ('QUEUED','SENT','DELIVERED','READ','RESPONDED','FAILED','EXPIRED')", name='ck_notifications_07'),
    CheckConstraint('response_code=btrim(response_code) AND char_length(response_code)>0', name='ck_notifications_08'),
    CheckConstraint('retry_count>=0', name='ck_notifications_09'),
)
Index('ix_notifications_01', notifications_table.c.recipient_user_id, notifications_table.c.status, notifications_table.c.created_at)
Index('ix_notifications_02', notifications_table.c.expires_at, notifications_table.c.status)
Index('ix_notifications_created_by', notifications_table.c.created_by, postgresql_where=text('created_by IS NOT NULL'))
Index('ix_notifications_updated_by', notifications_table.c.updated_by, postgresql_where=text('updated_by IS NOT NULL'))
notifications_table.primary_key.name = 'pk_notifications'

class Route(Base):
    __table__ = routes_table

class RouteStop(Base):
    __table__ = route_stops_table

class ScheduledTrip(Base):
    __table__ = scheduled_trips_table

class Booking(Base):
    __table__ = bookings_table

class Trip(Base):
    __table__ = trips_table

class VehicleRecord(Base):
    __table__ = vehicle_records_table

class Notification(Base):
    __table__ = notifications_table


favourite_vehicles_table = Table('favourite_vehicles', Base.metadata,
    Column('id', UUID(as_uuid=True), nullable=False, server_default=text('gen_random_uuid()'), primary_key=True),
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id', name='fk_favourite_vehicles_user_id', ondelete='CASCADE'), nullable=False),
    Column('vehicle_id', UUID(as_uuid=True), ForeignKey('vehicles.id', name='fk_favourite_vehicles_vehicle_id', ondelete='CASCADE'), nullable=False),
    Column('created_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
    UniqueConstraint('user_id', 'vehicle_id', name='uq_favourite_vehicles_user_vehicle'),
    Index('ix_favourite_vehicles_user', 'user_id', 'created_at'))

class FavouriteVehicle(Base):
    __table__ = favourite_vehicles_table


# Owner decision 15 Nov 2026: "My drivers" is the Owner's own saved list of Drivers (a bookmark, like favourite vehicles).
# It is not an Owner-Driver relationship and gives the Driver nothing: every assignment still needs the licence check and the Driver's acceptance.
owner_drivers_table = Table('owner_drivers', Base.metadata,
    Column('id', UUID(as_uuid=True), nullable=False, server_default=text('gen_random_uuid()'), primary_key=True),
    Column('owner_user_id', UUID(as_uuid=True), ForeignKey('users.id', name='fk_owner_drivers_owner_user_id', ondelete='CASCADE'), nullable=False),
    Column('driver_user_id', UUID(as_uuid=True), ForeignKey('users.id', name='fk_owner_drivers_driver_user_id', ondelete='CASCADE'), nullable=False),
    Column('nickname', String(60), nullable=True),
    Column('status', String(20), nullable=False, server_default=text("'ACTIVE'")),            # ACTIVE | DRIVER_REQUESTED | OWNER_INVITED | DECLINED
    Column('initiated_by', String(6), nullable=False, server_default=text("'OWNER'")),         # OWNER | DRIVER
    Column('created_at', DateTime(timezone=True), nullable=False, server_default=text('now()')),
    UniqueConstraint('owner_user_id', 'driver_user_id', name='uq_owner_drivers_owner_driver'),
    Index('ix_owner_drivers_owner', 'owner_user_id', 'created_at'))

class OwnerDriver(Base):
    __table__ = owner_drivers_table
