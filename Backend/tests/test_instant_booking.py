"""Book now: a Passenger picks an online vehicle nearby (with its fare) and the person sending its location accepts within the time limit."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4
import pytest
from sqlalchemy import select
from app.models.hire_models import Booking, Trip
from app.models.rate_models import ServiceType, VehicleService
from app.models.review_models import Vehicle
from app.models.ride_models import RideRequest
from app.schemas.rate_schemas import ExampleTrip
from conftest import bearer
from test_hire_pricing import external_driver, hire_setup  # noqa: F401  (hire_setup is a fixture)
from test_live_vehicles import linked_driver, online, send
from test_rates import rate_owner, rule  # noqa: F401  (fixture used by hire_setup)


def switch(client, tokens, c, enabled=True):
    return client.patch(f'/api/v1/vehicles/{c.vehicle_id}/live/instant-booking', headers=bearer(tokens), json={'enabled': enabled})


def go_live(client, tokens, c):
    assert online(client, tokens, c).status_code == 200
    assert send(client, tokens, c).status_code == 200


@pytest.fixture
def ride(client, hire_setup, monkeypatch):
    """A LOCAL service with the Owner's per-km area rate, an Owner who switched Book now on, and a fixed 30 km route measurement."""
    c = hire_setup
    with client.app.state.sessions() as db:
        service = db.get(ServiceType, c.service_id)
        service.settings = {**service.settings, 'pricing_scope': 'LOCAL'}
        version = db.scalar(select(VehicleService.version).where(VehicleService.vehicle_id == c.vehicle_id, VehicleService.service_type_id == c.service_id))
        db.commit()
    saved = client.put(f'/api/v1/vehicles/{c.vehicle_id}/services', headers=bearer(c.owner),
                       json={**c.config, 'expected_version': version, 'rules': [rule()]})
    assert saved.status_code == 200, saved.text

    def measure(itinerary, profile):
        usage = ExampleTrip.model_validate({'distance_km': '30', 'night_km': '0', 'waiting_minutes': '0',
            'service_hours': [str(h) for h in itinerary.service_hours], 'overnight_stays': 0})
        return {'usage': usage, 'source': 'trusted-test-provider', 'end_at': itinerary.requested_end(),
                'geometry': [[float(s.place.longitude), float(s.place.latitude)] for s in itinerary.stops]}
    monkeypatch.setattr(client.app.state.hire_routing, 'measure', measure)
    monkeypatch.setattr(client.app.state.hire_routing, 'estimate_hours', lambda itinerary: Decimal('1'))
    assert switch(client, c.owner, c).status_code == 200
    return c


def where(c, **extra):
    return {'pickup': {'latitude': 6.93, 'longitude': 79.86}, 'destination': c.places['B'], 'passenger_count': 2, **extra}


def options(client, c, tokens=None, **extra):
    return client.post('/api/v1/ride-now/options', headers=bearer(tokens or c.passenger), json={**where(c), **extra})


def ask(client, c, fare, tokens=None):
    return client.post('/api/v1/ride-now/requests', headers=bearer(tokens or c.passenger), json={**where(c), 'vehicle_id': str(c.vehicle_id), 'fare': fare})


def answer(client, tokens, request_id, what):
    return client.post(f'/api/v1/ride-now/requests/{request_id}/{what}', headers=bearer(tokens), json={})


def listed_fare(client, c):
    found = options(client, c)
    assert found.status_code == 200, found.text
    assert len(found.json()['items']) == 1
    return found.json()['items'][0]['fare']


def test_only_the_owner_can_turn_book_now_on_or_off(client, hire_setup):
    c = hire_setup
    driver, tokens = linked_driver(client, c)
    assert switch(client, tokens, c).status_code == 404
    assert switch(client, c.owner, c).json()['instant_booking'] is True
    with client.app.state.sessions() as db:
        assert db.get(Vehicle, c.vehicle_id).instant_booking is True
    assert switch(client, c.owner, c, False).json()['instant_booking'] is False


