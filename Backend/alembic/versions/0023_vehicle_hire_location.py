"""vehicle hire location and booking acceptance

Revision ID: 0023_vehicle_hire_location
Revises: 0022_owner_driver_status_length
"""
from alembic import op
import sqlalchemy as sa

revision = '0023_vehicle_hire_location'
down_revision = '0022_owner_driver_status_length'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('vehicles', sa.Column('accepts_hire_bookings', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('vehicles', sa.Column('base_location_label', sa.String(length=200), nullable=True))
    op.add_column('vehicles', sa.Column('base_latitude', sa.Numeric(9, 6), nullable=True))
    op.add_column('vehicles', sa.Column('base_longitude', sa.Numeric(9, 6), nullable=True))
    op.add_column('vehicles', sa.Column('pickup_distance_km', sa.Numeric(8, 2), nullable=True))
    op.add_column('vehicles', sa.Column('current_latitude', sa.Numeric(9, 6), nullable=True))
    op.add_column('vehicles', sa.Column('current_longitude', sa.Numeric(9, 6), nullable=True))
    op.add_column('vehicles', sa.Column('current_location_source', sa.String(length=12), nullable=True))
    op.add_column('vehicles', sa.Column('current_location_observed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('vehicles', sa.Column('current_location_accuracy_m', sa.Numeric(10, 2), nullable=True))
    for name, sql in (
        ('ck_vehicles_24', '(base_latitude IS NULL) = (base_longitude IS NULL)'),
        ('ck_vehicles_25', '(current_latitude IS NULL) = (current_longitude IS NULL)'),
        ('ck_vehicles_26', 'base_latitude IS NULL OR base_latitude BETWEEN -90 AND 90'),
        ('ck_vehicles_27', 'base_longitude IS NULL OR base_longitude BETWEEN -180 AND 180'),
        ('ck_vehicles_28', 'current_latitude IS NULL OR current_latitude BETWEEN -90 AND 90'),
        ('ck_vehicles_29', 'current_longitude IS NULL OR current_longitude BETWEEN -180 AND 180'),
        ('ck_vehicles_30', 'pickup_distance_km IS NULL OR pickup_distance_km>0'),
        ('ck_vehicles_31', "current_location_source IS NULL OR current_location_source IN ('GPS','MANUAL')"),
        ('ck_vehicles_32', '(current_latitude IS NULL) = (current_location_observed_at IS NULL)'),
        ('ck_vehicles_33', 'current_location_accuracy_m IS NULL OR current_location_accuracy_m>=0'),
    ):
        op.create_check_constraint(name, 'vehicles', sql)


def downgrade():
    for name in reversed([f'ck_vehicles_{n}' for n in range(24, 34)]):
        op.drop_constraint(name, 'vehicles', type_='check')
    for name in ('current_location_accuracy_m', 'current_location_observed_at', 'current_location_source',
                 'current_longitude', 'current_latitude', 'pickup_distance_km', 'base_longitude',
                 'base_latitude', 'base_location_label', 'accepts_hire_bookings'):
        op.drop_column('vehicles', name)
