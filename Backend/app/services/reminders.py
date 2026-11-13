"""Reminders job: document expiry (DOCUMENT_EXPIRY) and vehicle maintenance (MAINTENANCE_DUE) notifications.

Rules:
- Document expiry: PRD reminder default of 5 working days before the expiry date (configurable:
  REMINDER_WORKING_DAYS), then once more when it has expired. Only current, approved documents are checked.
- Maintenance: the PRD 4.16 summary of each approved vehicle. A reminder goes out once per service cycle and stage:
  - DUE_SOON: the earliest limit (estimated distance date or calendar date) is within the same working-day window.
  - DUE and OVERDUE: as the summary reports them.
  A new service record starts a new cycle.
- Working days are Monday to Friday; public holidays are not known to the system.

Every reminder carries `action_payload.reminder_key`, so running the job again never sends a duplicate. An advisory
lock makes two runs at the same time take turns. Email copies (channel EMAIL) are sent only when
REMINDER_EMAIL_ENABLED is true and the recipient's email is verified.
"""
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from sqlalchemy import select, text
from app.api.routers.vehicle_records_api import summarise
from app.models import User
from app.models.hire_models import Booking, Notification, Trip
from app.models.payment_models import Payment
from app.services import commission_overdue
from app.models.review_models import Document, Vehicle

COLOMBO = ZoneInfo('Asia/Colombo')
NAMES = {'NIC': 'National identity card', 'PASSPORT': 'Passport', 'DRIVING_LICENCE': 'Driving licence',
         'BUSINESS_REGISTRATION': 'Business registration', 'OWNER_AUTHORISATION': 'Owner authorisation',
         'BANK_PROOF': 'Bank proof', 'VEHICLE_REGISTRATION': 'Vehicle registration', 'REVENUE_LICENCE': 'Revenue licence',
         'INSURANCE': 'Insurance', 'EMISSION': 'Emission certificate', 'FITNESS': 'Fitness certificate', 'ROUTE_PERMIT': 'Route permit'}
TASK_NAMES = {'OIL_CHANGE': 'Oil change', 'OIL_FILTER_CHANGE': 'Oil filter change', 'TYRE_CHANGE': 'Tyre change',
              'TYRE_ROTATION': 'Tyre rotation', 'WHEEL_ALIGNMENT': 'Wheel alignment', 'WHEEL_BALANCING': 'Wheel balancing',
              'GENERAL_SERVICE': 'General service', 'BRAKE_SERVICE': 'Brake service', 'BATTERY_SERVICE': 'Battery service'}


def working_days_between(start, end):
    """Monday-Friday days after `start` up to and including `end` (0 when end <= start)."""
    days, day = 0, start
    while day < end:
        day += timedelta(days=1)
        if day.weekday() < 5:
            days += 1
    return days


def already_sent(db, recipient, kind, key):
    return db.scalar(select(Notification.id).where(Notification.recipient_user_id == recipient, Notification.notification_type == kind,
                                                   Notification.action_payload['reminder_key'].astext == key).limit(1)) is not None


def remind(db, mailer, settings, recipient, kind, key, title, body, payload, moment):
    if already_sent(db, recipient, kind, key):
        return False
    data = {'reminder_key': key, **payload}
    db.add(Notification(recipient_user_id=recipient, notification_type=kind, channel='IN_APP', title=title, body=body,
                        action_required=True, action_payload=data, status='QUEUED'))
    user = db.get(User, recipient)
    if settings.reminder_email_enabled and mailer and user and user.email and user.email_verified_at:
        outcome = mailer.deliver(user.email, 'Travelly: ' + title, body + '\n\nOpen Travelly to see the details.')
        sent = outcome in ('provider_accepted', 'captured')
        db.add(Notification(recipient_user_id=recipient, notification_type=kind, channel='EMAIL', title=title, body=body,
                            action_required=False, action_payload={**data, 'delivery': outcome},
                            status='SENT' if sent else 'FAILED', sent_at=moment if sent else None))
    return True


