"""Ticket seat-hold contracts (matrix 40-41). Strict bodies; no payment or confirmation fields."""
import re
from typing import List, Optional
from uuid import UUID
import phonenumbers
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.schemas import clean_text, email_address


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class TravellerDraft(Strict):
    seat_id: UUID
    full_name: str = Field(min_length=1, max_length=150)
    contact_phone: Optional[str] = Field(None, max_length=20)
    contact_email: Optional[str] = Field(None, max_length=254)
    special_assistance: Optional[str] = Field(None, max_length=1000)

    @field_validator('full_name', 'special_assistance')
    @classmethod
    def plain(cls, value):
        return clean_text(value) if value is not None else value

    @field_validator('contact_phone')
    @classmethod
    def phone(cls, value):
        if value is None:
            return value
        if not re.fullmatch(r'\+[1-9][0-9]{6,14}', value):
            raise ValueError('Use an international number such as +94771234567.')
        if not phonenumbers.is_valid_number(phonenumbers.parse(value, None)):
            raise ValueError('Enter a valid phone number.')
        return value

    @field_validator('contact_email')
    @classmethod
    def email(cls, value):
        return email_address(value) if value is not None else value


class TicketHoldRequest(Strict):
    scheduled_trip_id: UUID
    travellers: List[TravellerDraft] = Field(min_length=1, max_length=100)
    boarding_stop_id: Optional[UUID] = None
    dropoff_stop_id: Optional[UUID] = None
    idempotency_key: str = Field(min_length=8, max_length=40, pattern=r'^[A-Za-z0-9_-]+$')

    @model_validator(mode='after')
    def distinct_seats(self):
        seats = [t.seat_id for t in self.travellers]
        if len(seats) != len(set(seats)):
            raise ValueError('Each traveller needs a different seat.')
        # Each stop is optional on its own (decision 9 Nov 2026): no get-on stop = route start, no get-off stop = route end.
        return self


class HoldRelease(Strict):
    expected_version: Optional[int] = Field(None, ge=1)
    reason: Optional[str] = Field(None, max_length=500)

    @field_validator('reason')
    @classmethod
    def plain(cls, value):
        return clean_text(value) if value is not None else value


class TicketHoldSettings(Strict):
    expected_version: int = Field(ge=1)
    hold_minutes: int = Field(ge=1, le=1440)
