"""A Passenger can see the replacement vehicle, its Owner and the seat layout, and the boarding code names the seats."""
from test_ticket_holds import api, ticket
from test_payments import held, intent, outcome


def test_boarding_code_lists_seats(client, held):
    payment = intent(client, held).json()
    assert outcome(client, held, payment['id']).json()['status'] == 'PAID'
    code = api(client, held['passenger'], 'get', f"/bookings/{held['booking']['id']}/boarding-code").json()
    assert sorted(s['seat_code'] for s in code['seats']) == ['A1', 'A2']


def test_detail_has_no_replacement_by_default(client, held):
    detail = api(client, held['passenger'], 'get', f"/bookings/{held['booking']['id']}").json()
    assert detail['replacement'] is None