def document_reminders(db, mailer, settings, today, moment):
    sent = 0
    window = settings.reminder_working_days
    for doc in db.scalars(select(Document).where(Document.status == 'APPROVED', Document.expiry_date.is_not(None),
                                                 Document.expiry_date <= today + timedelta(days=window * 2 + 7))
                          .order_by(Document.expiry_date, Document.id)):
        if doc.expiry_date < today:
            stage = 'EXPIRED'
        elif working_days_between(today, doc.expiry_date) <= window:
            stage = 'EXPIRING'
        else:
            continue
        vehicle = db.get(Vehicle, doc.vehicle_id) if doc.vehicle_id else None
        recipient = doc.user_id or (vehicle.owner_user_id if vehicle else None)
        if recipient is None:
            continue
        name = NAMES.get(doc.document_type, doc.document_type.replace('_', ' ').title())
        whose = f' for vehicle {vehicle.registration_number}' if vehicle else ''
        when = doc.expiry_date.strftime('%d %b %Y')
        if stage == 'EXPIRED':
            title, body = f'{name} expired', f'Your {name.lower()}{whose} expired on {when}. Upload a renewed copy.'
        else:
            title, body = f'{name} expires soon', f'Your {name.lower()}{whose} expires on {when}. Upload a renewed copy before then.'
        payload = {'document_id': str(doc.id), 'document_type': doc.document_type, 'expiry_date': doc.expiry_date.isoformat(),
                   'stage': stage, **({'vehicle_id': str(vehicle.id)} if vehicle else {})}
        sent += remind(db, mailer, settings, recipient, 'DOCUMENT_EXPIRY', f'DOCUMENT_EXPIRY:{doc.id}:{doc.expiry_date}:{stage}',
                       title, body, payload, moment)
    return sent


def maintenance_reminders(db, mailer, settings, today, moment):
    sent = 0
    window = settings.reminder_working_days
    for vehicle in db.scalars(select(Vehicle).where(Vehicle.verification_status == 'APPROVED',
                                                    Vehicle.availability_status.not_in(('INACTIVE', 'SUSPENDED')))
                              .order_by(Vehicle.id)):
        for item in summarise(db, vehicle, moment)['items']:
            if not item['last_record_id']:
                continue
            first = min([date.fromisoformat(d) for d in (item['estimated_due_date'], item['genuine_calendar_due_date']) if d],
                        default=None)
            if item['status'] in ('OVERDUE', 'DUE'):
                stage = item['status']
            elif item['status'] == 'UPCOMING' and first and working_days_between(today, first) <= window:
                stage = 'DUE_SOON'
            else:
                continue
            name = TASK_NAMES.get(item['task'], item['task'].replace('_', ' ').title())
            details = []
            if item['remaining_km'] is not None:
                details.append(f"{item['remaining_km']} km left" if not item['remaining_km'].startswith('-')
                               else f"{item['remaining_km'][1:]} km past the limit")
            if first and first > today:
                details.append(('estimated ' if first.isoformat() == item['estimated_due_date'] else 'by ') + first.strftime('%d %b %Y'))
            extra = f" ({', '.join(details)})" if details else ''
            title = {'OVERDUE': f'{name} overdue', 'DUE': f'{name} due', 'DUE_SOON': f'{name} due soon'}[stage]
            body = f'{title} for {vehicle.registration_number}{extra}. Add a record in the Maintenance tab when it is done.'
            payload = {'vehicle_id': str(vehicle.id), 'task': item['task'], 'stage': stage, 'record_id': item['last_record_id'],
                       'remaining_km': item['remaining_km'], 'due_date': first.isoformat() if first else None}
            sent += remind(db, mailer, settings, vehicle.owner_user_id, 'MAINTENANCE_DUE',
                           f"MAINTENANCE_DUE:{vehicle.id}:{item['task']}:{item['last_record_id']}:{stage}", title, body, payload, moment)
    return sent


