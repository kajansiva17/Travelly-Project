# Trip reviews: remember when the Passenger changed a review (the Owner sees "Edited").
from alembic import op
from sqlalchemy import Column, DateTime

revision = '0033_review_edited'
down_revision = '0032_trip_reviews'
branch_labels = depends_on = None


def upgrade():
    op.add_column('trip_reviews', Column('edited_at', DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column('trip_reviews', 'edited_at')
