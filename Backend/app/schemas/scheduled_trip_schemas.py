"""Seat-layout and scheduled Ticket departure contracts (matrix 32-39). Strict bodies."""
import re
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator

SEAT_TYPES = Literal['STANDARD', 'WINDOW', 'AISLE', 'PREMIUM', 'ACCESSIBLE', 'CREW']
POLICIES = Literal['FIXED_GUARANTEED', 'MINIMUM_SEATS_WITH_PROTECTED_FULFILMENT']


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class SeatIn(Strict):
    code: str = Field(min_length=1, max_length=12)
    row: int = Field(ge=0, le=200)
    column: int = Field(ge=0, le=50)
    deck: int = Field(1, ge=1, le=3)
    type: SEAT_TYPES = 'STANDARD'
    bookable: bool = True


class SeatLayoutIn(Strict):
    layout_version: int = Field(ge=1)
    seats: List[SeatIn] = Field(min_length=1, max_length=120)


class TimezoneChecked(Strict):
    @field_validator('*', mode='after')
    @classmethod
    def timezone_required(cls, value):
        if isinstance(value, datetime) and value.tzinfo is None:
            raise ValueError('Include a time zone offset, for example +05:30.')
        return value


class DepartureFields(TimezoneChecked):
    route_id: UUID
    vehicle_id: UUID
    departure_at: datetime
    estimated_arrival_at: datetime
    booking_cutoff_at: datetime
    fare_per_seat: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    fulfilment_policy: POLICIES = 'FIXED_GUARANTEED'
    minimum_confirmed_seats: Optional[int] = Field(None, ge=1, le=200)
    decision_deadline: Optional[datetime] = None
    accepted_time_window_minutes: int = Field(0, ge=0, le=1440)
    accepted_replacement_terms: Dict[str, Any] = Field(default_factory=dict)
    operator_driver_user_id: Optional[UUID] = None


class BoardingMark(BaseModel):
    """One traveller the assigned Driver has just seen board."""
    model_config = {'extra': 'forbid'}
    traveller_id: UUID


class DepartureCreate(DepartureFields):
    pass


class DeparturePatch(TimezoneChecked):
    expected_version: int = Field(ge=1)
    # An Owner who does not drive assigns or changes the operator here while the departure is a draft.
    operator_driver_user_id: Optional[UUID] = None
    route_id: Optional[UUID] = None
    vehicle_id: Optional[UUID] = None
    departure_at: Optional[datetime] = None
    estimated_arrival_at: Optional[datetime] = None
    booking_cutoff_at: Optional[datetime] = None
    fare_per_seat: Optional[Decimal] = Field(None, ge=0, max_digits=12, decimal_places=2)
    fulfilment_policy: Optional[POLICIES] = None
    minimum_confirmed_seats: Optional[int] = Field(None, ge=1, le=200)
    decision_deadline: Optional[datetime] = None
    accepted_time_window_minutes: Optional[int] = Field(None, ge=0, le=1440)
    accepted_replacement_terms: Optional[Dict[str, Any]] = None
    operator_driver_user_id: Optional[UUID] = None


class PublishRequest(Strict):
    expected_version: int = Field(ge=1)
    publish_confirmed: Literal[True]


class DriverLookup(Strict):
    """A Driver's public reference, as shown on their Travelly profile (USR- and 16 hex characters)."""
    driver_reference: str = Field(min_length=20, max_length=20)

    @field_validator('driver_reference', mode='before')
    @classmethod
    def normalise(cls, value):
        value = value.strip().upper() if isinstance(value, str) else value
        if not isinstance(value, str) or not re.fullmatch(r'USR-[0-9A-F]{16}', value):
            raise ValueError('Enter a public reference like USR-0123456789ABCDEF.')
        return value


# --------------------------------------------------------------------------- protected fulfilment (matrix 54-58, D08)

class DepartureCommit(Strict):
    expected_version: int = Field(ge=1)


class DepartureProblem(Strict):
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=5, max_length=1000)
