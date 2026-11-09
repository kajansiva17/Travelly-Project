"""Route and ordered-stop contracts (matrix entries 27-31). Strict bodies; unknown fields are rejected."""
from decimal import Decimal
from typing import List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class StopIn(Strict):
    id: Optional[UUID] = None
    stop_code: Optional[str] = Field(None, min_length=1, max_length=30)
    stop_name: str = Field(min_length=1, max_length=150)
    latitude: Decimal = Field(ge=-90, le=90, max_digits=9, decimal_places=6)
    longitude: Decimal = Field(ge=-180, le=180, max_digits=9, decimal_places=6)
    pickup_allowed: bool = True
    dropoff_allowed: bool = True
    scheduled_offset_minutes: int = Field(0, ge=0, le=100000)


class RouteFields(Strict):
    route_name: str = Field(min_length=1, max_length=150)
    origin_name: str = Field(min_length=1, max_length=150)
    destination_name: str = Field(min_length=1, max_length=150)
    origin_latitude: Optional[Decimal] = Field(None, ge=-90, le=90, max_digits=9, decimal_places=6)
    origin_longitude: Optional[Decimal] = Field(None, ge=-180, le=180, max_digits=9, decimal_places=6)
    destination_latitude: Optional[Decimal] = Field(None, ge=-90, le=90, max_digits=9, decimal_places=6)
    destination_longitude: Optional[Decimal] = Field(None, ge=-180, le=180, max_digits=9, decimal_places=6)
    estimated_distance_km: Optional[Decimal] = Field(None, ge=0, max_digits=12, decimal_places=3)
    estimated_duration_minutes: Optional[int] = Field(None, ge=0)


class RouteCreate(RouteFields):
    route_code: str = Field(min_length=1, max_length=30, pattern=r'^[A-Za-z0-9][A-Za-z0-9_-]*$')
    active: bool = False
    stops: List[StopIn] = Field(min_length=2, max_length=50)


class RoutePatch(Strict):
    expected_version: int = Field(ge=1)
    route_name: Optional[str] = Field(None, min_length=1, max_length=150)
    origin_name: Optional[str] = Field(None, min_length=1, max_length=150)
    destination_name: Optional[str] = Field(None, min_length=1, max_length=150)
    origin_latitude: Optional[Decimal] = Field(None, ge=-90, le=90, max_digits=9, decimal_places=6)
    origin_longitude: Optional[Decimal] = Field(None, ge=-180, le=180, max_digits=9, decimal_places=6)
    destination_latitude: Optional[Decimal] = Field(None, ge=-90, le=90, max_digits=9, decimal_places=6)
    destination_longitude: Optional[Decimal] = Field(None, ge=-180, le=180, max_digits=9, decimal_places=6)
    estimated_distance_km: Optional[Decimal] = Field(None, ge=0, max_digits=12, decimal_places=3)
    estimated_duration_minutes: Optional[int] = Field(None, ge=0)
    status: Optional[Literal['DRAFT', 'ACTIVE', 'INACTIVE']] = None


class StopsReplace(Strict):
    expected_version: int = Field(ge=1)
    stops: List[StopIn] = Field(min_length=2, max_length=50)


class OwnerStopIn(StopIn):
    # Owner's price from the first stop to this stop (decision 9 Nov 2026); only with stop_prices_enabled.
    price_from_start: Optional[Decimal] = Field(None, ge=0, max_digits=12, decimal_places=2)


class OwnerRouteIn(Strict):
    """An Owner's own route. Start and end come from the first and last stop; the route code is generated.
    With stop_prices_enabled every stop carries a price from the start; a Passenger pays
    price(get-off stop) - price(get-on stop). Without it, each departure uses one price for the whole trip."""
    route_name: Optional[str] = Field(None, min_length=1, max_length=150)
    estimated_distance_km: Optional[Decimal] = Field(None, ge=0, max_digits=12, decimal_places=3)
    estimated_duration_minutes: Optional[int] = Field(None, ge=0, le=100000)
    stop_prices_enabled: bool = False
    stops: List[OwnerStopIn] = Field(min_length=2, max_length=50)

    @model_validator(mode='after')
    def prices(self):
        given = [s.price_from_start for s in self.stops]
        if not self.stop_prices_enabled:
            if any(p is not None for p in given):
                raise ValueError('Turn on "different price for each stop" to enter stop prices.')
            return self
        if any(p is None for p in given):
            raise ValueError('Enter a price from the start for every stop.')
        if given[0] != 0:
            raise ValueError('The first stop is the start, so its price from the start is 0.')
        if any(b < a for a, b in zip(given, given[1:])):
            raise ValueError('Prices from the start must not go down along the route.')
        if given[-1] <= 0:
            raise ValueError('Enter the price for the whole trip at the last stop.')
        return self


class OwnerRouteUpdate(OwnerRouteIn):
    expected_version: int = Field(ge=1)


class OwnerRouteStatus(Strict):
    expected_version: int = Field(ge=1)
    active: bool
