"""Self-drive rental (owner decision 14 Nov 2026). The Passenger rents the vehicle and drives it; no Driver is assigned.

Price = day rate x booked days
        + km beyond the free km (free km per day x booked days, pooled over the rental) x extra km rate
        + late hours (after a 1 hour grace past the booked end) x late hour rate.
The Owner photographs the odometer when handing the vehicle over and when taking it back (the existing 03O odometer
photo endpoints work on the rental trip: the Owner is the trip operator). The bill is worked out from those two
readings and the rates the Owner saved for this vehicle. Deposit, fuel and damage are settled between Owner and renter.

    PUT  /vehicles/{id}/rental            Owner saves this vehicle's rental rates (and turns rental on or off)
    GET  /vehicles/{id}/rental            the saved rates
    POST /rentals/search                  Passenger: vehicles free for the dates, with the rates
    POST /rentals                         Passenger: ask to rent (licence number)
    POST /rentals/{id}/accept | decline   Owner
    POST /rentals/{id}/cancel             Passenger or Owner, before handover
    POST /rentals/{id}/handover           Owner: licence checked, start odometer -> rental starts
    POST /rentals/{id}/return             Owner: end odometer -> bill, rental completed, payment opens
    POST /rentals/{id}/confirm            Passenger: confirms the handover or the return (a record, not a gate)
Payment after the return uses the normal booking payment endpoints (online or cash collected by the Owner).
"""
import copy
import math
import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, Request
from pydantic import Field, StrictBool, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.routers.api import current, require_role, touch, allowed_account
from app.api.routers.hire_api import commission_gate, odometer_rules, safe_vehicle
from app.api.routers.rate_api import owned
from app.api.routers.review_api import locked_authority
from app.core.errors import ApiError
from app.dependencies.database import get_db
from app.models import User
from app.models.hire_models import Booking, Trip
from app.models.rate_models import ServiceType, VehicleService
from app.models.review_models import Vehicle
from app.schemas.rate_schemas import Amount, RateModel
from app.services.hire_services import audited, booking_summary, digest, eligible_vehicle, no_conflict, notify
from app.services.vehicle_odometer import advance_odometer

router = APIRouter(prefix='/api/v1', tags=['Rental'])
RENTAL_CODE = 'SELF_DRIVE_RENTAL'
LATE_GRACE_HOURS = 1
MAX_DAYS = 30
CENT = Decimal('.01')


def money(value):
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


class Extra(RateModel):
    """An optional paid extra the Owner offers with this vehicle (child seat, GPS, ...). Charged per rental day or once."""
    id: UUID
    name: str = Field(min_length=1, max_length=80)
    price: Amount
    per: Literal['DAY', 'ONCE']

    @field_validator('price')
    @classmethod
    def sensible_price(cls, value):
        if not 0 < value <= Decimal('9999999.99') or -value.as_tuple().exponent > 2: raise ValueError('Enter a price above zero with at most two decimals.')
        return value


class RentalTerms(RateModel):
    expected_version: int = Field(strict=True, ge=0)
    enabled: StrictBool
    day_rate: Amount
    free_km_per_day: Amount
    extra_km_rate: Amount
    late_hour_rate: Amount
    max_days: int = Field(default=14, strict=True, ge=1, le=MAX_DAYS)
    notes: str | None = Field(default=None, max_length=500)   # deposit, fuel and damage rules, shown to the renter
    cash_accepted: StrictBool | None = None
    extras: list[Extra] = Field(default_factory=list, max_length=10)

    @field_validator('extras')
    @classmethod
    def unique_extras(cls, value):
        if len({e.id for e in value}) != len(value): raise ValueError('Extra identifiers must be unique.')
        return value

    @field_validator('day_rate')
    @classmethod
    def day_rate_positive(cls, value):
        if not 0 < value <= Decimal('9999999.99'): raise ValueError('Enter a day rate above zero.')
        return value

    @field_validator('free_km_per_day', 'extra_km_rate', 'late_hour_rate')
    @classmethod
    def bounded(cls, value):
        if value > Decimal('9999999.99'): raise ValueError('That amount is too large.')
        return value

    @field_validator('day_rate', 'extra_km_rate', 'late_hour_rate')
    @classmethod
    def cents(cls, value):
        if -value.as_tuple().exponent > 2: raise ValueError('Use at most two decimals.')
        return value


