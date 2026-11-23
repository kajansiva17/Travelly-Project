"""Ticket boarding by QR code or PIN: the Passenger opens the code of a paid booking, the departure's Driver checks it, then boards the travellers."""
from uuid import UUID
from sqlalchemy import select
from app.models.seat_models import ScheduledTripSeat
from test_departure_trips import drivable  # noqa: F401  (fixture)
from test_ticket_holds import api, configure_hold, hold_body, person, ticket  # noqa: F401


def hold_and_pay(client, ticket, seats):
    configure_hold(client, ticket)
    passenger = person(client)
    held = api(client, passenger, 'post', '/bookings/ticket-holds', hold_body(ticket, seats))
    assert held.status_code == 201, held.text
    return passenger, held.json()


def pay(client, ticket):
    with client.app.state.sessions() as db:
        for seat in db.scalars(select(ScheduledTripSeat).where(ScheduledTripSeat.scheduled_trip_id == UUID(ticket['trip']['id']), ScheduledTripSeat.seat_status == 'HELD')):
            seat.seat_status, seat.booked_booking_id, seat.held_by_booking_id, seat.hold_expires_at = 'BOOKED', seat.held_by_booking_id, None, None
        db.commit()


def test_the_code_opens_only_after_payment_and_only_for_the_passenger(client, drivable):
    ticket = drivable
    passenger, held = hold_and_pay(client, ticket, ['A1', 'A2'])
    path = f"/bookings/{held['id']}/boarding-code"
    assert api(client, passenger, 'get', path).json()['code'] == 'SEATS_NOT_CONFIRMED'   # still only held
    pay(client, ticket)
    code = api(client, passenger, 'get', path)
    assert code.status_code == 200, code.text
    body = code.json()
    assert len(body['pin']) == 6 and body['pin'].isdigit() and body['qr_token'] and body['travellers'] == 2 and body['boarded'] == 0
    assert api(client, passenger, 'get', path).json() == body   # the same code every time
    assert api(client, person(client), 'get', path).status_code == 404   # somebody else's booking


def test_the_driver_checks_the_qr_or_the_pin_and_boards_the_travellers(client, drivable):
    ticket = drivable   # the Owner drives this departure
    passenger, held = hold_and_pay(client, ticket, ['A1', 'A2'])
    pay(client, ticket)
    code = api(client, passenger, 'get', f"/bookings/{held['id']}/boarding-code").json()
    check = f"/scheduled-trips/{ticket['trip']['id']}/boarding-checks"
    assert api(client, ticket['owner'], 'post', check, {}).status_code == 422                       # neither code
    assert api(client, ticket['owner'], 'post', check, {'pin': code['pin'], 'qr_token': code['qr_token']}).status_code == 422   # both codes
    wrong = '000000' if code['pin'] != '000000' else '111111'
    assert api(client, ticket['owner'], 'post', check, {'pin': wrong}).json()['code'] == 'BOARDING_CODE_INVALID'
    assert api(client, ticket['owner'], 'post', check, {'qr_token': 'not-a-code'}).json()['code'] == 'BOARDING_CODE_INVALID'
    assert api(client, passenger, 'post', check, {'pin': code['pin']}).status_code == 404            # a Passenger cannot check tickets
    by_pin = api(client, ticket['owner'], 'post', check, {'pin': code['pin']})
    assert by_pin.status_code == 200, by_pin.text
    by_qr = api(client, ticket['owner'], 'post', check, {'qr_token': code['qr_token']})
    assert by_qr.json() == by_pin.json()
    travellers = by_pin.json()['matches'][0]['travellers']
    assert len(travellers) == 2 and all(item['can_board'] for item in travellers)
    for item in travellers:
        assert api(client, ticket['owner'], 'post', f"/scheduled-trips/{ticket['trip']['id']}/boardings", {'traveller_id': item['traveller_id']}).status_code == 200
    assert api(client, passenger, 'get', f"/bookings/{held['id']}/boarding-code").json()['boarded'] == 2
    again = api(client, ticket['owner'], 'post', check, {'pin': code['pin']}).json()['matches'][0]['travellers']
    assert [item['status'] for item in again] == ['BOARDED', 'BOARDED'] and not any(item['can_board'] for item in again)
