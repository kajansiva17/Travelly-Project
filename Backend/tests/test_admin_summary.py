"""Admin dashboard summary: the numbers behind the Command Centre tiles."""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID
from app.models.review_models import Vehicle
from test_ticket_holds import api, person, ticket  # noqa: F401  (ticket is a fixture)


def test_the_admin_summary_has_trips_money_a_seven_day_trend_and_live_vehicles(client, ticket):
    first = api(client, ticket['admin'], 'get', '/admin/dashboard-summary')
    assert first.status_code == 200, first.text
    body = first.json()
    assert body['currency'] == 'LKR' and set(body['trips']) == {'today', 'on_the_road', 'finished_today'}
    assert body['money_today'] == {'collected': '0.00', 'commission': '0.00'} and body['live_vehicles'] == []
    assert len(body['booking_trend']) == 7 and body['booking_trend'][-1]['date'] == body['date']
    with client.app.state.sessions() as db:
        vehicle = db.get(Vehicle, UUID(ticket['trip']['vehicle_id']))
        vehicle.current_latitude, vehicle.current_longitude = Decimal('6.927079'), Decimal('79.861244')
        vehicle.current_location_observed_at = datetime.now(timezone.utc)
        db.commit()
    live = api(client, ticket['admin'], 'get', '/admin/dashboard-summary').json()['live_vehicles']
    assert len(live) == 1 and live[0]['id'] == ticket['trip']['vehicle_id'] and live[0]['online'] is False and live[0]['on_trip'] is False


def test_only_admins_read_the_summary(client, ticket):
    assert api(client, ticket['owner'], 'get', '/admin/dashboard-summary').status_code == 403
    assert api(client, person(client), 'get', '/admin/dashboard-summary').status_code == 403
