"""Vehicle records and maintenance summary (PRD matrix 71-73, data dictionary 4.16 and record rules 9.1)."""
from datetime import datetime, timedelta, timezone
from uuid import UUID
import pytest
from app.models.review_models import Vehicle
from test_ticket_holds import api, person, ticket


@pytest.fixture
def fleet(client, ticket):
    with client.app.state.sessions() as db:
        vehicle = db.get(Vehicle, UUID(ticket['trip']['vehicle_id']))
        vehicle.current_odometer_km = None
        vehicle.odometer_updated_at = None
        db.commit()
    return {**ticket, 'vehicle_id': ticket['trip']['vehicle_id']}


def at(days_ago=0, hours=0):
    return (datetime.now(timezone.utc) - timedelta(days=days_ago, hours=hours)).isoformat()


def add(client, t, body, who=None):
    return api(client, who or t['owner'], 'post', f"/vehicles/{t['vehicle_id']}/records", body)


def odometer_of(client, t):
    with client.app.state.sessions() as db:
        return db.get(Vehicle, UUID(t['vehicle_id'])).current_odometer_km


def test_an_oil_change_moves_the_odometer_and_sets_the_next_service(client, fleet):
    saved = add(client, fleet, {'record_type': 'OIL_CHANGE', 'recorded_at': at(1), 'odometer_km': '50000.0', 'amount': '8500.00',
                                'next_due_odometer_km': '55000.0', 'genuine_calendar_due_date': (datetime.now().date() + timedelta(days=180)).isoformat(),
                                'service_provider': 'Lanka Auto Care'})
    assert saved.status_code == 201, saved.text
    body = saved.json()
    assert body['odometer_status'] == 'APPLIED' and body['currency'] == 'LKR' and body['review_status'] is None
    assert str(odometer_of(client, fleet)) == '50000.0'
    listed = api(client, fleet['owner'], 'get', f"/vehicles/{fleet['vehicle_id']}/records").json()
    assert listed['current_odometer_km'] == '50000.0' and listed['totals']['maintenance'] == '8500.00' and listed['can_add']
    assert 'FUEL_PURCHASE' in listed['allowed_record_types'] and 'EV_CHARGING' not in listed['allowed_record_types']


def test_maintenance_summary_estimates_the_due_date_from_recent_driving(client, fleet):
    add(client, fleet, {'record_type': 'ODOMETER_UPDATE', 'recorded_at': at(20), 'odometer_km': '48000.0'})
    add(client, fleet, {'record_type': 'OIL_CHANGE', 'recorded_at': at(10), 'odometer_km': '49000.0', 'next_due_odometer_km': '50500.0'})
    add(client, fleet, {'record_type': 'ODOMETER_UPDATE', 'recorded_at': at(0, 1), 'odometer_km': '50000.0'})
    summary = api(client, fleet['owner'], 'get', f"/vehicles/{fleet['vehicle_id']}/maintenance-summary").json()
    assert summary['current_odometer_km'] == '50000.0' and summary['data_period']['readings'] == 3
    assert summary['average_daily_km'] is not None and 95 < float(summary['average_daily_km']) < 110
    oil = summary['items'][0]
    assert oil['task'] == 'OIL_CHANGE' and oil['status'] == 'UPCOMING' and oil['remaining_km'] == '500.0'
    assert oil['estimated_due_date'] is not None and oil['due_by'] == 'DISTANCE'
    assert any(i['task'] == 'WHEEL_ALIGNMENT' and i['status'] == 'NOT_RECORDED' for i in summary['items'])


def test_overdue_by_distance_or_date(client, fleet):
    add(client, fleet, {'record_type': 'GENERAL_SERVICE', 'recorded_at': at(200), 'odometer_km': '40000.0', 'next_due_odometer_km': '45000.0'})
    add(client, fleet, {'record_type': 'ODOMETER_UPDATE', 'recorded_at': at(0, 1), 'odometer_km': '46000.0'})
    summary = api(client, fleet['owner'], 'get', f"/vehicles/{fleet['vehicle_id']}/maintenance-summary").json()
    service = next(i for i in summary['items'] if i['task'] == 'GENERAL_SERVICE')
    assert service['status'] == 'OVERDUE' and service['remaining_km'] == '-1000.0'
    assert summary['items'][0]['status'] == 'OVERDUE'
    assert summary['estimate_note']  # only one reading in 30 days: no average


def test_a_lower_newer_reading_is_kept_for_review_and_does_not_move_the_odometer(client, fleet):
    add(client, fleet, {'record_type': 'ODOMETER_UPDATE', 'recorded_at': at(2), 'odometer_km': '60000.0'})
    lower = add(client, fleet, {'record_type': 'ODOMETER_UPDATE', 'recorded_at': at(1), 'odometer_km': '6000.0'})
    assert lower.status_code == 201 and lower.json()['odometer_status'] == 'NEEDS_REVIEW' and lower.json()['review_status'] == 'NEEDS_REVIEW'
    assert str(odometer_of(client, fleet)) == '60000.0'
    older = add(client, fleet, {'record_type': 'ODOMETER_UPDATE', 'recorded_at': at(30), 'odometer_km': '55000.0'})
    assert older.json()['odometer_status'] == 'HISTORICAL' and older.json()['review_status'] is None


