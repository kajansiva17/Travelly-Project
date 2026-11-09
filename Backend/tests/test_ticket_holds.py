"""Ticket departures (matrix 32-39) and seat holds (40-41) on the PRD tables."""
import threading
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
import pytest
from sqlalchemy import func, select, update
from app.models import UserRole
from app.models.hire_models import Booking
from app.models.rate_models import ServiceType
from app.models.seat_models import BookingTraveller, ScheduledTripSeat
from conftest import bearer, signed_in
from test_vehicles import approve, submitted


def person(client, *roles):
    user, tokens = signed_in(client, {'full_name': 'Test Person', 'email': uuid4().hex + '@example.com',
                                      'phone_e164': '+9477' + str(uuid4().int % 10000000).zfill(7),
                                      'password': 'TravellyStrong1!', 'accept_terms': True})
    with client.app.state.sessions() as db:
        for role in roles:
            db.add(UserRole(user_id=UUID(user['id']), role_code=role, approval_status='APPROVED',
                            approved_by=UUID(user['id']), approved_at=func.now()))
        db.commit()
    return {'id': user['id'], 'tokens': tokens}


def api(client, who, method, path, body=None):
    kwargs = {'json': body} if body is not None else {}
    return client.request(method.upper(), '/api/v1' + path, headers=bearer(who['tokens']), **kwargs)


def iso(delta):
    return (datetime.now(timezone.utc) + delta).isoformat()


@pytest.fixture
def ticket(client):
    with client.app.state.sessions() as db:
        # The per-test TRUNCATE ... CASCADE on users also clears service_types; restore the migration seed.
        if not db.scalar(select(ServiceType.id).where(ServiceType.category == 'TICKET_HIRE')):
            db.add(ServiceType(code='TICKET_HIRE', name='Scheduled ticket', category='TICKET_HIRE', is_active=True,
                               display_order=100, default_pricing_basis='PER_SEAT', settings={}))
            db.commit()
        # Start every test unconfigured; tests that need a hold time set it through the Admin API.
        for service in db.scalars(select(ServiceType).where(ServiceType.category == 'TICKET_HIRE')).all():
            service.settings = {k: v for k, v in service.settings.items() if k != 'hold_minutes'}
        db.commit()
    owner, admin = person(client, 'OWNER', 'DRIVER'), person(client, 'ADMIN')
    actors = {'owner': owner, 'admin': admin}
    vehicle = approve(client, actors, submitted(client, actors))
    route = api(client, admin, 'post', '/admin/routes', {
        'route_code': 'R-' + uuid4().hex[:8], 'route_name': 'Colombo to Kandy', 'origin_name': 'Colombo',
        'destination_name': 'Kandy', 'active': True, 'stops': [
            {'stop_name': 'Colombo Fort', 'latitude': '6.933', 'longitude': '79.850'},
            {'stop_name': 'Kegalle', 'latitude': '7.251', 'longitude': '80.346', 'scheduled_offset_minutes': 90},
            {'stop_name': 'Kandy', 'latitude': '7.290', 'longitude': '80.633', 'scheduled_offset_minutes': 150}]})
    assert route.status_code == 201, route.text
    route = route.json()
    seats = [{'code': 'DRV', 'row': 0, 'column': 1, 'type': 'CREW', 'bookable': False},
             {'code': 'F1', 'row': 0, 'column': 0, 'bookable': False}] + [
            {'code': f'A{i}', 'row': 1, 'column': i - 1} for i in (1, 2, 3)]
    layout = api(client, owner, 'put', f"/vehicles/{vehicle['id']}/seat-layout", {'layout_version': 1, 'seats': seats})
    assert layout.status_code == 200, layout.text
    trip = api(client, owner, 'post', '/scheduled-trips', {
        'route_id': route['id'], 'vehicle_id': vehicle['id'], 'departure_at': iso(timedelta(days=2)),
        'estimated_arrival_at': iso(timedelta(days=2, hours=3)), 'booking_cutoff_at': iso(timedelta(days=1)),
        'fare_per_seat': '1500.00', 'fulfilment_policy': 'FIXED_GUARANTEED', 'accepted_time_window_minutes': 0,
        'accepted_replacement_terms': {}})
    assert trip.status_code == 201, trip.text
    trip = trip.json()
    published = api(client, owner, 'post', f"/scheduled-trips/{trip['id']}/publish",
                    {'expected_version': trip['version'], 'publish_confirmed': True})
    assert published.status_code == 200, published.text
    seat_map = client.get(f"/api/v1/scheduled-trips/{trip['id']}/seats").json()['seats']
    services = api(client, admin, 'get', '/admin/ticket-services')
    assert services.status_code == 200, services.text
    service = services.json()['items'][0]
    return {'owner': owner, 'admin': admin, 'trip': published.json(), 'route': route, 'service': service,
            'seats': {s['code']: s['seat_id'] for s in seat_map}, 'seat_map': seat_map}


