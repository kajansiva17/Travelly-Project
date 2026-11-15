"""Finished departures: moved to history (never deleted) and repeated for the next trip on the same route."""
from datetime import timedelta
from uuid import UUID
from sqlalchemy import select
from app.models.hire_models import ScheduledTrip
from test_ticket_holds import api, iso, person, ticket


def finish(client, trip_id, status='COMPLETED'):
    with client.app.state.sessions() as db:
        db.get(ScheduledTrip, UUID(trip_id)).status = status
        db.commit()


def mine(client, ticket, archived=False):
    result = api(client, ticket['owner'], 'get', '/scheduled-trips?mine=true' + ('&archived=true' if archived else ''))
    assert result.status_code == 200, result.text
    return [i['id'] for i in result.json()['items']]


def test_a_running_departure_cannot_be_moved_to_history(client, ticket):
    assert api(client, ticket['owner'], 'post', f"/scheduled-trips/{ticket['trip']['id']}/archive", {}).status_code == 409


def test_a_finished_departure_leaves_the_list_but_stays_as_history(client, ticket):
    trip_id = ticket['trip']['id']
    finish(client, trip_id)
    assert api(client, ticket['owner'], 'post', f'/scheduled-trips/{trip_id}/archive', {}).status_code == 200
    assert trip_id not in mine(client, ticket)
    assert trip_id in mine(client, ticket, archived=True)
    with client.app.state.sessions() as db:
        assert db.get(ScheduledTrip, UUID(trip_id)).status == 'COMPLETED'  # untouched


def test_only_the_owner_can_archive(client, ticket):
    finish(client, ticket['trip']['id'])
    other = person(client, 'OWNER')
    assert api(client, other, 'post', f"/scheduled-trips/{ticket['trip']['id']}/archive", {}).status_code == 404


def test_repeat_makes_a_draft_on_the_same_route_and_archives_the_finished_one(client, ticket):
    old = ticket['trip']
    finish(client, old['id'])
    when = iso(timedelta(days=9))
    made = api(client, ticket['owner'], 'post', f"/scheduled-trips/{old['id']}/repeat", {'departure_at': when})
    assert made.status_code == 201, made.text
    new = made.json()
    assert new['status'] == 'DRAFT' and new['id'] != old['id']
    assert new['route']['id'] == old['route']['id'] and new['vehicle_id'] == old['vehicle_id']
    assert new['fare_per_seat'] == old['fare_per_seat']
    gap = lambda a, b: __import__('datetime').datetime.fromisoformat(a) - __import__('datetime').datetime.fromisoformat(b)
    assert gap(new['estimated_arrival_at'], new['departure_at']) == gap(old['estimated_arrival_at'], old['departure_at'])
    assert gap(new['departure_at'], new['booking_cutoff_at']) == gap(old['departure_at'], old['booking_cutoff_at'])
    assert old['id'] not in mine(client, ticket) and new['id'] in mine(client, ticket)
    assert old['id'] in mine(client, ticket, archived=True)


def test_repeat_into_the_past_is_refused_and_keeps_the_old_one_listed(client, ticket):
    old = ticket['trip']
    finish(client, old['id'])
    result = api(client, ticket['owner'], 'post', f"/scheduled-trips/{old['id']}/repeat", {'departure_at': iso(timedelta(days=-1))})
    assert result.status_code == 422
    assert old['id'] in mine(client, ticket)


def test_a_published_departure_whose_time_passed_can_be_moved_to_history(client, ticket):
    trip_id = ticket['trip']['id']
    with client.app.state.sessions() as db:
        trip = db.get(ScheduledTrip, UUID(trip_id))
        gone = timedelta(days=3)
        trip.booking_cutoff_at -= gone + timedelta(days=1)
        trip.departure_at -= gone + timedelta(days=1)
        trip.estimated_arrival_at -= gone
        db.commit()
    assert api(client, ticket['owner'], 'post', f'/scheduled-trips/{trip_id}/archive', {}).status_code == 200
    assert trip_id in mine(client, ticket, archived=True)
