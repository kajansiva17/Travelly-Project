"""Owner routes (project-owner decision 9 Nov 2026): Owners create and edit their own routes, which are active
immediately; Admin can only turn a route off, and an Admin switch-off cannot be undone by the Owner."""
from datetime import timedelta
from uuid import uuid4
from test_ticket_holds import api, iso, person, ticket  # noqa: F401  (ticket is a fixture)

STOPS = [{'stop_name': 'Colombo', 'latitude': '6.927100', 'longitude': '79.861200'},
         {'stop_name': 'Vavuniya', 'latitude': '8.751400', 'longitude': '80.497100', 'scheduled_offset_minutes': 300},
         {'stop_name': 'Jaffna', 'latitude': '9.661500', 'longitude': '80.025500', 'scheduled_offset_minutes': 420}]


def create(client, owner, **extra):
    result = api(client, owner, 'post', '/owners/me/routes', {'stops': STOPS, **extra})
    assert result.status_code == 201, result.text
    return result.json()


def departure(client, owner, route_id, vehicle_id):
    return api(client, owner, 'post', '/scheduled-trips', {
        'route_id': route_id, 'vehicle_id': vehicle_id, 'departure_at': iso(timedelta(days=3)),
        'estimated_arrival_at': iso(timedelta(days=3, hours=7)), 'booking_cutoff_at': iso(timedelta(days=2)),
        'fare_per_seat': '3500.00', 'fulfilment_policy': 'FIXED_GUARANTEED', 'accepted_time_window_minutes': 0,
        'accepted_replacement_terms': {}})


def test_owner_route_is_active_at_once_with_generated_code_and_names(client):
    owner = person(client, 'OWNER')
    route = create(client, owner)
    assert route['status'] == 'ACTIVE' and route['mine'] is True
    assert route['route_code'].startswith('R-') and len(route['route_code']) == 12
    assert (route['route_name'], route['origin_name'], route['destination_name']) == ('Colombo - Jaffna', 'Colombo', 'Jaffna')
    assert [s['stop_name'] for s in route['stops']] == ['Colombo', 'Vavuniya', 'Jaffna']
    named = create(client, owner, route_name='Night express', estimated_distance_km='400', estimated_duration_minutes=420)
    assert named['route_name'] == 'Night express' and named['estimated_duration_minutes'] == 420
    listed = api(client, owner, 'get', '/owners/me/routes').json()['items']
    assert {r['id'] for r in listed if r['mine']} == {route['id'], named['id']}


def test_owner_route_needs_owner_role_and_valid_stops(client):
    passenger = person(client)
    assert api(client, passenger, 'post', '/owners/me/routes', {'stops': STOPS}).status_code == 403
    owner = person(client, 'OWNER')
    assert api(client, owner, 'post', '/owners/me/routes', {'stops': STOPS[:1]}).status_code == 422
    backwards = [STOPS[0], {**STOPS[1], 'scheduled_offset_minutes': 300}, {**STOPS[2], 'scheduled_offset_minutes': 10}]
    assert api(client, owner, 'post', '/owners/me/routes', {'stops': backwards}).status_code == 422
    assert api(client, owner, 'post', '/owners/me/routes', {'stops': STOPS, 'route_code': 'X'}).status_code == 422


def test_owner_sees_own_and_admin_routes_but_not_other_owners(client, ticket):
    mine = create(client, ticket['owner'])
    other_owner = person(client, 'OWNER')
    theirs = create(client, other_owner)
    ids = {r['id']: r for r in api(client, ticket['owner'], 'get', '/owners/me/routes').json()['items']}
    assert mine['id'] in ids and ticket['route']['id'] in ids and theirs['id'] not in ids
    assert ids[ticket['route']['id']]['mine'] is False
    # Another Owner's route cannot be used for a departure or edited.
    vehicle_id = ticket['trip']['vehicle_id']
    blocked = departure(client, ticket['owner'], theirs['id'], vehicle_id)
    assert blocked.status_code == 422 and blocked.json()['code'] == 'ROUTE_NOT_AVAILABLE'
    assert api(client, ticket['owner'], 'put', f"/owners/me/routes/{theirs['id']}",
               {'expected_version': theirs['version'], 'stops': STOPS}).status_code == 404
    assert departure(client, ticket['owner'], mine['id'], vehicle_id).status_code == 201


def test_owner_edits_route_and_stops_keep_ids(client):
    owner = person(client, 'OWNER')
    route = create(client, owner)
    stops = [{k: v for k, v in s.items() if k not in ('stop_order', 'stop_code')} for s in route['stops']]
    stops.insert(1, {'stop_name': 'Anuradhapura', 'latitude': '8.311400', 'longitude': '80.403700', 'scheduled_offset_minutes': 240})
    edited = api(client, owner, 'put', f"/owners/me/routes/{route['id']}", {'expected_version': route['version'], 'stops': stops})
    assert edited.status_code == 200, edited.text
    edited = edited.json()
    assert [s['stop_name'] for s in edited['stops']] == ['Colombo', 'Anuradhapura', 'Vavuniya', 'Jaffna']
    assert edited['stops'][0]['id'] == route['stops'][0]['id'] and edited['version'] == route['version'] + 1
    stale = api(client, owner, 'put', f"/owners/me/routes/{route['id']}", {'expected_version': route['version'], 'stops': stops})
    assert stale.status_code == 409 and stale.json()['code'] == 'VERSION_CONFLICT'


