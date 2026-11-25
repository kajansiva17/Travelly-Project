"""Ticket boarding by QR code or PIN (owner decision 23 Nov 2026).
 * The Passenger of a paid ticket booking opens the booking's boarding code: a QR code and the six digits printed under it. Neither is stored; both are derived
   from the application secret and the booking id, like the private-hire pickup code, so the Passenger can open the same code again at any time.
 * The Driver of the departure scans the QR code, or types the six digits when the camera does not work. The answer lists the travellers of that booking on
   this departure; the Driver then marks them boarded with the existing boarding call. Trying codes is limited.
 * Six digits can match two bookings on one departure; the Driver then sees both and picks by name."""
from uuid import UUID
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.routers.api import current
from app.api.routers.scheduled_trip_api import departure_crew
from app.api.routers.ticket_booking_api import own_ticket_booking
from app.core.errors import ApiError
from app.dependencies.database import get_db
from app.models.hire_models import Booking
from app.models.seat_models import BookingTraveller, ScheduledTripSeat, VehicleSeat
from app.services.pickup_codes import PIN_DIGITS, _mac, same
import base64

router = APIRouter(prefix='/api/v1', tags=['Ticket boarding'])
ATTEMPTS = 40          # code checks one Driver may make on one departure
WINDOW_SECONDS = 600


def ticket_pin(booking_id):
    return str(int.from_bytes(_mac(booking_id, 0, 'ticket-pin')[:8], 'big') % 10 ** PIN_DIGITS).zfill(PIN_DIGITS)


def ticket_token(booking_id):
    return base64.urlsafe_b64encode(_mac(booking_id, 0, 'ticket-qr')).decode().rstrip('=')


class Check(BaseModel):
    model_config = {'extra': 'forbid'}
    qr_token: str | None = Field(default=None, max_length=200)
    pin: str | None = Field(default=None, pattern=r'^\d{6}$')

    @model_validator(mode='after')
    def one_of(self):
        if bool(self.qr_token) == bool(self.pin):
            raise ValueError('Send the QR code or the six digits.')
        return self


def traveller_rows(db, booking_id):
    return db.execute(select(BookingTraveller, ScheduledTripSeat, VehicleSeat)
                      .join(ScheduledTripSeat, ScheduledTripSeat.id == BookingTraveller.scheduled_trip_seat_id)
                      .join(VehicleSeat, VehicleSeat.id == ScheduledTripSeat.vehicle_seat_id)
                      .where(BookingTraveller.booking_id == booking_id, BookingTraveller.traveller_status.notin_(('CANCELLED', 'MOVED')))
                      .order_by(VehicleSeat.deck_number, VehicleSeat.row_number, VehicleSeat.column_number)).all()


@router.get('/bookings/{booking_id}/boarding-code')
def boarding_code(booking_id: UUID, user=Depends(current), db: Session = Depends(get_db)):
    booking = own_ticket_booking(db, booking_id, user)
    rows = traveller_rows(db, booking.id)
    if not rows or not any(inventory.seat_status == 'BOOKED' for _, inventory, _ in rows):
        raise ApiError(409, 'SEATS_NOT_CONFIRMED', 'The boarding code opens after the seats are paid for.')
    return {'qr_token': ticket_token(booking.id), 'pin': ticket_pin(booking.id), 'travellers': len(rows),
            'boarded': sum(1 for traveller, _, _ in rows if traveller.traveller_status in ('BOARDED', 'COMPLETED'))}


@router.post('/scheduled-trips/{trip_id}/boarding-checks')
def boarding_check(trip_id: UUID, body: Check, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    departure, run = departure_crew(db, trip_id, user)
    if not run or run.driver_user_id != user.id:
        raise ApiError(403, 'NOT_THE_DEPARTURE_DRIVER', 'Only the assigned Driver checks tickets.')
    if run.status not in ('READY', 'IN_PROGRESS'):
        raise ApiError(409, 'TRIP_NOT_READY', 'Boarding belongs to a departure that has not finished.')
    request.app.state.store.rate(f'board-check:{user.id}:{departure.id}', ATTEMPTS, WINDOW_SECONDS)
    booking_ids = list(dict.fromkeys(db.scalars(
        select(BookingTraveller.booking_id).join(ScheduledTripSeat, ScheduledTripSeat.id == BookingTraveller.scheduled_trip_seat_id)
        .where(ScheduledTripSeat.scheduled_trip_id == departure.id, BookingTraveller.traveller_status.notin_(('CANCELLED', 'MOVED'))))))
    matches = []
    for booking_id in booking_ids:
        given, expected = (body.qr_token, ticket_token(booking_id)) if body.qr_token else (body.pin, ticket_pin(booking_id))
        if same(given, expected):
            matches.append(booking_id)
    if not matches:
        raise ApiError(422, 'BOARDING_CODE_INVALID', 'No ticket on this departure matches that code.')
    out = []
    for booking_id in matches:
        booking = db.get(Booking, booking_id)
        out.append({'booking_reference': booking.booking_reference, 'booking_id': str(booking.id),
                    'travellers': [{'traveller_id': str(traveller.id), 'full_name': traveller.full_name, 'seat_code': seat.seat_code,
                                    'status': traveller.traveller_status, 'can_board': inventory.seat_status == 'BOOKED' and traveller.traveller_status == 'ACTIVE'}
                                   for traveller, inventory, seat in traveller_rows(db, booking_id)]})
    return {'matches': out}
