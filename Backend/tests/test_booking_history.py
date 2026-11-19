"""A finished booking can be hidden from my own list (never deleted); a ticket booking opens with its Travellers."""
from uuid import UUID
from sqlalchemy import select
from app.models.hire_models import Booking
from test_ticket_holds import api, person, ticket, configure_hold, hold_body


def booked(client, t):
    configure_hold(client, t)
    passenger = person(client)
    held = api(client, passenger, 'post', '/bookings/ticket-holds', hold_body(t, ['A1', 'A2']))
    assert held.status_code == 201, held.text
    return passenger, held.json()['id']


def set_status(client, booking_id, status):
    with client.app.state.sessions() as db:
        db.get(Booking, UUID(booking_id)).status = status
        db.commit()


def ids(client, who, role, hidden=False):
    r = api(client, who, 'get', f'/bookings?as={role}' + ('&hidden=true' if hidden else ''))
    assert r.status_code == 200, r.text
    return [i['id'] for i in r.json()['items']]


def test_a_ticket_booking_detail_lists_its_travellers_for_the_owner_and_the_passenger(client, ticket):
    passenger, booking_id = booked(client, ticket)
    for who in (ticket['owner'], passenger):
        detail = api(client, who, 'get', f'/bookings/{booking_id}')
        assert detail.status_code == 200, detail.text
        body = detail.json()
        assert body['booking_type'] == 'TICKET_HIRE'
        assert sorted(t['seat_code'] for t in body['travellers']) == ['A1', 'A2']
        assert body['origin_text'] and body['destination_text']


def test_only_a_finished_booking_can_be_hidden(client, ticket):
    passenger, booking_id = booked(client, ticket)
    assert api(client, ticket['owner'], 'post', f'/bookings/{booking_id}/hide', {}).status_code == 409


def test_hiding_removes_it_from_my_list_only_and_keeps_it_in_history(client, ticket):
    passenger, booking_id = booked(client, ticket)
    set_status(client, booking_id, 'COMPLETED')
    assert api(client, ticket['owner'], 'post', f'/bookings/{booking_id}/hide', {}).status_code == 200
    assert booking_id not in ids(client, ticket['owner'], 'owner')
    assert booking_id in ids(client, ticket['owner'], 'owner', hidden=True)
    assert booking_id in ids(client, passenger, 'passenger')  # the Passenger's list is their own
    with client.app.state.sessions() as db:
        assert db.get(Booking, UUID(booking_id)).status == 'COMPLETED'


def test_a_stranger_cannot_hide_someone_elses_booking(client, ticket):
    passenger, booking_id = booked(client, ticket)
    set_status(client, booking_id, 'CANCELLED')
    assert api(client, person(client, 'OWNER'), 'post', f'/bookings/{booking_id}/hide', {}).status_code == 404
