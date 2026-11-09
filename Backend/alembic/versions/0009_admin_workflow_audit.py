"""Stage 5 Admin workflow oversight. Create only; never apply in this workspace."""
from alembic import op
revision='0009_admin_workflow_audit'
down_revision='0008_stage4_finance_maintenance'
branch_labels=None
depends_on=None
COMMON="""id UUID PRIMARY KEY DEFAULT gen_random_uuid(), created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), created_by UUID NULL REFERENCES users(id) ON DELETE RESTRICT, updated_by UUID NULL REFERENCES users(id) ON DELETE RESTRICT, version INTEGER NOT NULL DEFAULT 1 CHECK(version>=1), CHECK(updated_at>=created_at)"""
def upgrade():
 op.execute(f"""CREATE TABLE vehicle_type_catalog ({COMMON}, code VARCHAR(40) NOT NULL UNIQUE, display_name VARCHAR(100) NOT NULL, status VARCHAR(12) NOT NULL DEFAULT 'PENDING', requested_by_user_id UUID NULL REFERENCES users(id) ON DELETE RESTRICT, reviewed_by_user_id UUID NULL REFERENCES users(id) ON DELETE RESTRICT, reviewed_at TIMESTAMPTZ NULL, review_reason TEXT NULL, CHECK(code ~ '^[A-Z0-9_]{1,40}$'), CHECK(display_name=btrim(display_name) AND char_length(display_name)>0), CHECK(status IN ('PENDING','APPROVED','REJECTED')))""")
 op.execute("INSERT INTO vehicle_type_catalog (code,display_name,status) VALUES ('BIKE','Bike','APPROVED'),('THREE_WHEELER','Three-wheeler','APPROVED'),('CAR','Car','APPROVED'),('VAN','Van','APPROVED'),('BUS','Bus','APPROVED'),('OTHER','Other','APPROVED')")
 op.execute(f"""CREATE TABLE admin_manual_fulfilment_events ({COMMON}, booking_id UUID NULL REFERENCES bookings(id) ON DELETE RESTRICT, trip_id UUID NULL REFERENCES trips(id) ON DELETE RESTRICT, vehicle_id UUID NULL REFERENCES vehicles(id) ON DELETE RESTRICT, event_type VARCHAR(32) NOT NULL, summary VARCHAR(300) NOT NULL, details TEXT NOT NULL, status VARCHAR(16) NOT NULL DEFAULT 'OPEN', closed_by_user_id UUID NULL REFERENCES users(id) ON DELETE RESTRICT, closed_at TIMESTAMPTZ NULL, CHECK(event_type IN ('EXCEPTION_REVIEW','VEHICLE_SUPPORT','SAFETY_ESCALATION','PAYMENT_DISPUTE')), CHECK(status IN ('OPEN','CLOSED')), CHECK(summary=btrim(summary) AND char_length(summary)>0), CHECK(details=btrim(details) AND char_length(details)>0))""")
 op.execute("CREATE INDEX ix_vehicle_type_catalog_stage5 ON vehicle_type_catalog(status,created_at)")
 op.execute("CREATE INDEX ix_manual_fulfilment_stage5 ON admin_manual_fulfilment_events(status,created_at)")
def downgrade():
 for table in ('admin_manual_fulfilment_events','vehicle_type_catalog'):op.drop_table(table)
