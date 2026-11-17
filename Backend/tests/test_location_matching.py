from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.schemas.hire_schemas import Itinerary
from app.services import location_matching


class EmptySchedule:
    def scalar(self, _query):
        return None

    def get(self, *_args):
        return None


class Routing:
    def __init__(self, seconds=300):
        self.seconds = seconds

    def travel_seconds(self, *_args):
        if isinstance(self.seconds, list):
            return self.seconds.pop(0)
        return self.seconds


class Scheduled:
    def __init__(self, values):
        self.values = iter(values)

    def scalar(self, _query):
        return next(self.values)

    def get(self, *_args):
        return None


def place(label, latitude, longitude):
    return {'label': label, 'latitude': str(latitude), 'longitude': str(longitude), 'token': 'x' * 30}


def itinerary(start, pickup):
    return Itinerary.model_validate({
        'start_at': start.isoformat(), 'direction': 'ONE_WAY', 'method': 'DISTANCE',
        'service_hours': ['1'], 'stops': [
            {'place': pickup, 'wait_minutes': '0', 'overnight_rest': False},
            {'place': place('Destination', 6.95, 79.88), 'wait_minutes': '0', 'overnight_rest': False},
        ],
    })


def vehicle(now, *, accepting=True, observed=None):
    return SimpleNamespace(
        id=uuid4(), accepts_hire_bookings=accepting,
        base_latitude=Decimal('9.6615'), base_longitude=Decimal('80.0255'),
        pickup_distance_km=Decimal('50'), current_latitude=Decimal('6.9271'),
        current_longitude=Decimal('79.8612'), current_location_source='MANUAL',
        current_location_observed_at=observed if observed is not None else now,
    )


def assess(v, trip, now, seconds=300):
    return location_matching.assess(EmptySchedule(), Routing(seconds), v, trip,
        trip.requested_end(), 'driving-car', now=now)


def test_fresh_colombo_position_can_match_immediate_colombo_pickup():
    now = datetime.now(timezone.utc)
    trip = itinerary(now + timedelta(hours=1), place('Colombo', 6.9271, 79.8612))
    assert assess(vehicle(now), trip, now)['status'] == 'AVAILABLE'


def test_fresh_colombo_position_cannot_match_immediate_jaffna_pickup():
    now = datetime.now(timezone.utc)
    trip = itinerary(now + timedelta(hours=1), place('Jaffna', 9.6615, 80.0255))
    result = assess(vehicle(now), trip, now)
    assert result['status'] == 'UNREACHABLE'
    assert result['code'] == 'PICKUP_DISTANCE_EXCEEDED'


def test_bookings_off_wins_even_when_vehicle_is_nearby():
    now = datetime.now(timezone.utc)
    trip = itinerary(now + timedelta(hours=1), place('Colombo', 6.9271, 79.8612))
    assert assess(vehicle(now, accepting=False), trip, now)['code'] == 'BOOKINGS_OFF'


def test_stale_immediate_location_requires_owner_confirmation():
    now = datetime.now(timezone.utc)
    trip = itinerary(now + timedelta(hours=1), place('Colombo', 6.9271, 79.8612))
    result = assess(vehicle(now, observed=now - timedelta(minutes=16)), trip, now)
    assert result['status'] == 'CONFIRMATION_REQUIRED'
    assert result['code'] == 'VEHICLE_LOCATION_STALE'


def test_future_request_uses_base_not_todays_distant_position():
    now = datetime.now(timezone.utc)
    trip = itinerary(now + timedelta(days=2), place('Jaffna', 9.6615, 80.0255))
    result = assess(vehicle(now), trip, now)
    assert result['status'] == 'AVAILABLE'
    assert result['origin_source'] == 'BASE_LOCATION'


def test_unknown_routing_requires_confirmation_and_cannot_be_available():
    now = datetime.now(timezone.utc)
    trip = itinerary(now + timedelta(hours=1), place('Colombo', 6.9271, 79.8612))
    result = assess(vehicle(now), trip, now, seconds=None)
    assert result['status'] == 'CONFIRMATION_REQUIRED'
    assert result['code'] == 'REACHABILITY_UNKNOWN'


def test_preparation_time_is_added_to_pickup_travel_time():
    now = datetime.now(timezone.utc)
    trip = itinerary(now + timedelta(minutes=20), place('Colombo', 6.9271, 79.8612))
    result = assess(vehicle(now), trip, now, seconds=6 * 60)
    assert result['status'] == 'UNREACHABLE'
    assert result['code'] == 'PICKUP_UNREACHABLE'


def test_future_booking_checks_repositioning_from_before_and_to_after_commitments():
    now = datetime.now(timezone.utc)
    trip = itinerary(now + timedelta(days=2), place('Colombo', 6.9271, 79.8612))
    prior = SimpleNamespace(end_at=trip.start_at - timedelta(hours=1), itinerary_snapshot={
        'itinerary': {'stops': [{'place': place('Prior start', 7.0, 80.0)}, {'place': place('Prior end', 6.9271, 79.8612)}]},
    })
    following = SimpleNamespace(start_at=trip.requested_end() + timedelta(minutes=30), itinerary_snapshot={
        'itinerary': {'stops': [{'place': place('Next pickup', 7.2906, 80.6337)}, {'place': place('Next end', 7.3, 80.7)}]},
    })
    db = Scheduled([prior, following, None, None])
    result = location_matching.assess(db, Routing([300, 3600]), vehicle(now), trip,
        trip.requested_end(), 'driving-car', now=now)
    assert result['status'] == 'UNREACHABLE'
    assert result['code'] == 'NEXT_COMMITMENT_UNREACHABLE'
