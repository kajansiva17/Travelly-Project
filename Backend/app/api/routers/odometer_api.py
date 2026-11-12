"""Odometer photo proof at trip start and finish (owner decision 13 Nov 2026). Rules: app/services/odometer_proof.py.

    POST /trips/{trip_id}/odometer-session          the trip's operator opens the camera: one-time capture code (10 min)
    POST /trips/{trip_id}/odometer-photo            multipart: capture_code, stage, typed_km, latitude, longitude,
                                                    [accuracy_m], file -> MATCH / MISMATCH / UNREADABLE / NOT_CHECKED
    GET  /trips/{trip_id}/odometer-proof            readings, distance and photo availability for the trip's operator,
                                                    Owner and Admin, and the Passenger of a private hire
    GET  /trips/{trip_id}/odometer-photos/{stage}   the photo itself (same people), until it is deleted after 7 days
"""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile
from app.api.routers.api import current
from app.core.config import get_settings
from app.core.errors import ApiError
from app.dependencies.database import get_db
from app.models import UserRole
from app.models.hire_models import Booking, Trip
from app.models.review_models import Vehicle
from app.services import odometer_proof as proof

router = APIRouter(prefix='/api/v1', tags=['odometer'])
RUNNING = ('IN_PROGRESS', 'BREAKDOWN', 'ASSISTANCE_REQUIRED')


class Session_(BaseModel):
    model_config = ConfigDict(extra='forbid')
    stage: Literal['START', 'END']


def operated(db, trip_id, user, stage):
    trip = db.get(Trip, trip_id)
    if not trip or trip.driver_user_id != user.id:
        raise ApiError(404, 'TRIP_NOT_FOUND', 'Trip not found.')
    if stage == 'START' and not (trip.status == 'READY' and trip.assignment_status == 'ACCEPTED'):
        raise ApiError(409, 'TRIP_NOT_READY', 'Only an accepted trip that has not started takes a start photo.')
    if stage == 'END' and trip.status not in RUNNING:
        raise ApiError(409, 'TRIP_NOT_READY', 'Only a running trip takes a finish photo.')
    return trip


def settings_of(request):
    return request.app.state.settings


