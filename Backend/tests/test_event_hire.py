from uuid import uuid4
from sqlalchemy import select
from app.models.rate_models import ServiceType
from conftest import bearer
from test_hire_pricing import hire_setup, accept, committed  # noqa: F401  (fixture + helpers)
from test_rates import rate_owner  # noqa: F401


def as_event(client, c, packages=None):
    with client.app.state.sessions() as db:
        service = db.get(ServiceType, c.service_id)
        service.settings = {**service.settings, 'pricing_scope': 'EVENT'}
        db.commit()
    packages = packages or [{'id': str(uuid4()), 'name': 'Wedding car 6 hours', 'hours': '6', 'price': '25000', 'notes': 'Decorated car and Driver'},
                            {'id': str(uuid4()), 'name': 'Wedding car 3 hours', 'hours': '3', 'price': '15000'}]
    saved = client.put(f'/api/v1/vehicles/{c.vehicle_id}/event-packages', headers=bearer(c.owner),
                       json={'service_type_id': str(c.service_id), 'expected_version': 1, 'enabled': True, 'packages': packages})
    assert saved.status_code == 200, saved.text
    return packages


def event_itinerary(c, package):
    it = c.itinerary(('A', 'B'), hours=package['hours'])
    return {**it, 'event_package_id': package['id']}


def test_event_search_lists_each_package_with_the_owner_price(client, hire_setup):
    c = hire_setup; packages = as_event(client, c)
    body = {'service_type_id': str(c.service_id), 'itinerary': c.itinerary(('A', 'B'), hours='3'), 'passenger_count': 2,
            'large_luggage_count': 0, 'small_luggage_count': 0}
    found = client.post('/api/v1/search/vehicles', json=body)
    assert found.status_code == 200, found.text
    data = found.json()
    item = (data['items'] + data['quote_on_request'])[0]   # a vehicle whose position the Owner must confirm is listed under quote_on_request
    assert item['price'] is None
    assert {p['name'] for p in item['packages']} == {'Wedding car 3 hours', 'Wedding car 6 hours'}
    selected = client.post(f"/api/v1/search/vehicles/{item['id']}/quote", json={**body, 'itinerary': event_itinerary(c, packages[1])})
    assert selected.status_code == 200, selected.text
    assert selected.json()['price']['total'] == '15000.00' and selected.json()['price']['method'] == 'EVENT_PACKAGE'
    public = client.get('/api/v1/service-types').json()['items']
    assert any(s['pricing_scope'] == 'EVENT' for s in public)


def test_event_booking_uses_the_package_price_and_cannot_be_changed(client, hire_setup):
    c = hire_setup; packages = as_event(client, c); big = packages[0]
    row = c.confirm_position(c.create(event_itinerary(c, big)))
    assert row['proposal']['quote']['calculation']['total'] == '25000.00'
    accepted = accept(client, c, row)
    assert accepted['total_amount'] == '25000.00'
    done = client.post(f"/api/v1/bookings/{row['id']}/self-drive", headers=bearer(c.owner), json={'expected_version': accepted['version']})
    assert done.status_code == 200, done.text
    row = done.json()
    changed = client.post(f"/api/v1/bookings/{row['id']}/changes", headers=bearer(c.owner),
                          json={'expected_version': row['version'], 'reason': 'ADDED_STOP', 'itinerary': c.itinerary(('A', 'Stop', 'B'), hours='6')})
    assert changed.status_code == 409 and changed.json()['code'] == 'EVENT_FIXED_PACKAGE'


def test_event_package_must_match_hours_and_exist(client, hire_setup):
    c = hire_setup; packages = as_event(client, c)
    wrong_hours = {**c.itinerary(('A', 'B'), hours='4'), 'event_package_id': packages[0]['id']}
    body = {'vehicle_id': str(c.vehicle_id), 'service_type_id': str(c.service_id), 'itinerary': wrong_hours,
            'passenger_count': 2, 'large_luggage_count': 0, 'small_luggage_count': 0, 'idempotency_key': uuid4().hex}
    r = client.post('/api/v1/bookings/private-hires', headers=bearer(c.passenger), json=body)
    assert r.status_code == 422 and r.json()['code'] == 'EVENT_PACKAGE_MISMATCH'
    body['itinerary'] = {**wrong_hours, 'service_hours': ['6'], 'event_package_id': str(uuid4())}
    body['idempotency_key'] = uuid4().hex
    r = client.post('/api/v1/bookings/private-hires', headers=bearer(c.passenger), json=body)
    assert r.status_code == 422 and r.json()['code'] == 'EVENT_PACKAGE_REQUIRED'


def test_event_and_route_rates_do_not_mix(client, hire_setup):
    c = hire_setup; as_event(client, c)
    route = client.put(f'/api/v1/vehicles/{c.vehicle_id}/services', headers=bearer(c.owner), json={**c.config, 'expected_version': 2})
    assert route.status_code == 422 and route.json()['code'] == 'EVENT_PACKAGES_REQUIRED'
    # a package id on a normal service is refused
    with client.app.state.sessions() as db:
        service = db.get(ServiceType, c.service_id); service.settings = {**service.settings, 'pricing_scope': 'LONG_DISTANCE'}; db.commit()
    body = {'service_type_id': str(c.service_id), 'itinerary': {**c.itinerary(), 'event_package_id': str(uuid4())}, 'passenger_count': 2,
            'large_luggage_count': 0, 'small_luggage_count': 0}
    r = client.post('/api/v1/search/vehicles', json=body)
    assert r.status_code == 422 and r.json()['code'] == 'EVENT_PACKAGE_UNAVAILABLE'
