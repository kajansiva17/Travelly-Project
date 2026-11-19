"""Airport hire needs an airport at one end; Long distance needs the Admin's minimum distance (owner decisions 15 Nov 2026)."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4
from sqlalchemy import func
from app.models import UserRole
from app.models.rate_models import ServiceType
from app.services.airports import DEFAULT_AIRPORTS, airports_of, km_between, min_distance_km, near_airport
from conftest import bearer
from test_rates import rate_owner  # noqa: F401
from test_hire_pricing import hire_setup, signed_in  # noqa: F401


def admin_tokens(client):
    person, tokens = signed_in(client, {'full_name': 'Rule Admin', 'email': uuid4().hex + '@example.com', 'phone_e164': '+9477' + str(uuid4().int % 10000000).zfill(7),
                                        'password': 'TravellyStrong1!', 'accept_terms': True})
    with client.app.state.sessions() as db:
        db.add(UserRole(user_id=UUID(person['id']), role_code='ADMIN', approval_status='APPROVED', approved_at=func.now())); db.commit()
    return tokens


def search_body(c, names, service_id=None):
    start = datetime.now(timezone.utc) + timedelta(days=2)
    return {'service_type_id': str(service_id or c.service_id), 'passenger_count': 2, 'large_luggage_count': 0, 'small_luggage_count': 0,
            'itinerary': {'start_at': start.isoformat(), 'direction': 'ONE_WAY', 'method': 'DISTANCE', 'service_hours': ['3'],
                          'stops': [{'place': c.places[n], 'wait_minutes': '0', 'overnight_rest': False} for n in names]}}


def test_the_default_list_has_the_main_airports_and_a_place_next_to_one_counts():
    codes = {a['code'] for a in DEFAULT_AIRPORTS}
    assert {'CMB', 'RML', 'HRI', 'JAF'} <= codes
    cmb = next(a for a in DEFAULT_AIRPORTS if a['code'] == 'CMB')
    assert (cmb['latitude'], cmb['longitude']) == ('7.173397', '79.887110')  # provider-verified terminal road access
    place = type('P', (), {'latitude': Decimal('7.19'), 'longitude': Decimal('79.887')})  # about 2 km from the terminal
    far = type('P', (), {'latitude': Decimal('6.93'), 'longitude': Decimal('79.86')})     # Colombo Fort
    assert near_airport(DEFAULT_AIRPORTS, place) and not near_airport(DEFAULT_AIRPORTS, far)
    assert abs(km_between(7.1808, 79.8841, 7.1808, 79.8841)) < 0.001
    assert airports_of(type('S', (), {'settings': {}})) == DEFAULT_AIRPORTS and min_distance_km(type('S', (), {'settings': {}})) == 100


def test_public_list_of_airports_signs_each_place(client, hire_setup):
    c = hire_setup
    with client.app.state.sessions() as db:
        service = db.get(ServiceType, c.service_id); service.settings = {**service.settings, 'pricing_scope': 'AIRPORT'}; db.commit()
    items = client.get('/api/v1/airports').json()['items']
    assert {i['code'] for i in items} >= {'CMB', 'JAF'}
    first = items[0]
    client.app.state.rate_locations.verify(type('P', (), {'token': first['place']['token'], 'label': first['place']['label'],
                                                         'latitude': Decimal(first['place']['latitude']), 'longitude': Decimal(first['place']['longitude'])}))


def test_airport_hire_needs_an_airport_at_one_end(client, hire_setup, monkeypatch):
    c = hire_setup
    from app.core.errors import ApiError
    def unavailable(itinerary, profile): raise ApiError(503, 'ROUTING_NOT_CONFIGURED', 'Trusted routing is not configured.')
    monkeypatch.setattr(client.app.state.hire_routing, 'measure', unavailable)   # only the airport rule is under test, not the price
    with client.app.state.sessions() as db:
        service = db.get(ServiceType, c.service_id); service.settings = {**service.settings, 'pricing_scope': 'AIRPORT'}; db.commit()
    airport = client.get('/api/v1/airports').json()['items'][0]['place']
    c.places['Airport'] = airport
    refused = client.post('/api/v1/search/vehicles', json=search_body(c, ('A', 'B')))
    assert refused.status_code == 422 and refused.json()['code'] == 'AIRPORT_LOCATION_REQUIRED'
    assert refused.json()['field_errors'][0]['field'] == 'itinerary.stops'
    for names in (('Airport', 'A'), ('A', 'Airport')):   # the airport as pickup or as destination
        answer = client.post('/api/v1/search/vehicles', json=search_body(c, names))
        assert answer.json().get('code') != 'AIRPORT_LOCATION_REQUIRED', answer.text


def test_admin_edits_the_airport_list_and_a_switched_off_airport_is_not_offered(client, hire_setup):
    c = hire_setup; tokens = admin_tokens(client)
    with client.app.state.sessions() as db:
        service = db.get(ServiceType, c.service_id); service.settings = {**service.settings, 'pricing_scope': 'AIRPORT'}; db.commit(); version = service.version
    listing = next(i for i in client.get('/api/v1/admin/service-types', headers=bearer(tokens)).json()['items'] if i['id'] == str(c.service_id))
    assert listing['supports_airports'] is True and len(listing['airports']) == len(DEFAULT_AIRPORTS)
    path = f'/api/v1/admin/service-types/{c.service_id}/airports'
    changed = [{**a, 'is_active': a['code'] != 'JAF'} for a in listing['airports']] + [{'code': 'XYZ', 'name': 'Test Strip', 'latitude': '8.100000', 'longitude': '80.500000', 'is_active': True}]
    saved = client.put(path, headers=bearer(tokens), json={'expected_version': listing['version'], 'airports': changed})
    assert saved.status_code == 200, saved.text
    codes = {i['code'] for i in client.get('/api/v1/airports').json()['items']}
    assert 'JAF' not in codes and 'XYZ' in codes and 'CMB' in codes
    assert client.put(path, headers=bearer(tokens), json={'expected_version': listing['version'], 'airports': changed}).status_code == 409   # stale version
    dup = client.put(path, headers=bearer(tokens), json={'expected_version': saved.json()['version'], 'airports': changed[:1] + changed[:1]})
    assert dup.status_code == 422
    out = client.put(path, headers=bearer(tokens), json={'expected_version': saved.json()['version'], 'airports': [{**changed[0], 'latitude': '40.000000'}]})
    assert out.status_code == 422
    assert client.put(path, headers=bearer(c.passenger), json={'expected_version': 1, 'airports': changed}).status_code in (401, 403, 404)
    # a service that is not Airport hire refuses the list
    with client.app.state.sessions() as db:
        service = db.get(ServiceType, c.service_id); service.settings = {**service.settings, 'pricing_scope': 'LOCAL'}; db.commit(); version = service.version
    refused = client.put(path, headers=bearer(tokens), json={'expected_version': version, 'airports': changed})
    assert refused.status_code == 422 and refused.json()['code'] == 'AIRPORTS_NOT_ALLOWED'


def test_long_distance_needs_the_minimum_road_distance_and_admin_can_change_it(client, hire_setup, monkeypatch):
    c = hire_setup; tokens = admin_tokens(client)
    km = {'value': Decimal('8.4')}
    monkeypatch.setattr(client.app.state.hire_routing, 'road_km', lambda stops: km['value'])
    refused = client.post('/api/v1/search/vehicles', json=search_body(c, ('A', 'B')))
    assert refused.status_code == 422 and refused.json()['code'] == 'TRIP_TOO_SHORT_FOR_LONG_DISTANCE'
    fields = {f['field']: f['message'] for f in refused.json()['field_errors']}
    assert fields == {'distance_km': '8', 'min_distance_km': '100'}
    assert '8 km' in refused.json()['message'] and '100 km' in refused.json()['message']
    public = next(i for i in client.get('/api/v1/service-types').json()['items'] if i['id'] == str(c.service_id))
    assert public['min_distance_km'] == 100
    km['value'] = Decimal('100')   # exactly the minimum is allowed
    assert client.post('/api/v1/search/vehicles', json=search_body(c, ('A', 'B'))).json().get('code') != 'TRIP_TOO_SHORT_FOR_LONG_DISTANCE'
    row = next(i for i in client.get('/api/v1/admin/service-types', headers=bearer(tokens)).json()['items'] if i['id'] == str(c.service_id))
    assert row['supports_min_distance'] is True and row['min_distance_km'] == 100
    path = f'/api/v1/admin/service-types/{c.service_id}/distance-rule'
    saved = client.patch(path, headers=bearer(tokens), json={'expected_version': row['version'], 'min_distance_km': 60})
    assert saved.status_code == 200 and saved.json()['min_distance_km'] == 60
    km['value'] = Decimal('80')
    assert client.post('/api/v1/search/vehicles', json=search_body(c, ('A', 'B'))).json().get('code') != 'TRIP_TOO_SHORT_FOR_LONG_DISTANCE'
    assert client.patch(path, headers=bearer(tokens), json={'expected_version': row['version'], 'min_distance_km': 10}).status_code == 409
    assert client.patch(path, headers=bearer(tokens), json={'expected_version': saved.json()['version'], 'min_distance_km': -1}).status_code == 422
    off = client.patch(path, headers=bearer(tokens), json={'expected_version': saved.json()['version'], 'min_distance_km': 0})
    km['value'] = Decimal('2')
    assert off.status_code == 200 and client.post('/api/v1/search/vehicles', json=search_body(c, ('A', 'B'))).json().get('code') != 'TRIP_TOO_SHORT_FOR_LONG_DISTANCE'


def test_an_unmeasurable_distance_does_not_block_and_other_services_have_no_minimum(client, hire_setup, monkeypatch):
    c = hire_setup
    monkeypatch.setattr(client.app.state.hire_routing, 'road_km', lambda stops: None)   # routing down: the price step reports the real problem
    assert client.post('/api/v1/search/vehicles', json=search_body(c, ('A', 'B'))).json().get('code') != 'TRIP_TOO_SHORT_FOR_LONG_DISTANCE'
    monkeypatch.setattr(client.app.state.hire_routing, 'road_km', lambda stops: Decimal('3'))
    with client.app.state.sessions() as db:
        service = db.get(ServiceType, c.service_id); service.settings = {**service.settings, 'pricing_scope': 'LOCAL'}; db.commit()
    assert client.post('/api/v1/search/vehicles', json=search_body(c, ('A', 'B'))).json().get('code') != 'TRIP_TOO_SHORT_FOR_LONG_DISTANCE'
