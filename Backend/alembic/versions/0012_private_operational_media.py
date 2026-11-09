"""Private operational-media metadata amendment. Create only; do not apply here."""
from alembic import op

revision='0012_private_operational_media'
down_revision='0011_ticket_booking'
branch_labels=None
depends_on=None

def upgrade():
    op.execute("ALTER TABLE trip_media ALTER COLUMN trip_id DROP NOT NULL")
    op.execute("ALTER TABLE trip_media ADD COLUMN vehicle_record_id UUID NULL REFERENCES vehicle_records(id) ON DELETE RESTRICT")
    op.execute("ALTER TABLE trip_media ADD COLUMN retention_until TIMESTAMPTZ NULL")
    op.execute("ALTER TABLE trip_media DROP CONSTRAINT IF EXISTS trip_media_media_kind_check")
    op.execute("ALTER TABLE trip_media ADD CONSTRAINT ck_trip_media_kind_private CHECK(media_kind IN ('DASHBOARD','DEPARTURE_ODOMETER','PICKUP_ODOMETER','DROPOFF_ODOMETER','RETURN_ODOMETER','EXPENSE_RECEIPT','MAINTENANCE_RECEIPT','RENTAL_INSPECTION'))")
    op.execute("ALTER TABLE trip_media ADD CONSTRAINT ck_trip_media_parent CHECK((trip_id IS NOT NULL)::integer + (vehicle_record_id IS NOT NULL)::integer >= 1)")

def downgrade():
    op.execute("ALTER TABLE trip_media DROP CONSTRAINT IF EXISTS ck_trip_media_parent")
    op.execute("ALTER TABLE trip_media DROP CONSTRAINT IF EXISTS ck_trip_media_kind_private")
    op.execute("ALTER TABLE trip_media DROP COLUMN retention_until")
    op.execute("ALTER TABLE trip_media DROP COLUMN vehicle_record_id")
    op.execute("ALTER TABLE trip_media ALTER COLUMN trip_id SET NOT NULL")