def test_options_show_online_vehicles_with_their_own_fare_and_nothing_else(client, ride):
    c = ride
    assert options(client, c).json()['items'] == []   # not online yet
    go_live(client, c.owner, c)
    item = options(client, c).json()['items'][0]
    assert item['vehicle_id'] == str(c.vehicle_id) and item['distance_km'] == 0.0 and item['minutes_away'] >= 1
    assert Decimal(item['fare']) > 0 and 'latitude' not in item and 'owner' not in str(item).lower()
    assert options(client, c, radius_km=1).json()['items'][0]['vehicle_id'] == str(c.vehicle_id)
    far = options(client, c, pickup={'latitude': 7.5, 'longitude': 80.5})
    assert far.json()['items'] == []
    assert switch(client, c.owner, c, False).status_code == 200
    assert options(client, c).json()['items'] == []   # the Owner switched Book now off


def test_a_stale_position_is_not_listed(client, ride):
    c = ride
    go_live(client, c.owner, c)
    with client.app.state.sessions() as db:
        db.get(Vehicle, c.vehicle_id).current_location_observed_at = datetime.now(timezone.utc) - timedelta(minutes=30)
        db.commit()
    assert options(client, c).json()['items'] == []


def test_owner_driving_accepts_and_the_booking_and_trip_are_confirmed_at_once(client, ride):
    c = ride
    go_live(client, c.owner, c)
    fare = listed_fare(client, c)
    asked = ask(client, c, fare)
    assert asked.status_code == 201, asked.text
    request_id = asked.json()['id']
    assert asked.json()['status'] == 'OFFERED' and 0 < asked.json()['seconds_left'] <= 120
    waiting = client.get('/api/v1/me/ride-requests', headers=bearer(c.owner)).json()['items']
    assert [w['id'] for w in waiting] == [request_id] and waiting[0]['fare'] == fare
    accepted = answer(client, c.owner, request_id, 'accept')
    assert accepted.status_code == 200, accepted.text
    body = accepted.json()
    assert body['status'] == 'ACCEPTED' and body['booking']['status'] == 'CONFIRMED' and body['booking']['vehicle_committed'] is True
    assert Decimal(body['booking']['total_amount']) == Decimal(fare)
    with client.app.state.sessions() as db:
        trips = db.scalars(select(Trip).where(Trip.booking_id == UUID(body['booking_id']))).all()
        assert len(trips) == 1 and trips[0].assignment_type == 'OWNER_SELF_DRIVE' and trips[0].assignment_status == 'ACCEPTED' and trips[0].status == 'READY'
    assert client.get(f"/api/v1/bookings/{body['booking_id']}", headers=bearer(c.passenger)).status_code == 200
    assert client.get(f'/api/v1/ride-now/requests/{request_id}', headers=bearer(c.passenger)).json()['booking_id'] == body['booking_id']
    assert options(client, c).json()['items'] == []   # the vehicle is on a trip now


def test_a_listed_driver_online_accepts_for_the_owner_vehicle(client, ride):
    c = ride
    driver, tokens = linked_driver(client, c)
    go_live(client, tokens, c)
    request_id = ask(client, c, listed_fare(client, c)).json()['id']
    assert answer(client, c.owner, request_id, 'accept').status_code == 404   # only the person sending the location answers
    accepted = answer(client, tokens, request_id, 'accept')
    assert accepted.status_code == 200, accepted.text
    with client.app.state.sessions() as db:
        trip = db.scalar(select(Trip).where(Trip.booking_id == UUID(accepted.json()['booking_id'])))
        assert trip.assignment_type == 'EXTERNAL_DRIVER' and str(trip.driver_user_id) == driver['id'] and trip.assignment_status == 'ACCEPTED'