class RentalSearch(RateModel):
    start_at: datetime
    days: int = Field(strict=True, ge=1, le=MAX_DAYS)


class RentalRequest(RateModel):
    vehicle_id: UUID
    start_at: datetime
    days: int = Field(strict=True, ge=1, le=MAX_DAYS)
    licence_number: str = Field(min_length=5, max_length=30, pattern=r'^[A-Za-z0-9 /-]+$')
    extras: list[UUID] = Field(default_factory=list, max_length=10)   # ids of the Owner's extras the renter wants
    idempotency_key: str = Field(min_length=16, max_length=80, pattern=r'^[A-Za-z0-9_-]+$')


class Versioned(RateModel):
    expected_version: int = Field(strict=True, ge=1)


class Cancel(Versioned):
    reason: str = Field(min_length=1, max_length=500)


class Handover(Versioned):
    start_odometer_km: Amount
    licence_checked: Literal[True]
    note: str | None = Field(default=None, max_length=500)   # fuel level, deposit taken, existing marks

    @field_validator('start_odometer_km')
    @classmethod
    def reading(cls, value):
        if value > Decimal('99999999999.9') or value % Decimal('.1'): raise ValueError('Use the odometer in km with at most one decimal place.')
        return value


class Return(Versioned):
    end_odometer_km: Amount
    note: str | None = Field(default=None, max_length=500)   # fuel level, damage found

    @field_validator('end_odometer_km')
    @classmethod
    def reading(cls, value):
        if value > Decimal('99999999999.9') or value % Decimal('.1'): raise ValueError('Use the odometer in km with at most one decimal place.')
        return value


class Confirm(RateModel):
    stage: Literal['HANDOVER', 'RETURN']


# ------------------------------------------------------------------------------------------------ pricing

def terms_view(terms):
    return {k: terms[k] for k in ('day_rate', 'free_km_per_day', 'extra_km_rate', 'late_hour_rate', 'max_days', 'notes', 'extras') if k in terms}


def extra_amount(extra, days):
    return money(Decimal(extra['price']) * (days if extra['per'] == 'DAY' else 1))


def estimate(terms, days, chosen=()):
    base = money(Decimal(terms['day_rate']) * days)
    extras = sum((extra_amount(e, days) for e in chosen), Decimal(0))
    return {'days': days, 'day_rate': terms['day_rate'], 'base_price': format(base + extras, '.2f'), 'extras_price': format(extras, '.2f'),
            'free_km_total': format(Decimal(terms['free_km_per_day']) * days, 'f'), 'extra_km_rate': terms['extra_km_rate'],
            'late_hour_rate': terms['late_hour_rate'], 'late_grace_hours': LATE_GRACE_HOURS, 'currency': 'LKR'}


def bill(terms, days, start_odometer, end_odometer, started_at, returned_at, chosen=()):
    """The final amount from the two photographed readings. Returning early is not refunded; the booked days are charged."""
    lines = []
    def line(code, label, quantity, rate):
        lines.append({'code': code, 'label': label, 'quantity': str(quantity), 'rate': str(rate), 'amount': str(money(quantity * rate)), 'kind': 'CHARGE'})
    km = Decimal(end_odometer) - Decimal(start_odometer)
    free = Decimal(terms['free_km_per_day']) * days
    line('DAYS', f'{days} day rental', Decimal(days), Decimal(terms['day_rate']))
    line('EXTRA_KM', f'Distance beyond {free:f} free km', max(Decimal(0), km - free), Decimal(terms['extra_km_rate']))
    over = (returned_at - started_at).total_seconds() / 3600 - 24 * days - LATE_GRACE_HOURS
    late_hours = Decimal(max(0, math.ceil(over)))
    line('LATE', 'Hours returned late', late_hours, Decimal(terms['late_hour_rate']))
    for number, extra in enumerate(chosen, 1):
        quantity = Decimal(days if extra['per'] == 'DAY' else 1)
        line(f'EXTRA_{number}', extra['name'], quantity, Decimal(extra['price']))
    total = sum((Decimal(x['amount']) for x in lines), Decimal(0)).quantize(CENT)
    if total > Decimal('9999999999.99'): raise ApiError(422, 'PRICING_UNAVAILABLE', 'The calculated total exceeds the supported booking amount.')
    return {'currency': 'LKR', 'breakdown': lines, 'total': format(total, '.2f'), 'distance_km': format(km, 'f'), 'free_km': format(free, 'f'),
            'late_hours': str(late_hours), 'policy': 'TRAVELLY_RENTAL_2026_11_14'}