def configure_hold(client, t, minutes=10):
    result = api(client, t['admin'], 'patch', f"/admin/ticket-services/{t['service']['id']}/hold-settings",
                 {'expected_version': t['service']['version'], 'hold_minutes': minutes})
    assert result.status_code == 200, result.text
    assert result.json()['hold_minutes'] == minutes


def hold_body(t, codes, key=None):
    return {'scheduled_trip_id': t['trip']['id'], 'idempotency_key': key or uuid4().hex,
            'travellers': [{'seat_id': t['seats'][c], 'full_name': f'Traveller {c}'} for c in codes]}


def test_seat_map_only_sells_bookable_seats_with_the_owner_fare(client, ticket):
    assert set(ticket['seats']) == {'A1', 'A2', 'A3'}
    assert all(s['status'] == 'AVAILABLE' and s['fare'] == '1500.00' for s in ticket['seat_map'])


def test_hold_requires_admin_hold_time_and_passenger_role(client, ticket):
    passenger = person(client)
    blocked = api(client, passenger, 'post', '/bookings/ticket-holds', hold_body(ticket, ['A1']))
    assert blocked.status_code == 409 and blocked.json()['code'] == 'TICKET_HOLD_NOT_CONFIGURED'
    assert api(client, ticket['admin'], 'patch', f"/admin/ticket-services/{ticket['service']['id']}/hold-settings",
               {'expected_version': ticket['service']['version'], 'hold_minutes': 0}).status_code == 422
    assert api(client, passenger, 'patch', f"/admin/ticket-services/{ticket['service']['id']}/hold-settings",
               {'expected_version': ticket['service']['version'], 'hold_minutes': 5}).status_code == 403


def test_hold_creates_requested_booking_travellers_and_held_seats(client, ticket):
    configure_hold(client, ticket, 7)
    passenger = person(client)
    result = api(client, passenger, 'post', '/bookings/ticket-holds', hold_body(ticket, ['A1', 'A2']))
    assert result.status_code == 201, result.text
    booking = result.json()
    assert booking['status'] == 'REQUESTED' and booking['hold_active'] is True
    assert booking['total_amount'] == '3000.00' and booking['currency'] == 'LKR'
    assert booking['assurance_type'] == 'FIXED_DEPARTURE'
    assert [t['seat_code'] for t in booking['travellers']] == ['A1', 'A2']
    assert sum(t['is_primary'] for t in booking['travellers']) == 1
    expires = datetime.fromisoformat(booking['hold_expires_at'])
    assert timedelta(minutes=6) < expires - datetime.now(timezone.utc) <= timedelta(minutes=7)
    seats = {s['code']: s['status'] for s in client.get(f"/api/v1/scheduled-trips/{ticket['trip']['id']}/seats").json()['seats']}
    assert seats == {'A1': 'HELD', 'A2': 'HELD', 'A3': 'AVAILABLE'}
    assert client.get(f"/api/v1/scheduled-trips/{ticket['trip']['id']}").json()['available_seats'] == 1
    other = person(client)
    taken = api(client, other, 'post', '/bookings/ticket-holds', hold_body(ticket, ['A2', 'A3']))
    assert taken.status_code == 409 and taken.json()['code'] == 'SEAT_UNAVAILABLE'
    assert api(client, other, 'get', f"/bookings/{booking['id']}/ticket").status_code == 404
    assert api(client, passenger, 'get', f"/bookings/{booking['id']}/ticket").json()['hold_active'] is True


def test_idempotent_retry_returns_the_same_hold(client, ticket):
    configure_hold(client, ticket)
    passenger = person(client)
    body = hold_body(ticket, ['A3'], key='retry-key-0001')
    first = api(client, passenger, 'post', '/bookings/ticket-holds', body)
    again = api(client, passenger, 'post', '/bookings/ticket-holds', body)
    assert first.status_code == 201 and again.status_code == 200
    assert first.json()['id'] == again.json()['id']
    # The same key from another Passenger is a different request, not a replay.
    other = api(client, person(client), 'post', '/bookings/ticket-holds', {**body})
    assert other.status_code == 409 and other.json()['code'] == 'SEAT_UNAVAILABLE'


def test_concurrent_requests_cannot_hold_the_same_seat(client, ticket):
    configure_hold(client, ticket)
    passengers = [person(client) for _ in range(5)]
    barrier, results = threading.Barrier(len(passengers)), []

    def race(who):
        barrier.wait()
        results.append(api(client, who, 'post', '/bookings/ticket-holds', hold_body(ticket, ['A1'])).status_code)

    threads = [threading.Thread(target=race, args=(p,)) for p in passengers]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(results) == [201, 409, 409, 409, 409]
    with client.app.state.sessions() as db:
        held = db.scalars(select(ScheduledTripSeat).where(ScheduledTripSeat.id == UUID(ticket['seats']['A1']))).one()
        assert held.seat_status == 'HELD'
        assert db.scalar(select(func.count()).select_from(Booking).where(
            Booking.current_scheduled_trip_id == UUID(ticket['trip']['id']))) == 1


