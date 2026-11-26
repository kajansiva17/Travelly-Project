"""Admin oversight pages read the PRD tables (they used to read legacy tables with no migration and answered 503)."""
from test_ticket_holds import api, person, ticket, configure_hold, hold_body
from test_payments import held, intent, outcome


def test_every_admin_oversight_page_answers_from_prd_tables(client, held):
    payment = intent(client, held).json()
    outcome(client, held, payment['id'])
    boss = held['admin']
    books = api(client, boss, 'get', '/admin/workflow/bookings')
    assert books.status_code == 200, books.text
    assert {'items', 'page', 'page_size', 'total'} <= set(books.json())
    assert any(b['booking_reference'] == held['booking']['booking_reference'] and b['status'] == 'CONFIRMED' for b in books.json()['items'])
    pays = api(client, boss, 'get', '/admin/workflow/payments').json()
    assert pays['total'] >= 1 and pays['items'][0]['payment_reference'] == payment['payment_reference'] and pays['items'][0]['status'] == 'PAID'
    report = api(client, boss, 'get', '/admin/workflow/reports').json()
    assert report['payments_collected_lkr'] == '3000.00' and report['bookings_confirmed'] >= 1
    types = api(client, boss, 'get', '/admin/vehicle-types').json()['items']
    assert types and all(t['vehicles'] >= 1 and t['status'] == 'ACTIVE' for t in types)
    manual = api(client, boss, 'get', '/admin/manual-fulfilment-events').json()
    assert manual['items'] == []
    assert api(client, held['owner'], 'get', '/admin/workflow/payments').status_code == 403
