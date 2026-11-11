"""Running a published departure: its trip row, boarding, and the Owner's Driver choices.

Everything uses the PRD tables: trips.scheduled_trip_id, scheduled_trips.operator_driver_user_id
and booking_travellers.traveller_status (ACTIVE -> BOARDED -> COMPLETED).
"""
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
import pytest
from sqlalchemy import func, select
from app.models.review_models import Document, Vehicle
from app.models.rate_models import ServiceType
from app.models.hire_models import Trip
from app.models.seat_models import BookingTraveller, ScheduledTripSeat
from conftest import bearer
from test_ticket_holds import api, iso, person, ticket, configure_hold, hold_body


def journey(client, departure_id):
    with client.app.state.sessions() as db:
        return db.scalar(select(Trip).where(Trip.scheduled_trip_id == UUID(departure_id)))


@pytest.fixture
def drivable(client, ticket):
    """The Owner drives their own departure: licence on file and the service matched to the vehicle."""
    owner_id = UUID(ticket['owner']['id'])
    with client.app.state.sessions() as db:
        service = db.scalar(select(ServiceType).where(ServiceType.category == 'TICKET_HIRE'))
        service.settings = {**service.settings, 'licence_compatibility': {'TEST_CAR': ['B']}}
        db.add(Document(user_id=owner_id, document_type='DRIVING_LICENCE', status='APPROVED', submitted_at=func.now(),
                        verified_by=owner_id, verified_at=func.now(), issuing_country='LK',
                        expiry_date=(datetime.now(timezone.utc) + timedelta(days=365)).date(),
                        storage_key=uuid4().hex, original_file_name='licence.png', mime_type='image/png',
                        file_size_bytes=1, file_checksum='0' * 64, verified_categories=['B']))
        db.commit()
    return ticket


def at_departure(monkeypatch, client, ticket, minutes=1):
    """Move the clock the API reads to just after the departure time."""
    import app.api.routers.hire_api as module
    start = datetime.fromisoformat(ticket['trip']['departure_at']) + timedelta(minutes=minutes)

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None): return start.astimezone(tz or timezone.utc)
    monkeypatch.setattr(module, 'datetime', Clock)


def test_publishing_a_departure_creates_the_journey_the_driver_runs(client, ticket):
    run = journey(client, ticket['trip']['id'])
    assert run is not None
    assert run.status == 'READY' and run.assignment_status == 'ACCEPTED'
    assert run.assignment_type == 'OWNER_SELF_DRIVE'
    assert str(run.driver_user_id) == ticket['owner']['id']
    assert run.scheduled_start_at.isoformat() == ticket['trip']['departure_at']


def test_the_owner_sees_the_drivers_they_have_worked_with(client, ticket):
    listed = api(client, ticket['owner'], 'get', '/owners/me/drivers')
    assert listed.status_code == 200, listed.text
    items = listed.json()['items']
    assert [item['id'] for item in items] == [ticket['owner']['id']]
    assert items[0]['eligible'] and items[0]['how_you_know_them'] == 'You'
    assert 'phone' not in items[0] and 'contact_phone' not in items[0]
    stranger = person(client, 'OWNER')
    assert api(client, stranger, 'get', '/owners/me/drivers').json()['items'] == []


