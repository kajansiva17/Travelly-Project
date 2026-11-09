# Default Ticket seat-hold time chosen by the project owner (9 November 2026): 10 minutes.
# Stored in the existing service_types.settings JSONB (PRD 4.5 hold_minutes); Admin can change it later
# from the dashboard. Data-only migration: no table or column is added.
from alembic import op

revision = '0008_ticket_hold_default'
down_revision = '0007_ticket_seat_inventory'
branch_labels = depends_on = None


def upgrade():
    # Only fills a missing value; an Admin-configured hold time is never overwritten.
    op.execute(
        "UPDATE service_types SET settings = settings || '{\"hold_minutes\": 10}'::jsonb, "
        "version = version + 1, updated_at = greatest(now(), updated_at) "
        "WHERE category = 'TICKET_HIRE' AND NOT (settings ? 'hold_minutes')"
    )


def downgrade():
    # Leave the value in place: it may since have been changed by an Admin.
    pass
