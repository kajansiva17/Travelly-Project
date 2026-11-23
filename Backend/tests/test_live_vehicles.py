"""Go online: the vehicle's live location comes from a phone; a Passenger sees who is online nearby."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID
from app.models.hire_models import OwnerDriver
from app.models.review_models import Vehicle
from conftest import bearer
from test_hire_pricing import external_driver, hire_setup  # noqa: F401  (hire_setup is a fixture)
from test_rates import rate_owner  # noqa: F401  (fixture used by hire_setup)

COLOMBO_FORT = (6.93, 79.86)


def online(client, tokens, c):
    return client.post(f'/api/v1/vehicles/{c.vehicle_id}/live/online', headers=bearer(tokens), json={})


def offline(client, tokens, c):
    return client.post(f'/api/v1/vehicles/{c.vehicle_id}/live/offline', headers=bearer(tokens), json={})


def send(client, tokens, c, lat=COLOMBO_FORT[0], lng=COLOMBO_FORT[1], **extra):
    return client.put(f'/api/v1/vehicles/{c.vehicle_id}/live/location', headers=bearer(tokens), json={'latitude': lat, 'longitude': lng, **extra})


def nearby(client, tokens, lat=COLOMBO_FORT[0], lng=COLOMBO_FORT[1], radius=10):
    return client.get(f'/api/v1/hire/nearby-now?latitude={lat}&longitude={lng}&radius_km={radius}', headers=bearer(tokens))


def linked_driver(client, c):
    driver, tokens = external_driver(client, c)
    with client.app.state.sessions() as db:
        owner = db.get(Vehicle, c.vehicle_id).owner_user_id
        db.add(OwnerDriver(owner_user_id=owner, driver_user_id=UUID(driver['id']), status='ACTIVE', initiated_by='OWNER'))
        db.commit()
    return driver, tokens


def vehicle_row(client, c):
    with client.app.state.sessions() as db:
        v = db.get(Vehicle, c.vehicle_id)
        return {'lat': v.current_latitude, 'lng': v.current_longitude, 'source': v.current_location_source, 'seen': v.current_location_observed_at,
                'who': v.live_online_user_id, 'version': v.version}


def test_owner_goes_online_and_the_phone_position_becomes_the_vehicle_position(client, hire_setup):
    c = hire_setup
    before = vehicle_row(client, c)['version']
    assert send(client, c.owner, c).status_code == 409   # not online yet
    went = online(client, c.owner, c)
    assert went.status_code == 200, went.text
    assert went.json()['sending'] is True
    sent = send(client, c.owner, c, lat=7.0, lng=80.0, accuracy_m=12.5)
    assert sent.status_code == 200, sent.text
    row = vehicle_row(client, c)
    assert row['source'] == 'GPS' and row['lat'] == Decimal('7.000000') and row['lng'] == Decimal('80.000000')
    assert datetime.now(timezone.utc) - row['seen'] < timedelta(seconds=30)
    assert row['version'] == before   # live GPS does not touch the vehicle version
    mine = client.get('/api/v1/me/live-vehicles', headers=bearer(c.owner)).json()['items']
    assert mine[0]['online'] is True and mine[0]['sending'] is True and mine[0]['ready'] is True


def test_a_vague_or_invalid_position_is_refused(client, hire_setup):
    c = hire_setup
    assert online(client, c.owner, c).status_code == 200
    assert send(client, c.owner, c, accuracy_m=5000).status_code == 422
    assert send(client, c.owner, c, lat=123).status_code == 422


def test_a_passenger_cannot_go_online_and_a_driver_needs_an_active_owner_link(client, hire_setup):
    c = hire_setup
    assert online(client, c.passenger, c).status_code == 404
    driver, tokens = external_driver(client, c)
    assert online(client, tokens, c).status_code == 404   # approved Driver, but not listed by this Owner
    with client.app.state.sessions() as db:
        owner = db.get(Vehicle, c.vehicle_id).owner_user_id
        db.add(OwnerDriver(owner_user_id=owner, driver_user_id=UUID(driver['id']), status='ACTIVE', initiated_by='OWNER'))
        db.commit()
    assert online(client, tokens, c).status_code == 200


def test_one_person_sends_per_vehicle_and_only_the_owner_can_take_over(client, hire_setup):
    c = hire_setup
    first, first_tokens = linked_driver(client, c)
    second, second_tokens = linked_driver(client, c)
    assert online(client, first_tokens, c).status_code == 200 and send(client, first_tokens, c).status_code == 200
    taken = online(client, second_tokens, c)
    assert taken.status_code == 409 and 'VEHICLE_ALREADY_ONLINE' in taken.text
    listed = client.get('/api/v1/me/live-vehicles', headers=bearer(second_tokens)).json()['items'][0]
    assert listed['taken_by_someone_else'] is True and listed['sending'] is False
    assert online(client, c.owner, c).status_code == 200   # the Owner may take it over
    assert send(client, first_tokens, c).status_code == 409   # and the first Driver is no longer sending


def test_going_offline_stops_the_position_counting_as_live(client, hire_setup):
    c = hire_setup
    assert online(client, c.owner, c).status_code == 200 and send(client, c.owner, c).status_code == 200
    assert len(nearby(client, c.passenger).json()['items']) == 1
    assert offline(client, c.owner, c).status_code == 200
    row = vehicle_row(client, c)
    assert row['who'] is None and datetime.now(timezone.utc) - row['seen'] > timedelta(minutes=15)   # kept as last known, not live
    assert nearby(client, c.passenger).json()['items'] == []
    assert offline(client, c.owner, c).status_code == 200   # idempotent


def test_a_removed_driver_is_cut_off_at_the_next_position(client, hire_setup):
    c = hire_setup
    driver, tokens = linked_driver(client, c)
    assert online(client, tokens, c).status_code == 200 and send(client, tokens, c).status_code == 200
    with client.app.state.sessions() as db:
        db.query(OwnerDriver).filter(OwnerDriver.driver_user_id == UUID(driver['id'])).delete()
        db.commit()
    assert send(client, tokens, c).status_code == 403
    assert vehicle_row(client, c)['who'] is None


def test_nearby_now_lists_online_vehicles_nearest_first_without_coordinates(client, hire_setup):
    c = hire_setup
    assert nearby(client, c.passenger).json()['items'] == []   # nobody is online yet
    assert online(client, c.owner, c).status_code == 200 and send(client, c.owner, c, lat=6.95, lng=79.86).status_code == 200
    found = nearby(client, c.passenger)
    assert found.status_code == 200, found.text
    item = found.json()['items'][0]
    assert item['vehicle_id'] == str(c.vehicle_id) and 0 < item['distance_km'] < 5 and item['minutes_away'] >= 1 and item['instant_booking'] is False
    assert not ({'latitude', 'longitude', 'owner', 'owner_user_id'} & set(item))
    assert nearby(client, c.passenger, lat=9.66, lng=80.01).json()['items'] == []   # Jaffna is far from Colombo
    assert nearby(client, c.passenger, radius=0).status_code == 422
