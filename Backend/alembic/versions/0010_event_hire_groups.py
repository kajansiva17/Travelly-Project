"""Event Hire V1 groups and all-or-nothing vehicle allocations. Create only; never apply automatically."""
from alembic import op

revision = '0010_event_hire_groups'
down_revision = '0009_admin_workflow_audit'
branch_labels = None
depends_on = None

COMMON = "id UUID PRIMARY KEY DEFAULT gen_random_uuid(), created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), created_by UUID NULL REFERENCES users(id) ON DELETE RESTRICT, updated_by UUID NULL REFERENCES users(id) ON DELETE RESTRICT, version INTEGER NOT NULL DEFAULT 1 CHECK(version>=1), CHECK(updated_at>=created_at)"

def upgrade():
    op.execute(f"""CREATE TABLE event_booking_groups ({COMMON}, event_reference VARCHAR(40) NOT NULL UNIQUE, passenger_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT, owner_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT, service_type_id UUID NOT NULL REFERENCES service_types(id) ON DELETE RESTRICT, event_type VARCHAR(100) NOT NULL, venue_snapshot JSONB NOT NULL, pickup_snapshots JSONB NOT NULL, event_start_at TIMESTAMPTZ NOT NULL, expected_hours NUMERIC(6,2) NOT NULL CHECK(expected_hours>0 AND expected_hours<=24), vehicles_required SMALLINT NOT NULL CHECK(vehicles_required BETWEEN 1 AND 20), passenger_count INTEGER NOT NULL CHECK(passenger_count>0), request_snapshot JSONB NOT NULL, quote_snapshot JSONB NULL, accepted_quote_digest CHAR(64) NULL, total_amount NUMERIC(12,2) NULL CHECK(total_amount>=0), currency CHAR(3) NOT NULL DEFAULT 'LKR' CHECK(currency='LKR'), status VARCHAR(24) NOT NULL DEFAULT 'REQUESTED', accepted_at TIMESTAMPTZ NULL, owner_accepted_at TIMESTAMPTZ NULL, confirmed_at TIMESTAMPTZ NULL, CHECK(jsonb_typeof(venue_snapshot)='object'), CHECK(jsonb_typeof(pickup_snapshots)='array'), CHECK(jsonb_typeof(request_snapshot)='object'), CHECK(quote_snapshot IS NULL OR jsonb_typeof(quote_snapshot)='object'), CHECK(status IN ('REQUESTED','QUOTED','PASSENGER_ACCEPTED','OWNER_ACCEPTED','ASSIGNMENT_PENDING','CONFIRMED','REJECTED','CANCELLED')))""")
    op.execute(f"""CREATE TABLE event_vehicle_allocations ({COMMON}, event_group_id UUID NOT NULL REFERENCES event_booking_groups(id) ON DELETE RESTRICT, allocation_no SMALLINT NOT NULL CHECK(allocation_no>0), vehicle_id UUID NOT NULL REFERENCES vehicles(id) ON DELETE RESTRICT, driver_user_id UUID NULL REFERENCES users(id) ON DELETE RESTRICT, booking_id UUID NULL UNIQUE REFERENCES bookings(id) ON DELETE RESTRICT, trip_id UUID NULL UNIQUE REFERENCES trips(id) ON DELETE RESTRICT, rate_version INTEGER NOT NULL CHECK(rate_version>0), package_snapshot JSONB NOT NULL, allocation_amount NUMERIC(12,2) NOT NULL CHECK(allocation_amount>=0), status VARCHAR(20) NOT NULL DEFAULT 'QUOTED', CHECK(jsonb_typeof(package_snapshot)='object'), CHECK(status IN ('QUOTED','PASSENGER_ACCEPTED','ASSIGNED','CONFIRMED','REJECTED','CANCELLED')), UNIQUE(event_group_id,allocation_no), UNIQUE(event_group_id,vehicle_id))""")
    op.execute('CREATE INDEX ix_event_groups_passenger ON event_booking_groups(passenger_user_id,created_at DESC)')
    op.execute('CREATE INDEX ix_event_groups_owner ON event_booking_groups(owner_user_id,status,created_at DESC)')
    op.execute('CREATE INDEX ix_event_allocations_vehicle ON event_vehicle_allocations(vehicle_id,status)')

def downgrade():
    op.drop_table('event_vehicle_allocations')
    op.drop_table('event_booking_groups')
