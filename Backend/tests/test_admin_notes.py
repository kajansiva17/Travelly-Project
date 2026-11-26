"""Admin notes (Manual fulfilment page): the Admin writes, edits and deletes notes, optionally tied to a booking or a departure."""
from uuid import UUID
from app.models.hire_models import Booking, ScheduledTrip
from test_ticket_holds import api, ticket  # noqa: F401  (ticket is a fixture)
from test_payments import held  # noqa: F401  (a fixture)

URL = '/admin/manual-fulfilment-events'


def test_the_admin_writes_edits_and_deletes_notes(client, held):
    boss = held['admin']
    assert api(client, boss, 'get', URL).json()['items'] == []
    made = api(client, boss, 'post', URL, {'summary': 'Phoned the passenger', 'details': 'Agreed to refund by cash.'})
    assert made.status_code == 201, made.text
    note = made.json()
    assert note['summary'] == 'Phoned the passenger' and note['link'] is None and note['updated_at'] is None
    edited = api(client, boss, 'patch', f"{URL}/{note['id']}", {'summary': 'Phoned the passenger twice', 'details': 'Agreed to refund by cash.'})
    assert edited.status_code == 200 and edited.json()['summary'] == 'Phoned the passenger twice' and edited.json()['updated_at']
    assert [n['id'] for n in api(client, boss, 'get', URL).json()['items']] == [note['id']]
    assert api(client, boss, 'delete', f"{URL}/{note['id']}").json() == {'deleted': True}
    assert api(client, boss, 'get', URL).json()['items'] == []
    assert api(client, boss, 'patch', f"{URL}/{note['id']}", {'summary': 'x', 'details': 'y'}).status_code == 404
    assert api(client, boss, 'delete', f"{URL}/{note['id']}").status_code == 404


def test_a_note_can_be_tied_to_a_booking_or_a_departure_and_shows_what_it_is_about(client, held):
    boss = held['admin']
    reference = held['booking']['booking_reference']
    made = api(client, boss, 'post', URL, {'summary': 'Check this booking', 'details': 'Seat moved by hand.', 'reference': reference.lower()})
    assert made.status_code == 201, made.text
    link = made.json()['link']
    assert link['type'] == 'BOOKING' and link['reference'] == reference and link['status']
    with client.app.state.sessions() as db:
        departure = db.get(ScheduledTrip, db.get(Booking, UUID(held['booking']['id'])).current_scheduled_trip_id).departure_reference
    moved = api(client, boss, 'patch', f"{URL}/{made.json()['id']}", {'summary': 'Check this departure', 'details': 'Driver changed.', 'reference': departure})
    assert moved.status_code == 200 and moved.json()['link']['type'] == 'DEPARTURE' and moved.json()['link']['reference'] == departure
    cleared = api(client, boss, 'patch', f"{URL}/{made.json()['id']}", {'summary': 'No link now', 'details': 'Just a note.'})
    assert cleared.json()['link'] is None
    unknown = api(client, boss, 'post', URL, {'summary': 'x', 'details': 'y', 'reference': 'TKT-DOESNOTEXIST'})
    assert unknown.status_code == 404 and unknown.json()['code'] == 'REFERENCE_NOT_FOUND'


def test_only_admins_use_notes_and_blank_notes_are_refused(client, held):
    assert api(client, held['owner'], 'get', URL).status_code == 403
    assert api(client, held['owner'], 'post', URL, {'summary': 'x', 'details': 'y'}).status_code == 403
    assert api(client, held['admin'], 'post', URL, {'summary': '   ', 'details': 'y'}).status_code == 422
    assert api(client, held['admin'], 'post', URL, {'summary': 'x', 'details': ''}).status_code == 422