def test_the_fare_the_passenger_saw_must_still_be_the_fare(client, ride):
    c = ride
    go_live(client, c.owner, c)
    wrong = ask(client, c, '1.00')
    assert wrong.status_code == 409 and wrong.json()['code'] == 'FARE_CHANGED'
    assert Decimal(wrong.json()['field_errors'][0]['message']) == Decimal(listed_fare(client, c))


def test_one_open_request_per_passenger_and_per_vehicle(client, ride):
    c = ride
    go_live(client, c.owner, c)
    fare = listed_fare(client, c)
    assert ask(client, c, fare).status_code == 201
    again = ask(client, c, fare)
    assert again.status_code == 409 and again.json()['code'] in ('REQUEST_ALREADY_OPEN', 'VEHICLE_NOT_AVAILABLE')
    assert options(client, c).json()['items'] == []   # a vehicle with an open request is not offered to someone else


def test_decline_cancel_and_timeout_free_the_vehicle(client, ride):
    c = ride
    go_live(client, c.owner, c)
    fare = listed_fare(client, c)
    first = ask(client, c, fare).json()['id']
    assert answer(client, c.owner, first, 'decline').json()['status'] == 'DECLINED'
    second = ask(client, c, fare).json()['id']
    assert answer(client, c.passenger, second, 'cancel').json()['status'] == 'CANCELLED'
    third = ask(client, c, fare).json()['id']
    with client.app.state.sessions() as db:
        db.get(RideRequest, UUID(third)).expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    assert client.get(f'/api/v1/ride-now/requests/{third}', headers=bearer(c.passenger)).json()['status'] == 'EXPIRED'
    late = answer(client, c.owner, third, 'accept')
    assert late.status_code == 409
    assert ask(client, c, fare).status_code == 201   # free again after the timeout


def test_going_offline_before_accepting_stops_the_booking(client, ride):
    c = ride
    go_live(client, c.owner, c)
    request_id = ask(client, c, listed_fare(client, c)).json()['id']
    assert client.post(f'/api/v1/vehicles/{c.vehicle_id}/live/offline', headers=bearer(c.owner), json={}).status_code == 200
    blocked = answer(client, c.owner, request_id, 'accept')
    assert blocked.status_code == 409 and blocked.json()['code'] == 'NOT_ONLINE'
    with client.app.state.sessions() as db:
        assert db.scalars(select(Booking).where(Booking.idempotency_key == 'RIDE-' + UUID(request_id).hex)).first() is None


def test_after_accept_the_passenger_follows_the_vehicle_and_both_can_come_back_to_the_trip(client, ride):
    c = ride
    go_live(client, c.owner, c)
    accepted = answer(client, c.owner, ask(client, c, listed_fare(client, c)).json()['id'], 'accept').json()
    trip_id = accepted['trip_id']
    assert trip_id and accepted['booking_id']
    for tokens in (c.passenger, c.owner):   # the dashboard card: the trip is listed before it starts, so a page left by mistake can be opened again
        active = client.get('/api/v1/trips/active', headers=bearer(tokens)).json()['items']
        assert [item['trip_id'] for item in active] == [trip_id] and active[0]['phase'] == 'PICKUP'
    seen = client.get(f'/api/v1/trips/{trip_id}', headers=bearer(c.passenger)).json()
    assert seen['book_now'] is True and seen['status'] == 'READY'
    assert float(seen['location']['latitude']) == pytest.approx(6.93) and float(seen['location']['longitude']) == pytest.approx(79.86)
    mapped = client.get(f'/api/v1/trips/{trip_id}/map', headers=bearer(c.passenger)).json()
    assert mapped['book_now'] is True and mapped['viewer_is_passenger'] is True and mapped['status'] == 'READY'
    assert mapped['position']['latitude'] == seen['location']['latitude'] and [p['kind'] for p in mapped['points']] == ['START', 'END']
    assert client.get(f'/api/v1/trips/{trip_id}/map', headers=bearer(c.owner)).json()['viewer_is_passenger'] is False
    with client.app.state.sessions() as db:
        db.get(Vehicle, c.vehicle_id).current_location_observed_at = datetime.now(timezone.utc) - timedelta(minutes=30)
        db.commit()
    assert client.get(f'/api/v1/trips/{trip_id}', headers=bearer(c.passenger)).json()['location'] is None   # an old position is never shown as live


