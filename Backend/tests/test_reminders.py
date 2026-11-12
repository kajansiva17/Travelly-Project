"""Reminders job: document expiry (PRD default 5 working days) and maintenance due notifications, never duplicated."""
from datetime import date, datetime, timedelta, timezone
from uuid import UUID, uuid4
from sqlalchemy import func, select
from app.models.hire_models import Notification
from app.models.review_models import Document, Vehicle
from app.services.reminders import run_reminders, working_days_between
from test_ticket_holds import api, person, ticket
from test_vehicle_records import fleet, add, at


def run(client, **overrides):
    settings = client.app.state.settings.model_copy(update=overrides)
    with client.app.state.sessions() as db:
        counts = run_reminders(db, settings, overrides.pop('mailer', None) if 'mailer' in overrides else None)
        db.commit()
    return counts


def notices(client, user, kind, channel='IN_APP'):
    with client.app.state.sessions() as db:
        return db.scalars(select(Notification).where(Notification.recipient_user_id == UUID(user['id']), Notification.notification_type == kind,
                                                     Notification.channel == channel).order_by(Notification.created_at)).all()


def licence(client, user, expiry):
    with client.app.state.sessions() as db:
        doc = Document(user_id=UUID(user['id']), document_type='DRIVING_LICENCE', status='APPROVED', issuing_country='LK', expiry_date=expiry,
                       verified_categories=['B'], submitted_at=func.now(), verified_at=func.now(), verified_by=UUID(user['id']), storage_key=uuid4().hex,
                       original_file_name='test.png', mime_type='image/png', file_size_bytes=1, file_checksum='0' * 64)
        db.add(doc)
        db.commit()
        return doc.id


def test_working_days_skip_weekends():
    friday = date(2026, 11, 13)
    assert working_days_between(friday, friday) == 0
    assert working_days_between(friday, date(2026, 11, 16)) == 1   # Saturday and Sunday do not count
    assert working_days_between(friday, date(2026, 11, 20)) == 5
    assert working_days_between(friday, date(2026, 11, 10)) == 0


def test_a_document_reminder_goes_once_before_expiry_and_once_after(client):
    driver = person(client, 'DRIVER')
    today = datetime.now(timezone.utc).date()
    doc_id = licence(client, driver, today + timedelta(days=2))
    far = person(client, 'DRIVER')
    licence(client, far, today + timedelta(days=60))
    run(client)
    first = notices(client, driver, 'DOCUMENT_EXPIRY')
    assert len(first) == 1 and first[0].action_payload['stage'] == 'EXPIRING' and 'Driving licence' in first[0].title
    assert first[0].action_payload['document_id'] == str(doc_id) and first[0].action_required
    run(client)
    assert len(notices(client, driver, 'DOCUMENT_EXPIRY')) == 1   # never twice
    assert not notices(client, far, 'DOCUMENT_EXPIRY')
    with client.app.state.sessions() as db:
        db.get(Document, doc_id).expiry_date = today - timedelta(days=1)
        db.commit()
    run(client)
    stages = [n.action_payload['stage'] for n in notices(client, driver, 'DOCUMENT_EXPIRY')]
    assert stages == ['EXPIRING', 'EXPIRED']


def test_vehicle_documents_go_to_the_vehicle_owner(client, ticket):
    today = datetime.now(timezone.utc).date()
    with client.app.state.sessions() as db:
        doc = db.scalar(select(Document).where(Document.vehicle_id == UUID(ticket['trip']['vehicle_id']), Document.status == 'APPROVED')
                        .order_by(Document.document_type).limit(1))
        doc.expiry_date = today + timedelta(days=1)
        db.commit()
    run(client)
    found = notices(client, ticket['owner'], 'DOCUMENT_EXPIRY')
    assert any(n.action_payload.get('vehicle_id') == ticket['trip']['vehicle_id'] for n in found)


def test_maintenance_reminders_once_per_cycle_and_stage(client, fleet):
    add(client, fleet, {'record_type': 'OIL_CHANGE', 'recorded_at': at(5), 'odometer_km': '40000.0', 'next_due_odometer_km': '45000.0'})
    add(client, fleet, {'record_type': 'ODOMETER_UPDATE', 'recorded_at': at(0, 1), 'odometer_km': '46000.0'})
    run(client)
    run(client)
    overdue = notices(client, fleet['owner'], 'MAINTENANCE_DUE')
    assert len(overdue) == 1 and overdue[0].action_payload['stage'] == 'OVERDUE' and overdue[0].action_payload['task'] == 'OIL_CHANGE'
    assert '1000.0 km past the limit' in overdue[0].body
    # Serviced: a new cycle starts; its limit is far away (even at ~1,200 km a day), so nothing new is sent.
    add(client, fleet, {'record_type': 'OIL_CHANGE', 'recorded_at': at(0, 0), 'odometer_km': '46000.0', 'next_due_odometer_km': '146000.0'})
    run(client)
    assert len(notices(client, fleet['owner'], 'MAINTENANCE_DUE')) == 1
    # A calendar limit three days away is "due soon".
    from zoneinfo import ZoneInfo
    soon = (datetime.now(ZoneInfo('Asia/Colombo')).date() + timedelta(days=2)).isoformat()   # Sri Lanka's date, not UTC
    add(client, fleet, {'record_type': 'BRAKE_SERVICE', 'recorded_at': at(0, 0), 'genuine_calendar_due_date': soon})
    run(client)
    stages = {n.action_payload['task']: n.action_payload['stage'] for n in notices(client, fleet['owner'], 'MAINTENANCE_DUE')}
    assert stages == {'OIL_CHANGE': 'OVERDUE', 'BRAKE_SERVICE': 'DUE_SOON'}


class FakeMailer:
    def __init__(self):
        self.sent = []

    def deliver(self, recipient, subject, body):
        self.sent.append((recipient, subject))
        return 'captured'


def test_email_copies_only_when_enabled(client):
    driver = person(client, 'DRIVER')
    licence(client, driver, datetime.now(timezone.utc).date() + timedelta(days=1))
    mailer = FakeMailer()
    settings = client.app.state.settings.model_copy(update={'reminder_email_enabled': True})
    with client.app.state.sessions() as db:
        run_reminders(db, settings, mailer)
        db.commit()
    emails = notices(client, driver, 'DOCUMENT_EXPIRY', 'EMAIL')
    assert len(emails) == 1 and emails[0].status == 'SENT' and mailer.sent and mailer.sent[0][1].startswith('Travelly: ')
    off = person(client, 'DRIVER')
    licence(client, off, datetime.now(timezone.utc).date() + timedelta(days=1))
    quiet = FakeMailer()
    with client.app.state.sessions() as db:
        run_reminders(db, client.app.state.settings, quiet)
        db.commit()
    assert notices(client, off, 'DOCUMENT_EXPIRY') and not notices(client, off, 'DOCUMENT_EXPIRY', 'EMAIL') and not quiet.sent
