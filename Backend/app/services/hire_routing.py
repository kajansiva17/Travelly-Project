"""Trusted planned route measurements. Provider failures never produce zero fares."""
from datetime import timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo
import httpx
from app.core.errors import ApiError
from app.schemas.rate_schemas import ExampleTrip

ZONE = ZoneInfo('Asia/Colombo')


def night_distance(km, start, seconds):
    """Integrate individual provider instruction segments over local night boundaries."""
    end = start + timedelta(seconds=float(seconds))
    cursor, night = start, Decimal('0')
    while cursor < end:
        local = cursor.astimezone(ZONE)
        boundary = local.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        part_end = min(end, boundary)
        if local.hour >= 22 or local.hour < 5:
            night += Decimal(str((part_end - cursor).total_seconds()))
        cursor = part_end
    return km * night / seconds if seconds else Decimal('0')


class HireRouting:
    def __init__(self, settings, locations): self.settings, self.locations = settings, locations

    def road_km(self, stops):
        """Road distance of the whole stop chain in km, or None when it cannot be measured (the price step then reports the real problem).
        One directions call per distinct chain; the answer is kept in memory so a search does not spend the free routing quota again."""
        for stop in stops: self.locations.verify(stop.place)
        if not self.settings.routing_api_key: return None
        coordinates = [[float(s.place.longitude), float(s.place.latitude)] for s in stops]
        key = tuple((round(c[0], 5), round(c[1], 5)) for c in coordinates)
        cache = self.__dict__.setdefault('_road_km_cache', {})
        if key in cache: return cache[key]
        try:
            response = httpx.post(self.settings.routing_base_url.rstrip('/') + '/openrouteservice/v2/directions/driving-car/geojson',
                headers={'Authorization': self.settings.routing_api_key}, timeout=15, json={'coordinates': coordinates, 'instructions': False})
            response.raise_for_status()
            km = Decimal(str(response.json()['features'][0]['properties']['summary']['distance'])) / 1000
            if not km.is_finite() or km < 0: return None
        except (httpx.HTTPError, ValueError, TypeError, KeyError, IndexError, ArithmeticError):
            return None
        if len(cache) >= 300: cache.pop(next(iter(cache)))
        cache[key] = km
        return km

    def measure(self, itinerary, profile):
        for stop in itinerary.stops: self.locations.verify(stop.place)
        if not self.settings.routing_api_key:
            raise ApiError(503, 'ROUTING_NOT_CONFIGURED', 'Trip pricing needs the configured route service. Request a quote once route measurements are available.')
        try:
            response = httpx.post(self.settings.routing_base_url.rstrip('/') + '/openrouteservice/v2/directions/' + profile + '/geojson',
                headers={'Authorization': self.settings.routing_api_key}, timeout=15,
                json={'coordinates': [[float(s.place.longitude), float(s.place.latitude)] for s in itinerary.stops], 'instructions': True})
            response.raise_for_status()
            route = response.json()['features'][0]
            segments = route['properties']['segments']
            if len(segments) != len(itinerary.stops) - 1: raise ValueError()
            geometry = route['geometry']['coordinates']
            if not geometry or len(geometry) > 100000: raise ValueError()
            return self.from_segments(itinerary, segments, geometry)
        except ApiError: raise
        except (httpx.HTTPError, ValueError, TypeError, KeyError, IndexError, ArithmeticError):
            raise ApiError(503, 'ROUTING_UNAVAILABLE', 'A trustworthy route price is unavailable. Please try again or request an Owner quote.') from None

    def from_segments(self, itinerary, segments, geometry):
        distance = night = waiting = Decimal('0')
        cursor = itinerary.start_at
        waiting_periods = []
        for i, stop in enumerate(itinerary.stops):
            minutes = stop.wait_minutes
            if minutes and not stop.overnight_rest:
                remaining = minutes
                while remaining:
                    hours = Decimal(str((cursor - itinerary.start_at).total_seconds())) / Decimal('3600')
                    day = int(hours // 24); offset = hours - day * 24
                    duration = min(remaining, (24 - offset) * 60)
                    waiting_periods.append({'day': day, 'start_hour': str(offset), 'minutes': str(duration)})
                    remaining -= duration; cursor += timedelta(minutes=float(duration))
                waiting += minutes
            else:
                cursor += timedelta(minutes=float(minutes))
            if i == len(segments): break
            segment = segments[i]
            steps = segment['steps']
            if not steps: raise ValueError()
            step_total = sum((Decimal(str(s['distance'])) for s in steps), Decimal('0'))
            if abs(step_total - Decimal(str(segment['distance']))) > Decimal('2'): raise ValueError()
            for step in steps:
                km = Decimal(str(step['distance'])) / 1000
                seconds = Decimal(str(step['duration']))
                if not km.is_finite() or not seconds.is_finite() or km < 0 or seconds < 0 or (km > 0 and seconds == 0): raise ValueError()
                movement_end = cursor + timedelta(seconds=float(seconds))
                check = cursor
                while check < movement_end:
                    elapsed = Decimal(str((check - itinerary.start_at).total_seconds())) / Decimal('3600')
                    day = int(elapsed // 24)
                    if day >= len(itinerary.service_hours): raise ValueError()
                    window_end = itinerary.start_at + timedelta(hours=24*day + float(itinerary.service_hours[day]))
                    if check >= window_end or (movement_end > window_end and itinerary.service_hours[day] < 24):
                        raise ApiError(422, 'ITINERARY_TIME_CONFLICT', 'Route travel falls outside the booked service hours. Add an explicit rest stop or adjust the service windows.')
                    check = min(movement_end, window_end)
                distance += km; night += night_distance(km, cursor, seconds)
                cursor += timedelta(seconds=float(seconds))
        if cursor > itinerary.requested_end():
            raise ApiError(422, 'ITINERARY_TIME_CONFLICT', 'The trusted route and stops exceed the booked service windows. Allow enough time for the itinerary.')
        try:
            usage = ExampleTrip.model_validate({'distance_km': str(distance), 'night_km': str(night), 'waiting_minutes': str(waiting),
                'service_hours': [str(h) for h in itinerary.service_hours], 'overnight_stays': sum(s.overnight_rest for s in itinerary.stops),
                'waiting_periods': waiting_periods if itinerary.method == 'DAY_HIRE' else []})
        except ValueError:
            raise ApiError(422, 'ITINERARY_TIME_CONFLICT', 'Planned waiting must fit the booked service windows. Review the stop times.') from None
        return {'usage': usage, 'end_at': cursor, 'geometry': geometry, 'source': 'openrouteservice', 'measured_at': itinerary.start_at.isoformat()}