def ask_trip(client, c, round_trip):
    """A Book now trip that is ready to start: accepted, the Passenger checked and the pickup time reached (set directly in the database)."""
    go_live(client, c.owner, c)
    item = options(client, c, round_trip=round_trip).json()['items'][0]
    asked = client.post('/api/v1/ride-now/requests', headers=bearer(c.passenger),
                        json={**where(c), 'vehicle_id': str(c.vehicle_id), 'fare': item['fare'], 'round_trip': round_trip})
    assert asked.status_code == 201, asked.text
    accepted = answer(client, c.owner, asked.json()['id'], 'accept').json()
    now = datetime.now(timezone.utc)
    with client.app.state.sessions() as db:
        booking = db.get(Booking, UUID(accepted['booking_id']))
        booking.start_at = now - timedelta(minutes=5)
        trip = db.get(Trip, UUID(accepted['trip_id']))
        trip.scheduled_start_at = now - timedelta(minutes=5)
        trip.pickup_code_version, trip.pickup_verified_at = 1, now
        db.commit()
    return item, accepted


def trip_version(client, tokens, trip_id):
    return client.get(f'/api/v1/trips/{trip_id}', headers=bearer(tokens)).json()['version']


def trip_call(client, tokens, trip_id, action, **body):
    return client.post(f'/api/v1/trips/{trip_id}/{action}', headers=bearer(tokens), json={'expected_version': trip_version(client, tokens, trip_id), **body})


def begin(client, c, trip_id):
    started = trip_call(client, c.owner, trip_id, 'start', start_odometer_km='1000.0', checklist_confirmed=True)
    assert started.status_code == 200, started.text


def test_a_return_lists_the_free_waiting_minutes_and_the_waiting_rate_up_front(client, ride):
    c = ride
    go_live(client, c.owner, c)
    oneway = options(client, c).json()['items'][0]
    assert 'waiting' not in oneway
    back = options(client, c, round_trip=True).json()['items'][0]
    free, rate = Decimal(back['waiting']['free_minutes']), Decimal(back['waiting']['hour_rate'])
    assert free >= 0 and rate >= 0 and Decimal(back['fare']) > 0
    asked = client.post('/api/v1/ride-now/requests', headers=bearer(c.passenger),
                        json={**where(c), 'vehicle_id': str(c.vehicle_id), 'fare': back['fare'], 'round_trip': True})
    assert asked.status_code == 201 and asked.json()['round_trip'] is True


