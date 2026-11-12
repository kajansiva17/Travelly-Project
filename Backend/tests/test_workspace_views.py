"""One workspace per person (owner request 12 Nov 2026): an Owner or Driver books, pays and drives from their own
dashboard, so the API says how the caller takes part in each booking."""
from uuid import UUID
from sqlalchemy import select
from app.models.hire_models import Trip
from test_ticket_holds import api, person, ticket, hold_body
from test_payments import held
from test_refunds import paid


def ids(client, who, view=None):
    url = '/bookings' + (f'?as={view}' if view else '')
    response = api(client, who, 'get', url)
    assert response.status_code == 200, response.text
    return {i['id']: i['viewer_roles'] for i in response.json()['items']}


def test_each_booking_says_how_the_caller_takes_part(client, paid):
    booking = paid['booking']['id']
    assert ids(client, paid['passenger'])[booking] == ['PASSENGER']
    assert booking in ids(client, paid['passenger'], 'passenger') and booking not in ids(client, paid['passenger'], 'owner')
    with client.app.state.sessions() as db:
        driver = db.scalar(select(Trip.driver_user_id).where(Trip.scheduled_trip_id == UUID(paid['trip']['id'])))
    owner_view = ids(client, paid['owner'])
    expected = ['OWNER', 'DRIVER'] if str(driver) == paid['owner']['id'] else ['OWNER']
    assert owner_view[booking] == expected and booking in ids(client, paid['owner'], 'owner')
    assert booking not in ids(client, paid['owner'], 'passenger')
    assert (booking in ids(client, paid['owner'], 'driver')) == ('DRIVER' in expected)


def test_an_owner_books_as_a_passenger_from_the_same_account(client, paid):
    # The Owner of one departure buys a seat as an ordinary Passenger (every account has the Passenger role).
    other_owner = paid['owner']
    hold = api(client, other_owner, 'post', '/bookings/ticket-holds', hold_body(paid, ['A3']))
    assert hold.status_code == 201, hold.text
    mine = ids(client, other_owner, 'passenger')
    assert mine[hold.json()['id']][0] == 'PASSENGER'


def test_unknown_view_is_refused(client, ticket):
    refused = api(client, ticket['owner'], 'get', '/bookings?as=admin')
    assert refused.status_code == 422


def test_only_approved_drivers_list_the_departures_they_drive(client, ticket):
    # Driving always needs the DRIVER role (self-drive included), so an Owner without it has no "My driving".
    owner_only = person(client, 'OWNER')
    assert api(client, owner_only, 'get', '/scheduled-trips?driving=true').status_code == 403
    assert api(client, person(client, 'OWNER', 'DRIVER'), 'get', '/scheduled-trips?driving=true').status_code == 200
