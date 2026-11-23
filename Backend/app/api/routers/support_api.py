"""Support chat (sidebar > Support for Passenger, Owner and Driver; Admin inbox at /admin/support).
A ticket is a chat thread between one person and the Travelly Admins: the person writes, an Admin replies, both keep writing until it is closed.
 * One ticket belongs to one person and is opened from one of their approved workspaces; only that person and Admins can read it.
 * Unread flags show who has something new to read. Reading a ticket clears the reader's flag. There is no push connection: the pages read the
   ticket again every few seconds while it is open.
 * A reply from an Admin moves OPEN to IN_PROGRESS and sends the person a notification; a message from the person reopens a RESOLVED ticket.
 * No attachments yet; a ticket may point at one of the person's own bookings."""
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from app.api.routers.api import current, require_role
from app.api.routers.review_api import admin, is_admin
from app.core.errors import ApiError
from app.dependencies.database import get_db
from app.models import User
from app.models.hire_models import Booking, Notification, Trip
from app.models.support_models import SupportMessage, SupportTicket

router = APIRouter(prefix='/api/v1', tags=['Support'])
MAX_OPEN_TICKETS = 5
CATEGORIES = ('PAYMENT', 'BOOKING', 'VEHICLE', 'DRIVER', 'REFUND', 'ACCOUNT', 'APP', 'OTHER')


class NewTicket(BaseModel):
    role: Literal['PASSENGER', 'OWNER', 'DRIVER']
    category: Literal['PAYMENT', 'BOOKING', 'VEHICLE', 'DRIVER', 'REFUND', 'ACCOUNT', 'APP', 'OTHER']
    subject: str = Field(min_length=1, max_length=120)
    message: str = Field(min_length=1, max_length=2000)
    booking_id: UUID | None = None