def test_the_waiting_is_charged_by_the_minutes_actually_waited_after_the_free_minutes_and_paid_after_the_trip(client, ride):
    c = ride
    item, accepted = ask_trip(client, c, True)
    trip_id = accepted['trip_id']
    free, rate = Decimal(item['waiting']['free_minutes']), Decimal(item['waiting']['hour_rate'])
    assert trip_call(client, c.owner, trip_id, 'wait/start').json()['code'] == 'TRIP_NOT_READY'   # the trip has not started yet
    begin(client, c, trip_id)
    assert client.get(f'/api/v1/trips/{trip_id}', headers=bearer(c.passenger)).json()['wait']['state'] == 'NOT_STARTED'
    assert trip_call(client, c.owner, trip_id, 'wait/end').json()['code'] == 'WAITING_NOT_RUNNING'
    assert trip_call(client, c.passenger, trip_id, 'wait/start').status_code == 404   # only the operator records the waiting
    started = trip_call(client, c.owner, trip_id, 'wait/start')
    assert started.status_code == 200 and started.json()['wait']['state'] == 'WAITING'
    assert trip_call(client, c.owner, trip_id, 'wait/start').json()['code'] == 'WAITING_ALREADY_STARTED'
    assert client.get(f'/api/v1/trips/{trip_id}', headers=bearer(c.passenger)).json()['wait']['state'] == 'WAITING'   # the Passenger sees the timer
    assert trip_call(client, c.owner, trip_id, 'wait/end').json()['wait']['state'] == 'RETURNING'
    waited = free + Decimal('30')   # thirty minutes beyond the free minutes
    with client.app.state.sessions() as db:
        trip = db.get(Trip, UUID(trip_id))
        trip.wait_started_at = trip.wait_ended_at - timedelta(minutes=float(waited))
        db.commit()
    done = trip_call(client, c.owner, trip_id, 'complete', end_odometer_km='1030.0')
    assert done.status_code == 200, done.text
    charge = (Decimal('30') / Decimal('60') * rate).quantize(Decimal('0.01'))
    assert charge > 0
    with client.app.state.sessions() as db:
        booking = db.get(Booking, UUID(accepted['booking_id']))
        assert booking.total_amount == Decimal(item['fare']) + charge and booking.quoted_amount == Decimal(item['fare'])
        assert Decimal(booking.price_snapshot['waiting']['charge']) == charge
    shown = client.get(f"/api/v1/bookings/{accepted['booking_id']}/payment-summary", headers=bearer(c.passenger)).json()
    assert Decimal(shown['amount_due']) == Decimal(item['fare']) + charge   # paid once, after the trip, with the waiting included


def test_waiting_within_the_free_minutes_costs_nothing_and_a_wait_left_running_is_closed_at_completion(client, ride):
    c = ride
    item, accepted = ask_trip(client, c, True)
    trip_id = accepted['trip_id']
    begin(client, c, trip_id)
    assert trip_call(client, c.owner, trip_id, 'wait/start').status_code == 200
    done = trip_call(client, c.owner, trip_id, 'complete', end_odometer_km='1030.0')   # finished without tapping "Return started"
    assert done.status_code == 200, done.text
    with client.app.state.sessions() as db:
        booking = db.get(Booking, UUID(accepted['booking_id']))
        assert db.get(Trip, UUID(trip_id)).wait_ended_at is not None
        assert booking.total_amount == Decimal(item['fare']) and 'waiting' not in booking.price_snapshot


def test_a_one_way_trip_has_no_waiting_to_record(client, ride):
    c = ride
    item, accepted = ask_trip(client, c, False)
    begin(client, c, accepted['trip_id'])
    assert trip_call(client, c.owner, accepted['trip_id'], 'wait/start').json()['code'] == 'NOT_A_RETURN_TRIP'
    assert client.get(f"/api/v1/trips/{accepted['trip_id']}", headers=bearer(c.passenger)).json()['wait'] is None


def charged(minutes, free, rate):
    return (max(Decimal('0'), Decimal(minutes) - free) / Decimal('60') * rate).quantize(Decimal('0.01'))


def finish_with(client, c, accepted, **extra):
    done = trip_call(client, c.owner, accepted['trip_id'], 'complete', end_odometer_km='1030.0', **extra)
    assert done.status_code == 200, done.text
    with client.app.state.sessions() as db:
        return db.get(Booking, UUID(accepted['booking_id'])).total_amount


