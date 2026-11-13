"""Monthly Owner report (owner decision 13 Nov 2026)."""
from datetime import datetime
from zoneinfo import ZoneInfo
from conftest import bearer
from test_rates import rule, rate_owner
from test_hire_pricing import hire_setup, committed
from test_trip_operations import running
from test_ticket_holds import person, api

THIS_MONTH = datetime.now(ZoneInfo('Asia/Colombo')).strftime('%Y-%m')


def test_owner_gets_the_month_as_json_and_pdf(client, running):
    c = running.ctx
    done = client.post(f"/api/v1/trips/{running.trip['id']}/complete", headers=bearer(c.owner),
                       json={'expected_version': running.trip['version'], 'end_odometer_km': '1300.5'})
    assert done.status_code == 200, done.text
    report = client.get(f'/api/v1/owners/me/reports/monthly/{THIS_MONTH}', headers=bearer(c.owner))
    assert report.status_code == 200, report.text
    data = report.json()
    assert data['period'] == THIS_MONTH and data['summary']['completed_trips'] == 1
    trip = data['trips']['items'][0]
    assert trip['kind'] == 'Private hire' and trip['start_km'] and trip['end_km'] == '1300.5' and trip['distance_km']
    assert data['summary']['total_km'] == trip['distance_km'] and data['trips']['per_vehicle'][0]['trips'] == 1
    assert {'items', 'payouts', 'open_balance_today'} <= data['earnings'].keys()
    assert {'items', 'coming_up_today'} <= data['maintenance'].keys() and 'items' in data['documents']
    result = data['result']
    assert {'income', 'expenses_total', 'profit', 'is_loss', 'note'} <= result.keys()
    from decimal import Decimal
    assert Decimal(result['profit']) == Decimal(result['income']) - Decimal(result['expenses_total'])
    assert data['summary']['profit'] == result['profit']
    pdf = client.get(f'/api/v1/owners/me/reports/monthly/{THIS_MONTH}/pdf', headers=bearer(c.owner))
    assert pdf.status_code == 200 and pdf.headers['content-type'] == 'application/pdf'
    assert pdf.content[:5] == b'%PDF-' and len(pdf.content) > 2000
    assert f'travelly-report-{THIS_MONTH}.pdf' in pdf.headers['content-disposition']


def test_only_the_owner_sees_their_own_month(client, running):
    other_owner = person(client, 'OWNER')
    empty = api(client, other_owner, 'get', f'/owners/me/reports/monthly/{THIS_MONTH}').json()
    assert empty['summary']['completed_trips'] == 0 and empty['trips']['items'] == [] and empty['summary']['vehicles'] == 0
    assert client.get(f'/api/v1/owners/me/reports/monthly/{THIS_MONTH}', headers=bearer(running.ctx.passenger)).status_code == 403
    assert api(client, other_owner, 'get', '/owners/me/reports/monthly/2999-01').status_code == 422
    assert api(client, other_owner, 'get', '/owners/me/reports/monthly/nov-2026').status_code == 422
    assert api(client, other_owner, 'get', f'/owners/me/reports/monthly/{THIS_MONTH}/pdf').content[:5] == b'%PDF-'   # an empty month still prints


from test_ticket_holds import ticket  # noqa: E402
from test_vehicle_records import fleet, add  # noqa: E402


def test_expenses_make_a_loss_when_nothing_was_earned(client, fleet):
    now = datetime.now(ZoneInfo('UTC')).isoformat()
    assert add(client, fleet, {'record_type': 'OIL_CHANGE', 'recorded_at': now, 'odometer_km': '50000.0', 'amount': '8500.00',
                               'service_provider': 'Auto Miraj'}).status_code == 201
    assert add(client, fleet, {'record_type': 'REPAIR', 'recorded_at': now, 'odometer_km': '50010.0', 'amount': '5000.00'}).status_code == 201
    data = api(client, fleet['owner'], 'get', f'/owners/me/reports/monthly/{THIS_MONTH}').json()
    result = data['result']
    assert result['expenses_service_and_repair'] == '13500.00' and result['expenses_total'] == '13500.00'
    assert result['income'] == '0.00' and result['profit'] == '-13500.00' and result['is_loss'] is True
    assert len(data['maintenance']['items']) == 2
    assert api(client, fleet['owner'], 'get', f'/owners/me/reports/monthly/{THIS_MONTH}/pdf').content[:5] == b'%PDF-'


def test_admin_gets_the_whole_platform_month(client, running):
    c = running.ctx
    done = client.post(f"/api/v1/trips/{running.trip['id']}/complete", headers=bearer(c.owner),
                       json={'expected_version': running.trip['version'], 'end_odometer_km': '1300.5'})
    assert done.status_code == 200, done.text
    boss = person(client, 'ADMIN')
    data = api(client, boss, 'get', f'/admin/reports/monthly/{THIS_MONTH}').json()
    assert data['summary']['completed_trips'] >= 1 and data['summary']['private_hire_bookings'] >= 1
    assert data['summary']['new_users'] >= 2 and {x['role'] for x in data['people']['roles']} == {'Owner', 'Driver'}
    assert {'departures', 'refunds', 'documents', 'applications'} <= data['attention'].keys()
    assert {'income', 'commission_online', 'commission_cash', 'cash_commission_still_due', 'note'} <= data['result'].keys()
    assert [x['service'] for x in data['money']['per_service']][:2] == ['Private hire', 'Tickets']
    pdf = api(client, boss, 'get', f'/admin/reports/monthly/{THIS_MONTH}/pdf')
    assert pdf.status_code == 200 and pdf.content[:5] == b'%PDF-' and 'travelly-admin-report' in pdf.headers['content-disposition']
    assert client.get(f'/api/v1/admin/reports/monthly/{THIS_MONTH}', headers=bearer(c.owner)).status_code == 403