def commission_reminders(db, mailer, settings, moment):
    """Cash commission rule (owner decision 13 Nov 2026): the Owner hears at day 10, 14, 16, 17 and 18 of the oldest unpaid
    cash commission. If the job missed some days only the latest stage reached is sent. A new debt starts new stages."""
    sent = 0
    owners = db.scalars(select(Payment.payee_owner_user_id).where(*commission_overdue._due()).distinct()).all()
    free, block = settings.commission_free_days, settings.commission_block_days
    stages = [(block, 'BLOCKED', 'New bookings are stopped',
               'Your commission is more than {block} days old, so your vehicles take no new bookings until it is paid. Bookings already made are not affected.'),
              (block - 1, 'LAST_DAY', 'Last day to pay your commission', 'Pay your {amount} LKR commission today. From tomorrow your vehicles take no new bookings.'),
              (block - 2, 'FINAL_DAYS', 'Pay your commission', 'Your {amount} LKR commission is overdue. New bookings stop in 2 days.'),
              (free, 'GRACE_STARTED', 'Your commission is due', 'Your free period has ended. Pay your {amount} LKR commission within {left} days to keep taking bookings.'),
              (free - 4, 'FREE_ENDING', 'Commission due soon', 'You owe Travelly {amount} LKR commission from cash trips. Please pay within {free_left} days.')]
    for owner_id in owners:
        info = commission_overdue.standing(db, settings, owner_id, moment)
        stage = next(((n, t, b) for d, n, t, b in stages if info['days_open'] >= d), None)
        if stage is None:
            continue
        name, title, text_ = stage
        if name == 'BLOCKED' and not info['blocked']:
            continue
        body = text_.format(block=block, amount=info['amount_due'], left=max(0, block - info['days_open']),
                            free_left=max(0, free - info['days_open']))
        key = f"commission:{owner_id}:{info['oldest_due_at'][:10]}:{name}"
        sent += remind(db, mailer, settings, owner_id, 'PAYMENT', key, title, body,
                       {'stage': info['stage'], 'amount_due': info['amount_due'], 'days_open': info['days_open']}, moment)
    return sent


def rental_reminders(db, mailer, settings, moment):
    """Self-drive rental (owner decision 14 Nov 2026), once each per rental:
    REQUESTED and unanswered for a day -> Owner; start within 24 h -> both ("tomorrow"); start passed and not handed over -> both;
    IN_PROGRESS and due back within 24 h -> both; return time passed -> both."""
    sent = 0
    grace = timedelta(hours=1)
    rows = db.scalars(select(Booking).where(Booking.booking_type == 'RENTAL', Booking.status.in_(('REQUESTED', 'CONFIRMED', 'IN_PROGRESS')))
                      .order_by(Booking.start_at).limit(2000)).all()
    for row in rows:
        payload = {'booking_id': str(row.id), 'booking_reference': row.booking_reference}
        both = (row.passenger_user_id, row.owner_user_id)
        plan = []
        if row.status == 'REQUESTED':
            if moment - row.created_at >= timedelta(days=1) and row.start_at > moment:
                plan.append(('UNANSWERED', (row.owner_user_id,), 'Rental request waiting', f'A rental request ({row.booking_reference}) has waited a day. Accept or decline it.'))
        elif row.status == 'CONFIRMED':
            if row.start_at <= moment:
                plan.append(('NOT_HANDED_OVER', both, 'Rental not handed over', f'The pickup time of rental {row.booking_reference} has passed and the vehicle is not handed over yet.'))
            elif row.start_at - moment <= timedelta(hours=24):
                plan.append(('STARTS_SOON', both, 'Your rental starts soon', f'Rental {row.booking_reference} starts within 24 hours. Bring your driving licence.'))
        else:
            trip = db.scalar(select(Trip).where(Trip.booking_id == row.id, Trip.status == 'IN_PROGRESS').limit(1))
            days = int(((row.itinerary_snapshot or {}).get('rental') or {}).get('days') or 0)
            if trip is not None and trip.actual_start_at is not None and days:
                due = trip.actual_start_at + timedelta(days=days) + grace
                if due <= moment:
                    plan.append(('OVERDUE', both, 'Rental return is late', f'Rental {row.booking_reference} should have been returned. Late hours are charged per the Owner\u2019s rate.'))
                elif due - moment <= timedelta(hours=24):
                    plan.append(('RETURN_SOON', both, 'Return the vehicle soon', f'Rental {row.booking_reference} is due back within 24 hours.'))
        for stage, people, title, body in plan:
            for person in people:
                sent += remind(db, mailer, settings, person, 'RECONFIRMATION', f'rental:{row.id}:{stage}', title, body, {**payload, 'stage': stage}, moment)
    return sent


def run_reminders(db, settings, mailer=None, moment=None):
    """One pass of both checks. The caller commits. Returns how many new reminders were created."""
    moment = moment or datetime.now(timezone.utc)
    today = moment.astimezone(COLOMBO).date()
    db.execute(text("SELECT pg_advisory_xact_lock(hashtext('travelly-reminders'))"))
    return {'documents': document_reminders(db, mailer, settings, today, moment),
            'maintenance': maintenance_reminders(db, mailer, settings, today, moment),
            'commission': commission_reminders(db, mailer, settings, moment),
            'rental': rental_reminders(db, mailer, settings, moment)}
