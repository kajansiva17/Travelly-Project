"""Closing an account (owner decisions 14 Nov 2026): deactivate or delete request.

An account with open business cannot be closed, so nobody can walk away from a booking, a trip or money owed. The check is the
same for deactivating and for deleting. After a delete request the account stays DEACTIVATED for DELETE_AFTER_DAYS; signing in
again in that time cancels the request. After that a daily job (scripts/anonymize_deleted_accounts.py) removes the personal data.
"""
from datetime import timedelta
from sqlalchemy import func, select
from app.models import User
from app.models.hire_models import Booking, ScheduledTrip, Trip
from app.models.payment_models import Payment

DELETE_AFTER_DAYS = 30
OPEN_BOOKING = ('REQUESTED', 'AWAITING_DRIVER', 'OWNER_ACTION_REQUIRED', 'CONFIRMED', 'IN_PROGRESS')
OPEN_TRIP = ('READY', 'IN_PROGRESS', 'BREAKDOWN', 'ASSISTANCE_REQUIRED')
OPEN_DEPARTURE = ('PUBLISHED', 'BOOKING_OPEN', 'DECISION_REQUIRED', 'COMMITTED', 'READY', 'IN_PROGRESS', 'DISRUPTED')
MESSAGES = {
    'OPEN_BOOKINGS_AS_PASSENGER': 'You have bookings that are not finished.',
    'OPEN_BOOKINGS_AS_OWNER': 'Bookings for your vehicles are not finished.',
    'OPEN_TRIPS_AS_DRIVER': 'You are assigned to a trip that is not finished.',
    'OPEN_DEPARTURES': 'You have ticket departures that are not finished.',
    'COMMISSION_DUE': 'Cash commission is still owed to Travelly.',
    'OWNER_PAYOUT_PENDING': 'Travelly still holds money that is payable to you.',
    'REFUND_PENDING': 'A refund to you is still being processed.',
}


def blockers(db, user_id):
    """What stops this person closing their account: a list of {code, message, count}; empty means they can."""
    def count(statement):
        return db.scalar(statement) or 0
    found = {
        'OPEN_BOOKINGS_AS_PASSENGER': count(select(func.count(Booking.id)).where(Booking.passenger_user_id == user_id, Booking.status.in_(OPEN_BOOKING))),
        'OPEN_BOOKINGS_AS_OWNER': count(select(func.count(Booking.id)).where(Booking.owner_user_id == user_id, Booking.status.in_(OPEN_BOOKING))),
        'OPEN_TRIPS_AS_DRIVER': count(select(func.count(Trip.id)).where(
            (Trip.driver_user_id == user_id) | (Trip.operating_owner_user_id == user_id), Trip.status.in_(OPEN_TRIP),
            Trip.assignment_status.in_(('NOT_REQUIRED', 'PENDING', 'ACCEPTED')))),
        'OPEN_DEPARTURES': count(select(func.count(ScheduledTrip.id)).where(ScheduledTrip.owner_user_id == user_id, ScheduledTrip.status.in_(OPEN_DEPARTURE))),
        'COMMISSION_DUE': count(select(func.count(Payment.id)).where(Payment.payee_owner_user_id == user_id, Payment.owner_settlement_status == 'COMMISSION_DUE')),
        'OWNER_PAYOUT_PENDING': count(select(func.count(Payment.id)).where(Payment.payee_owner_user_id == user_id, Payment.owner_settlement_status == 'OWNER_PAYABLE')),
        'REFUND_PENDING': count(select(func.count(Payment.id)).join(Booking, Booking.id == Payment.booking_id).where(
            Booking.passenger_user_id == user_id, Payment.transaction_type.in_(('PARTIAL_REFUND', 'FULL_REFUND')), Payment.status.in_(('PENDING', 'PROCESSING')))),
    }
    return [{'code': code, 'message': MESSAGES[code], 'count': n} for code, n in found.items() if n]


def anonymise(db, user, hasher, secrets_module):
    """Remove the personal data of a person whose delete request is due. Booking, payment and trip records stay, under the name
    "Deleted user". The account becomes CLOSED and can never sign in again."""
    token = secrets_module.token_hex(8)
    user.full_name, user.display_name = 'Deleted user', None
    user.email, user.email_verified_at = f'deleted-{user.public_user_reference.lower()}-{token}@deleted.invalid', None
    user.phone_e164, user.phone_verified_at = None, None
    user.profile_image_url = None
    user.password_hash = hasher.hash(secrets_module.token_urlsafe(32))
    user.external_auth_provider = user.external_auth_subject = None
    user.totp_secret, user.totp_enabled_at, user.totp_backup_codes, user.totp_last_step = None, None, [], None
    user.notification_preferences = {}
    user.account_status = 'CLOSED'
    user.auth_version += 1


def due_ids(db, now):
    return db.scalars(select(User.id).where(User.account_status == 'DEACTIVATED', User.deletion_requested_at.is_not(None),
                                            User.deletion_requested_at <= now - timedelta(days=DELETE_AFTER_DAYS))).all()
