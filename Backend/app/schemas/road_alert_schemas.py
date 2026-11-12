from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID
from pydantic import Field, field_validator
from app.schemas.scheduled_trip_schemas import Strict

AlertType = Literal['POLICE_PRESENCE', 'SPEED_CHECK', 'ACCIDENT', 'ROADBLOCK', 'ROAD_HAZARD']


class RoadAlertIn(Strict):
    trip_id: UUID
    alert_type: AlertType
    latitude: Decimal = Field(ge=-90, le=90)
    longitude: Decimal = Field(ge=-180, le=180)
    travel_direction_degrees: Optional[Decimal] = Field(default=None, ge=0, lt=360)
    description: Optional[str] = Field(default=None, min_length=1, max_length=280)
    source_input: Literal['BUTTON', 'VOICE'] = 'BUTTON'
    confidence_score: Optional[Decimal] = Field(default=None, ge=0, le=1)
    # PRD: voice classification never creates an alert by itself; the Driver confirms what was understood.
    driver_confirmed: bool = False

    @field_validator('latitude', 'longitude')
    @classmethod
    def six_places(cls, value):
        return value.quantize(Decimal('0.000001'))

    @field_validator('travel_direction_degrees')
    @classmethod
    def three_places(cls, value):
        return None if value is None else value.quantize(Decimal('0.001'))


class VoiceText(Strict):
    transcript: str = Field(min_length=1, max_length=300)
    language: Literal['en', 'ta', 'si'] = 'en'


class AlertVote(Strict):
    vote: Literal['CONFIRM', 'DENY']


class AlertModeration(Strict):
    expected_version: int = Field(ge=1)
    action: Literal['VERIFY', 'REJECT', 'REMOVE']
    reason: Optional[str] = Field(default=None, min_length=3, max_length=1000)
