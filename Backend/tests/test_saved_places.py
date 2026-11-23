"""Passenger saved places: named places picked with one tap when booking."""
from conftest import bearer
from test_hire_pricing import external_driver, hire_setup  # noqa: F401  (hire_setup is a fixture)
from test_rates import rate_owner, rule  # noqa: F401  (fixture used by hire_setup)

URL = '/api/v1/me/saved-places'


def place(client, label='Colombo Fort', lat=6.9344, lon=79.8428):
    return client.app.state.rate_locations.signed(label, lat, lon)


def test_a_person_saves_lists_and_removes_their_own_places(client, hire_setup):
    c = hire_setup
    assert client.get(URL, headers=bearer(c.passenger)).json()['items'] == []
    made = client.post(URL, headers=bearer(c.passenger), json={'name': ' Home ', 'place': place(client)})
    assert made.status_code == 201, made.text
    item = made.json()
    assert item['name'] == 'Home' and item['place']['label'] == 'Colombo Fort' and item['place']['token']
    listed = client.get(URL, headers=bearer(c.passenger)).json()['items']
    assert [x['name'] for x in listed] == ['Home']
    client.app.state.rate_locations.verify(__import__('app.schemas.rate_schemas', fromlist=['Place']).Place.model_validate(listed[0]['place']))   # a fresh proof, usable at once
    assert client.get(URL, headers=bearer(c.owner)).json()['items'] == []   # nobody else sees it
    assert client.delete(f"{URL}/{item['id']}", headers=bearer(c.owner)).status_code == 404
    assert client.delete(f"{URL}/{item['id']}", headers=bearer(c.passenger)).status_code == 200
    assert client.get(URL, headers=bearer(c.passenger)).json()['items'] == []


def test_a_name_is_used_once_a_forged_place_is_refused_and_the_list_is_limited(client, hire_setup):
    c = hire_setup
    assert client.post(URL, headers=bearer(c.passenger), json={'name': 'Home', 'place': place(client)}).status_code == 201
    again = client.post(URL, headers=bearer(c.passenger), json={'name': 'home', 'place': place(client, 'Kandy', 7.29, 80.63)})
    assert again.status_code == 409 and again.json()['code'] == 'SAVED_PLACE_EXISTS'
    forged = {**place(client), 'latitude': '7.000000'}
    assert client.post(URL, headers=bearer(c.passenger), json={'name': 'Work', 'place': forged}).json()['code'] == 'INVALID_LOCATION'
    for number in range(9):
        assert client.post(URL, headers=bearer(c.passenger), json={'name': f'Spot {number}', 'place': place(client, f'Place {number}', 6.9 + number / 100, 79.8)}).status_code == 201
    full = client.post(URL, headers=bearer(c.passenger), json={'name': 'One more', 'place': place(client, 'Galle', 6.03, 80.21)})
    assert full.status_code == 409 and full.json()['code'] == 'SAVED_PLACES_FULL'