# ------------------------------------------------------------------------------------------------ helpers

def rental_service(db, user=None):
    service = db.scalar(select(ServiceType).where(ServiceType.code == RENTAL_CODE))
    if service is None and user is not None:
        service = ServiceType(code=RENTAL_CODE, name='Self-drive rental', category='RENTAL', is_active=True, display_order=50,
                              default_pricing_basis='TIME', settings={'commission_percent': '0.00'}, created_by=user.id, updated_by=user.id)
        db.add(service); db.flush()
    return service


def rental_terms(row):
    return ((row.owner_terms or {}).get('rental') or None) if row else None


def rental_row(db, vehicle_id, service, *, enabled_only=True):
    query = select(VehicleService).where(VehicleService.vehicle_id == vehicle_id, VehicleService.service_type_id == service.id)
    if enabled_only: query = query.where(VehicleService.is_enabled.is_(True))
    return db.scalar(query)


def terms_out(row):
    terms = rental_terms(row)
    return {'service_type_id': str(row.service_type_id), 'version': row.version, 'enabled': row.is_enabled, 'currency': row.currency,
            **(terms_view(terms) if terms else {}), 'cash_accepted': (row.owner_terms.get('cash') or {}).get('accepted') is True}


def rental_booking(db, request, booking_id, user, expected, *, party):
    """Lock the booking and vehicle; `party` is OWNER, PASSENGER or ANY (Owner or Passenger)."""
    before = db.get(Booking, booking_id)
    if not before or before.booking_type != 'RENTAL' or user.id not in (before.owner_user_id, before.passenger_user_id) \
            or (party == 'OWNER' and user.id != before.owner_user_id) or (party == 'PASSENGER' and user.id != before.passenger_user_id):
        raise ApiError(404, 'BOOKING_NOT_FOUND', 'Booking not found.')
    locked_authority(db, request, user, before.owner_user_id if user.id != before.owner_user_id else before.passenger_user_id, require_admin=False)
    vehicle = db.scalar(select(Vehicle).where(Vehicle.id == before.vehicle_id).with_for_update().execution_options(populate_existing=True))
    row = db.scalar(select(Booking).where(Booking.id == booking_id).with_for_update().execution_options(populate_existing=True))
    if expected is not None and row.version != expected: raise ApiError(409, 'VERSION_CONFLICT', 'Booking changed. Reload before retrying.')
    return row, vehicle


def rental_trip(db, row):
    return db.scalar(select(Trip).where(Trip.booking_id == row.id, Trip.status != 'CANCELLED').order_by(Trip.created_at.desc()).limit(1).with_for_update()
                     .execution_options(populate_existing=True))


def finish(request, db, user, row, previous, reason, title, message):
    notify(db, row, title, message)
    audited(request, db, user, row, previous, reason)
    return booking_summary(row)


def aware(value):
    if value.tzinfo is None: raise ApiError(422, 'VALIDATION_ERROR', 'Send the time with its time zone.')
    return value


# ------------------------------------------------------------------------------------------------ Owner: rates

