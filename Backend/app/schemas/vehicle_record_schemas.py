"""Vehicle records (PRD matrix 71-73): maintenance, energy, odometer and personal-use entries. Strict bodies."""
from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

RECORD_TYPES = Literal['OIL_CHANGE', 'OIL_FILTER_CHANGE', 'TYRE_CHANGE', 'TYRE_ROTATION', 'WHEEL_ALIGNMENT', 'WHEEL_BALANCING',
                       'GENERAL_SERVICE', 'BRAKE_SERVICE', 'BATTERY_SERVICE', 'REPAIR', 'FUEL_PURCHASE', 'EV_CHARGING',
                       'PERSONAL_EXTRA_USE', 'ODOMETER_UPDATE']
KM = Field(None, ge=0, max_digits=12, decimal_places=1)


class VehicleRecordIn(BaseModel):
    """AVAILABILITY_BLOCK is not accepted here: blocks use the calendar endpoints (contract 09)."""
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    record_type: RECORD_TYPES
    recorded_at: datetime
    odometer_km: Optional[Decimal] = KM
    start_odometer_km: Optional[Decimal] = KM
    end_odometer_km: Optional[Decimal] = KM
    amount: Optional[Decimal] = Field(None, ge=0, max_digits=12, decimal_places=2)
    currency: Optional[str] = Field(None, pattern=r'^[A-Z]{3}$')
    quantity: Optional[Decimal] = Field(None, gt=0, max_digits=12, decimal_places=3)
    unit: Optional[Literal['L']] = None
    fuel_type: Optional[Literal['PETROL', 'DIESEL']] = None
    fuel_grade_product: Optional[str] = Field(None, min_length=1, max_length=100)
    charging_kwh: Optional[Decimal] = Field(None, ge=0, max_digits=12, decimal_places=3)
    next_due_odometer_km: Optional[Decimal] = KM
    genuine_calendar_due_date: Optional[date] = None
    service_provider: Optional[str] = Field(None, min_length=1, max_length=150)
    notes: Optional[str] = Field(None, min_length=1, max_length=2000)
    confirm_duplicate: bool = False

    @field_validator('recorded_at')
    @classmethod
    def aware(cls, value):
        if value.tzinfo is None:
            raise ValueError('Include the time zone, for example 2026-11-12T09:30:00+05:30.')
        return value