def test_fuel_needs_product_litres_and_amount_and_matching_fuel(client, fleet):
    missing = add(client, fleet, {'record_type': 'FUEL_PURCHASE', 'recorded_at': at(1), 'amount': '6000.00'})
    assert missing.status_code == 422
    wrong = add(client, fleet, {'record_type': 'FUEL_PURCHASE', 'recorded_at': at(1), 'amount': '6000.00', 'quantity': '15.5',
                                'fuel_grade_product': 'Lanka Super Diesel', 'fuel_type': 'DIESEL'})
    assert wrong.status_code == 422 and wrong.json()['code'] == 'RECORD_NOT_COMPATIBLE'
    body = {'record_type': 'FUEL_PURCHASE', 'recorded_at': at(1), 'amount': '6000.00', 'quantity': '15.5', 'fuel_grade_product': 'Octane 92'}
    first = add(client, fleet, body)
    assert first.status_code == 201 and first.json()['fuel_type'] == 'PETROL' and first.json()['unit'] == 'L'
    again = add(client, fleet, body)
    assert again.status_code == 409 and again.json()['code'] == 'POSSIBLE_DUPLICATE'
    assert add(client, fleet, {**body, 'confirm_duplicate': True}).status_code == 201


def test_power_type_and_field_rules(client, fleet):
    charging = add(client, fleet, {'record_type': 'EV_CHARGING', 'recorded_at': at(1), 'amount': '900.00'})
    assert charging.status_code == 422 and charging.json()['code'] == 'RECORD_NOT_COMPATIBLE'
    stray = add(client, fleet, {'record_type': 'OIL_CHANGE', 'recorded_at': at(1), 'quantity': '4'})
    assert stray.status_code == 422 and stray.json()['code'] == 'FIELD_NOT_APPLICABLE'
    future = add(client, fleet, {'record_type': 'ODOMETER_UPDATE', 'recorded_at': (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(), 'odometer_km': '1.0'})
    assert future.status_code == 422
    backwards = add(client, fleet, {'record_type': 'OIL_CHANGE', 'recorded_at': at(1), 'odometer_km': '5000.0', 'next_due_odometer_km': '4000.0'})
    assert backwards.status_code == 422
    with client.app.state.sessions() as db:
        vehicle = db.get(Vehicle, UUID(fleet['vehicle_id']))
        vehicle.power_type, vehicle.engine_fuel_type = 'BEV', None
        db.commit()
    assert add(client, fleet, {'record_type': 'OIL_CHANGE', 'recorded_at': at(1)}).json()['code'] == 'RECORD_NOT_COMPATIBLE'
    assert add(client, fleet, {'record_type': 'EV_CHARGING', 'recorded_at': at(1), 'amount': '900.00', 'charging_kwh': '30.5'}).status_code == 201
    tasks = [i['task'] for i in api(client, fleet['owner'], 'get', f"/vehicles/{fleet['vehicle_id']}/maintenance-summary").json()['items']]
    assert 'OIL_CHANGE' not in tasks and 'TYRE_CHANGE' in tasks


def test_only_the_owner_adds_and_strangers_see_nothing(client, fleet):
    stranger = person(client, 'OWNER')
    assert add(client, fleet, {'record_type': 'ODOMETER_UPDATE', 'recorded_at': at(1), 'odometer_km': '1.0'}, who=stranger).status_code == 404
    assert api(client, stranger, 'get', f"/vehicles/{fleet['vehicle_id']}/records").status_code == 404
    assert api(client, stranger, 'get', f"/vehicles/{fleet['vehicle_id']}/maintenance-summary").status_code == 404
    block = add(client, fleet, {'record_type': 'AVAILABILITY_BLOCK', 'recorded_at': at(1)})
    assert block.status_code == 422  # blocks use the calendar endpoints


from conftest import bearer
from test_rates import rule, rate_owner
from test_hire_pricing import hire_setup, committed
from test_trip_operations import running


def test_finishing_a_trip_moves_the_vehicle_odometer_forward(client, running):
    c = running.ctx
    done = client.post(f"/api/v1/trips/{running.trip['id']}/complete", headers=bearer(c.owner),
                       json={'expected_version': running.trip['version'], 'end_odometer_km': '1300.5'})
    assert done.status_code == 200, done.text
    with client.app.state.sessions() as db:
        vehicle = db.get(Vehicle, UUID(str(c.vehicle_id)))
        assert str(vehicle.current_odometer_km) == '1300.5' and vehicle.odometer_updated_at is not None
