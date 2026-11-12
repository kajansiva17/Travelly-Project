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
from app.models.hire_models import Notification
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


def run_reminders(db, settings, mailer=None, moment=None):
    """One pass of both checks. The caller commits. Returns how many new reminders were created."""
    moment = moment or datetime.now(timezone.utc)
    today = moment.astimezone(COLOMBO).date()
    db.execute(text("SELECT pg_advisory_xact_lock(hashtext('travelly-reminders'))"))
    return {'documents': document_reminders(db, mailer, settings, today, moment),
            'maintenance': maintenance_reminders(db, mailer, settings, today, moment)}