def test_an_owner_who_does_not_drive_can_assign_a_driver_to_a_draft(client, ticket):
    owner = person(client, 'OWNER')  # no Driver role of their own
    driver = person(client, 'DRIVER')
    with client.app.state.sessions() as db:
        vehicle = db.get(Vehicle, UUID(ticket['trip']['vehicle_id']))
        vehicle.owner_user_id = UUID(owner['id'])
        db.commit()
    draft = api(client, owner, 'post', '/scheduled-trips', {
        'route_id': ticket['route']['id'], 'vehicle_id': ticket['trip']['vehicle_id'], 'departure_at': iso(timedelta(days=3)),
        'estimated_arrival_at': iso(timedelta(days=3, hours=3)), 'booking_cutoff_at': iso(timedelta(days=2)),
        'fare_per_seat': '1500.00', 'fulfilment_policy': 'FIXED_GUARANTEED', 'accepted_time_window_minutes': 0,
        'accepted_replacement_terms': {}})
    assert draft.status_code == 201, draft.text
    draft = draft.json()
    assert draft['operator_driver_user_id'] is None
    assigned = api(client, owner, 'patch', f"/scheduled-trips/{draft['id']}",
                   {'expected_version': draft['version'], 'operator_driver_user_id': driver['id']})
    assert assigned.status_code == 200, assigned.text
    assert assigned.json()['operator_driver_user_id'] == driver['id']
    refused = api(client, owner, 'patch', f"/scheduled-trips/{draft['id']}",
                  {'expected_version': assigned.json()['version'], 'operator_driver_user_id': ticket['admin']['id']})
    assert refused.status_code == 422 and refused.json()['code'] == 'DRIVER_NOT_ELIGIBLE'


def test_the_driver_starts_the_departure_and_the_departure_moves_with_it(client, drivable, monkeypatch):
    ticket = drivable
    run = journey(client, ticket['trip']['id'])
    at_departure(monkeypatch, client, ticket)
    started = api(client, ticket['owner'], 'post', f"/trips/{run.id}/start",
                  {'expected_version': run.version, 'start_odometer_km': '4000.0', 'checklist_confirmed': True})
    assert started.status_code == 200, started.text
    assert started.json()['status'] == 'IN_PROGRESS'
    detail = api(client, ticket['owner'], 'get', f"/scheduled-trips/{ticket['trip']['id']}")
    assert detail.json()['status'] == 'IN_PROGRESS'


def test_a_departure_cannot_start_before_its_time(client, drivable):
    ticket = drivable
    run = journey(client, ticket['trip']['id'])
    early = api(client, ticket['owner'], 'post', f"/trips/{run.id}/start",
                {'expected_version': run.version, 'start_odometer_km': '4000.0', 'checklist_confirmed': True})
    assert early.status_code == 409 and early.json()['code'] == 'TRIP_NOT_READY'


def booked_traveller(client, ticket):
    """A paid seat: payment is not built yet, so the seat is marked booked directly."""
    configure_hold(client, ticket)
    passenger = person(client)
    held = api(client, passenger, 'post', '/bookings/ticket-holds', hold_body(ticket, ['A1']))
    assert held.status_code == 201, held.text
    with client.app.state.sessions() as db:
        seat = db.scalar(select(ScheduledTripSeat).where(ScheduledTripSeat.id == UUID(ticket['seats']['A1'])))
        seat.seat_status = 'BOOKED'
        seat.booked_booking_id = seat.held_by_booking_id
        seat.held_by_booking_id = None
        seat.hold_expires_at = None
        db.commit()
    return passenger, held.json()


