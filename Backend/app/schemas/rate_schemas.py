"""Bounded reusable rate input. Monetary values are explicit decimal strings."""
import re
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID
from pydantic import BaseModel, BeforeValidator, Field, model_validator


def quantity(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]{1,10}(?:\.[0-9]{1,10})?', value):
        raise ValueError('Enter a nonnegative decimal value without separators or exponent notation.')
    return Decimal(value)


Amount = Annotated[Decimal, BeforeValidator(quantity)]


class RateModel(BaseModel):
    model_config = {'extra': 'forbid'}


class Place(RateModel):
    label: str = Field(min_length=1, max_length=200)
    latitude: Decimal = Field(ge=-90, le=90)
    longitude: Decimal = Field(ge=-180, le=180)
    token: str = Field(min_length=30, max_length=1500)


class Area(RateModel):
    label: str = Field(min_length=1, max_length=120)
    south: Decimal = Field(ge=-90, le=90)
    north: Decimal = Field(ge=-90, le=90)
    west: Decimal = Field(ge=-180, le=180)
    east: Decimal = Field(ge=-180, le=180)

    @model_validator(mode='after')
    def ordered(self):
        if self.south >= self.north or self.west >= self.east:
            raise ValueError('Use a nonempty area with south below north and west below east.')
        return self


class Coverage(RateModel):
    kind: Literal['ROUTE', 'AREA', 'ANY']
    places: list[Place] | None = Field(default=None, min_length=2, max_length=12)
    area: Area | None = None

    @model_validator(mode='after')
    def conditional(self):
        if self.kind == 'ROUTE' and (not self.places or self.area is not None):
            raise ValueError('A route needs ordered pickup/destination/stops, without area coverage.')
        if self.kind == 'AREA' and (self.area is None or self.places is not None):
            raise ValueError('Area coverage needs explicit boundaries, without a route list.')
        if self.kind == 'ANY' and (self.area is not None or self.places is not None):
            raise ValueError('General pricing cannot contain hidden route or area coverage.')
        return self


class ChangeLimits(RateModel):
    added_km: Amount
    added_hours: Amount
    added_wait_minutes: Amount
    added_amount: Amount


class OtherCharge(RateModel):
    label: str = Field(min_length=1, max_length=120)
    treatment: Literal['INCLUDED', 'SEPARATE_AT_COST']


class DepartureApplicability(RateModel):
    kind: Literal['ANY_TIME', 'WEEKLY_WINDOW']
    weekdays: list[Annotated[int, Field(strict=True, ge=0, le=6)]] | None = Field(default=None, min_length=1, max_length=7)
    from_time: str | None = Field(default=None, pattern=r'^(?:[01][0-9]|2[0-3]):[0-5][0-9]$')
    until_time: str | None = Field(default=None, pattern=r'^(?:[01][0-9]|2[0-3]):[0-5][0-9]$')

    @model_validator(mode='after')
    def explicit_window(self):
        if self.kind == 'ANY_TIME':
            if any(v is not None for v in (self.weekdays, self.from_time, self.until_time)):
                raise ValueError('Any-time applicability must not contain a hidden departure window.')
        elif (not self.weekdays or len(set(self.weekdays)) != len(self.weekdays)
              or not self.from_time or not self.until_time or self.from_time == self.until_time):
            raise ValueError('Select unique weekdays and a nonempty departure window; choose Any time for unrestricted departures.')
        return self


def departure_intervals(value):
    if value is None or value.kind == 'ANY_TIME':
        return [(0, 7 * 1440)]
    minutes = lambda s: int(s[:2]) * 60 + int(s[3:])
    start, end = minutes(value.from_time), minutes(value.until_time)
    result = []
    for day in value.weekdays:
        a, b = day * 1440 + start, day * 1440 + end + (1440 if end < start else 0)
        if b > 7 * 1440:
            result.extend([(a, 7 * 1440), (0, b - 7 * 1440)])
        else: result.append((a, b))
    return result


def departure_applies(value, local_start):
    if value is None: return False  # Legacy rules need explicit applicability before new offers.
    minute = local_start.weekday() * 1440 + local_start.hour * 60 + local_start.minute + local_start.second / 60
    return any(a <= minute < b for a, b in departure_intervals(value))


