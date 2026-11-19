"""Airports for Airport hire (owner decision 15 Nov 2026).

The list lives in the Airport service's settings (`settings.airports`), so Admin can add, correct or switch off an airport without a new table.
A service that has never been edited uses DEFAULT_AIRPORTS. A place counts as an airport when it is within AIRPORT_RADIUS_KM of an active airport,
so the Passenger can choose the airport from the dropdown or search for a place right next to it.
Coordinates are public-map values; Admin should check them once.
"""
import math
from app.services.pricing_scope import private_hire_scope

AIRPORT_RADIUS_KM = 3.0
MAX_AIRPORTS = 50
DEFAULT_MIN_DISTANCE_KM = 100
DEFAULT_AIRPORTS = [
    # The terminal point is the verified public road-access pickup/drop-off returned by the configured provider.
    # The former airport-centre point (7.180800, 79.884100) was inside the airfield and could not be road-snapped.
    {'code': 'CMB', 'name': 'Bandaranaike International Airport, Katunayake', 'latitude': '7.173397', 'longitude': '79.887110', 'is_active': True},
    {'code': 'RML', 'name': 'Ratmalana Airport, Colombo', 'latitude': '6.821900', 'longitude': '79.886200', 'is_active': True},
    {'code': 'HRI', 'name': 'Mattala Rajapaksa International Airport, Mattala', 'latitude': '6.284400', 'longitude': '81.124100', 'is_active': True},
    {'code': 'JAF', 'name': 'Jaffna International Airport, Palaly', 'latitude': '9.792300', 'longitude': '80.070000', 'is_active': True},
    {'code': 'BTC', 'name': 'Batticaloa Airport', 'latitude': '7.705800', 'longitude': '81.678800', 'is_active': True},
    {'code': 'TRR', 'name': 'China Bay Airport, Trincomalee', 'latitude': '8.538500', 'longitude': '81.181900', 'is_active': True},
    {'code': 'SGT', 'name': 'Sigiriya Airport', 'latitude': '7.957000', 'longitude': '80.728500', 'is_active': True},
    {'code': 'KCT', 'name': 'Koggala Airport', 'latitude': '5.993700', 'longitude': '80.320300', 'is_active': True},
]


def km_between(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(float(lat1)), math.radians(float(lat2))
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(float(lon2) - float(lon1)) / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(a))


def airports_of(service):
    """Every airport of one Airport service (active or not), the default list when Admin has not saved one."""
    saved = (service.settings or {}).get('airports') if service else None
    return list(saved) if isinstance(saved, list) else [dict(a) for a in DEFAULT_AIRPORTS]


def active_airports(db):
    """The airports a Passenger can choose: active ones of every active Airport service, one entry per code."""
    from sqlalchemy import select
    from app.models.rate_models import ServiceType
    found = {}
    for row in db.scalars(select(ServiceType).where(ServiceType.category == 'PRIVATE_HIRE', ServiceType.is_active.is_(True)).order_by(ServiceType.display_order, ServiceType.id).limit(100)).all():
        if private_hire_scope(row) != 'AIRPORT': continue
        for airport in airports_of(row):
            if airport.get('is_active', True) and airport.get('code') and airport['code'] not in found: found[airport['code']] = airport
    return list(found.values())


def near_airport(airports, place):
    return any(km_between(place.latitude, place.longitude, a['latitude'], a['longitude']) <= AIRPORT_RADIUS_KM for a in airports)


def min_distance_km(service):
    value = (service.settings or {}).get('min_distance_km', DEFAULT_MIN_DISTANCE_KM) if service else DEFAULT_MIN_DISTANCE_KM
    try: return max(0, int(value))
    except (TypeError, ValueError): return DEFAULT_MIN_DISTANCE_KM
