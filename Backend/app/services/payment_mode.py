"""How the Owner lets Passengers pay, per vehicle service (owner decision, 25 Nov 2026).

    ONLINE_ONLY       only online (the default)
    CASH_ONLY         only cash: a Ticket seat is paid to the Driver on the bus, a hire at the end of the trip
    ONLINE_AND_CASH   the Passenger chooses

Stored in `vehicle_services.owner_terms` (no migration): `payment_mode`, and `cash.accepted` which older code reads. Rows saved before this
had only `cash.accepted`: true meant online and cash. Every service type can use every mode, Ticket seats included.
"""
from sqlalchemy import select
from app.models.hire_models import Booking
from app.models.rate_models import VehicleService

MODES = ('ONLINE_ONLY', 'CASH_ONLY', 'ONLINE_AND_CASH')


def mode_of(terms):
    terms = terms or {}
    if terms.get('payment_mode') in MODES:
        return terms['payment_mode']
    return 'ONLINE_AND_CASH' if (terms.get('cash') or {}).get('accepted') is True else 'ONLINE_ONLY'


def payment_mode(db, vehicle_id, service_type_id):
    row = db.scalar(select(VehicleService).where(VehicleService.vehicle_id == vehicle_id, VehicleService.service_type_id == service_type_id))
    return mode_of(row.owner_terms if row else None)


def cash_ok(mode):
    return mode in ('CASH_ONLY', 'ONLINE_AND_CASH')


def online_ok(mode):
    return mode in ('ONLINE_ONLY', 'ONLINE_AND_CASH')


def booking_payments(db, booking_ids):
    """What each booking owes, for the Driver's lists: {booking_id: {payment_status, cash_due, amount, currency}}."""
    ids = list(booking_ids)
    if not ids:
        return {}
    rows = db.execute(select(Booking.id, Booking.payment_status_snapshot, Booking.total_amount, Booking.currency).where(Booking.id.in_(ids))).all()
    return {row.id: {'payment_status': row.payment_status_snapshot, 'cash_due': row.payment_status_snapshot == 'CASH_AWAITING_CONFIRMATION',
                     'amount': format(row.total_amount, '.2f') if row.total_amount is not None else None, 'currency': row.currency} for row in rows}
