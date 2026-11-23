"""Owner > Seat inventory: how full every ticket departure is."""
from test_ticket_holds import api, configure_hold, hold_body, person, ticket  # noqa: F401  (ticket is a fixture)


def test_the_owner_sees_available_held_and_booked_seats_per_departure(client, ticket):
    first = api(client, ticket['owner'], 'get', '/owners/me/seat-inventory')
    assert first.status_code == 200, first.text
    row = first.json()['items'][0]
    assert row['id'] == ticket['trip']['id'] and row['seats'] == {'total': 3, 'available': 3, 'held': 0, 'booked': 0, 'other': 0}
    assert row['booked_amount'] == '0.00' and row['currency'] == 'LKR' and ' → ' in row['route'] and row['vehicle']
    configure_hold(client, ticket, 7)
    assert api(client, person(client), 'post', '/bookings/ticket-holds', hold_body(ticket, ['A1', 'A2'])).status_code == 201
    row = api(client, ticket['owner'], 'get', '/owners/me/seat-inventory').json()['items'][0]
    assert row['seats'] == {'total': 3, 'available': 1, 'held': 2, 'booked': 0, 'other': 0}


def test_other_people_see_nothing_and_a_passenger_is_refused(client, ticket):
    assert api(client, person(client, 'OWNER'), 'get', '/owners/me/seat-inventory').json()['items'] == []
    assert api(client, person(client), 'get', '/owners/me/seat-inventory').status_code == 403