def test_stops_frozen_while_a_published_departure_uses_the_route(client, ticket):
    route = create(client, ticket['owner'])
    trip = departure(client, ticket['owner'], route['id'], ticket['trip']['vehicle_id'])
    assert trip.status_code == 201, trip.text
    trip = trip.json()
    published = api(client, ticket['owner'], 'post', f"/scheduled-trips/{trip['id']}/publish",
                    {'expected_version': trip['version'], 'publish_confirmed': True})
    assert published.status_code == 200, published.text
    same = [{k: v for k, v in s.items() if k not in ('stop_order', 'stop_code')} for s in route['stops']]
    renamed = api(client, ticket['owner'], 'put', f"/owners/me/routes/{route['id']}",
                  {'expected_version': route['version'], 'route_name': 'Renamed', 'stops': same})
    assert renamed.status_code == 200 and renamed.json()['route_name'] == 'Renamed'
    moved = [*same[:2], {**same[2], 'stop_name': 'Point Pedro'}]
    blocked = api(client, ticket['owner'], 'put', f"/owners/me/routes/{route['id']}",
                  {'expected_version': renamed.json()['version'], 'stops': moved})
    assert blocked.status_code == 409 and blocked.json()['code'] == 'ROUTE_IN_USE'


def test_owner_switch_off_and_admin_switch_off(client, ticket):
    owner, admin = ticket['owner'], ticket['admin']
    route = create(client, owner)
    off = api(client, owner, 'patch', f"/owners/me/routes/{route['id']}/status", {'expected_version': route['version'], 'active': False})
    assert off.status_code == 200 and off.json()['status'] == 'INACTIVE'
    blocked = departure(client, owner, route['id'], ticket['trip']['vehicle_id'])
    assert blocked.status_code == 422 and blocked.json()['code'] == 'ROUTE_NOT_AVAILABLE'
    on = api(client, owner, 'patch', f"/owners/me/routes/{route['id']}/status", {'expected_version': off.json()['version'], 'active': True})
    assert on.status_code == 200 and on.json()['status'] == 'ACTIVE'
    listed = {r['id']: r for r in api(client, admin, 'get', '/admin/routes').json()['items']}
    assert listed[route['id']]['owner_user_id'] == owner['id']
    # Admin may only switch an Owner route off/on, not edit it.
    assert api(client, admin, 'patch', f"/admin/routes/{route['id']}",
               {'expected_version': on.json()['version'], 'route_name': 'Admin edit'}).json()['code'] == 'OWNER_ROUTE'
    admin_off = api(client, admin, 'patch', f"/admin/routes/{route['id']}", {'expected_version': on.json()['version'], 'status': 'INACTIVE'})
    assert admin_off.status_code == 200 and admin_off.json()['deactivated_by_admin'] is True
    again = api(client, owner, 'patch', f"/owners/me/routes/{route['id']}/status",
                {'expected_version': admin_off.json()['version'], 'active': True})
    assert again.status_code == 409 and again.json()['code'] == 'ROUTE_DEACTIVATED_BY_ADMIN'
    admin_on = api(client, admin, 'patch', f"/admin/routes/{route['id']}", {'expected_version': admin_off.json()['version'], 'status': 'ACTIVE'})
    assert admin_on.status_code == 200 and admin_on.json()['deactivated_by_admin'] is False


# ---------------------------------------------------------------- stop-wise fares (decision 9 Nov 2026)
from test_ticket_holds import configure_hold  # noqa: E402

PRICED = [{**STOPS[0], 'price_from_start': '0'},
          {'stop_name': 'Anuradhapura', 'latitude': '8.311400', 'longitude': '80.403700', 'scheduled_offset_minutes': 240,
           'price_from_start': '2000'},
          {**STOPS[1], 'price_from_start': '2500'}, {**STOPS[2], 'price_from_start': '3500'}]


def test_stop_prices_are_validated(client):
    owner = person(client, 'OWNER')
    post = lambda stops, enabled=True: api(client, owner, 'post', '/owners/me/routes', {'stops': stops, 'stop_prices_enabled': enabled})
    assert post(PRICED, enabled=False).status_code == 422            # prices without the tick
    assert post([*PRICED[:3], {**PRICED[3], 'price_from_start': None}]).status_code == 422   # a stop without a price
    assert post([{**PRICED[0], 'price_from_start': '100'}, *PRICED[1:]]).status_code == 422  # start must be 0
    assert post([PRICED[0], PRICED[3]]).status_code == 201                # two stops, rising price
    down = [PRICED[0], PRICED[1], {**PRICED[2], 'price_from_start': '1500'}, PRICED[3]]
    assert post(down).status_code == 422                               # prices must not go down
    route = post(PRICED).json()
    assert route['stop_prices_enabled'] is True
    assert [s['price_from_start'] for s in route['stops']] == ['0.00', '2000.00', '2500.00', '3500.00']
    flat = create(client, owner)
    assert flat['stop_prices_enabled'] is False and 'price_from_start' not in flat['stops'][0]


