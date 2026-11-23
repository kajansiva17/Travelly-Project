"""Owner pays Driver for a completed trip: online is final at once, cash needs the Driver's confirmation, both sides see it."""
from uuid import UUID
import pytest
from app.models.hire_models import Trip
from conftest import bearer
from test_hire_pricing import accept, external_driver, hire_setup  # noqa: F401  (hire_setup is a fixture)
from test_rates import rate_owner  # noqa: F401  (fixture used by hire_setup)


@pytest.fixture
def done(client, hire_setup):
    """A booking whose trip had an external Driver and is now COMPLETED."""
    c = hire_setup
    driver, dt = external_driver(client, c)
    b = accept(client, c, c.create())
    result = client.post(f"/api/v1/bookings/{b['id']}/driver-assignments", headers=bearer(c.owner),
                         json={'expected_version': b['version'], 'driver_reference': driver['public_user_reference']})
    assert result.status_code == 200, result.text
    trip_id = UUID(client.get(f"/api/v1/bookings/{b['id']}", headers=bearer(dt)).json()['trip']['id'])
    with client.app.state.sessions() as db:
        trip = db.get(Trip, trip_id)
        trip.assignment_status, trip.status = 'ACCEPTED', 'COMPLETED'
        db.commit()
        owner_id = trip.operating_owner_user_id
    assert owner_id is not None
    return type('Done', (), {'c': c, 'driver': driver, 'dt': dt, 'trip_id': str(trip_id)})


def record(client, done, **body):
    return client.post(f'/api/v1/trips/{done.trip_id}/driver-payment', headers=bearer(done.c.owner),
                       json={'amount': '2500.00', 'method': 'CASH', **body})


def test_online_payment_is_recorded_and_final_with_its_reference(client, done):
    made = record(client, done, method='ONLINE', reference='BANK-TRF-0001')
    assert made.status_code == 201, made.text
    assert made.json()['status'] == 'CONFIRMED' and made.json()['reference'] == 'BANK-TRF-0001'
    mine = client.get('/api/v1/drivers/me/payments', headers=bearer(done.dt)).json()
    assert mine['totals']['confirmed_total'] == '2500.00' and mine['items'][0]['method'] == 'ONLINE'
    owners = client.get('/api/v1/owners/me/driver-payments', headers=bearer(done.c.owner)).json()
    assert owners['totals']['confirmed_total'] == '2500.00'


def test_online_payment_needs_a_reference(client, done):
    assert record(client, done, method='ONLINE').status_code == 422


def test_cash_waits_for_the_driver_and_counts_only_after_confirmation(client, done):
    made = record(client, done)
    assert made.status_code == 201, made.text
    payment_id = made.json()['id']
    assert made.json()['status'] == 'PENDING_DRIVER'
    before = client.get('/api/v1/owners/me/driver-payments', headers=bearer(done.c.owner)).json()['totals']
    assert before['confirmed_total'] == '0.00' and before['waiting_total'] == '2500.00'
    # The Owner cannot confirm for the Driver.
    assert client.post(f'/api/v1/driver-payments/{payment_id}/confirm', headers=bearer(done.c.owner), json={}).status_code in (403, 404)
    ok = client.post(f'/api/v1/driver-payments/{payment_id}/confirm', headers=bearer(done.dt), json={})
    assert ok.status_code == 200, ok.text
    assert ok.json()['status'] == 'CONFIRMED' and ok.json()['driver_confirmed_at']
    after = client.get('/api/v1/drivers/me/payments', headers=bearer(done.dt)).json()['totals']
    assert after['confirmed_total'] == '2500.00' and after['waiting_total'] == '0.00'
    # A second confirmation is refused.
    assert client.post(f'/api/v1/driver-payments/{payment_id}/confirm', headers=bearer(done.dt), json={}).status_code == 409


def test_one_live_payment_per_trip_and_a_declined_cash_can_be_recorded_again(client, done):
    first = record(client, done)
    assert first.status_code == 201, first.text
    assert record(client, done).status_code == 409
    declined = client.post(f"/api/v1/driver-payments/{first.json()['id']}/decline", headers=bearer(done.dt), json={'note': 'Nothing received'})
    assert declined.status_code == 200 and declined.json()['status'] == 'DECLINED'
    assert client.get('/api/v1/owners/me/driver-payments', headers=bearer(done.c.owner)).json()['items'] == []
    again = record(client, done, method='ONLINE', reference='REF-2')
    assert again.status_code == 201, again.text


def test_only_the_trips_owner_can_record_and_only_after_completion(client, done):
    stranger = client.post(f'/api/v1/trips/{done.trip_id}/driver-payment', headers=bearer(done.dt), json={'amount': '100.00', 'method': 'CASH'})
    assert stranger.status_code in (403, 404)
    with client.app.state.sessions() as db:
        trip = db.get(Trip, UUID(done.trip_id)); trip.status = 'IN_PROGRESS'; db.commit()
    assert record(client, done).status_code == 409
    assert record(client, done, amount='0').status_code == 422


def test_paid_on_defaults_to_today_and_can_be_an_earlier_day_but_not_a_future_one(client, done):
    from datetime import timedelta
    from app.api.routers.driver_payment_api import today_in_sri_lanka
    today = today_in_sri_lanka()
    assert record(client, done, paid_on=(today + timedelta(days=1)).isoformat()).status_code == 422
    earlier = (today - timedelta(days=3)).isoformat()
    made = record(client, done, paid_on=earlier)
    assert made.status_code == 201, made.text
    assert made.json()['paid_on'] == earlier


def test_paid_on_is_today_when_not_given(client, done):
    from app.api.routers.driver_payment_api import today_in_sri_lanka
    made = record(client, done)
    assert made.status_code == 201, made.text
    assert made.json()['paid_on'] == today_in_sri_lanka().isoformat()


def test_due_list_shows_unpaid_trips_and_drops_them_once_paid(client, done):
    due = client.get('/api/v1/owners/me/driver-payments/due', headers=bearer(done.c.owner))
    assert due.status_code == 200, due.text
    assert [i['trip_id'] for i in due.json()['items']] == [done.trip_id]
    assert due.json()['items'][0]['driver']['reference'] == done.driver['public_user_reference']
    assert record(client, done, method='ONLINE', reference='BANK-TRF-0002').status_code == 201
    assert client.get('/api/v1/owners/me/driver-payments/due', headers=bearer(done.c.owner)).json()['count'] == 0


def test_due_list_shows_a_declined_cash_payment_again_with_the_note(client, done):
    payment_id = record(client, done).json()['id']
    assert client.get('/api/v1/owners/me/driver-payments/due', headers=bearer(done.c.owner)).json()['count'] == 0
    assert client.post(f'/api/v1/driver-payments/{payment_id}/decline', headers=bearer(done.dt), json={'note': 'Nothing received'}).status_code == 200
    due = client.get('/api/v1/owners/me/driver-payments/due', headers=bearer(done.c.owner)).json()
    assert due['count'] == 1 and due['items'][0]['declined_note'] == 'Nothing received'


def test_only_an_owner_can_see_the_due_list(client, done):
    assert client.get('/api/v1/owners/me/driver-payments/due', headers=bearer(done.dt)).status_code in (403, 404)