def test_the_driver_boards_a_paid_traveller_and_only_a_paid_one(client, drivable):
    ticket = drivable
    configure_hold(client, ticket)
    passenger = person(client)
    held = api(client, passenger, 'post', '/bookings/ticket-holds', hold_body(ticket, ['A1', 'A2']))
    assert held.status_code == 201, held.text
    listed = api(client, ticket['owner'], 'get', f"/scheduled-trips/{ticket['trip']['id']}/travellers")
    assert listed.status_code == 200, listed.text
    items = listed.json()['items']
    assert len(items) == 2 and all(item['seat_status'] == 'HELD' and not item['can_board'] for item in items)
    refused = api(client, ticket['owner'], 'post', f"/scheduled-trips/{ticket['trip']['id']}/boardings",
                  {'traveller_id': items[0]['traveller_id']})
    assert refused.status_code == 409 and refused.json()['code'] == 'SEAT_NOT_PAID'
    with client.app.state.sessions() as db:
        for seat in db.scalars(select(ScheduledTripSeat).where(ScheduledTripSeat.scheduled_trip_id == UUID(ticket['trip']['id']),
                                                               ScheduledTripSeat.seat_status == 'HELD')):
            seat.seat_status = 'BOOKED'
            seat.booked_booking_id = seat.held_by_booking_id
            seat.held_by_booking_id = None
            seat.hold_expires_at = None
        db.commit()
    boarded = api(client, ticket['owner'], 'post', f"/scheduled-trips/{ticket['trip']['id']}/boardings",
                  {'traveller_id': items[0]['traveller_id']})
    assert boarded.status_code == 200, boarded.text
    assert boarded.json()['status'] == 'BOARDED'
    assert boarded.json()['seat_code'] == items[0]['seat_code']
    again = api(client, ticket['owner'], 'post', f"/scheduled-trips/{ticket['trip']['id']}/boardings",
                {'traveller_id': items[0]['traveller_id']})
    assert again.status_code == 200 and again.json()['status'] == 'BOARDED'
    assert api(client, passenger, 'post', f"/scheduled-trips/{ticket['trip']['id']}/boardings",
               {'traveller_id': items[1]['traveller_id']}).status_code == 404
    after = api(client, ticket['owner'], 'get', f"/scheduled-trips/{ticket['trip']['id']}/travellers").json()
    assert after['boarded'] == 1


def test_finishing_the_departure_closes_the_travellers_who_boarded(client, drivable, monkeypatch):
    ticket = drivable
    passenger, booking = booked_traveller(client, ticket)
    run = journey(client, ticket['trip']['id'])
    at_departure(monkeypatch, client, ticket)
    started = api(client, ticket['owner'], 'post', f"/trips/{run.id}/start",
                  {'expected_version': run.version, 'start_odometer_km': '4000.0', 'checklist_confirmed': True})
    assert started.status_code == 200, started.text
    listed = api(client, ticket['owner'], 'get', f"/scheduled-trips/{ticket['trip']['id']}/travellers").json()
    boarded = api(client, ticket['owner'], 'post', f"/scheduled-trips/{ticket['trip']['id']}/boardings",
                  {'traveller_id': listed['items'][0]['traveller_id']})
    assert boarded.status_code == 200, boarded.text
    done = api(client, ticket['owner'], 'post', f"/trips/{run.id}/complete",
               {'expected_version': started.json()['version'], 'end_odometer_km': '4120.0'})
    assert done.status_code == 200, done.text
    assert done.json()['trip']['status'] == 'COMPLETED'
    assert done.json()['trip']['calculated_distance_km'] == '120.0'
    with client.app.state.sessions() as db:
        statuses = db.scalars(select(BookingTraveller.traveller_status)
                              .where(BookingTraveller.booking_id == UUID(booking['id']))).all()
    assert statuses == ['COMPLETED']
    assert api(client, ticket['owner'], 'get', f"/scheduled-trips/{ticket['trip']['id']}").json()['status'] == 'COMPLETED'


def test_a_seated_passenger_may_follow_the_journey_and_a_stranger_may_not(client, drivable):
    ticket = drivable
    passenger, _ = booked_traveller(client, ticket)
    run = journey(client, ticket['trip']['id'])
    seen = api(client, passenger, 'get', f"/trips/{run.id}")
    assert seen.status_code == 200
    assert seen.json()['scheduled_trip_id'] == ticket['trip']['id']
    assert api(client, person(client), 'get', f"/trips/{run.id}").status_code == 404


def test_the_driver_lists_the_departures_they_are_assigned_to_drive(client, ticket):
    listed = api(client, ticket['owner'], 'get', '/scheduled-trips?driving=true')
    assert listed.status_code == 200, listed.text
    assert [item['id'] for item in listed.json()['items']] == [ticket['trip']['id']]
    other = person(client, 'DRIVER')
    assert api(client, other, 'get', '/scheduled-trips?driving=true').json()['items'] == []
    assert api(client, person(client), 'get', '/scheduled-trips?driving=true').status_code == 403