def test_the_vehicle_driving_away_from_the_waiting_spot_asks_the_driver_and_the_clock_stops_there(client, ride):
    c = ride
    item, accepted = ask_trip(client, c, True)
    trip_id = accepted['trip_id']
    begin(client, c, trip_id)
    here = {'latitude': '6.950000', 'longitude': '79.900000'}
    moved = client.patch(f'/api/v1/trips/{trip_id}/location', headers=bearer(c.owner), json={'expected_version': trip_version(client, c.owner, trip_id), **here})
    assert moved.status_code == 200, moved.text
    assert trip_call(client, c.owner, trip_id, 'wait/start').status_code == 200
    near = {'latitude': '6.950500', 'longitude': '79.900000'}   # about 55 m: still waiting
    client.patch(f'/api/v1/trips/{trip_id}/location', headers=bearer(c.owner), json={'expected_version': trip_version(client, c.owner, trip_id), **near})
    assert client.get(f'/api/v1/trips/{trip_id}', headers=bearer(c.passenger)).json()['wait']['state'] == 'WAITING'
    far = {'latitude': '6.960000', 'longitude': '79.900000'}   # about 1.1 km: the Passenger is back on board
    client.patch(f'/api/v1/trips/{trip_id}/location', headers=bearer(c.owner), json={'expected_version': trip_version(client, c.owner, trip_id), **far})
    wait = client.get(f'/api/v1/trips/{trip_id}', headers=bearer(c.passenger)).json()['wait']
    assert wait['state'] == 'MOVED' and wait['moved_at'] and wait['ended_at'] is None   # asked, not ended: the Driver answers (test_waiting_prompt.py)


def test_at_finish_the_driver_can_only_lower_the_measured_waiting(client, ride):
    c = ride
    item, accepted = ask_trip(client, c, True)
    trip_id = accepted['trip_id']
    free, rate = Decimal(item['waiting']['free_minutes']), Decimal(item['waiting']['hour_rate'])
    begin(client, c, trip_id)
    assert trip_call(client, c.owner, trip_id, 'wait/start').status_code == 200
    assert trip_call(client, c.owner, trip_id, 'wait/end').status_code == 200
    with client.app.state.sessions() as db:
        trip = db.get(Trip, UUID(trip_id))
        trip.wait_started_at = trip.wait_ended_at - timedelta(minutes=float(free + 40))
        db.commit()
    total = finish_with(client, c, accepted, waiting_minutes=str(free + 500))   # more than measured: the measured 40 min count
    assert total == Decimal(item['fare']) + charged(free + 40, free, rate)


def test_with_no_timer_the_driver_adds_the_waited_minutes_up_to_a_limit(client, ride):
    c = ride
    item, accepted = ask_trip(client, c, True)
    trip_id = accepted['trip_id']
    free, rate = Decimal(item['waiting']['free_minutes']), Decimal(item['waiting']['hour_rate'])
    begin(client, c, trip_id)
    total = finish_with(client, c, accepted, waiting_minutes=str(free + 500))
    assert total == Decimal(item['fare']) + charged(180, free, rate)   # at most 180 minutes can be added by hand
    with client.app.state.sessions() as db:
        trip = db.get(Trip, UUID(trip_id))
        assert trip.wait_source == 'MANUAL' and trip.wait_confirmed_minutes == Decimal('180.0')
    assert client.get(f'/api/v1/trips/{trip_id}', headers=bearer(c.passenger)).json()['wait']['source'] == 'MANUAL'   # the Passenger can see it was added by hand


def test_the_passenger_can_cancel_a_ride_before_it_starts_and_the_vehicle_is_free_again(client, ride):
    c = ride
    item, accepted = ask_trip(client, c, False)
    trip_id = accepted['trip_id']
    done = trip_call(client, c.passenger, trip_id, 'cancel-ride')
    assert done.status_code == 200, done.text
    assert done.json()['status'] == 'CANCELLED' and done.json()['trip']['status'] == 'CANCELLED'
    with client.app.state.sessions() as db:
        booking = db.get(Booking, UUID(accepted['booking_id']))
        assert booking.cancelled_by_user_id is not None and booking.vehicle_committed is False
    assert client.get('/api/v1/trips/active', headers=bearer(c.passenger)).json()['items'] == []
    assert trip_call(client, c.passenger, trip_id, 'cancel-ride').json()['code'] in ('CANCELLATION_TOO_LATE', 'VERSION_CONFLICT')
    assert len(options(client, c).json()['items']) == 1   # the vehicle can be booked again