def test_passenger_pays_the_part_of_the_route_they_travel(client, ticket):
    configure_hold(client, ticket)
    owner = ticket['owner']
    route = api(client, owner, 'post', '/owners/me/routes', {'stops': PRICED, 'stop_prices_enabled': True}).json()
    vehicle_id = ticket['trip']['vehicle_id']
    wrong = api(client, owner, 'post', '/scheduled-trips', {**departure_body(route['id'], vehicle_id), 'fare_per_seat': '3000.00'})
    assert wrong.status_code == 422 and wrong.json()['code'] == 'FARE_FROM_ROUTE_PRICES'
    trip = api(client, owner, 'post', '/scheduled-trips', departure_body(route['id'], vehicle_id)).json()
    trip = api(client, owner, 'post', f"/scheduled-trips/{trip['id']}/publish",
               {'expected_version': trip['version'], 'publish_confirmed': True}).json()
    detail = client.get(f"/api/v1/scheduled-trips/{trip['id']}").json()
    assert detail['stop_prices_enabled'] is True
    stops = {s['stop_name']: s for s in detail['stops']}
    assert stops['Vavuniya']['price_from_start'] == '2500.00'
    seats = [s['seat_id'] for s in client.get(f"/api/v1/scheduled-trips/{trip['id']}/seats").json()['seats'] if s.get('seat_id')]
    passenger = person(client)

    def hold(seat_ids, **chosen):
        return api(client, passenger, 'post', '/bookings/ticket-holds', {
            'scheduled_trip_id': trip['id'], 'idempotency_key': uuid4().hex,
            'travellers': [{'seat_id': s, 'full_name': 'Kajan'} for s in seat_ids], **chosen})
    part = hold(seats[:2], boarding_stop_id=stops['Vavuniya']['id'])           # Vavuniya -> Jaffna, two seats
    assert part.status_code == 201, part.text
    assert part.json()['total_amount'] == '2000.00'
    assert {t['fare'] for t in part.json()['travellers']} == {'1000.00'}
    whole = hold(seats[2:3])                                                     # start -> end
    assert whole.status_code == 201 and whole.json()['total_amount'] == '3500.00'


def test_equal_stop_prices_give_no_fare_and_prices_freeze_when_published(client, ticket):
    configure_hold(client, ticket)
    owner = ticket['owner']
    same = [PRICED[0], PRICED[1], {**PRICED[2], 'price_from_start': '2000'}, PRICED[3]]
    route = api(client, owner, 'post', '/owners/me/routes', {'stops': same, 'stop_prices_enabled': True}).json()
    trip = api(client, owner, 'post', '/scheduled-trips', departure_body(route['id'], ticket['trip']['vehicle_id'])).json()
    trip = api(client, owner, 'post', f"/scheduled-trips/{trip['id']}/publish",
               {'expected_version': trip['version'], 'publish_confirmed': True}).json()
    stops = {s['stop_name']: s['id'] for s in client.get(f"/api/v1/scheduled-trips/{trip['id']}").json()['stops']}
    seat = client.get(f"/api/v1/scheduled-trips/{trip['id']}/seats").json()['seats'][0]['seat_id']
    free = api(client, person(client), 'post', '/bookings/ticket-holds', {
        'scheduled_trip_id': trip['id'], 'idempotency_key': uuid4().hex, 'travellers': [{'seat_id': seat, 'full_name': 'A'}],
        'boarding_stop_id': stops['Anuradhapura'], 'dropoff_stop_id': stops['Vavuniya']})
    assert free.status_code == 422 and free.json()['code'] == 'NO_FARE_FOR_STOPS'
    current = [{k: v for k, v in s.items() if k not in ('stop_order', 'stop_code')} for s in route['stops']]
    raised = [*current[:3], {**current[3], 'price_from_start': '4000'}]
    blocked = api(client, owner, 'put', f"/owners/me/routes/{route['id']}",
                  {'expected_version': route['version'], 'stop_prices_enabled': True, 'stops': raised})
    assert blocked.status_code == 409 and blocked.json()['code'] == 'ROUTE_IN_USE'


def departure_body(route_id, vehicle_id):
    return {'route_id': route_id, 'vehicle_id': vehicle_id, 'departure_at': iso(timedelta(days=3)),
            'estimated_arrival_at': iso(timedelta(days=3, hours=7)), 'booking_cutoff_at': iso(timedelta(days=2)),
            'fare_per_seat': '3500.00', 'fulfilment_policy': 'FIXED_GUARANTEED', 'accepted_time_window_minutes': 0,
            'accepted_replacement_terms': {}}
