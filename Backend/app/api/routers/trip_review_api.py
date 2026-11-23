"""Trip reviews. After a finished trip the Passenger rates it once; the Owner of the vehicle reads the reviews and may reply once.
 * Only the Passenger of the booking can review, only when the trip is COMPLETED, once per trip; a review is never edited or deleted.
 * `rating` (1-5) is for the vehicle and the service; `driver_rating` (1-5, optional) only when the trip had a Driver. The comment is optional (500 characters).
 * The Owner sees the Passenger's first name only. One reply per review (300 characters)."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.api.routers.api import current, require_role
from app.core.errors import ApiError
from app.dependencies.database import get_db
from app.models import User
from app.models.hire_models import Booking, Trip
from app.models.review_models import Vehicle
from app.models.trip_review_models import TripReview

router = APIRouter(prefix='/api/v1', tags=['Trip reviews'])
EDIT_DAYS = 7   # the Passenger may change or delete a review for 7 days; after that it is locked


class NewReview(BaseModel):
    rating: int = Field(ge=1, le=5)
    driver_rating: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = Field(default=None, max_length=500)


class Reply(BaseModel):
    text: str = Field(min_length=1, max_length=300)


def review_out(row, vehicle=None, trip=None, passenger=None):
    out = {'id': str(row.id), 'trip_id': str(row.trip_id), 'rating': row.rating, 'driver_rating': row.driver_rating, 'comment': row.comment,
           'reply': row.reply, 'created_at': row.created_at.isoformat(), 'replied_at': row.replied_at.isoformat() if row.replied_at else None,
           'edited_at': row.edited_at.isoformat() if row.edited_at else None}
    if vehicle is not None:
        out['vehicle_id'] = str(row.vehicle_id)
        out['vehicle'] = vehicle.registration_number
    if trip is not None:
        out['trip_reference'] = trip.trip_reference
    if passenger is not None:
        out['passenger'] = (passenger.display_name or passenger.full_name or '').split(' ')[0] or None
    return out


def editable(row):
    return datetime.now(timezone.utc) < row.created_at + timedelta(days=EDIT_DAYS)


def trip_and_booking(db, trip_id):
    trip = db.get(Trip, trip_id)
    booking = db.get(Booking, trip.booking_id) if trip and trip.booking_id else None
    if not trip or not booking:
        raise ApiError(404, 'TRIP_NOT_FOUND', 'This trip was not found.')
    return trip, booking


@router.get('/trips/{trip_id}/review')
def trip_review(trip_id: UUID, user=Depends(current), db: Session = Depends(get_db)):
    trip, booking = trip_and_booking(db, trip_id)
    if user.id not in (booking.passenger_user_id, booking.owner_user_id, trip.operating_owner_user_id):
        raise ApiError(404, 'TRIP_NOT_FOUND', 'This trip was not found.')
    row = db.scalar(select(TripReview).where(TripReview.trip_id == trip.id))
    mine = user.id == booking.passenger_user_id
    return {'review': review_out(row) if row else None, 'can_review': bool(mine and not row and trip.status == 'COMPLETED'),
            'can_edit': bool(mine and row and editable(row)), 'edit_days': EDIT_DAYS, 'has_driver': trip.driver_user_id is not None}


@router.post('/trips/{trip_id}/review', status_code=201)
def write_review(trip_id: UUID, body: NewReview, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    request.app.state.store.rate(f'review:{user.id}', 20, 3600)
    trip, booking = trip_and_booking(db, trip_id)
    if booking.passenger_user_id != user.id:
        raise ApiError(404, 'TRIP_NOT_FOUND', 'This trip was not found.')
    if trip.status != 'COMPLETED':
        raise ApiError(409, 'TRIP_NOT_FINISHED', 'You can review a trip after it has finished.')
    if body.driver_rating is not None and trip.driver_user_id is None:
        raise ApiError(422, 'VALIDATION_ERROR', 'This trip had no Driver to rate.', [{'field': 'driver_rating', 'message': 'This trip had no Driver.'}])
    comment = (body.comment or '').strip() or None
    row = TripReview(trip_id=trip.id, booking_id=booking.id, vehicle_id=trip.vehicle_id, passenger_user_id=user.id,
                     owner_user_id=trip.operating_owner_user_id or booking.owner_user_id, driver_user_id=trip.driver_user_id,
                     rating=body.rating, driver_rating=body.driver_rating, comment=comment)
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ApiError(409, 'REVIEW_EXISTS', 'You have already reviewed this trip.')
    return review_out(row)


def own_review(db, trip_id, user):
    trip, booking = trip_and_booking(db, trip_id)
    row = db.scalar(select(TripReview).where(TripReview.trip_id == trip.id))
    if booking.passenger_user_id != user.id or not row:
        raise ApiError(404, 'REVIEW_NOT_FOUND', 'This review was not found.')
    if not editable(row):
        raise ApiError(409, 'REVIEW_LOCKED', f'A review can be changed or deleted for {EDIT_DAYS} days only.')
    return trip, row


@router.put('/trips/{trip_id}/review')
def change_review(trip_id: UUID, body: NewReview, user=Depends(current), db: Session = Depends(get_db)):
    trip, row = own_review(db, trip_id, user)
    if body.driver_rating is not None and row.driver_user_id is None:
        raise ApiError(422, 'VALIDATION_ERROR', 'This trip had no Driver to rate.', [{'field': 'driver_rating', 'message': 'This trip had no Driver.'}])
    row.rating, row.driver_rating = body.rating, body.driver_rating
    row.comment = (body.comment or '').strip() or None
    row.edited_at = datetime.now(timezone.utc)
    db.commit()
    return review_out(row)


@router.delete('/trips/{trip_id}/review')
def delete_review(trip_id: UUID, user=Depends(current), db: Session = Depends(get_db)):
    trip, row = own_review(db, trip_id, user)
    db.delete(row)
    db.commit()
    return {'deleted': True}


@router.get('/owners/me/reviews')
def owner_reviews(user=Depends(current), db: Session = Depends(get_db)):
    require_role(db, user, 'OWNER')
    rows = db.scalars(select(TripReview).where(TripReview.owner_user_id == user.id).order_by(TripReview.created_at.desc()).limit(300)).all()
    vehicles = {v.id: v for v in db.scalars(select(Vehicle).where(Vehicle.id.in_({r.vehicle_id for r in rows})))} if rows else {}
    trips = {t.id: t for t in db.scalars(select(Trip).where(Trip.id.in_({r.trip_id for r in rows})))} if rows else {}
    people = {u.id: u for u in db.scalars(select(User).where(User.id.in_({r.passenger_user_id for r in rows})))} if rows else {}
    per_vehicle = {}
    for r in rows:
        count, total = per_vehicle.get(r.vehicle_id, (0, 0))
        per_vehicle[r.vehicle_id] = (count + 1, total + r.rating)
    average = lambda total, count: format((Decimal(total) / Decimal(count)).quantize(Decimal('0.1')), '.1f')
    return {'count': len(rows), 'average': average(sum(r.rating for r in rows), len(rows)) if rows else None,
            'vehicles': [{'id': str(vid), 'registration': vehicles[vid].registration_number, 'count': c, 'average': average(t, c)} for vid, (c, t) in per_vehicle.items()],
            'items': [review_out(r, vehicles[r.vehicle_id], trips.get(r.trip_id), people.get(r.passenger_user_id)) for r in rows]}


@router.post('/reviews/{review_id}/reply')
def reply(review_id: UUID, body: Reply, user=Depends(current), db: Session = Depends(get_db)):
    row = db.get(TripReview, review_id)
    if not row or row.owner_user_id != user.id:
        raise ApiError(404, 'REVIEW_NOT_FOUND', 'This review was not found.')
    text = body.text.strip()
    if not text:
        raise ApiError(422, 'VALIDATION_ERROR', 'Write a reply.', [{'field': 'text', 'message': 'This is required.'}])
    row.reply, row.replied_at = text, datetime.now(timezone.utc)   # a second reply replaces the first
    db.commit()
    return review_out(row)


@router.delete('/reviews/{review_id}/reply')
def delete_reply(review_id: UUID, user=Depends(current), db: Session = Depends(get_db)):
    row = db.get(TripReview, review_id)
    if not row or row.owner_user_id != user.id:
        raise ApiError(404, 'REVIEW_NOT_FOUND', 'This review was not found.')
    row.reply, row.replied_at = None, None
    db.commit()
    return review_out(row)