def test_the_vehicle_can_cancel_before_pickup_but_nobody_can_cancel_a_started_ride(client, ride):
    c = ride
    item, accepted = ask_trip(client, c, False)
    trip_id = accepted['trip_id']
    done = trip_call(client, c.owner, trip_id, 'cancel-ride', reason='Flat tyre')
    assert done.status_code == 200 and done.json()['status'] == 'CANCELLED'
    item, accepted = ask_trip(client, c, False)
    begin(client, c, accepted['trip_id'])
    for tokens in (c.passenger, c.owner):
        assert trip_call(client, tokens, accepted['trip_id'], 'cancel-ride').json()['code'] == 'CANCELLATION_TOO_LATE'


def broadcast(client, c, fare, tokens=None):
    return client.post('/api/v1/ride-now/requests/broadcast', headers=bearer(tokens or c.passenger),
                       json={**where(c), 'vehicles': [{'vehicle_id': str(c.vehicle_id), 'fare': fare}]})


def test_one_ask_makes_a_group_and_the_first_accept_closes_it(client, ride):
    c = ride
    go_live(client, c.owner, c)
    fare = listed_fare(client, c)
    made = broadcast(client, c, fare)
    assert made.status_code == 201, made.text
    group = made.json()['group_id']
    assert len(made.json()['items']) == 1 and made.json()['skipped'] == []
    waiting = client.get(f'/api/v1/ride-now/groups/{group}', headers=bearer(c.passenger)).json()
    assert waiting['status'] == 'OPEN' and waiting['asked'] == 1 and waiting['still_waiting'] == 1 and 0 < waiting['seconds_left'] <= 120
    accepted = answer(client, c.owner, made.json()['items'][0]['id'], 'accept')
    assert accepted.status_code == 200, accepted.text
    done = client.get(f'/api/v1/ride-now/groups/{group}', headers=bearer(c.passenger)).json()
    assert done['status'] == 'ACCEPTED' and done['accepted']['trip_id'] == accepted.json()['trip_id']


def test_a_sibling_request_of_the_group_is_cancelled_when_one_is_accepted(client, ride):
    c = ride
    go_live(client, c.owner, c)
    fare = listed_fare(client, c)
    made = broadcast(client, c, fare).json()
    with client.app.state.sessions() as db:   # a second vehicle's request of the same ask (set directly: the test has one vehicle)
        first = db.get(RideRequest, UUID(made['items'][0]['id']))
        other = db.scalars(select(Vehicle).where(Vehicle.id != first.vehicle_id)).first()
        if other is None:
            pytest.skip('needs a second vehicle')
        db.add(RideRequest(passenger_user_id=first.passenger_user_id, vehicle_id=other.id, operator_user_id=first.operator_user_id,
            service_type_id=first.service_type_id, group_id=first.group_id, pickup=first.pickup, destination=first.destination,
            passenger_count=first.passenger_count, round_trip=first.round_trip, fare=first.fare, status='OFFERED', expires_at=first.expires_at))
        db.commit()
    assert answer(client, c.owner, made['items'][0]['id'], 'accept').status_code == 200
    with client.app.state.sessions() as db:
        rows = db.scalars(select(RideRequest).where(RideRequest.group_id == UUID(made['group_id']))).all()
        assert sorted(r.status for r in rows) == ['ACCEPTED', 'CANCELLED']


def test_cancelling_the_group_frees_every_vehicle(client, ride):
    c = ride
    go_live(client, c.owner, c)
    fare = listed_fare(client, c)
    group = broadcast(client, c, fare).json()['group_id']
    cancelled = client.post(f'/api/v1/ride-now/groups/{group}/cancel', headers=bearer(c.passenger), json={})
    assert cancelled.status_code == 200 and cancelled.json()['status'] == 'ENDED' and cancelled.json()['ended_because'] == 'CANCELLED'
    assert len(options(client, c).json()['items']) == 1   # the vehicle can be asked again