# Owner decision 14 Nov 2026: for every extra charge the Owner chooses NOT_OFFERED (the journey needs a quote if it uses it),
# FREE (no extra charge, the rate is 0) or CHARGED (the rates are filled in). Unset = CHARGED (older rules).
EXTRA_RATE_FIELDS = {'WAITING': ('free_wait_minutes', 'waiting_hour_rate'), 'EXTRA_KM': ('extra_km_rate',),
                     'EXTRA_HOURS': ('extra_hour_rate',), 'OVERNIGHT': ('overnight_driver_cost',)}
EXTRA_METHODS = {'WAITING': ('DISTANCE', 'DAY_HIRE', 'FIXED_ROUTE'), 'EXTRA_KM': ('DISTANCE', 'DAY_HIRE'),
                 'EXTRA_HOURS': ('DAY_HIRE',), 'OVERNIGHT': ('DAY_HIRE',)}


def extra_mode(rule, key):
    return rule.extra_policy.get(key, 'CHARGED')


class RateRule(RateModel):
    id: UUID
    label: str = Field(min_length=1, max_length=120)
    pickup_area: Area | None = None  # retained for older rules; vehicle location settings now control pickup matching
    coverage: Coverage
    direction: Literal['ONE_WAY', 'RETURN']
    effective_from: date
    effective_until: date | None = None
    method: Literal['DISTANCE', 'DAY_HIRE', 'FIXED_ROUTE']
    base_charge: Amount | None = None
    included_km: Amount | None = None
    extra_km_rate: Amount | None = None
    night_km_rate: Amount | None = None
    day_charge: Amount | None = None
    included_km_per_day: Amount | None = None
    included_hours_per_day: Amount | None = None
    extra_hour_rate: Amount | None = None
    overnight_driver_cost: Amount | None = None
    fixed_fare: Amount | None = None
    departure: DepartureApplicability | None = None
    free_wait_minutes: Amount
    waiting_hour_rate: Amount
    return_to_base: Literal['INCLUDED', 'SEPARATE_FIXED']
    return_to_base_charge: Amount | None = None
    return_to_base_notes: str = Field(min_length=1, max_length=500)
    tolls: Literal['INCLUDED', 'SEPARATE_AT_COST']
    parking: Literal['INCLUDED', 'SEPARATE_AT_COST']
    other_charges: list[OtherCharge] = Field(max_length=10)
    change_limits: ChangeLimits
    extra_policy: dict[Literal['WAITING', 'EXTRA_KM', 'EXTRA_HOURS', 'OVERNIGHT'], Literal['NOT_OFFERED', 'FREE', 'CHARGED']] = Field(default_factory=dict)

    @model_validator(mode='after')
    def relevant_fields(self):
        for key, mode in self.extra_policy.items():
            if self.method not in EXTRA_METHODS[key]:
                raise ValueError(f'extra_policy.{key}: not used by the {self.method} method.')
            if mode != 'CHARGED' and any(getattr(self, name) != 0 for name in EXTRA_RATE_FIELDS[key]):
                raise ValueError(f'extra_policy.{key}: enter 0 for the rate when it is not offered or free, or choose CHARGED.')
        distance = {'base_charge', 'included_km', 'extra_km_rate', 'night_km_rate'}
        day = {'day_charge', 'included_km_per_day', 'included_hours_per_day', 'extra_km_rate', 'extra_hour_rate', 'night_km_rate', 'overnight_driver_cost'}
        fixed = {'fixed_fare'}
        required = {'DISTANCE': distance, 'DAY_HIRE': day, 'FIXED_ROUTE': fixed}[self.method]
        for name in distance | day | fixed:
            if (getattr(self, name) is not None) != (name in required):
                raise ValueError(f'{name}: provide only fields for the selected pricing method.')
        if self.included_hours_per_day is not None and not 0 < self.included_hours_per_day <= 24:
            raise ValueError('included_hours_per_day: Included service hours per day must be greater than zero and at most 24.')
        if self.effective_until is not None and self.effective_until < self.effective_from:
            raise ValueError('effective_until: Effective end must not precede the start.')
        if self.method == 'FIXED_ROUTE' and self.coverage.kind != 'ROUTE':
            raise ValueError('A fixed-route fare requires explicit route coverage.')
        if self.method != 'FIXED_ROUTE' and self.departure is not None:
            raise ValueError('Departure applicability belongs to fixed-route fares only.')
        if (self.return_to_base_charge is not None) != (self.return_to_base == 'SEPARATE_FIXED'):
            raise ValueError('return_to_base_charge: Enter a disclosed return-to-base charge only when separately payable.')
        return self


