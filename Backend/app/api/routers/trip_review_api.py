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
from sqlalchemy.orm import Session, object_session
from app.api.routers.api import current, require_role
from app.core.errors import ApiError
from app.dependencies.database import get_db
from app.models import User
from app.models.hire_models import Booking, Notification, Trip
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


def tell(db, user_id, booking, trip, title, body):
    """An information notice about a review (type REVIEW); it opens the booking."""
    db.add(Notification(recipient_user_id=user_id, booking_id=booking.id, trip_id=trip.id, notification_type='REVIEW', channel='IN_APP',
                        title=title, body=body, action_required=False, action_payload={'booking_id': str(booking.id), 'trip_id': str(trip.id)}, status='QUEUED'))


def vehicle_ratings(db, vehicle_ids):
    """{vehicle id: {'average': '4.5', 'count': 12}} from the reviews that are not hidden; a vehicle with no review is left out."""
    if not vehicle_ids:
        return {}
    rows = db.execute(select(TripReview.vehicle_id, func.count(TripReview.id), func.avg(TripReview.rating))
                      .where(TripReview.vehicle_id.in_(list(vehicle_ids)), TripReview.hidden_at.is_(None)).group_by(TripReview.vehicle_id)).all()
    return {vid: {'average': format(Decimal(str(avg)).quantize(Decimal('0.1')), '.1f'), 'count': count} for vid, count, avg in rows}


def rating_of(vehicle):
    """The public rating of one vehicle ({'average': '4.5', 'count': 12}), or None when nobody has reviewed it yet."""
    session = object_session(vehicle)
    return vehicle_ratings(session, [vehicle.id]).get(vehicle.id) if session is not None else None


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
    owner_id = row.owner_user_id
    tell(db, owner_id, booking, trip, 'New review', f'A Passenger rated your vehicle {body.rating} out of 5.')
    if body.driver_rating is not None and trip.driver_user_id and trip.driver_user_id != owner_id:
        tell(db, trip.driver_user_id, booking, trip, 'New review', f'A Passenger rated your driving {body.driver_rating} out of 5.')
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
    rows = db.scalars(select(TripReview).where(TripReview.owner_user_id == user.id, TripReview.hidden_at.is_(None)).order_by(TripReview.created_at.desc()).limit(300)).all()
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
    trip, booking = trip_and_booking(db, row.trip_id)
    tell(db, row.passenger_user_id, booking, trip, 'The Owner replied to your review', text[:200])
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


@router.get('/drivers/me/reviews')
def driver_reviews(user=Depends(current), db: Session = Depends(get_db)):
    """What Passengers rated about the Driver's driving (only trips where the Passenger gave a Driver rating)."""
    require_role(db, user, 'DRIVER')
    rows = db.scalars(select(TripReview).where(TripReview.driver_user_id == user.id, TripReview.driver_rating.isnot(None), TripReview.hidden_at.is_(None))
                      .order_by(TripReview.created_at.desc()).limit(300)).all()
    trips = {t.id: t for t in db.scalars(select(Trip).where(Trip.id.in_({r.trip_id for r in rows})))} if rows else {}
    people = {u.id: u for u in db.scalars(select(User).where(User.id.in_({r.passenger_user_id for r in rows})))} if rows else {}
    average = format((Decimal(sum(r.driver_rating for r in rows)) / Decimal(len(rows))).quantize(Decimal('0.1')), '.1f') if rows else None
    return {'count': len(rows), 'average': average, 'items': [
        {'id': str(r.id), 'driver_rating': r.driver_rating, 'comment': r.comment, 'created_at': r.created_at.isoformat(),
         'trip_reference': trips[r.trip_id].trip_reference if r.trip_id in trips else None,
         'passenger': (people[r.passenger_user_id].display_name or people[r.passenger_user_id].full_name or '').split(' ')[0] or None} for r in rows]}


class HideReview(BaseModel):
    model_config = {'extra': 'forbid'}
    note: str = Field(min_length=1, max_length=300)


@router.get('/admin/reviews')
def admin_reviews(user=Depends(current), db: Session = Depends(get_db)):
    require_role(db, user, 'ADMIN')
    rows = db.scalars(select(TripReview).order_by(TripReview.created_at.desc()).limit(200)).all()
    vehicles = {v.id: v for v in db.scalars(select(Vehicle).where(Vehicle.id.in_({r.vehicle_id for r in rows})))} if rows else {}
    trips = {t.id: t for t in db.scalars(select(Trip).where(Trip.id.in_({r.trip_id for r in rows})))} if rows else {}
    people = {u.id: u for u in db.scalars(select(User).where(User.id.in_({r.passenger_user_id for r in rows})))} if rows else {}
    items = []
    for r in rows:
        out = review_out(r, vehicles[r.vehicle_id], trips.get(r.trip_id), people.get(r.passenger_user_id))
        out['hidden_at'] = r.hidden_at.isoformat() if r.hidden_at else None
        out['hidden_note'] = r.hidden_note
        items.append(out)
    return {'items': items}


def admin_review(db, user, review_id):
    require_role(db, user, 'ADMIN')
    row = db.get(TripReview, review_id)
    if not row:
        raise ApiError(404, 'REVIEW_NOT_FOUND', 'This review was not found.')
    return row


@router.post('/admin/reviews/{review_id}/hide')
def hide_review(review_id: UUID, body: HideReview, user=Depends(current), db: Session = Depends(get_db)):
    row = admin_review(db, user, review_id)
    note = body.note.strip()
    if not note:
        raise ApiError(422, 'VALIDATION_ERROR', 'Write the reason.', [{'field': 'note', 'message': 'This is required.'}])
    row.hidden_at, row.hidden_note = datetime.now(timezone.utc), note
    db.commit()
    return {'id': str(row.id), 'hidden_at': row.hidden_at.isoformat(), 'hidden_note': row.hidden_note}


@router.post('/admin/reviews/{review_id}/unhide')
def unhide_review(review_id: UUID, user=Depends(current), db: Session = Depends(get_db)):
    row = admin_review(db, user, review_id)
    row.hidden_at, row.hidden_note = None, None
    db.commit()
    return {'id': str(row.id), 'hidden_at': None, 'hidden_note': None}