class Say(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class SetStatus(BaseModel):
    status: Literal['IN_PROGRESS', 'RESOLVED', 'CLOSED']


def now_utc():
    return datetime.now(timezone.utc)


def ticket_out(ticket, db, *, for_admin=False, last=None):
    out = {'id': str(ticket.id), 'category': ticket.category, 'subject': ticket.subject, 'status': ticket.status, 'workspace_role': ticket.workspace_role,
           'booking_id': str(ticket.booking_id) if ticket.booking_id else None, 'created_at': ticket.created_at.isoformat(),
           'last_message_at': ticket.last_message_at.isoformat(), 'unread': bool(ticket.admin_unread if for_admin else ticket.user_unread),
           'last_message': (last or '')[:120]}
    if for_admin:
        person = db.get(User, ticket.user_id)
        out['person'] = {'name': (person.display_name or person.full_name) if person else None, 'reference': person.public_user_reference if person else None}
    return out


def last_text(db, ticket_id):
    return db.scalar(select(SupportMessage.body).where(SupportMessage.ticket_id == ticket_id).order_by(SupportMessage.created_at.desc()).limit(1))


def message_out(row, viewer_is_admin):
    # "mine" is whose side the message is on for the person looking at it.
    return {'id': str(row.id), 'body': row.body, 'from_admin': row.from_admin, 'mine': row.from_admin == viewer_is_admin, 'created_at': row.created_at.isoformat()}


def readable(db, ticket_id, user):
    ticket = db.get(SupportTicket, ticket_id)
    staff = is_admin(db, user)
    if not ticket or not (ticket.user_id == user.id or staff):
        raise ApiError(404, 'TICKET_NOT_FOUND', 'This support ticket was not found.')
    return ticket, staff


def own_booking(db, user, booking_id):
    booking = db.get(Booking, booking_id)
    drives = db.scalar(select(Trip.id).where(Trip.booking_id == booking_id, Trip.driver_user_id == user.id)) if booking else None
    if not booking or (user.id not in (booking.passenger_user_id, booking.owner_user_id) and not drives):
        raise ApiError(404, 'BOOKING_NOT_FOUND', 'This booking was not found.')


@router.post('/support/tickets', status_code=201)
def open_ticket(body: NewTicket, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    request.app.state.store.rate(f'support-open:{user.id}', 10, 3600)
    require_role(db, user, body.role)
    subject, message = body.subject.strip(), body.message.strip()
    if not subject or not message:
        raise ApiError(422, 'VALIDATION_ERROR', 'Write a subject and a message.', [{'field': 'subject' if not subject else 'message', 'message': 'This is required.'}])
    if body.booking_id:
        own_booking(db, user, body.booking_id)
    open_count = db.scalar(select(func.count()).select_from(SupportTicket).where(SupportTicket.user_id == user.id, SupportTicket.status.in_(('OPEN', 'IN_PROGRESS')))) or 0
    if open_count >= MAX_OPEN_TICKETS:
        raise ApiError(409, 'TOO_MANY_OPEN_TICKETS', f'You already have {MAX_OPEN_TICKETS} open tickets. Wait for a reply or close one first.')
    ticket = SupportTicket(user_id=user.id, workspace_role=body.role, category=body.category, subject=subject, booking_id=body.booking_id,
                           status='OPEN', last_message_at=now_utc(), user_unread=False, admin_unread=True)
    db.add(ticket)
    db.flush()
    db.add(SupportMessage(ticket_id=ticket.id, sender_user_id=user.id, from_admin=False, body=message))
    db.commit()
    return ticket_out(ticket, db, last=message)


@router.get('/me/support/tickets')
def my_tickets(user=Depends(current), db: Session = Depends(get_db)):
    rows = db.scalars(select(SupportTicket).where(SupportTicket.user_id == user.id).order_by(SupportTicket.last_message_at.desc()).limit(100)).all()
    return {'items': [ticket_out(row, db, last=last_text(db, row.id)) for row in rows], 'max_open': MAX_OPEN_TICKETS}


@router.get('/admin/support/tickets')
def inbox(user=Depends(admin), db: Session = Depends(get_db)):
    rows = db.scalars(select(SupportTicket).order_by(SupportTicket.admin_unread.desc(), SupportTicket.last_message_at.desc()).limit(200)).all()
    return {'items': [ticket_out(row, db, for_admin=True, last=last_text(db, row.id)) for row in rows]}


@router.get('/support/tickets/{ticket_id}')
def read_ticket(ticket_id: UUID, user=Depends(current), db: Session = Depends(get_db)):
    ticket, staff = readable(db, ticket_id, user)
    viewer_is_admin = staff and ticket.user_id != user.id
    if viewer_is_admin and ticket.admin_unread:
        ticket.admin_unread = False
    elif not viewer_is_admin and ticket.user_unread:
        ticket.user_unread = False
    messages = db.scalars(select(SupportMessage).where(SupportMessage.ticket_id == ticket.id).order_by(SupportMessage.created_at, SupportMessage.id)).all()
    db.commit()
    return {**ticket_out(ticket, db, for_admin=viewer_is_admin), 'messages': [message_out(row, viewer_is_admin) for row in messages]}


@router.post('/support/tickets/{ticket_id}/messages', status_code=201)
def say(ticket_id: UUID, body: Say, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    request.app.state.store.rate(f'support-say:{user.id}', 30, 60)
    ticket, staff = readable(db, ticket_id, user)
    text = body.body.strip()
    if not text:
        raise ApiError(422, 'VALIDATION_ERROR', 'Write a message.', [{'field': 'body', 'message': 'This is required.'}])
    if ticket.status == 'CLOSED':
        raise ApiError(409, 'TICKET_CLOSED', 'This ticket is closed. Open a new one if you still need help.')
    from_admin = staff and ticket.user_id != user.id
    row = SupportMessage(ticket_id=ticket.id, sender_user_id=user.id, from_admin=from_admin, body=text)
    db.add(row)
    ticket.last_message_at = now_utc()
    if from_admin:
        ticket.user_unread = True
        if ticket.status == 'OPEN':
            ticket.status = 'IN_PROGRESS'
        db.add(Notification(recipient_user_id=ticket.user_id, notification_type='ADMIN_ACTION', channel='IN_APP', title='Support replied',
                            body=ticket.subject, action_required=False, action_payload={'support_ticket_id': str(ticket.id)}, status='QUEUED'))
    else:
        ticket.admin_unread = True
        if ticket.status == 'RESOLVED':
            ticket.status = 'OPEN'
    db.commit()
    return message_out(row, from_admin)


@router.post('/support/tickets/{ticket_id}/status')
def set_status(ticket_id: UUID, body: SetStatus, user=Depends(admin), db: Session = Depends(get_db)):
    ticket = db.get(SupportTicket, ticket_id)
    if not ticket:
        raise ApiError(404, 'TICKET_NOT_FOUND', 'This support ticket was not found.')
    ticket.status = body.status
    if body.status in ('RESOLVED', 'CLOSED'):
        ticket.user_unread = True
    db.commit()
    return ticket_out(ticket, db, for_admin=True)


@router.post('/support/tickets/{ticket_id}/close')
def close_ticket(ticket_id: UUID, user=Depends(current), db: Session = Depends(get_db)):
    ticket = db.get(SupportTicket, ticket_id)
    if not ticket or ticket.user_id != user.id:
        raise ApiError(404, 'TICKET_NOT_FOUND', 'This support ticket was not found.')
    ticket.status = 'CLOSED'
    db.commit()
    return ticket_out(ticket, db)
