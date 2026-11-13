"""Admin oversight pages (read-only), backed by the approved PRD tables.

The paths are kept for the existing Admin screens (AdminWorkflowPage): bookings, trip detail, payments, reports,
vehicle types and manual fulfilment. The earlier version read tables that were never part of the 20-table PRD
catalogue (trip_payments, trip_fare_calculations, vehicle_type_catalog, admin_manual_fulfilment_events) and had no
migration, so every page answered 503. Response shapes are unchanged: lists are {items, page, page_size, total}.
"""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from app.api.routers.review_api import admin
from app.api.routers.settlement_api import row_out
from app.core.errors import ApiError
from app.dependencies.database import get_db
from app.models.hire_models import Booking, Trip
from app.models.payment_models import Payment
from app.models.review_models import Vehicle
from app.services.refunds import REFUNDS

router = APIRouter(prefix='/api/v1', tags=['Admin oversight'])
ZERO = Decimal('0')


def pages(request):
    try:
        page = max(1, int(request.query_params.get('page', '1')))
        size = min(100, max(1, int(request.query_params.get('page_size', '25'))))
    except ValueError:
        raise ApiError(422, 'VALIDATION_ERROR', 'page and page_size must be whole numbers.') from None
    return page, size


def money(value):
    return format(value if value is not None else ZERO, '.2f')


def event_package(booking):
    """Name and hours of the Event package (Event hire), from the accepted price or the open quote; None for other bookings."""
    snap = (booking.price_snapshot or {}).get('current') or ((booking.pending_change or {}).get('quote')) or {}
    return (snap.get('calculation') or {}).get('package')


def booking_view(booking, trip):
    return {'event_package': event_package(booking), 'id': str(booking.id), 'trip_id': str(trip.id) if trip else None, 'booking_reference': booking.booking_reference,
            'booking_type': booking.booking_type, 'status': booking.status, 'booking_status': booking.status,
            'payment_status': booking.payment_status_snapshot, 'start_at': booking.start_at.isoformat() if booking.start_at else None,
            'end_at': booking.end_at.isoformat() if booking.end_at else None, 'origin': booking.origin_text,
            'destination': booking.destination_text, 'passenger_count': booking.passenger_count,
            'total_amount': None if booking.total_amount is None else money(booking.total_amount), 'currency': booking.currency,
            'trip_reference': trip.trip_reference if trip else None, 'trip_status': trip.status if trip else None,
            'created_at': booking.created_at.isoformat()}


def latest_trip(db, booking):
    return db.scalar(select(Trip).where(Trip.booking_id == booking.id).order_by(Trip.created_at.desc()).limit(1))


@router.get('/admin/workflow/bookings')
def bookings(request: Request, user=Depends(admin), db: Session = Depends(get_db)):
    page, size = pages(request)
    status = request.query_params.get('status')
    text = request.query_params.get('q', '').strip()
    query = select(Booking)
    if status:
        query = query.where(Booking.status == status)
    if text:
        query = query.where(Booking.booking_reference.ilike('%' + text + '%'))
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.scalars(query.order_by(Booking.created_at.desc()).offset((page - 1) * size).limit(size)).all()
    return {'items': [booking_view(b, latest_trip(db, b)) for b in rows], 'page': page, 'page_size': size, 'total': total}


@router.get('/admin/workflow/trips/{trip_id}')
def trip_detail(trip_id: UUID, user=Depends(admin), db: Session = Depends(get_db)):
    trip = db.get(Trip, trip_id)
    if not trip:
        raise ApiError(404, 'TRIP_NOT_FOUND', 'Trip not found.')
    booking = db.get(Booking, trip.booking_id) if trip.booking_id else None
    payments = db.scalars(select(Payment).where(Payment.booking_id == trip.booking_id).order_by(Payment.created_at)).all() if booking else []
    return {**(booking_view(booking, trip) if booking else {'trip_id': str(trip.id), 'trip_reference': trip.trip_reference}),
            'trip': {'id': str(trip.id), 'trip_reference': trip.trip_reference, 'status': trip.status,
                     'assignment_type': trip.assignment_type, 'assignment_status': trip.assignment_status,
                     'scheduled_start_at': trip.scheduled_start_at.isoformat() if trip.scheduled_start_at else None,
                     'actual_start_at': trip.actual_start_at.isoformat() if trip.actual_start_at else None,
                     'actual_end_at': trip.actual_end_at.isoformat() if trip.actual_end_at else None,
                     'calculated_distance_km': None if trip.calculated_distance_km is None else str(trip.calculated_distance_km),
                     'breakdown_details': trip.breakdown_details},
            'payments': [row_out(p, booking) for p in payments]}


