"""Owner decision 15 Nov 2026: the Passenger does not state service hours; Travelly works them out from the route (one-day trips)."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4
from app.schemas.hire_schemas import Itinerary
from app.services.hire_routing import HireRouting
from conftest import bearer
from test_rates import rate_owner  # noqa: F401
from test_hire_pricing import hire_setup, day_rule  # noqa: F401


def with_day_rule(client, c):
    day = day_rule().model_dump(mode='json'); day['coverage'] = {'kind': 'ROUTE', 'places': [c.places['A'], c.places['B']]}
    cfg = {**c.config, 'expected_version': 1, 'rules': [c.rule, day]}
    assert client.put(f'/api/v1/vehicles/{c.vehicle_id}/services', headers=bearer(c.owner), json=cfg).status_code == 200


def hours_left_out(c):
    itin = c.itinerary(); itin['method'] = 'DAY_HIRE'; del itin['service_hours']
    return itin


def quote(client, c, itin):
    body = {'service_type_id': str(c.service_id), 'itinerary': itin, 'passenger_count': 2, 'large_luggage_count': 0, 'small_luggage_count': 0}
    return client.post(f'/api/v1/search/vehicles/{c.vehicle_id}/quote', json=body)


def test_trip_longer_than_the_package_shows_the_extra_hours_in_the_quote(client, hire_setup, monkeypatch):
    c = hire_setup; with_day_rule(client, c)
    monkeypatch.setattr(client.app.state.hire_routing, 'estimate_hours', lambda itinerary: Decimal('10.5'))
    r = quote(client, c, hours_left_out(c)); assert r.status_code == 200, r.text
    lines = {x['code']: x for x in r.json()['price']['breakdown']}
    assert Decimal(lines['EXTRA_HOURS_1']['quantity']) == Decimal('2.5')
    assert r.json()['price']['reserved_service_hours'] == ['10.5']


def test_shorter_trip_pays_the_package_and_reserves_the_package_hours(client, hire_setup, monkeypatch):
    c = hire_setup; with_day_rule(client, c)
    monkeypatch.setattr(client.app.state.hire_routing, 'estimate_hours', lambda itinerary: Decimal('5'))
    itin = hours_left_out(c)
    r = quote(client, c, itin); assert r.status_code == 200, r.text
    lines = {x['code']: x for x in r.json()['price']['breakdown']}
    assert Decimal(lines['DAY_1']['amount']) == Decimal('1000') and Decimal(lines['EXTRA_HOURS_1']['quantity']) == 0
    assert r.json()['price']['reserved_service_hours'] == ['8']
    assert datetime.fromisoformat(r.json()['reserved_end_at']) - datetime.fromisoformat(itin['start_at']) == timedelta(hours=8)


def test_more_than_a_day_asks_for_a_multi_day_trip(client, hire_setup, monkeypatch):
    c = hire_setup; with_day_rule(client, c)
    monkeypatch.setattr(client.app.state.hire_routing, 'estimate_hours', lambda itinerary: Decimal('25.4'))
    r = quote(client, c, hours_left_out(c))
    assert r.status_code == 422 and r.json()['code'] == 'TRIP_TOO_LONG_FOR_ONE_DAY'


def test_search_route_provider_failure_is_an_error_not_a_successful_empty_result(client, hire_setup, monkeypatch):
    c = hire_setup
    from app.core.errors import ApiError
    def unavailable(_itinerary):
        raise ApiError(503, 'ROUTING_UNAVAILABLE', 'Route service unavailable.')
    monkeypatch.setattr(client.app.state.hire_routing, 'estimate_hours', unavailable)
    body = {'service_type_id': str(c.service_id), 'itinerary': hours_left_out(c), 'passenger_count': 2,
            'large_luggage_count': 0, 'small_luggage_count': 0}
    response = client.post('/api/v1/search/vehicles', json=body)
    assert response.status_code == 503
    assert response.json()['code'] == 'ROUTING_UNAVAILABLE'


def test_booking_without_hours_stores_the_worked_out_hours_and_a_retry_returns_the_same_booking(client, hire_setup, monkeypatch):
    c = hire_setup; with_day_rule(client, c)
    monkeypatch.setattr(client.app.state.hire_routing, 'estimate_hours', lambda itinerary: Decimal('9.25'))
    body = {'vehicle_id': str(c.vehicle_id), 'service_type_id': str(c.service_id), 'itinerary': hours_left_out(c), 'passenger_count': 2,
            'large_luggage_count': 0, 'small_luggage_count': 0, 'idempotency_key': uuid4().hex}
    first = client.post('/api/v1/bookings/private-hires', headers=bearer(c.passenger), json=body); assert first.status_code == 201, first.text
    again = client.post('/api/v1/bookings/private-hires', headers=bearer(c.passenger), json=body); assert again.status_code == 201, again.text
    assert again.json()['id'] == first.json()['id']
    assert first.json()['proposal']['quote']['itinerary']['service_hours'] == ['9.25']


def test_a_caller_cannot_switch_the_automatic_hours_on_with_a_field(client, hire_setup):
    c = hire_setup
    itin = c.itinerary(); itin['auto_hours'] = True
    assert quote(client, c, itin).status_code == 422


def test_route_measurement_without_stated_hours_uses_the_vehicles_own_duration():
    start = datetime.now(timezone.utc) + timedelta(days=2)
    place = {'label': 'X', 'latitude': '7.0', 'longitude': '80.0', 'token': 'x' * 40}
    itin = Itinerary.model_validate({'start_at': start.isoformat(), 'direction': 'ONE_WAY', 'method': 'DAY_HIRE',
        'stops': [{'place': place, 'wait_minutes': '0', 'overnight_rest': False}, {'place': place, 'wait_minutes': '30', 'overnight_rest': False}]})
    assert itin._auto and itin.service_hours == [Decimal('24')]
    segments = [{'distance': 200000, 'steps': [{'distance': 200000, 'duration': 4.5 * 3600}]}]
    usage = HireRouting.from_segments(object(), itin, segments, [[80, 7]])['usage']
    assert usage.service_hours == [Decimal('5')] and usage.distance_km == Decimal('200')


def test_fractional_night_distance_is_bounded_instead_of_rejected_as_a_time_conflict():
    start = datetime(2027, 1, 10, 16, 7, tzinfo=timezone.utc)  # 21:37 in Sri Lanka; route crosses 22:00
    place = {'label': 'X', 'latitude': '7.0', 'longitude': '80.0', 'token': 'x' * 40}
    itin = Itinerary.model_validate({'start_at': start.isoformat(), 'direction': 'ONE_WAY', 'method': 'DISTANCE',
        'service_hours': ['2'], 'stops': [{'place': place, 'wait_minutes': '0', 'overnight_rest': False},
                                         {'place': place, 'wait_minutes': '0', 'overnight_rest': False}]})
    segments = [{'distance': 100000, 'steps': [{'distance': 100000, 'duration': 2 * 3600}]}]
    usage = HireRouting.from_segments(object(), itin, segments, [[80, 7]])['usage']
    assert usage.distance_km == Decimal('100.0000000000')
    assert usage.night_km == Decimal('80.8333333333')


def test_multi_day_without_hours_spreads_the_trip_over_the_booked_days_and_charges_each_package(client, hire_setup, monkeypatch):
    c = hire_setup; with_day_rule(client, c)
    seen = {}
    def estimate(itinerary):
        seen['days'] = len(itinerary.service_hours); return Decimal('6')   # per booked day
    monkeypatch.setattr(client.app.state.hire_routing, 'estimate_hours', estimate)
    itin = hours_left_out(c); itin['trip_days'] = 3
    r = quote(client, c, itin); assert r.status_code == 200, r.text
    price = r.json()['price']
    assert seen['days'] == 3 and price['package_days'] == 3 and price['planned_service_hours'] == ['6', '6', '6']
    assert price['package_hours'] == '8' and price['package_km'] == '100'
    assert datetime.fromisoformat(r.json()['reserved_end_at']) - datetime.fromisoformat(itin['start_at']) == timedelta(hours=24 * 2 + 8)


def test_trip_days_cannot_be_combined_with_stated_hours_to_change_the_price(client, hire_setup, monkeypatch):
    c = hire_setup; with_day_rule(client, c)
    itin = c.itinerary(); itin['method'] = 'DAY_HIRE'; itin['trip_days'] = 5
    r = quote(client, c, itin); assert r.status_code == 200, r.text
    assert r.json()['price']['planned_service_hours'] == ['3']