@router.post('/trips/{trip_id}/odometer-session')
def open_camera(trip_id: UUID, body: Session_, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    trip = operated(db, trip_id, user, body.stage)
    request.app.state.store.rate(f'odometer-session:{user.id}', 30, 600)
    code, until = proof.new_code(request.app.state.store, trip.id, user.id, body.stage)
    vehicle = db.get(Vehicle, trip.vehicle_id)
    floor = trip.start_odometer_km if body.stage == 'END' else (vehicle.current_odometer_km if vehicle else None)
    record = proof.read_record(settings_of(request), trip.id, body.stage) or {}
    return {'capture_code': code, 'expires_at': until.isoformat(), 'stage': body.stage,
            'minimum_km': None if floor is None else str(floor), 'tries_unreadable': record.get('tries_unreadable', 0),
            'unreadable_tries_allowed': settings_of(request).odometer_unreadable_tries,
            'photo_required': settings_of(request).odometer_photo_required}


def number(value, field, low=None, high=None):
    try:
        out = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        raise ApiError(422, 'VALIDATION_ERROR', f'Enter a valid {field}.') from None
    if not out.is_finite() or (low is not None and out < low) or (high is not None and out > high):
        raise ApiError(422, 'VALIDATION_ERROR', f'Enter a valid {field}.')
    return out


@router.post('/trips/{trip_id}/odometer-photo')
async def take_photo(trip_id: UUID, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    allowed = {'capture_code', 'stage', 'typed_km', 'latitude', 'longitude', 'accuracy_m', 'file'}
    async with request.form(max_files=1, max_fields=7, max_part_size=8192) as form:
        pairs = list(form.multi_items())
        names = [k for k, _ in pairs]
        if len(set(names)) != len(names) or not set(names) <= allowed or not isinstance(form.get('file'), UploadFile) \
                or not {'capture_code', 'stage', 'typed_km', 'latitude', 'longitude'} <= set(names):
            raise ApiError(422, 'VALIDATION_ERROR', 'Send capture_code, stage, typed_km, latitude, longitude and one photo.')
        return await run_in_threadpool(place, trip_id, form, request, user, db)


def place(trip_id, form, request, user, db):
    settings = settings_of(request)
    stage = form.get('stage')
    if stage not in proof.STAGES:
        raise ApiError(422, 'VALIDATION_ERROR', 'stage must be START or END.')
    trip = operated(db, trip_id, user, stage)
    typed = number(form.get('typed_km'), 'odometer reading', Decimal('0'), Decimal('99999999999'))
    if typed != typed.quantize(Decimal('0.1')):
        raise ApiError(422, 'VALIDATION_ERROR', 'Enter the odometer with at most one decimal place.')
    lat = number(form.get('latitude'), 'latitude', Decimal('-90'), Decimal('90'))
    lng = number(form.get('longitude'), 'longitude', Decimal('-180'), Decimal('180'))
    accuracy = number(form.get('accuracy_m'), 'location accuracy', Decimal('0'), Decimal('100000')) if form.get('accuracy_m') else None
    request.app.state.store.rate(f'odometer-photo:{user.id}', 20, 600)
    proof.use_code(request.app.state.store, form.get('capture_code'), trip.id, user.id, stage)
    if stage == 'START':
        proof.below_last(db.get(Vehicle, trip.vehicle_id), typed)
        booking = db.get(Booking, trip.booking_id) if trip.booking_id else None
        stops = ((booking.itinerary_snapshot or {}).get('itinerary') or {}).get('stops') if booking else None
        if stops:
            pickup = stops[0]['place']
            away = proof.distance_km(float(lat), float(lng), float(pickup['latitude']), float(pickup['longitude']))
            if away > settings.odometer_pickup_radius_km:
                raise ApiError(422, 'NOT_AT_PICKUP', f'Take the start photo at the pickup point (you are {away:.1f} km away).')
    elif trip.start_odometer_km is not None and typed < trip.start_odometer_km:
        raise ApiError(422, 'ODOMETER_BELOW_START', f'The reading is lower than the start reading ({trip.start_odometer_km} km).')
    jpeg = proof.clean_photo(form.get('file'))
    read, engine = proof.read_odometer(get_settings(), request.app.state.store, jpeg)
    before = proof.read_record(settings, trip.id, stage) or {}
    tries = before.get('tries_unreadable', 0) + (1 if engine and read is None else 0)
    result, can_continue = proof.judge(typed, read, engine, tries, settings)
    now = datetime.now(timezone.utc)
    record = {'stage': stage, 'typed_km': str(typed), 'read_km': None if read is None else str(read), 'result': result,
              'can_continue': can_continue, 'tries_unreadable': tries, 'attempts': before.get('attempts', 0) + 1,
              'engine': engine, 'taken_at': now.isoformat(), 'taken_by': str(user.id), 'photo_available': True,
              'latitude': str(lat), 'longitude': str(lng), **({'accuracy_m': str(accuracy)} if accuracy is not None else {})}
    proof.write_record(settings, trip.id, stage, record, jpeg)
    return {'stage': stage, 'result': result, 'typed_km': str(typed), 'read_km': record['read_km'],
            'can_continue': can_continue, 'tries_unreadable': tries,
            'unreadable_tries_allowed': settings.odometer_unreadable_tries, 'message': MESSAGES[result]}


MESSAGES = {
    'MATCH': 'The photo matches the reading.',
    'MISMATCH': 'The photo shows a different reading. Check the number you typed, or take the photo again.',
    'UNREADABLE': 'The odometer could not be read from the photo. Take it again with the numbers clear and well lit.',
    'NOT_CHECKED': 'The photo is saved as proof. It could not be checked automatically right now.',
}


def viewer(db, trip_id, user):
    trip = db.get(Trip, trip_id)
    if not trip:
        raise ApiError(404, 'TRIP_NOT_FOUND', 'Trip not found.')
    if user.id in (trip.driver_user_id, trip.operating_owner_user_id):
        return trip
    if trip.booking_id and not trip.scheduled_trip_id:
        booking = db.get(Booking, trip.booking_id)
        if booking and booking.passenger_user_id == user.id:
            return trip
    if db.scalar(select(UserRole.id).where(UserRole.user_id == user.id, UserRole.role_code == 'ADMIN',
                                           UserRole.approval_status == 'APPROVED')):
        return trip
    raise ApiError(404, 'TRIP_NOT_FOUND', 'Trip not found.')


def stage_out(record, trip_reading, stage, trip_id):
    if record is None and trip_reading is None:
        return None
    record = record or {}
    available = bool(record.get('photo_available'))
    return {'reading_km': None if trip_reading is None else str(trip_reading), 'typed_km': record.get('typed_km'),
            'read_km': record.get('read_km'), 'result': record.get('result'), 'taken_at': record.get('taken_at'),
            'photo_available': available, 'photo_deleted_at': record.get('photo_deleted_at'),
            'photo_url': f'/api/v1/trips/{trip_id}/odometer-photos/{stage}' if available else None}


@router.get('/trips/{trip_id}/odometer-proof')
def read_proof(trip_id: UUID, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    trip = viewer(db, trip_id, user)
    settings = settings_of(request)
    proof.forget_photo(settings, trip)
    start, end = (proof.read_record(settings, trip.id, s) for s in proof.STAGES)
    keep_until = None
    if trip.actual_end_at:
        from datetime import timedelta
        keep_until = (trip.actual_end_at + timedelta(days=settings.odometer_photo_keep_days)).isoformat()
    return {'trip_id': str(trip.id), 'status': trip.status,
            'start': stage_out(start, trip.start_odometer_km, 'START', trip.id),
            'end': stage_out(end, trip.end_odometer_km, 'END', trip.id),
            'distance_km': None if trip.calculated_distance_km is None else str(trip.calculated_distance_km),
            'photos_kept_until': keep_until, 'photos_kept_days': settings.odometer_photo_keep_days}


@router.get('/trips/{trip_id}/odometer-photos/{stage}')
def read_photo(trip_id: UUID, stage: Literal['START', 'END'], request: Request, user=Depends(current), db: Session = Depends(get_db)):
    trip = viewer(db, trip_id, user)
    settings = settings_of(request)
    proof.forget_photo(settings, trip)
    _, photo, _ = proof.files(settings, trip.id, stage)
    if not photo.exists():
        raise ApiError(404, 'PHOTO_NOT_FOUND', 'The photo is not available (photos are kept for 7 days after the trip).')
    return Response(photo.read_bytes(), media_type='image/jpeg',
                    headers={'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff'})