@router.get('/admin/workflow/payments')
def payments(request: Request, user=Depends(admin), db: Session = Depends(get_db)):
    page, size = pages(request)
    status = request.query_params.get('status')
    query = select(Payment)
    if status:
        query = query.where(Payment.status == status)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.scalars(query.order_by(Payment.created_at.desc(), Payment.id.desc()).offset((page - 1) * size).limit(size)).all()
    books = {b.id: b for b in db.scalars(select(Booking).where(Booking.id.in_({r.booking_id for r in rows})))} if rows else {}
    return {'items': [row_out(r, books.get(r.booking_id)) for r in rows], 'page': page, 'page_size': size, 'total': total}


def amount(db, *where, column=Payment.amount):
    return db.scalar(select(func.coalesce(func.sum(column), 0)).where(*where)) or ZERO


@router.get('/admin/workflow/reports')
def reports(user=Depends(admin), db: Session = Depends(get_db)):
    paid = (Payment.transaction_type == 'PAYMENT', Payment.status.in_(('PAID', 'PARTIALLY_REFUNDED', 'REFUNDED')))
    count = lambda *where: db.scalar(select(func.count()).select_from(Booking).where(*where)) or 0
    return {'bookings_total': count(), 'bookings_confirmed': count(Booking.status == 'CONFIRMED'),
            'bookings_completed': count(Booking.status == 'COMPLETED'), 'bookings_cancelled': count(Booking.status == 'CANCELLED'),
            'trips_completed': db.scalar(select(func.count(Trip.id)).where(Trip.status == 'COMPLETED')) or 0,
            'trips_in_progress': db.scalar(select(func.count(Trip.id)).where(Trip.status == 'IN_PROGRESS')) or 0,
            'payments_collected_lkr': money(amount(db, *paid)),
            'refunded_lkr': money(amount(db, Payment.transaction_type.in_(REFUNDS), Payment.status == 'PAID')),
            'commission_earned_lkr': money(amount(db, *paid, column=Payment.commission_amount)),
            'owner_paid_out_lkr': money(amount(db, Payment.transaction_type == 'OWNER_PAYOUT', Payment.status == 'PAID')),
            'note': 'Figures come from bookings, trips and payments. Sandbox payments move no real money.'}


@router.get('/admin/vehicle-types')
def vehicle_types(user=Depends(admin), db: Session = Depends(get_db)):
    """Vehicle types in use. The PRD keeps the type as text on vehicles (vehicle_type_code); there is no type catalogue."""
    rows = db.execute(select(Vehicle.vehicle_type_code, func.count(Vehicle.id)).where(Vehicle.vehicle_type_code.is_not(None))
                      .group_by(Vehicle.vehicle_type_code).order_by(Vehicle.vehicle_type_code)).all()
    return {'items': [{'id': code, 'code': code, 'display_name': code.replace('_', ' ').title(), 'status': 'ACTIVE',
                       'vehicles': n} for code, n in rows]}


@router.post('/vehicle-types/requests', status_code=201)
def vehicle_type_request(user=Depends(admin)):
    raise ApiError(409, 'FEATURE_NOT_AVAILABLE', 'Vehicle types are chosen on the vehicle form; there is no separate type request.')


@router.patch('/admin/vehicle-types/{type_id}/review')
def vehicle_type_review(type_id: str, user=Depends(admin)):
    raise ApiError(409, 'FEATURE_NOT_AVAILABLE', 'Vehicle types are chosen on the vehicle form; there is nothing to review.')


@router.get('/admin/manual-fulfilment-events')
def manual_events(user=Depends(admin), db: Session = Depends(get_db)):
    """Protected-fulfilment escalations (PRD 54-58) are not built yet; nothing is recorded here so far."""
    return {'items': [], 'message': 'Protected-fulfilment escalations will appear here once that module is built.'}


@router.post('/admin/manual-fulfilment-events', status_code=201)
def create_manual_event(user=Depends(admin)):
    raise ApiError(409, 'FEATURE_NOT_AVAILABLE', 'Manual fulfilment events arrive with the protected-fulfilment module.')


@router.patch('/admin/manual-fulfilment-events/{event_id}/close')
def close_manual_event(event_id: str, user=Depends(admin)):
    raise ApiError(409, 'FEATURE_NOT_AVAILABLE', 'Manual fulfilment events arrive with the protected-fulfilment module.')
