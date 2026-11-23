"""Owner > Operations > Vehicle Expenses: one fleet-wide list built from the maintenance records."""
from test_ticket_holds import api, person, ticket  # noqa: F401  (ticket is a fixture)
from test_vehicle_records import add, at, fleet  # noqa: F401  (fleet is a fixture)


def test_the_owner_sees_every_fleet_cost_and_strangers_see_nothing(client, fleet):
    assert add(client, fleet, {'record_type': 'REPAIR', 'recorded_at': at(2), 'odometer_km': '40000.0', 'amount': '12500.00', 'service_provider': 'Lanka Auto Care'}).status_code == 201
    assert add(client, fleet, {'record_type': 'GENERAL_SERVICE', 'recorded_at': at(1), 'odometer_km': '41000.0', 'amount': '9000.00'}).status_code == 201
    listed = api(client, fleet['owner'], 'get', '/owners/me/expenses')
    assert listed.status_code == 200, listed.text
    body = listed.json()
    assert body['currency'] == 'LKR' and [v['id'] for v in body['vehicles']] == [fleet['vehicle_id']]
    assert [(i['type'], i['amount'], i['counts']) for i in body['items']] == [('General Service', '9000.00', True), ('Repair', '12500.00', True)]
    assert body['items'][1]['detail'] == 'Lanka Auto Care'
    stranger = person(client, 'OWNER')
    assert api(client, stranger, 'get', '/owners/me/expenses').json()['items'] == []
    assert api(client, person(client), 'get', '/owners/me/expenses').status_code == 403
