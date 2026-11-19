"""Owner decision 15 Nov 2026: an Owner does not type how long each stop takes. The time from the first stop to every other stop
comes from the road route (one directions call when the route is saved), plus a buffer for traffic and short halts."""
import logging
import math
from decimal import Decimal
import httpx
from app.services.airports import km_between

log = logging.getLogger('travelly.routing')
BUFFER = 1.15          # ORS drives at road speed; real buses stop and queue
ROUND_UP_MINUTES = 5   # passengers see "about 10:20", not 10:17
FALLBACK_KMH = 45      # only when the route service cannot answer
ROAD_FACTOR = 1.3      # straight line to road distance


def segment_seconds(routing, stops):
    """Driving seconds between each pair of neighbouring stops from the route service, or None when it cannot answer."""
    settings = routing.settings
    if not settings.routing_api_key: return None
    coordinates = [[float(s.longitude), float(s.latitude)] for s in stops]
    try:
        response = httpx.post(settings.routing_base_url.rstrip('/') + '/openrouteservice/v2/directions/driving-car/geojson',
            headers={'Authorization': settings.routing_api_key}, timeout=20, json={'coordinates': coordinates, 'instructions': True})
        response.raise_for_status()
        segments = response.json()['features'][0]['properties']['segments']
        seconds = [float(x['duration']) for x in segments]
        if len(seconds) != len(stops) - 1 or any(not math.isfinite(x) or x < 0 for x in seconds): return None
        return seconds
    except (httpx.HTTPError, ValueError, TypeError, KeyError, IndexError) as exc:
        response = getattr(exc, 'response', None)
        log.warning('stop times: route service failed status=%s body=%s', getattr(response, 'status_code', None), (getattr(response, 'text', '') or str(exc))[:200])
        return None


def straight_line_seconds(stops):
    return [km_between(float(a.latitude), float(a.longitude), float(b.latitude), float(b.longitude)) * ROAD_FACTOR / FALLBACK_KMH * 3600
            for a, b in zip(stops, stops[1:])]


def stop_offsets(routing, stops):
    """Minutes from the first stop to each stop (the first is 0), never decreasing."""
    seconds = segment_seconds(routing, stops) or straight_line_seconds(stops)
    total, offsets = 0.0, [0]
    for part in seconds:
        total += part
        minutes = math.ceil(total * BUFFER / 60 / ROUND_UP_MINUTES) * ROUND_UP_MINUTES
        offsets.append(max(minutes, offsets[-1]))
    return offsets


def with_times(routing, body):
    """A copy of the Owner's route body whose stop times are worked out here; any times sent by the client are ignored."""
    offsets = stop_offsets(routing, body.stops)
    stops = [s.model_copy(update={'scheduled_offset_minutes': m}) for s, m in zip(body.stops, offsets)]
    update = {'stops': stops}
    if body.estimated_duration_minutes is None: update['estimated_duration_minutes'] = offsets[-1] or None
    return body.model_copy(update=update)