def test_passenger_release_frees_seats_and_cancels_the_hold(client, ticket):
    configure_hold(client, ticket)
    passenger = person(client)
    booking = api(client, passenger, 'post', '/bookings/ticket-holds', hold_body(ticket, ['A1'])).json()
    assert api(client, person(client), 'delete', f"/bookings/{booking['id']}/seat-hold").status_code == 404
    stale = api(client, passenger, 'delete', f"/bookings/{booking['id']}/seat-hold", {'expected_version': booking['version'] + 5})
    assert stale.status_code == 409 and stale.json()['code'] == 'VERSION_CONFLICT'
    released = api(client, passenger, 'delete', f"/bookings/{booking['id']}/seat-hold", {'reason': 'Changed plans'})
    assert released.status_code == 204, released.text
    after = api(client, passenger, 'get', f"/bookings/{booking['id']}/ticket").json()
    assert after['status'] == 'CANCELLED' and after['hold_active'] is False
    assert after['travellers'][0]['traveller_status'] == 'CANCELLED'
    assert api(client, passenger, 'delete', f"/bookings/{booking['id']}/seat-hold").json()['code'] == 'HOLD_NOT_ACTIVE'
    again = api(client, person(client), 'post', '/bookings/ticket-holds', hold_body(ticket, ['A1']))
    assert again.status_code == 201, again.text


def test_expired_hold_is_released_before_the_next_hold(client, ticket):
    configure_hold(client, ticket)
    first = person(client)
    booking = api(client, first, 'post', '/bookings/ticket-holds', hold_body(ticket, ['A2'])).json()
    with client.app.state.sessions() as db:
        db.execute(update(ScheduledTripSeat).where(ScheduledTripSeat.held_by_booking_id == UUID(booking['id']))
                   .values(hold_expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)))
        db.commit()
    seats = {s['code']: s['status'] for s in client.get(f"/api/v1/scheduled-trips/{ticket['trip']['id']}/seats").json()['seats']}
    assert seats['A2'] == 'AVAILABLE'
    second = api(client, person(client), 'post', '/bookings/ticket-holds', hold_body(ticket, ['A2']))
    assert second.status_code == 201, second.text
    expired = api(client, first, 'get', f"/bookings/{booking['id']}/ticket").json()
    assert expired['status'] == 'CANCELLED' and expired['cancellation_reason'] == 'Seat hold expired.'
    gone = api(client, first, 'delete', f"/bookings/{booking['id']}/seat-hold")
    assert gone.status_code == 410 and gone.json()['code'] == 'HOLD_EXPIRED'
    with client.app.state.sessions() as db:
        statuses = db.scalars(select(BookingTraveller.traveller_status).where(BookingTraveller.booking_id == UUID(booking['id']))).all()
        assert statuses == ['CANCELLED']


def test_expired_hold_releases_on_the_owners_read(client, ticket):
    configure_hold(client, ticket)
    passenger = person(client)
    booking = api(client, passenger, 'post', '/bookings/ticket-holds', hold_body(ticket, ['A3'])).json()
    with client.app.state.sessions() as db:
        db.execute(update(ScheduledTripSeat).where(ScheduledTripSeat.held_by_booking_id == UUID(booking['id']))
                   .values(hold_expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)))
        db.commit()
    read = api(client, passenger, 'get', f"/bookings/{booking['id']}/ticket").json()
    assert read['status'] == 'CANCELLED' and read['hold_active'] is False
    with client.app.state.sessions() as db:
        seat = db.get(ScheduledTripSeat, UUID(ticket['seats']['A3']))
        assert seat.seat_status == 'AVAILABLE' and seat.held_by_booking_id is None and seat.hold_expires_at is None