@router.put('/vehicles/{vehicle_id}/rental')
def save_rental(vehicle_id: UUID, body: RentalTerms, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    owned(db, request, user, vehicle_id, lock=True)
    service = rental_service(db, user)
    if not service.is_active: raise ApiError(409, 'SERVICE_UNAVAILABLE', 'Rental is switched off by Admin.')
    row = rental_row(db, vehicle_id, service, enabled_only=False)
    if body.expected_version != (row.version if row else 0):
        raise ApiError(409, 'VERSION_CONFLICT', 'Rental rates changed. Reload them before editing again.')
    saved = {'day_rate': str(body.day_rate), 'free_km_per_day': str(body.free_km_per_day), 'extra_km_rate': str(body.extra_km_rate),
             'late_hour_rate': str(body.late_hour_rate), 'max_days': body.max_days, 'notes': body.notes,
             'extras': [{'id': str(e.id), 'name': e.name, 'price': str(e.price), 'per': e.per} for e in body.extras]}
    terms = {**(row.owner_terms if row else {}), 'schema_version': 2, 'service_scope': 'RENTAL', 'policy': 'TRAVELLY_RENTAL_2026_11_14', 'rental': saved}
    if body.cash_accepted is not None:
        terms['cash'] = {'accepted': body.cash_accepted, 'collection_stage': 'END'}
    if row:
        row.is_enabled, row.owner_terms, row.pricing_basis = body.enabled, terms, 'TIME'
        row.base_price = row.price_per_km = row.price_per_hour = None
        row.minimum_hire_hours = row.minimum_hire_km = None
        row.currency = 'LKR'; row.updated_by = user.id; touch(row)
    else:
        row = VehicleService(vehicle_id=vehicle_id, service_type_id=service.id, is_enabled=body.enabled, pricing_basis='TIME', currency='LKR',
                             owner_terms=terms, created_by=user.id, updated_by=user.id)
        db.add(row)
    db.commit()
    return {**terms_out(row), 'message': 'Rental rates saved. New rentals use these rates; accepted rentals keep theirs.'}


@router.get('/vehicles/{vehicle_id}/rental')
def read_rental(vehicle_id: UUID, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    owned(db, request, user, vehicle_id)
    service = rental_service(db)
    row = rental_row(db, vehicle_id, service, enabled_only=False) if service else None
    return terms_out(row) if row and rental_terms(row) else {'service_type_id': str(service.id) if service else None, 'version': 0, 'enabled': False}


# ------------------------------------------------------------------------------------------------ Passenger: find and ask

def offered(request, db, vehicle, service, start, days):
    """The rental rates of a vehicle that can be rented for these dates, or None."""
    row = rental_row(db, vehicle.id, service)
    terms = rental_terms(row)
    if not terms or days > int(terms.get('max_days', MAX_DAYS)): return None
    eligible_vehicle(db, vehicle, public=True, at=start)
    commission_gate(request, db, vehicle)
    no_conflict(db, vehicle.id, start, start + timedelta(days=days))
    return terms


@router.post('/rentals/search')
def search_rentals(body: RentalSearch, request: Request, db: Session = Depends(get_db)):
    start = aware(body.start_at)
    if start <= datetime.now(timezone.utc): raise ApiError(422, 'ITINERARY_IN_PAST', 'Choose a future pickup time.')
    service = rental_service(db)
    items = []
    if service and service.is_active:
        for vehicle in db.scalars(select(Vehicle).where(Vehicle.is_published.is_(True)).order_by(Vehicle.id).limit(100)).all():
            try: terms = offered(request, db, vehicle, service, start, body.days)
            except ApiError as exc:
                if exc.status == 503: raise
                continue
            if terms:
                items.append({**safe_vehicle(vehicle, db.get(User, vehicle.owner_user_id)), 'rental': {**terms_view(terms), **estimate(terms, body.days)}})
    return {'items': items, 'message': 'The final price is worked out when the vehicle is returned, from the odometer readings and these rates.'}


@router.post('/rentals', status_code=201)
def request_rental(body: RentalRequest, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    require_role(db, user, 'PASSENGER')
    start = aware(body.start_at)
    if start <= datetime.now(timezone.utc): raise ApiError(422, 'ITINERARY_IN_PAST', 'Choose a future pickup time.')
    def same(existing):
        return (existing.booking_type == 'RENTAL' and existing.passenger_user_id == user.id and existing.vehicle_id == body.vehicle_id
                and existing.start_at == start and (existing.itinerary_snapshot.get('rental') or {}).get('days') == body.days
                and (existing.itinerary_snapshot.get('rental') or {}).get('extras', []) == [str(i) for i in body.extras])
    existing = db.scalar(select(Booking).where(Booking.idempotency_key == body.idempotency_key))
    if existing:
        if not same(existing): raise ApiError(409, 'IDEMPOTENCY_CONFLICT', 'This request identifier was already used for a different request.')
        return booking_summary(existing)
    with request.app.state.audit.coordinated():
        locked_authority(db, request, user, user.id, require_admin=False)
        require_role(db, user, 'PASSENGER')
        if user.email_login_required and not user.email_verified_at:
            raise ApiError(403, 'EMAIL_VERIFICATION_REQUIRED', 'Verify your email before renting.')
        vehicle = db.scalar(select(Vehicle).where(Vehicle.id == body.vehicle_id).with_for_update())
        if not vehicle: raise ApiError(404, 'VEHICLE_NOT_FOUND', 'Vehicle not found.')
        if vehicle.owner_user_id == user.id: raise ApiError(409, 'OWN_VEHICLE', 'You cannot rent your own vehicle.')
        existing = db.scalar(select(Booking).where(Booking.idempotency_key == body.idempotency_key))
        if existing:
            if not same(existing): raise ApiError(409, 'IDEMPOTENCY_CONFLICT', 'The request identifier belongs to a different request.')
            return booking_summary(existing)
        service = rental_service(db)
        if not service or not service.is_active: raise ApiError(409, 'SERVICE_UNAVAILABLE', 'Rental is not available right now.')
        terms = offered(request, db, vehicle, service, start, body.days)
        if not terms: raise ApiError(409, 'VEHICLE_NOT_AVAILABLE', 'This vehicle is not offered for rental for these dates.')
        offered_extras = {e['id']: e for e in terms.get('extras', [])}
        if len(set(body.extras)) != len(body.extras) or any(str(i) not in offered_extras for i in body.extras):
            raise ApiError(422, 'EXTRA_UNAVAILABLE', 'Choose only extras this Owner offers, each once.')
        chosen = [offered_extras[str(i)] for i in body.extras]
        quote = estimate(terms, body.days, chosen)
        row = Booking(booking_reference='BKG-' + secrets.token_hex(10).upper(), passenger_user_id=user.id, booking_type='RENTAL',
                      service_type_id=service.id, requested_owner_user_id=vehicle.owner_user_id, owner_user_id=vehicle.owner_user_id,
                      vehicle_id=vehicle.id, start_at=start, end_at=start + timedelta(days=body.days), passenger_count=1,
                      status='REQUESTED', assurance_type='STANDARD_HIRE', currency='LKR', quoted_amount=Decimal(quote['base_price']),
                      idempotency_key=body.idempotency_key, created_by=user.id, updated_by=user.id,
                      itinerary_snapshot={'rental': {'days': body.days, 'start_at': start.isoformat(), 'licence_number': body.licence_number.strip(), 'extras': [str(i) for i in body.extras]}},
                      price_snapshot={'terms': copy.deepcopy(terms_view(terms)), 'estimate': quote, 'chosen_extras': copy.deepcopy(chosen)})
        row.price_snapshot = {**row.price_snapshot, 'digest': digest(row.price_snapshot)}
        db.add(row); db.flush()
        notify(db, row, 'Rental request', 'A renter asked to rent this vehicle. Accept it to reserve the vehicle for these dates.')
        request.app.state.audit.commit(db, actor=user.id, target={'resource': 'bookings', 'id': str(row.id)}, previous_status=None,
            new_status='REQUESTED', previous_version=0, new_version=1, full_reason=None, previous_decision_evidence={}, trace_id=request.state.trace_id)
    return booking_summary(row)


# ------------------------------------------------------------------------------------------------ Owner: accept, decline

@router.post('/rentals/{booking_id}/accept')
def accept_rental(booking_id: UUID, body: Versioned, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    with request.app.state.audit.coordinated():
        row, vehicle = rental_booking(db, request, booking_id, user, body.expected_version, party='OWNER')
        require_role(db, user, 'OWNER')
        if row.status != 'REQUESTED': raise ApiError(409, 'RENTAL_NOT_OPEN', 'Only a new request can be accepted.')
        if row.start_at <= datetime.now(timezone.utc): raise ApiError(409, 'RENTAL_NOT_OPEN', 'The pickup time has passed. Ask the renter to request again.')
        eligible_vehicle(db, vehicle, at=row.end_at)
        no_conflict(db, vehicle.id, row.start_at, row.end_at, exclude=row.id)
        previous = booking_summary(row)
        db.add(Trip(trip_reference='TRP-' + secrets.token_hex(10).upper(), booking_id=row.id, vehicle_id=vehicle.id, operating_owner_user_id=user.id,
                    driver_user_id=user.id, assignment_type='OWNER_SELF_DRIVE', assignment_status='ACCEPTED', status='READY',
                    scheduled_start_at=row.start_at, scheduled_end_at=row.end_at, created_by=user.id, updated_by=user.id))
        row.vehicle_committed = True; row.status = 'CONFIRMED'; row.confirmed_at = row.accepted_at = datetime.now(timezone.utc)
        return finish(request, db, user, row, previous, 'Owner accepted the rental', 'Rental accepted',
                      'The Owner accepted this rental. The vehicle is reserved for your dates.')


@router.post('/rentals/{booking_id}/decline')
def decline_rental(booking_id: UUID, body: Cancel, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    with request.app.state.audit.coordinated():
        row, vehicle = rental_booking(db, request, booking_id, user, body.expected_version, party='OWNER')
        require_role(db, user, 'OWNER')
        if row.status != 'REQUESTED': raise ApiError(409, 'RENTAL_NOT_OPEN', 'Only a new request can be declined.')
        previous = booking_summary(row)
        row.status = 'REJECTED'; row.cancellation_reason = body.reason
        return finish(request, db, user, row, previous, body.reason, 'Rental declined', 'The Owner declined this rental request.')


@router.post('/rentals/{booking_id}/cancel')
def cancel_rental(booking_id: UUID, body: Cancel, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    with request.app.state.audit.coordinated():
        row, vehicle = rental_booking(db, request, booking_id, user, body.expected_version, party='ANY')
        if row.status not in ('REQUESTED', 'CONFIRMED'):
            raise ApiError(409, 'CANCELLATION_REVIEW_REQUIRED', 'A rental that has started or finished cannot be cancelled here.')
        previous = booking_summary(row)
        row.status = 'CANCELLED'; row.vehicle_committed = False
        row.cancelled_by_user_id = user.id; row.cancelled_at = datetime.now(timezone.utc); row.cancellation_reason = body.reason
        for trip in db.scalars(select(Trip).where(Trip.booking_id == row.id).with_for_update()):
            trip.status = 'CANCELLED'; trip.assignment_status = 'CANCELLED'; touch(trip)
        return finish(request, db, user, row, previous, body.reason, 'Rental cancelled', 'This rental was cancelled and the vehicle is free again.')


# ------------------------------------------------------------------------------------------------ Owner: hand over and take back

@router.post('/rentals/{booking_id}/handover')
def hand_over(booking_id: UUID, body: Handover, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    with request.app.state.audit.coordinated():
        row, vehicle = rental_booking(db, request, booking_id, user, body.expected_version, party='OWNER')
        require_role(db, user, 'OWNER')
        trip = rental_trip(db, row)
        now = datetime.now(timezone.utc)
        if row.status != 'CONFIRMED' or trip is None or trip.status != 'READY':
            raise ApiError(409, 'RENTAL_NOT_READY', 'Only an accepted rental that has not started can be handed over.')
        if now < row.start_at - timedelta(hours=3): raise ApiError(409, 'RENTAL_NOT_READY', 'It is too early to hand the vehicle over.')
        if now >= row.end_at: raise ApiError(409, 'RENTAL_NOT_READY', 'The rental period has already ended. Cancel it and book again.')
        eligible_vehicle(db, vehicle)
        odometer_rules(request, trip, vehicle, 'START', body.start_odometer_km)
        previous = booking_summary(row)
        row.status = 'IN_PROGRESS'; trip.status = 'IN_PROGRESS'; trip.actual_start_at = now; trip.start_odometer_km = body.start_odometer_km; trip.tracking_status = 'OFF'
        touch(trip); trip.updated_by = user.id
        rental = (row.itinerary_snapshot or {}).get('rental') or {}
        row.itinerary_snapshot = {**row.itinerary_snapshot, 'rental': {**rental, 'handover': {'at': now.isoformat(), 'start_odometer_km': str(body.start_odometer_km),
                                  'licence_checked': True, 'note': body.note, 'passenger_confirmed_at': None}}}
        return finish(request, db, user, row, previous, 'Owner handed the vehicle over', 'Rental started',
                      f'The vehicle was handed over at {body.start_odometer_km} km. Please confirm the handover in the app.')


@router.post('/rentals/{booking_id}/return')
def take_back(booking_id: UUID, body: Return, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    with request.app.state.audit.coordinated():
        row, vehicle = rental_booking(db, request, booking_id, user, body.expected_version, party='OWNER')
        require_role(db, user, 'OWNER')
        trip = rental_trip(db, row)
        if row.status != 'IN_PROGRESS' or trip is None or trip.status != 'IN_PROGRESS' or trip.start_odometer_km is None:
            raise ApiError(409, 'RENTAL_NOT_READY', 'Only a rental that is in progress can be taken back.')
        if body.end_odometer_km < trip.start_odometer_km:
            raise ApiError(422, 'VALIDATION_ERROR', 'The closing odometer cannot be lower than the odometer recorded at the start.')
        odometer_rules(request, trip, None, 'END', body.end_odometer_km)
        now = datetime.now(timezone.utc)
        rental = (row.itinerary_snapshot or {}).get('rental') or {}
        final = bill(row.price_snapshot['terms'], int(rental['days']), trip.start_odometer_km, body.end_odometer_km, trip.actual_start_at, now,
                     row.price_snapshot.get('chosen_extras', []))
        previous = booking_summary(row)
        trip.actual_end_at = now; trip.end_odometer_km = body.end_odometer_km; trip.calculated_distance_km = body.end_odometer_km - trip.start_odometer_km
        advance_odometer(db, trip.vehicle_id, body.end_odometer_km, user.id, now)
        trip.status = 'COMPLETED'; trip.tracking_status = 'ENDED'; trip.completion_notes = body.note
        touch(trip); trip.updated_by = user.id
        row.status = 'COMPLETED'; row.vehicle_committed = False
        row.total_amount = row.quoted_amount = Decimal(final['total'])
        row.price_snapshot = {**row.price_snapshot, 'final': final}
        row.itinerary_snapshot = {**row.itinerary_snapshot, 'rental': {**rental, 'return': {'at': now.isoformat(), 'end_odometer_km': str(body.end_odometer_km),
                                  'note': body.note, 'passenger_confirmed_at': None}}}
        return finish(request, db, user, row, previous, 'Owner took the vehicle back; bill calculated', 'Rental completed',
                      f'The vehicle was returned. Total LKR {final["total"]} for {final["distance_km"]} km. You can pay now.')


@router.post('/rentals/{booking_id}/confirm')
def confirm_stage(booking_id: UUID, body: Confirm, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    """The renter confirms the handover or the return. It is a record for both sides; it does not block anything."""
    with request.app.state.audit.coordinated():
        row, vehicle = rental_booking(db, request, booking_id, user, None, party='PASSENGER')
        rental = (row.itinerary_snapshot or {}).get('rental') or {}
        key = 'handover' if body.stage == 'HANDOVER' else 'return'
        if key not in rental: raise ApiError(409, 'RENTAL_NOT_READY', 'The Owner has not recorded this step yet.')
        if rental[key].get('passenger_confirmed_at'): return booking_summary(row)
        previous = booking_summary(row)
        row.itinerary_snapshot = {**row.itinerary_snapshot, 'rental': {**rental, key: {**rental[key], 'passenger_confirmed_at': datetime.now(timezone.utc).isoformat()}}}
        return finish(request, db, user, row, previous, f'Renter confirmed the {key}', 'Renter confirmed',
                      'The renter confirmed the ' + ('handover.' if key == 'handover' else 'return.'))