def boxes_overlap(a, b):
    return a.south <= b.north and a.north >= b.south and a.west <= b.east and a.east >= b.west


def covered(area, place):
    return area.south <= place.latitude <= area.north and area.west <= place.longitude <= area.east


def conflicting(a, b):
    if (a.method == 'DAY_HIRE') != (b.method == 'DAY_HIRE') or a.direction != b.direction:
        return False
    if {a.method, b.method} == {'FIXED_ROUTE', 'DISTANCE'} and a.direction == 'ONE_WAY':
        return False  # Approved fixed-first precedence, not two additive services.
    if a.method == b.method == 'FIXED_ROUTE' and not any(
            x < v and y > u for x, y in departure_intervals(a.departure) for u, v in departure_intervals(b.departure)):
        return False
    if a.effective_from > (b.effective_until or date.max) or b.effective_from > (a.effective_until or date.max):
        return False
    ac, bc = a.coverage, b.coverage
    if 'ANY' in (ac.kind, bc.kind):
        return True
    if ac.kind == bc.kind == 'AREA':
        return boxes_overlap(ac.area, bc.area)
    if ac.kind == bc.kind == 'ROUTE':
        return [(p.latitude, p.longitude) for p in ac.places] == [(p.latitude, p.longitude) for p in bc.places]
    area, route = (ac.area, bc.places) if ac.kind == 'AREA' else (bc.area, ac.places)
    return all(covered(area, p) for p in route)


class RateConfiguration(RateModel):
    service_type_id: UUID
    expected_version: int = Field(strict=True, ge=0)
    enabled: bool = Field(strict=True)
    currency: Literal['LKR']
    rules: list[RateRule] = Field(min_length=1, max_length=30)

    @model_validator(mode='after')
    def no_conflicts(self):
        if any(r.method == 'FIXED_ROUTE' and r.departure is None for r in self.rules):
            raise ValueError('Fixed-route fares require explicit departure applicability before saving.')
        if len({r.id for r in self.rules}) != len(self.rules):
            raise ValueError('Rate identifiers must be unique.')
        for i, a in enumerate(self.rules):
            if any(conflicting(a, b) for b in self.rules[i + 1:]):
                raise ValueError('Rate coverage/effective dates overlap for the same trip type and direction.')
        return self


class WaitingPeriod(RateModel):
    day: int = Field(strict=True, ge=0, le=29)
    start_hour: Amount
    minutes: Amount


class ExampleTrip(RateModel):
    distance_km: Amount
    night_km: Amount
    waiting_minutes: Amount
    service_hours: list[Amount] = Field(min_length=1, max_length=30)
    overnight_stays: int = Field(strict=True, ge=0, le=29)
    waiting_periods: list[WaitingPeriod] = Field(default_factory=list, max_length=60)

    @model_validator(mode='after')
    def coherent(self):
        if self.night_km > self.distance_km or any(h > 24 for h in self.service_hours):
            raise ValueError('Night km cannot exceed total km; each service window is at most 24 hours.')
        if self.overnight_stays > len(self.service_hours) - 1:
            raise ValueError('Overnight stays cannot exceed the gaps between service windows.')
        previous = {}
        for period in sorted(self.waiting_periods, key=lambda w: (w.day, w.start_hour)):
            end = period.start_hour + period.minutes / Decimal('60')
            if period.day >= len(self.service_hours) or end > self.service_hours[period.day] or period.start_hour < previous.get(period.day, Decimal('0')):
                raise ValueError('Waiting periods must fit their service windows and must not overlap.')
            previous[period.day] = end
        if self.waiting_periods and sum((p.minutes for p in self.waiting_periods), Decimal('0')) != self.waiting_minutes:
            raise ValueError('Waiting periods must sum to total waiting minutes.')
        return self


class ExamplePreview(RateModel):
    rule: RateRule
    example: ExampleTrip
    @model_validator(mode='after')
    def applicability(self):
        if self.rule.method == 'FIXED_ROUTE' and self.rule.departure is None:
            raise ValueError('Fixed-route fares require explicit departure applicability.')
        return self
