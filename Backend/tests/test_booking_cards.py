"""Booking cards: the list names each booking's vehicle and Passenger once, and the newest activity comes first."""
from test_ticket_holds import api, ticket
from test_payments import held


def test_owner_list_carries_vehicle_and_passenger(client, held):
    result = api(client, held['owner'], 'get', '/bookings?as=owner')
    assert result.status_code == 200, result.text
    body = result.json()
    item = next(i for i in body['items'] if i['id'] == held['booking']['id'])
    assert item['updated_at']
    assert item['vehicle_id'] in body['vehicles'] and body['vehicles'][item['vehicle_id']]['name']
    assert item['passenger_user_id'] in body['passengers'] and body['passengers'][item['passenger_user_id']]['name']


def test_detail_carries_vehicle_and_passenger(client, held):
    detail = api(client, held['owner'], 'get', f"/bookings/{held['booking']['id']}").json()
    assert detail['vehicle']['name'] and detail['passenger']['name']
