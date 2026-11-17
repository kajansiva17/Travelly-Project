"""Where a vehicle most likely is, worked out from what Travelly already knows (owner decision 14 Nov 2026). No GPS and nothing
for the Owner to fill in:
1. LAST_TRIP     the last place of the vehicle's most recent completed private-hire / event trip (if it ended within STALE_DAYS).
                 A vehicle that finished Jaffna -> Colombo is now in Colombo.
2. SERVICE_AREA  otherwise the centre of the pickup area of the Owner's saved rate nearest to the pickup (the Owner's own "I work here").
3. None          unknown (a new vehicle with no trip and no rate): listed after the others, never hidden.
Search uses it only to order vehicles by straight-line distance to the pickup; the distance shown is approximate."""
from datetime import timedelta
from sqlalchemy import select
from app.models.hire_models import Booking, Trip
from app.services.odometer_proof import distance_km

STALE_DAYS = 7
NEAR_KM = 50.0


def last_places(db, vehicle_ids, now):
    """{vehicle_id: (lat, lng)} from each vehicle's latest completed trip that has a known last stop."""
    found = {}
    if not vehicle_ids: return found
    rows = db.execute(select(Trip.vehicle_id, Trip.actual_end_at, Booking.itinerary_snapshot).join(Booking, Booking.id == Trip.booking_id).where(
        Trip.vehicle_id.in_(vehicle_ids), Trip.status == 'COMPLETED', Trip.actual_end_at.is_not(None),
        Trip.actual_end_at >= now - timedelta(days=STALE_DAYS)).order_by(Trip.actual_end_at.desc()).limit(2000)).all()
    for vehicle_id, _, snapshot in rows:
        if vehicle_id in found: continue
        stops = ((snapshot or {}).get('itinerary') or {}).get('stops') or []
        if len(stops) >= 2:
            place = stops[-1].get('place') or {}
            if place.get('latitude') is not None and place.get('longitude') is not None:
                found[vehicle_id] = (float(place['latitude']), float(place['longitude']))
    return found


def area_centre(rules, pickup):
    """Centre of the pickup area of the saved rate nearest to the pickup."""
    best = None
    for rule in rules:
        area = rule.pickup_area
        if area is None:
            continue
        centre = ((float(area.south) + float(area.north)) / 2, (float(area.west) + float(area.east)) / 2)
        km = distance_km(float(pickup.latitude), float(pickup.longitude), *centre)
        if best is None or km < best[0]: best = (km, centre)
    return best[1] if best else None


def locate(vehicle_id, last, rules, pickup):
    """-> (distance_km or None, source or None)."""
    here = last.get(vehicle_id)
    source = 'LAST_TRIP'
    if here is None:
        here, source = area_centre(rules, pickup), 'SERVICE_AREA'
    if here is None: return None, None
    return round(distance_km(float(pickup.latitude), float(pickup.longitude), *here), 1), source


def order(entries):
    """Nearest first; unknown last. `near` marks vehicles within NEAR_KM."""
    for e in entries:
        e['near'] = e['distance_km'] is not None and e['distance_km'] <= NEAR_KM
    entries.sort(key=lambda e: (e['distance_km'] is None, e['distance_km'] if e['distance_km'] is not None else 0))
    return entries
