from datetime import timedelta
from decimal import Decimal
from typing import Literal
from uuid import UUID
from pydantic import AwareDatetime, Field, PrivateAttr, StrictBool, field_validator, model_validator
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
    service_hours: list[Amount] | None = Field(default=None, min_length=1, max_length=30)   # omitted = Travelly works the hours out from the route
    trip_days: int | None = Field(default=None, ge=1, le=30, strict=True)   # only with service_hours omitted: how many pickup-anchored days the Passenger books
    flight_number: str | None = Field(default=None, max_length=24, pattern=r'^[A-Za-z0-9 -]+$')
    return_start_at: AwareDatetime | None = None
    event_package_id: UUID | None = None   # Event hire only: which of the vehicle's Owner packages is booked
    _auto: bool = PrivateAttr(default=False)   # True only when the caller left service_hours out; never read from input or stored

    @model_validator(mode='after')
    def coherent(self):
        if self.service_hours is None:
            if any(s.overnight_rest for s in self.stops):
                raise ValueError('Overnight rest requires a multi-day booking with service hours for each day.')
            self.service_hours, self._auto = [Decimal('24')] * (self.trip_days or 1), True
        if not self._auto: self.trip_days = None   # explicit hours already say how many days
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


class PositioningConfirmation(Version):
    vehicle_expected_version: int = Field(strict=True, ge=1)
    kind: Literal['CURRENT', 'PLANNED']
    location: Place
    available_at: AwareDatetime | None = None
    accuracy_m: Decimal | None = Field(default=None, ge=0, le=Decimal('99999999.99'))

    @model_validator(mode='after')
    def timing(self):
        if self.kind == 'PLANNED' and self.available_at is None:
            raise ValueError('Planned positioning needs the time the vehicle will be there.')
        if self.kind == 'CURRENT' and self.available_at is not None:
            raise ValueError('A current-location confirmation uses the confirmation time.')
        return self


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
    # The Owner cannot do the requested time and offers another. Only the Passenger's acceptance moves the booking.
    proposed_start_at: AwareDatetime | None = None


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


class TripLocation(Version):
    latitude: Decimal = Field(ge=-90, le=90)
    longitude: Decimal = Field(ge=-180, le=180)
    accuracy_m: Decimal | None = Field(default=None, ge=0, le=Decimal('99999999.99'))
    speed_kph: Decimal | None = Field(default=None, ge=0, le=Decimal('999999.99'))
    @field_validator('latitude', 'longitude')
    @classmethod
    def map_precision(cls, value):
        if -value.as_tuple().exponent > 6: raise ValueError('Use at most six decimal places for a map position.')
        return value
    @field_validator('accuracy_m', 'speed_kph')
    @classmethod
    def sensor_precision(cls, value):
        if value is not None and -value.as_tuple().exponent > 2: raise ValueError('Use at most two decimal places.')
        return value


class Breakdown(Version):
    kind: Literal['BREAKDOWN', 'ASSISTANCE_REQUIRED']
    details: str = Field(min_length=1, max_length=2000)
    @field_validator('details')
    @classmethod
    def written(cls, value):
        if not value.strip(): raise ValueError('Describe what happened so the Owner and Passenger can act.')
        return value.strip()


class CompleteTrip(Version):
    end_odometer_km: Amount
    completion_notes: str | None = Field(default=None, max_length=2000)
    waiting_minutes: Decimal | None = Field(default=None, ge=0, le=1440, max_digits=6, decimal_places=1)   # Book now return: the waited minutes the Driver confirms
    @field_validator('end_odometer_km')
    @classmethod
    def closing_odometer(cls, value):
        if value > Decimal('99999999999.9') or value % Decimal('.1'):
            raise ValueError('Use actual odometer km with at most one decimal place.')
        return value


class PickupVerification(Version):
    """The Driver sends what they scanned, or the six digits the Passenger read out."""
    qr_token: str | None = Field(default=None, min_length=16, max_length=64)
    pin: str | None = Field(default=None, pattern=r'^[0-9]{6}$')
    @model_validator(mode='after')
    def exactly_one(self):
        if bool(self.qr_token) == bool(self.pin):
            raise ValueError('Send either the scanned code or the six-digit number, not both.')
        return self


class ChangeBody(Version):
    reason: Literal['ADDED_STOP', 'DESTINATION_CHANGE', 'EXTRA_WAIT', 'DEPARTURE_TIME_CHANGE']
    itinerary: Itinerary


class Resolution(Version):
    reason: str = Field(min_length=1, max_length=500)


class CancelRide(Version):
    reason: str | None = Field(default=None, max_length=300)   # Book now: why the ride was cancelled before it started


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
        if 'EMISSION' not in self.conditional_documents:
            raise ValueError('Admin must explicitly confirm whether the emission certificate is required (the fitness certificate is optional).')
        self.conditional_documents = {**self.conditional_documents, 'FITNESS': False, 'ROUTE_PERMIT': False}
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


class EventPackage(RateModel):
    """One Owner event package: this vehicle with its Driver for a fixed number of hours at a fixed price."""
    id: UUID
    name: str = Field(min_length=1, max_length=120)
    hours: Amount
    price: Amount
    notes: str | None = Field(default=None, max_length=500)

    @field_validator('hours')
    @classmethod
    def sensible_hours(cls, value):
        if not 0 < value <= 24: raise ValueError('An event package covers more than zero and at most 24 hours.')
        return value

    @field_validator('price')
    @classmethod
    def sensible_price(cls, value):
        if not 0 < value <= Decimal('9999999999.99') or -value.as_tuple().exponent > 2: raise ValueError('Enter a price above zero with at most two decimals.')
        return value


class EventPackages(RateModel):
    service_type_id: UUID
    expected_version: int = Field(strict=True, ge=0)
    enabled: bool = Field(strict=True)
    packages: list[EventPackage] = Field(min_length=1, max_length=20)

    @model_validator(mode='after')
    def unique(self):
        if len({p.id for p in self.packages}) != len(self.packages): raise ValueError('Package identifiers must be unique.')
        return self
