"""Call buttons. While a booking is live the people on it may call each other from the app.
 * GET /bookings/{id}/contacts: the phone numbers the signed-in person may call for this booking. Only the Passenger, the Owner and the assigned Driver of the
   booking can ask (anyone else gets 404).
 * A Passenger gets the Driver (or the Owner when nobody else drives); a Driver gets the Passenger; an Owner gets the Passenger and the Driver.
 * Numbers are given only while the booking is CONFIRMED or IN_PROGRESS, its trip is not finished, and the booking is within `contact_hours_before` hours of its
   start (Admin sets it per service, default 2; a Book now trip starts at once). Before that `allowed` is false and `opens_at` says when; after the trip the list is
   empty, so a number never stays in the app. `chat` says whether the booking chat is open (from confirmation until the trip ends). Nothing is stored or logged.
   The Passenger is shown by first name only.
 * GET /admin/contact-settings and PATCH /admin/service-types/{id}/contact-window: the Admin's hours setting, for every service.
Works for every service: hire, Book now, rental and ticket seats (the Driver of the departure)."""
import json
from datetime import datetime, timedelta, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.routers.api import current, touch
from app.api.routers.review_api import admin, locked_authority
from app.core.errors import ApiError
from app.dependencies.database import get_db
from app.models import User
from app.models.hire_models import Booking, ScheduledTrip, Trip
from app.models.rate_models import ServiceType
from app.services.contact_window import MAX_CONTACT_HOURS, contact_hours

router = APIRouter(prefix='/api/v1', tags=['Trip contacts'])
LIVE = ('CONFIRMED', 'IN_PROGRESS')
TRIP_OVER = ('COMPLETED', 'CANCELLED')


def trip_of(db, booking):
    """The trip of a booking: its own trip (hire, rental) or the departure's trip (ticket seat)."""
    trip = db.scalar(select(Trip).where(Trip.booking_id == booking.id).order_by(Trip.created_at.desc()))
    if trip is None and booking.current_scheduled_trip_id:
        trip = db.scalar(select(Trip).where(Trip.scheduled_trip_id == booking.current_scheduled_trip_id).order_by(Trip.created_at.desc()))
    return trip


def driver_of(db, booking, trip):
    if trip is not None and trip.driver_user_id:
        return trip.driver_user_id
    if booking.current_scheduled_trip_id:
        scheduled = db.get(ScheduledTrip, booking.current_scheduled_trip_id)
        if scheduled is not None and scheduled.operator_driver_user_id:
            return scheduled.operator_driver_user_id
    return None


def shown_name(user, first_only):
    name = (user.display_name or user.full_name or '').strip()
    return name.split()[0] if first_only and name else name


def parties_of(db, booking_id, user):
    """(booking, trip, parties, my roles). Anyone who is not on the booking gets 404."""
    booking = db.get(Booking, booking_id)
    if booking is None:
        raise ApiError(404, 'BOOKING_NOT_FOUND', 'This booking was not found.')
    trip = trip_of(db, booking)
    driver_id = driver_of(db, booking, trip)
    owner_id = booking.owner_user_id or (trip.operating_owner_user_id if trip is not None else None)
    parties = {'PASSENGER': booking.passenger_user_id, 'OWNER': owner_id, 'DRIVER': driver_id}
    mine = {role for role, person in parties.items() if person == user.id}
    if not mine:
        raise ApiError(404, 'BOOKING_NOT_FOUND', 'This booking was not found.')
    return booking, trip, parties, mine


def is_live(booking, trip):
    return booking.status in LIVE and not (trip is not None and trip.status in TRIP_OVER)


@router.get('/bookings/{booking_id}/contacts')
def booking_contacts(booking_id: UUID, user=Depends(current), db: Session = Depends(get_db)):
    booking, trip, parties, mine = parties_of(db, booking_id, user)
    driver_id = parties['DRIVER']
    live = is_live(booking, trip)
    if not live:
        return {'allowed': False, 'contacts': [], 'chat': False, 'opens_at': None}
    opens_at = booking.start_at - timedelta(hours=contact_hours(db.get(ServiceType, booking.service_type_id)))
    if datetime.now(timezone.utc) < opens_at:
        return {'allowed': False, 'contacts': [], 'chat': True, 'opens_at': opens_at.isoformat()}
    wanted = []
    if 'PASSENGER' in mine:
        wanted.append('DRIVER' if driver_id else 'OWNER')
    if 'DRIVER' in mine:
        wanted.append('PASSENGER')
    if 'OWNER' in mine:
        wanted += ['PASSENGER'] + (['DRIVER'] if driver_id else [])
    contacts, seen = [], {user.id}
    for role in wanted:
        person_id = parties[role]
        if person_id is None or person_id in seen:
            continue
        seen.add(person_id)
        person = db.get(User, person_id)
        if person is None or not person.phone_e164:
            continue
        contacts.append({'role': role, 'name': shown_name(person, first_only=role == 'PASSENGER'), 'phone': person.phone_e164})
    return {'allowed': True, 'contacts': contacts, 'chat': True, 'opens_at': None}


# --------------------------------------------------------------------------- Admin: how early the numbers show (service_types.settings)

class ContactWindow(BaseModel):
    expected_version: int = Field(ge=1)
    hours: int = Field(ge=0, le=MAX_CONTACT_HOURS)


def window_out(row):
    return {'id': str(row.id), 'code': row.code, 'name': row.name, 'category': row.category, 'is_active': row.is_active,
            'version': row.version, 'contact_hours_before': contact_hours(row)}


@router.get('/admin/contact-settings')
def list_contact_settings(user=Depends(admin), db: Session = Depends(get_db)):
    rows = db.scalars(select(ServiceType).order_by(ServiceType.display_order, ServiceType.code).limit(100)).all()
    return {'items': [window_out(r) for r in rows], 'max_hours': MAX_CONTACT_HOURS}


@router.patch('/admin/service-types/{service_id}/contact-window')
def update_contact_window(service_id: UUID, body: ContactWindow, request: Request, user=Depends(admin), db: Session = Depends(get_db)):
    with request.app.state.audit.coordinated():
        locked_authority(db, request, user, user.id)
        row = db.scalar(select(ServiceType).where(ServiceType.id == service_id).with_for_update().execution_options(populate_existing=True))
        if not row:
            raise ApiError(404, 'SERVICE_NOT_FOUND', 'Service not found.')
        if row.version != body.expected_version:
            raise ApiError(409, 'VERSION_CONFLICT', 'Service configuration changed. Reload before saving.')
        before, old = row.version, json.loads(json.dumps(row.settings or {}))
        row.settings = {**(row.settings or {}), 'contact_hours_before': body.hours}
        touch(row)
        row.updated_by = user.id
        request.app.state.audit.commit(db, actor=user.id, target={'resource': 'service_types', 'id': str(row.id)}, previous_status=None, new_status=None,
                                       previous_version=before, new_version=row.version, full_reason=None, previous_decision_evidence={'settings': old},
                                       trace_id=request.state.trace_id)
    return window_out(row)
