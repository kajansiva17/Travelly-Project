"""One snapshot of the approved occupancy sources; shared by calendar and hire."""
from datetime import datetime, timezone
from sqlalchemy import select, union_all, literal, cast, String, and_, or_
from sqlalchemy.exc import SQLAlchemyError
from app.models.hire_models import Booking, Trip, ScheduledTrip, VehicleRecord
from app.core.errors import ApiError

KINDS = ('PERSONAL', 'MAINTENANCE', 'EMERGENCY')
WITHDRAWN = tuple('WITHDRAWN_' + kind for kind in KINDS)


def incomplete():
    return ApiError(503, 'AVAILABILITY_INCOMPLETE', 'Availability is incomplete. A booking, departure, trip or block source could not be checked. Retry before making availability decisions.')


def occupancy(db, vehicle_id, start, end):
    """UNION is one MVCC snapshot, including empty sources. Never return partial data."""
    def columns(model, source, reference, begin, finish, status, restricts, *, reason=None, actor=None, booking=None):
        return [cast(model.id, String).label('id'), literal(source).label('source'), reference.label('reference'),
                begin.label('start_at'), finish.label('end_at'), status.label('status'), restricts.label('restricts'),
                model.version.label('version'), (reason if reason is not None else cast(literal(None), String)).label('reason'),
                (cast(actor, String) if actor is not None else cast(literal(None), String)).label('recorded_by'),
                (cast(booking, String) if booking is not None else cast(literal(None), String)).label('booking_id')]
    booking = select(*columns(Booking, 'BOOKING', Booking.booking_reference, Booking.start_at, Booking.end_at, Booking.status,
        and_(Booking.vehicle_committed.is_(True), Booking.status.notin_(('CANCELLED', 'REJECTED', 'COMPLETED'))))).where(
            Booking.vehicle_id == vehicle_id, Booking.vehicle_committed.is_(True))
    departure = select(*columns(ScheduledTrip, 'DEPARTURE', ScheduledTrip.departure_reference, ScheduledTrip.departure_at,
        ScheduledTrip.estimated_arrival_at, ScheduledTrip.status, ScheduledTrip.status.notin_(('DRAFT', 'CANCELLED', 'COMPLETED')))).where(
            ScheduledTrip.current_vehicle_id == vehicle_id, ScheduledTrip.status != 'DRAFT')
    trip = select(*columns(Trip, 'TRIP', Trip.trip_reference, Trip.scheduled_start_at, Trip.scheduled_end_at, Trip.status,
        and_(Trip.assignment_status == 'ACCEPTED', Trip.status.notin_(('CANCELLED', 'COMPLETED'))), booking=Trip.booking_id)).where(
            Trip.vehicle_id == vehicle_id, Trip.assignment_status == 'ACCEPTED')
    block = select(*columns(VehicleRecord, 'BLOCK', cast(VehicleRecord.id, String), VehicleRecord.start_at, VehicleRecord.end_at,
        VehicleRecord.approval_status, or_(VehicleRecord.approval_status.is_(None), VehicleRecord.approval_status.notin_(WITHDRAWN)),
        reason=VehicleRecord.notes, actor=VehicleRecord.recorded_by_user_id)).where(
            VehicleRecord.vehicle_id == vehicle_id, VehicleRecord.record_type == 'AVAILABILITY_BLOCK')
    source = union_all(booking, departure, trip, block).subquery()
    try:
        rows = db.execute(select(source).where(source.c.start_at < end, source.c.end_at > start)
                          .order_by(source.c.start_at, source.c.source, source.c.id).limit(2001)).mappings().all()
    except SQLAlchemyError:
        raise incomplete() from None
    if len(rows) > 2000:
        raise ApiError(503, 'AVAILABILITY_INCOMPLETE', 'Too many calendar entries to check completely. Narrow the date range.')
    return [dict(row) for row in rows]


def protected(events, exclude=None):
    return [e for e in events if e['restricts'] and e['source'] != 'BLOCK'
            and not (exclude and (e['source'] == 'BOOKING' and e['id'] == str(exclude) or e['booking_id'] == str(exclude)))]


def references(events):
    return [{k: e[k] for k in ('source', 'id', 'reference', 'status', 'start_at', 'end_at')} for e in events]


def no_vehicle_conflict(db, vehicle_id, start, end, exclude=None):
    events = occupancy(db, vehicle_id, start, end)
    if protected(events, exclude) or any(e['source'] == 'BLOCK' and e['restricts'] for e in events):
        raise ApiError(409, 'VEHICLE_SCHEDULE_CONFLICT', 'This interval overlaps a vehicle block or protected commitment. Resolve it before new use.')