def test_stops_must_be_on_the_route_and_in_order(client, ticket):
    configure_hold(client, ticket)
    passenger = person(client)
    trip = client.get(f"/api/v1/scheduled-trips/{ticket['trip']['id']}").json()
    stops = {s['stop_name']: s['id'] for s in trip['stops']}
    body = hold_body(ticket, ['A1'])
    backwards = api(client, passenger, 'post', '/bookings/ticket-holds',
                    {**body, 'boarding_stop_id': stops['Kandy'], 'dropoff_stop_id': stops['Kegalle']})
    assert backwards.status_code == 422 and backwards.json()['code'] == 'STOP_ORDER_INVALID'
    foreign = api(client, passenger, 'post', '/bookings/ticket-holds',
                  {**body, 'boarding_stop_id': str(uuid4()), 'dropoff_stop_id': stops['Kandy']})
    assert foreign.status_code == 422 and foreign.json()['code'] == 'STOP_NOT_ON_ROUTE'
    # Each stop is optional on its own (decision 9 Nov 2026): only a get-on stop means getting off at the route end.
    half = api(client, passenger, 'post', '/bookings/ticket-holds', {**body, 'boarding_stop_id': stops['Kegalle']})
    assert half.status_code == 201, half.text
    assert (half.json()['itinerary']['boarding_stop'], half.json()['itinerary']['dropoff_stop']) == ('Kegalle', 'Kandy')
    ok = api(client, passenger, 'post', '/bookings/ticket-holds',
             {**hold_body(ticket, ['A2']), 'boarding_stop_id': stops['Colombo Fort'], 'dropoff_stop_id': stops['Kegalle']})
    assert ok.status_code == 201, ok.text
    assert ok.json()['itinerary']['dropoff_stop'] == 'Kegalle'
    only_off = api(client, passenger, 'post', '/bookings/ticket-holds', {**hold_body(ticket, ['A3']), 'dropoff_stop_id': stops['Kegalle']})
    assert only_off.status_code == 201, only_off.text
    assert only_off.json()['itinerary']['boarding_stop'] == 'Colombo Fort'


def test_invalid_hold_requests_are_rejected(client, ticket):
    configure_hold(client, ticket)
    passenger = person(client)
    duplicate = hold_body(ticket, ['A1'])
    duplicate['travellers'].append(dict(duplicate['travellers'][0]))
    assert api(client, passenger, 'post', '/bookings/ticket-holds', duplicate).status_code == 422
    foreign = hold_body(ticket, ['A1'])
    foreign['travellers'][0]['seat_id'] = str(uuid4())
    result = api(client, passenger, 'post', '/bookings/ticket-holds', foreign)
    assert result.status_code == 422 and result.json()['code'] == 'SEAT_NOT_ON_DEPARTURE'
    phone = hold_body(ticket, ['A1'])
    phone['travellers'][0]['contact_phone'] = '0771234567'
    assert api(client, passenger, 'post', '/bookings/ticket-holds', phone).status_code == 422
    missing = api(client, passenger, 'post', '/bookings/ticket-holds', {**hold_body(ticket, ['A1']), 'scheduled_trip_id': str(uuid4())})
    assert missing.status_code == 404


def test_scheduled_job_releases_untouched_expired_holds(client, ticket):
    import importlib.util, pathlib
    spec = importlib.util.spec_from_file_location('release_job', pathlib.Path(__file__).parents[1] / 'scripts' / 'release_expired_holds.py')
    job = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(job)
    configure_hold(client, ticket)
    passenger = person(client)
    booking = api(client, passenger, 'post', '/bookings/ticket-holds', hold_body(ticket, ['A1', 'A2'])).json()
    assert job.run(client.app.state.engine) == 0
    with client.app.state.sessions() as db:
        db.execute(update(ScheduledTripSeat).where(ScheduledTripSeat.held_by_booking_id == UUID(booking['id']))
                   .values(hold_expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)))
        db.commit()
    assert job.run(client.app.state.engine) == 2
    with client.app.state.sessions() as db:
        assert db.get(Booking, UUID(booking['id'])).status == 'CANCELLED'



def run_hold_default_migration(client):
    import importlib.util, pathlib
    from sqlalchemy import text
    path = pathlib.Path(__file__).parents[1] / 'alembic' / 'versions' / '0008_ticket_hold_default.py'
    spec = importlib.util.spec_from_file_location('m0008', path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with client.app.state.sessions() as db:
        migration.op = type('Op', (), {'execute': staticmethod(lambda sql: db.execute(text(sql)))})
        migration.upgrade()
        db.commit()


def test_migration_default_fills_ten_minutes_without_overwriting_admin_value(client, ticket):
    run_hold_default_migration(client)
    service = api(client, ticket['admin'], 'get', '/admin/ticket-services').json()['items'][0]
    assert service['hold_minutes'] == 10
    changed = api(client, ticket['admin'], 'patch', f"/admin/ticket-services/{service['id']}/hold-settings",
                  {'expected_version': service['version'], 'hold_minutes': 15})
    assert changed.status_code == 200, changed.text
    run_hold_default_migration(client)
    assert api(client, ticket['admin'], 'get', '/admin/ticket-services').json()['items'][0]['hold_minutes'] == 15
    booking = api(client, person(client), 'post', '/bookings/ticket-holds', hold_body(ticket, ['A1'])).json()
    left = datetime.fromisoformat(booking['hold_expires_at']) - datetime.now(timezone.utc)
    assert timedelta(minutes=14) < left <= timedelta(minutes=15)
