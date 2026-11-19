"""Vehicle-position and adjacent-commitment feasibility for private hire."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy import select
from app.models.hire_models import Booking, ScheduledTrip, Route
from app.services.odometer_proof import distance_km

IMMEDIATE_WINDOW = timedelta(hours=2)
LOCATION_FRESHNESS = timedelta(minutes=15)
PREPARATION_TIME = timedelta(minutes=15)
OPEN_BOOKING = ('CANCELLED', 'REJECTED', 'COMPLETED')
OPEN_DEPARTURE = ('DRAFT', 'CANCELLED', 'COMPLETED')


def point(place):
    return float(place.latitude), float(place.longitude)


def itinerary_endpoint(snapshot, first=False):
    stops = ((snapshot or {}).get('itinerary') or {}).get('stops') or []
    if not stops:
        return None
    place = (stops[0] if first else stops[-1]).get('place') or {}
    if place.get('latitude') is None or place.get('longitude') is None:
        return None
    return float(place['latitude']), float(place['longitude'])


def adjacent_commitments(db, vehicle_id, start, end):
    previous = []
    following = []
    booking_before = db.scalar(select(Booking).where(Booking.vehicle_id == vehicle_id,
        Booking.vehicle_committed.is_(True), Booking.status.notin_(OPEN_BOOKING), Booking.end_at <= start)
        .order_by(Booking.end_at.desc()).limit(1))
    if booking_before:
        previous.append((booking_before.end_at, itinerary_endpoint(booking_before.itinerary_snapshot)))
    booking_after = db.scalar(select(Booking).where(Booking.vehicle_id == vehicle_id,
        Booking.vehicle_committed.is_(True), Booking.status.notin_(OPEN_BOOKING), Booking.start_at >= end)
        .order_by(Booking.start_at).limit(1))
    if booking_after:
        following.append((booking_after.start_at, itinerary_endpoint(booking_after.itinerary_snapshot, True)))
    departure_before = db.scalar(select(ScheduledTrip).where(ScheduledTrip.current_vehicle_id == vehicle_id,
        ScheduledTrip.status.notin_(OPEN_DEPARTURE), ScheduledTrip.estimated_arrival_at <= start)
        .order_by(ScheduledTrip.estimated_arrival_at.desc()).limit(1))
    if departure_before:
        route = db.get(Route, departure_before.route_id)
        previous.append((departure_before.estimated_arrival_at,
                         (float(route.destination_latitude), float(route.destination_longitude)) if route else None))
    departure_after = db.scalar(select(ScheduledTrip).where(ScheduledTrip.current_vehicle_id == vehicle_id,
        ScheduledTrip.status.notin_(OPEN_DEPARTURE), ScheduledTrip.departure_at >= end)
        .order_by(ScheduledTrip.departure_at).limit(1))
    if departure_after:
        route = db.get(Route, departure_after.route_id)
        following.append((departure_after.departure_at,
                          (float(route.origin_latitude), float(route.origin_longitude)) if route else None))
    prior = max(previous, key=lambda item: item[0]) if previous else None
    next_ = min(following, key=lambda item: item[0]) if following else None
    return prior, next_


def result(status, code, message, **extra):
    return {'status': status, 'code': code, 'message': message, **extra}


def assess(db, routing, vehicle, itinerary, reserved_end, profile, *, now=None, planned=None, require_accepting=True):
    """No locks or writes. AVAILABLE, CONFIRMATION_REQUIRED, or UNREACHABLE."""
    now = now or datetime.now(timezone.utc)
    if require_accepting and not vehicle.accepts_hire_bookings:
        return result('UNREACHABLE', 'BOOKINGS_OFF', 'This vehicle is not accepting new hire requests.')
    if vehicle.base_latitude is None or vehicle.base_longitude is None or vehicle.pickup_distance_km is None:
        return result('CONFIRMATION_REQUIRED', 'HIRE_LOCATION_NOT_CONFIGURED', 'Owner confirmation required: pickup settings are incomplete.')
    pickup = point(itinerary.stops[0].place)
    finish = point(itinerary.stops[-1].place)
    immediate = itinerary.start_at <= now + IMMEDIATE_WINDOW
    prior, next_ = adjacent_commitments(db, vehicle.id, itinerary.start_at, reserved_end)
    source = None
    provisional = None
    available_at = now
    if planned:
        origin = planned['point']
        radius_origin = origin
        available_at = planned['available_at']
        source = 'OWNER_CONFIRMED_' + planned.get('kind', 'PLANNED')
    elif immediate:
        fresh = (vehicle.current_location_observed_at is not None
                 and now - vehicle.current_location_observed_at <= LOCATION_FRESHNESS
                 and vehicle.current_latitude is not None and vehicle.current_longitude is not None)
        if not fresh:
            anchors = []
            if vehicle.current_latitude is not None and vehicle.current_longitude is not None:
                anchors.append(('LAST_DECLARED_POSITION', (float(vehicle.current_latitude), float(vehicle.current_longitude))))
            anchors.append(('BASE_LOCATION', (float(vehicle.base_latitude), float(vehicle.base_longitude))))
            matches = [(label, anchor, Decimal(str(distance_km(*anchor, *pickup))))
                       for label, anchor in anchors]
            matches = [candidate for candidate in matches if candidate[2] <= vehicle.pickup_distance_km]
            if not matches:
                return result('UNREACHABLE', 'PICKUP_DISTANCE_EXCEEDED',
                              'The pickup is outside this vehicle\'s accepted pickup distance.')
            source, radius_origin, straight = matches[0]
            origin = radius_origin
            provisional = ('VEHICLE_LOCATION_STALE',
                           'Owner confirmation required: the saved position is not current or verified for this pickup.')
        if fresh:
            origin = float(vehicle.current_latitude), float(vehicle.current_longitude)
            radius_origin = origin
            source = vehicle.current_location_source
    else:
        # The saved base is the provisional future discovery anchor. A prior
        # endpoint only proves (or disproves) repositioning feasibility; it is
        # not allowed to replace the Owner's pickup-radius centre indefinitely.
        radius_origin = float(vehicle.base_latitude), float(vehicle.base_longitude)
        provisional = ('FUTURE_POSITION_UNCONFIRMED',
                       'Owner confirmation required: confirm where the vehicle will be for this future pickup.')
        if prior:
            available_at, origin = prior
            source = 'PRECEDING_COMMITMENT'
            if origin is None:
                return result('CONFIRMATION_REQUIRED', 'PRECEDING_LOCATION_UNKNOWN',
                              'Owner confirmation required: the preceding trip endpoint is unknown.')
        else:
            origin = radius_origin
            source = 'BASE_LOCATION'
    if not (immediate and provisional):
        straight = Decimal(str(distance_km(*radius_origin, *pickup)))
    if straight > vehicle.pickup_distance_km:
        return result('UNREACHABLE', 'PICKUP_DISTANCE_EXCEEDED', 'The pickup is outside this vehicle\'s accepted pickup distance.')
    ready_at = None
    if not (immediate and provisional):
        seconds = routing.travel_seconds(origin, pickup, profile)
        if seconds is None:
            return result('CONFIRMATION_REQUIRED', 'REACHABILITY_UNKNOWN', 'Owner confirmation required: travel time to pickup could not be established.',
                          origin_source=source, distance_km=float(straight.quantize(Decimal('.1'))))
        ready_at = available_at + PREPARATION_TIME + timedelta(seconds=float(seconds))
        if ready_at > itinerary.start_at:
            return result('UNREACHABLE', 'PICKUP_UNREACHABLE', 'The vehicle cannot reach this pickup in time.')
    if next_:
        next_at, next_point = next_
        if next_point is None:
            return result('CONFIRMATION_REQUIRED', 'NEXT_LOCATION_UNKNOWN', 'Owner confirmation required: the next commitment pickup is unknown.')
        after = routing.travel_seconds(finish, next_point, profile)
        if after is None:
            return result('CONFIRMATION_REQUIRED', 'REACHABILITY_UNKNOWN', 'Owner confirmation required: travel time after this hire could not be established.')
        if reserved_end + PREPARATION_TIME + timedelta(seconds=float(after)) > next_at:
            return result('UNREACHABLE', 'NEXT_COMMITMENT_UNREACHABLE', 'This hire would prevent the vehicle reaching its next commitment.')
    if provisional:
        return result('CONFIRMATION_REQUIRED', provisional[0], provisional[1], immediate=immediate,
                      origin_source=source, distance_km=float(straight.quantize(Decimal('.1'))),
                      ready_at=ready_at.isoformat() if ready_at else None)
    return result('AVAILABLE', 'REACHABLE', 'Vehicle location and travel time are feasible.', immediate=immediate,
                  origin_source=source, distance_km=float(straight.quantize(Decimal('.1'))), ready_at=ready_at.isoformat())
