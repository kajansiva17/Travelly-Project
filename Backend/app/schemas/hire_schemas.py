from datetime import timedelta
from typing import Literal
from uuid import UUID
from pydantic import AwareDatetime, Field, StrictBool, field_validator, model_validator
from app.schemas.rate_schemas import RateModel, Amount, Place, RateConfiguration


class Stop(RateModel):
    place: Place
    wait_minutes: Amount
    overnight_rest: bool = Field(strict=True)


class Itinerary(RateModel):
    start_at: AwareDatetime
    direction: Literal['ONE_WAY', 'RETURN']
    method: Literal['DISTANCE', 'DAY_HIRE']
    stops: list[Stop] = Field(min_length=2, max_length=12)
    service_hours: list[Amount] = Field(min_length=1, max_length=30)
    flight_number: str | None = Field(default=None, max_length=24, pattern=r'^[A-Za-z0-9 -]+$')
    return_start_at: AwareDatetime | None = None

    @model_validator(mode='after')
    def coherent(self):
        if any(not 0 < h <= 24 for h in self.service_hours):
            raise ValueError('Each booked service window needs more than zero and at most 24 hours.')
        if sum(s.overnight_rest for s in self.stops) > len(self.service_hours) - 1:
            raise ValueError('Overnight rest requires a multi-day booking.')
        if self.stops[0].overnight_rest or self.stops[-1].overnight_rest:
            raise ValueError('Overnight rest belongs at an intermediate stop.')
        if self.direction == 'RETURN' and self.return_start_at is not None and self.return_start_at <= self.start_at:
            raise ValueError('Return pickup must be after the outbound pickup.')
        if self.direction == 'ONE_WAY' and self.return_start_at is not None:
            raise ValueError('A return pickup belongs only to a return journey.')
        return self

    def requested_end(self):
        duration = timedelta(hours=24 * (len(self.service_hours) - 1) + float(self.service_hours[-1]))
        return (self.return_start_at + duration) if self.return_start_at else self.start_at + duration

    def availability_intervals(self):
        duration = timedelta(hours=24 * (len(self.service_hours) - 1) + float(self.service_hours[-1]))
        return [(self.start_at, self.start_at + duration)] + ([(self.return_start_at, self.return_start_at + duration)] if self.return_start_at else [])


class HireRequest(RateModel):
    service_type_id: UUID
    vehicle_id: UUID
    itinerary: Itinerary
    passenger_count: int = Field(strict=True, ge=1, le=200)
    large_luggage_count: int = Field(strict=True, ge=0, le=200)
    small_luggage_count: int = Field(strict=True, ge=0, le=200)
    idempotency_key: str = Field(min_length=16, max_length=80, pattern=r'^[A-Za-z0-9_-]+$')


class SearchRequest(RateModel):
    service_type_id: UUID
    itinerary: Itinerary
    passenger_count: int = Field(strict=True, ge=1, le=200)
    large_luggage_count: int = Field(strict=True, ge=0, le=200)
    small_luggage_count: int = Field(strict=True, ge=0, le=200)


class Version(RateModel):
    expected_version: int = Field(strict=True, ge=1)


class Publication(Version):
    published: bool = Field(default=True, strict=True)


class PricingScope(Version):
    pricing_scope: Literal['LONG_DISTANCE', 'LOCAL', 'AIRPORT', 'EVENT', 'UNSPECIFIED']


class ServiceCreate(RateModel):
    code: str = Field(min_length=1, max_length=40, pattern=r'^[A-Z0-9_]+$')
    name: str = Field(min_length=1, max_length=100)
    default_pricing_basis: Literal['DISTANCE', 'TIME', 'FIXED', 'OWNER_QUOTE']
    is_active: bool = Field(strict=True)
    pricing_scope: Literal['LONG_DISTANCE', 'LOCAL', 'AIRPORT', 'EVENT', 'UNSPECIFIED']


class ServiceCatalogueUpdate(Version):
    pricing_scope: Literal['LONG_DISTANCE', 'LOCAL', 'AIRPORT', 'EVENT']
    status: Literal['DRAFT', 'ACTIVE', 'INACTIVE', 'NEEDS_REVIEW']


class QuoteBody(Version):
    rates: RateConfiguration


class Acceptance(Version):
    digest: str = Field(pattern=r'^[0-9a-f]{64}$')


class Assignment(Version):
    driver_reference: str | None = Field(default=None, pattern=r'^USR-[0-9A-F]{16}$')


class StartTrip(Version):
    start_odometer_km: Amount
    checklist_confirmed: Literal[True]
    @field_validator('checklist_confirmed', mode='before')
    @classmethod
    def explicit_confirmation(cls, value):
        if value is not True: raise ValueError('Confirm the readiness checklist explicitly.')
        return value
    @field_validator('start_odometer_km')
    @classmethod
    def supported_odometer(cls, value):
        from decimal import Decimal
        if value > Decimal('99999999999.9') or value % Decimal('.1'):
            raise ValueError('Use actual odometer km with at most one decimal place.')
        return value


class ChangeBody(Version):
    reason: Literal['ADDED_STOP', 'DESTINATION_CHANGE', 'EXTRA_WAIT', 'DEPARTURE_TIME_CHANGE']
    itinerary: Itinerary


class Resolution(Version):
    reason: str = Field(min_length=1, max_length=500)


class LicenceCategories(Version):
    categories: list[str] = Field(min_length=1, max_length=30)


class VehicleEligibility(Version):
    category: str = Field(min_length=1, max_length=60, pattern=r'^[A-Z0-9_]+$')
    conditional_documents: dict[Literal['EMISSION', 'FITNESS', 'ROUTE_PERMIT'], StrictBool]
    authorisation_required: bool = Field(strict=True)
    @model_validator(mode='after')
    def complete_applicability(self):
        # Project-owner decision (9 Nov 2026): a route permit is never mandatory, so Admin is not asked about it.
        # It is always stored as "not required"; an older client that still sends it cannot make it required.
        if not {'EMISSION', 'FITNESS'} <= set(self.conditional_documents):
            raise ValueError('Admin must explicitly confirm whether the emission and fitness certificates are required.')
        self.conditional_documents = {**self.conditional_documents, 'ROUTE_PERMIT': False}
        return self


class Compatibility(Version):
    matrix: dict[str, list[str]] = Field(min_length=1, max_length=30)
    routing_profiles: dict[str, Literal['driving-car', 'driving-hgv']]
    @model_validator(mode='after')
    def valid_matrix(self):
        import re
        if set(self.matrix) != set(self.routing_profiles) or any(not re.fullmatch(r'[A-Z0-9_]{1,60}', k) or not v or len(v) > 30 or any(not re.fullmatch(r'[A-Z0-9_-]{1,20}', c) for c in v) for k, v in self.matrix.items()):
            raise ValueError('Provide explicit category, licence codes and routing profile for every matrix entry.')
        return self
