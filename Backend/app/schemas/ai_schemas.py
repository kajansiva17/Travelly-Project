from typing import Literal, Optional
from pydantic import Field
from app.schemas.scheduled_trip_schemas import Strict

Language = Literal['en', 'ta', 'si']


class SearchFilters(Strict):
    """What is already known. Same names the response returns; the UI sends back the filters it got (edited or not)."""
    service: Optional[Literal['local', 'airport', 'long-distance', 'ticket']] = None
    journey: Optional[Literal['ONE_WAY', 'RETURN']] = None
    duration: Optional[Literal['ONE_DAY', 'MULTI_DAY']] = None
    pickup: Optional[str] = Field(default=None, min_length=1, max_length=100)
    destination: Optional[str] = Field(default=None, min_length=1, max_length=100)
    date: Optional[str] = Field(default=None, pattern=r'^\d{4}-\d{2}-\d{2}$')
    time: Optional[str] = Field(default=None, pattern=r'^([01]\d|2[0-3]):[0-5]\d$')
    return_date: Optional[str] = Field(default=None, pattern=r'^\d{4}-\d{2}-\d{2}$')
    return_time: Optional[str] = Field(default=None, pattern=r'^([01]\d|2[0-3]):[0-5]\d$')
    hours: Optional[int] = Field(default=None, ge=1, le=24)
    passengers: Optional[int] = Field(default=None, ge=1, le=200)
    large_luggage: Optional[int] = Field(default=None, ge=0, le=200)
    small_luggage: Optional[int] = Field(default=None, ge=0, le=200)
    flight: Optional[str] = Field(default=None, max_length=24, pattern=r'^[A-Za-z0-9 -]+$')


class SearchAssist(Strict):
    message: str = Field(min_length=1, max_length=500)
    language: Language = 'en'
    filters: SearchFilters = Field(default_factory=SearchFilters)
    # The field the previous answer asked about, so a bare reply ("5", "Colombo Fort") fills it.
    asking: Optional[Literal['service', 'pickup', 'destination', 'date', 'time', 'journey', 'return_date', 'return_time',
                             'hours', 'passengers', 'luggage']] = None


class HelpQuestion(Strict):
    question: str = Field(min_length=2, max_length=500)
    language: Language = 'en'
