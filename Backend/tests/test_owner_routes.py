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
