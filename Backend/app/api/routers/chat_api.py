"""Booking chat. Once a booking is confirmed the Passenger, the Owner and the assigned Driver can write to each other until the trip ends.
 * GET  /bookings/{id}/messages?after=<iso time>: the messages (oldest first, newest 200), marks the ones from others as read. Parties only (others get 404).
   `can_write` says whether the chat is still open; after the trip it stays readable but nobody can write.
 * POST /bookings/{id}/messages {body}: 1 to 500 characters. Everyone else on the booking gets one unread CHAT notice (not one per message), and the text is
   never put in the notice. Works for hire, Book now, rental and ticket seats."""
from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.routers.api import current
from app.api.routers.contact_api import is_live, parties_of, shown_name
from app.core.errors import ApiError
from app.dependencies.database import get_db
from app.models import User
from app.models.chat_models import BookingMessage
from app.models.hire_models import Notification

router = APIRouter(prefix='/api/v1', tags=['Booking chat'])


class NewMessage(BaseModel):
    body: str = Field(min_length=1, max_length=500)


def out(row, viewer_id, senders):
    person = senders.get(row.sender_user_id)
    role = next((name for name, uid in senders['roles'].items() if uid == row.sender_user_id), 'PASSENGER')
    return {'id': str(row.id), 'created_at': row.created_at.isoformat(), 'mine': row.sender_user_id == viewer_id, 'role': role,
            'name': shown_name(person, first_only=role == 'PASSENGER') if person is not None else '', 'body': row.body}


def senders_of(db, parties):
    people = {uid: db.get(User, uid) for uid in set(parties.values()) if uid is not None}
    people['roles'] = {role: uid for role, uid in parties.items() if uid is not None}
    return people


@router.get('/bookings/{booking_id}/messages')
def read_messages(booking_id: UUID, after: datetime | None = None, user=Depends(current), db: Session = Depends(get_db)):
    booking, trip, parties, mine = parties_of(db, booking_id, user)
    query = select(BookingMessage).where(BookingMessage.booking_id == booking.id)
    if after is not None:
        query = query.where(BookingMessage.created_at > after)
    rows = list(reversed(db.scalars(query.order_by(BookingMessage.created_at.desc()).limit(200)).all()))
    me = str(user.id)
    changed = False
    for row in rows:
        if row.sender_user_id != user.id and me not in (row.read_by or []):
            row.read_by = [*(row.read_by or []), me]
            changed = True
    if changed:
        for note in db.scalars(select(Notification).where(Notification.recipient_user_id == user.id, Notification.booking_id == booking.id,
                                                          Notification.notification_type == 'CHAT', Notification.read_at.is_(None))).all():
            note.read_at = datetime.now(timezone.utc)
        db.commit()
    people = senders_of(db, parties)
    return {'items': [out(r, user.id, people) for r in rows], 'can_write': is_live(booking, trip)}


@router.post('/bookings/{booking_id}/messages', status_code=201)
def send_message(booking_id: UUID, body: NewMessage, user=Depends(current), db: Session = Depends(get_db)):
    booking, trip, parties, mine = parties_of(db, booking_id, user)
    if not is_live(booking, trip):
        raise ApiError(409, 'CHAT_CLOSED', 'This chat is closed. Messages can be sent from confirmation until the trip ends.')
    text = body.body.strip()
    if not text:
        raise ApiError(422, 'VALIDATION_ERROR', 'Write a message.', [{'field': 'body', 'message': 'Write a message.'}])
    row = BookingMessage(booking_id=booking.id, sender_user_id=user.id, body=text, read_by=[])
    db.add(row)
    db.flush()
    sender = shown_name(user, first_only='PASSENGER' in mine)
    for other in {uid for uid in parties.values() if uid is not None and uid != user.id}:
        waiting = db.scalar(select(Notification.id).where(Notification.recipient_user_id == other, Notification.booking_id == booking.id,
                                                          Notification.notification_type == 'CHAT', Notification.read_at.is_(None)).limit(1))
        if waiting is None:
            db.add(Notification(recipient_user_id=other, booking_id=booking.id, trip_id=trip.id if trip is not None else None, notification_type='CHAT',
                                channel='IN_APP', title='New message', body=f'{sender} sent you a message about your booking.', action_required=False,
                                action_payload={'booking_id': str(booking.id)}, status='QUEUED'))
    db.commit()
    return out(row, user.id, senders_of(db, parties))
