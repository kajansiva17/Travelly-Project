"""Protected fulfilment of Ticket departures (matrix 54-58), first slice. Binding rules: PRD Final Decisions D08,
data dictionary scheduled_trips lifecycle, owner decisions of 12 Nov 2026.

    POST /scheduled-trips/{id}/commit                  Owner: "this departure will run" (minimum-seats policy, or
                                                        taking back a reported problem)
    POST /scheduled-trips/{id}/problem                 Owner: "I cannot run it" -> DISRUPTED, Admin is alerted.
                                                        An unsold departure (no paid seat, no live hold) is simply cancelled.
    GET  /admin/departures/attention                   Admin: departures that need a decision (missed deadline / problem)
    POST /admin/scheduled-trips/{id}/cannot-fulfil     Admin: Travelly cannot run it -> CANCELLED, every paid seat
                                                        refunded 100% (approved at once), holds released

D08: a missed decision deadline never cancels, refunds or commits by itself. It only moves the departure to
DECISION_REQUIRED and alerts the Admin (escalate_missed_deadlines, also run by scripts/escalate_departure_deadlines.py).
Bookings stay CONFIRMED while Travelly works on it. Refund for non-fulfilment only when Travelly cannot fulfil.
Slice 2 (owner decisions 12 Nov 2026):
    POST /scheduled-trips/{id}/replacement-vehicle     Owner puts one of their own vehicles in. Any type, but enough
                                                        bookable seats for every booked passenger; approved, active and free
                                                        at that time. Seats move automatically (same seat code if it
                                                        exists, else the next free seat). The departure runs (COMMITTED).
    POST /bookings/{id}/replacement-decision           Passenger: ACCEPT, or REJECT -> booking cancelled, 100% refund
                                                        queued for Admin approval. No answer = travels in the replacement.
A replacement from another Owner is not built: NBP excludes automatic cross-owner settlement.

Lock order as everywhere: scheduled_trips -> bookings (by id) -> scheduled_trip_seats (by id) -> payments.
"""
import copy
from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.api.routers.api import current, require_role, touch
from app.api.routers.refund_api import approve
from app.api.routers.review_api import admin, locked_authority
from app.api.routers.ticket_booking_api import cancel as cancel_booking, free, lock_trip
from app.core.errors import ApiError
from app.dependencies.database import get_db
from app.models import User, UserRole
from app.models.hire_models import Booking, Notification, Route, ScheduledTrip, Trip
from app.models.payment_models import Payment
from app.models.review_models import Vehicle
from app.models.seat_models import BookingTraveller, ScheduledTripSeat, VehicleSeat
from app.schemas.scheduled_trip_schemas import DepartureCommit, DepartureProblem, ReplacementDecision, ReplacementVehicle
from app.services.availability import no_vehicle_conflict
from app.services.refunds import queue_refund

router = APIRouter(prefix='/api/v1', tags=['Protected fulfilment'])
MINIMUM = 'MINIMUM_SEATS_WITH_PROTECTED_FULFILMENT'
OPEN = ('PUBLISHED', 'BOOKING_OPEN')                       # selling, no commitment yet (minimum-seats policy)
ATTENTION = ('DECISION_REQUIRED', 'DISRUPTED')             # waiting for Travelly
COMMITTABLE = OPEN + ATTENTION
REPORTABLE = OPEN + ('COMMITTED', 'DECISION_REQUIRED', 'READY')
REJECTED_CHANGE = {'policy': 'REPLACEMENT_REJECTED_2026_11', 'refund_percent': 100,
                   'rule': 'Owner decision 12 Nov 2026: a Passenger who rejects the replacement vehicle gets a full refund.'}
NOT_FULFILLED = {'policy': 'DEPARTURE_NOT_FULFILLED_2026_11', 'refund_percent': 100,
                 'rule': 'D08: Travelly could not fulfil the protected journey; every paid seat is refunded in full.'}


def now():
    return datetime.now(timezone.utc)


def notify(db, recipient, departure, kind, title, body, booking=None, action=False):
    db.add(Notification(recipient_user_id=recipient, booking_id=booking.id if booking else None, scheduled_trip_id=departure.id,
                        notification_type=kind, channel='IN_APP', title=title, body=body, action_required=action,
                        action_payload={'scheduled_trip_id': str(departure.id), **({'booking_id': str(booking.id)} if booking else {})},
                        status='QUEUED'))


def admins(db):
    return db.scalars(select(UserRole.user_id).where(UserRole.role_code == 'ADMIN', UserRole.approval_status == 'APPROVED')
                      .order_by(UserRole.user_id)).all()


def bookings_of(db, departure, statuses=('REQUESTED', 'CONFIRMED'), lock=False):
    query = select(Booking).where(Booking.current_scheduled_trip_id == departure.id, Booking.booking_type == 'TICKET_HIRE',
                                  Booking.status.in_(statuses)).order_by(Booking.id)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    return db.scalars(query).all()


def counts(db, departure):
    booked = db.scalar(select(func.count()).select_from(ScheduledTripSeat).where(
        ScheduledTripSeat.scheduled_trip_id == departure.id, ScheduledTripSeat.seat_status == 'BOOKED')) or 0
    held = db.scalar(select(func.count()).select_from(ScheduledTripSeat).where(
        ScheduledTripSeat.scheduled_trip_id == departure.id, ScheduledTripSeat.seat_status == 'HELD',
        ScheduledTripSeat.hold_expires_at > now())) or 0
    return booked, held


def journey(db, departure):
    return db.scalar(select(Trip).where(Trip.scheduled_trip_id == departure.id, Trip.status != 'CANCELLED')
                     .order_by(Trip.created_at.desc()).limit(1).with_for_update().execution_options(populate_existing=True))


def departure_out(db, departure):
    route = db.get(Route, departure.route_id)
    vehicle = db.get(Vehicle, departure.current_vehicle_id)
    booked, held = counts(db, departure)
    paid = db.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(
        Payment.booking_id.in_(select(Booking.id).where(Booking.current_scheduled_trip_id == departure.id)),
        Payment.transaction_type == 'PAYMENT', Payment.status.in_(('PAID', 'PARTIALLY_REFUNDED'))))
    owner = db.get(User, departure.owner_user_id)
    return {'id': str(departure.id), 'departure_reference': departure.departure_reference, 'status': departure.status,
            'version': departure.version, 'replacement_status': departure.replacement_status,
            'fulfilment_policy': departure.fulfilment_policy, 'minimum_confirmed_seats': departure.minimum_confirmed_seats,
            'decision_deadline': departure.decision_deadline.isoformat() if departure.decision_deadline else None,
            'committed_at': departure.committed_at.isoformat() if departure.committed_at else None,
            'departure_at': departure.departure_at.isoformat(), 'estimated_arrival_at': departure.estimated_arrival_at.isoformat(),
            'route': {'route_name': route.route_name, 'origin_name': route.origin_name, 'destination_name': route.destination_name} if route else None,
            'vehicle': {'public_vehicle_reference': vehicle.public_vehicle_reference, 'vehicle_type_code': vehicle.vehicle_type_code,
                        'seat_capacity': vehicle.seat_capacity} if vehicle else None,
            'owner': {'public_user_reference': owner.public_user_reference, 'display_name': owner.display_name or owner.full_name} if owner else None,
            'booked_seats': booked, 'held_seats': held, 'paid_amount': format(paid or 0, '.2f'), 'currency': departure.currency,
            'cancellation_reason': departure.cancellation_reason}


# --------------------------------------------------------------------------- missed deadline -> Admin (D08)

def escalate_missed_deadlines(db, moment=None):
    """Minimum-seats departures past their decision deadline without an Owner commitment move to DECISION_REQUIRED and
    the Admin is alerted. Nothing is cancelled, refunded or committed. The caller commits. Returns the count."""
    moment = moment or now()
    rows = db.scalars(select(ScheduledTrip).where(ScheduledTrip.fulfilment_policy == MINIMUM, ScheduledTrip.status.in_(OPEN),
                                                  ScheduledTrip.decision_deadline <= moment, ScheduledTrip.committed_at.is_(None))
                      .order_by(ScheduledTrip.id).with_for_update(skip_locked=True)).all()
    for departure in rows:
        departure.status = 'DECISION_REQUIRED'
        touch(departure)
        booked, _ = counts(db, departure)
        text = (f'Departure {departure.departure_reference} passed its decision deadline without the Owner committing '
                f'({booked} of {departure.minimum_confirmed_seats} minimum seats booked). The bookings stay confirmed.')
        for admin_id in admins(db):
            notify(db, admin_id, departure, 'ADMIN_ACTION', 'Departure needs a decision', text, action=True)
        notify(db, departure.owner_user_id, departure, 'RECONFIRMATION', 'Decision deadline passed',
               f'The decision deadline for {departure.departure_reference} has passed. Commit to run it, or report that you cannot.',
               action=True)
    return len(rows)


# --------------------------------------------------------------------------- Owner

def owned(db, trip_id, user):
    departure = db.get(ScheduledTrip, trip_id)
    if not departure or departure.owner_user_id != user.id:
        raise ApiError(404, 'DEPARTURE_NOT_FOUND', 'Departure not found.')
    departure = lock_trip(db, departure.id)
    return departure


def audit(request, db, user, departure, before_version, before_status, reason):
    request.app.state.audit.commit(db, actor=user.id, target={'resource': 'scheduled_trips', 'id': str(departure.id)},
                                   previous_status=before_status, new_status=departure.status, previous_version=before_version,
                                   new_version=departure.version, full_reason=reason, previous_decision_evidence=None,
                                   trace_id=request.state.trace_id)


@router.post('/scheduled-trips/{trip_id}/commit')
def commit_departure(trip_id: UUID, body: DepartureCommit, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    require_role(db, user, 'OWNER')
    with request.app.state.audit.coordinated():
        locked_authority(db, request, user, user.id, require_admin=False)
        departure = owned(db, trip_id, user)
        if departure.version != body.expected_version:
            raise ApiError(409, 'VERSION_CONFLICT', 'The departure changed. Refresh before committing.')
        if departure.status not in COMMITTABLE:
            raise ApiError(409, 'DEPARTURE_NOT_COMMITTABLE', 'Only a published departure that is not running yet can be committed.')
        if departure.fulfilment_policy != MINIMUM and departure.status in OPEN:
            raise ApiError(409, 'DEPARTURE_ALREADY_GUARANTEED', 'A fixed departure is already guaranteed; there is nothing to commit.')
        if departure.departure_at <= now():
            raise ApiError(409, 'DEPARTURE_STARTED', 'The departure time has passed.')
        before_version, before_status = departure.version, departure.status
        departure.status = 'COMMITTED'
        departure.committed_at = departure.committed_at or now()
        departure.final_operating_owner_user_id = departure.owner_user_id
        touch(departure); departure.updated_by = user.id
        for booking in bookings_of(db, departure, ('CONFIRMED',)):
            notify(db, booking.passenger_user_id, departure, 'BOOKING_CONFIRMED', 'Your departure will run',
                   f'The Owner confirmed that departure {departure.departure_reference} will run as booked.', booking)
        if before_status in ATTENTION:
            for admin_id in admins(db):
                notify(db, admin_id, departure, 'ADMIN_ACTION', 'Departure resolved by the Owner',
                       f'The Owner committed to run {departure.departure_reference}. No action is needed.')
        audit(request, db, user, departure, before_version, before_status, 'Owner committed to run the departure.')
    return departure_out(db, departure)


@router.post('/scheduled-trips/{trip_id}/problem')
def report_problem(trip_id: UUID, body: DepartureProblem, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    require_role(db, user, 'OWNER')
    with request.app.state.audit.coordinated():
        locked_authority(db, request, user, user.id, require_admin=False)
        departure = owned(db, trip_id, user)
        if departure.version != body.expected_version:
            raise ApiError(409, 'VERSION_CONFLICT', 'The departure changed. Refresh before reporting.')
        run = journey(db, departure)
        if departure.status not in REPORTABLE or (run and run.status != 'READY'):
            raise ApiError(409, 'DEPARTURE_NOT_REPORTABLE', 'A problem can be reported only before the departure starts.')
        moment = now()
        before_version, before_status = departure.version, departure.status
        holds = bookings_of(db, departure, ('REQUESTED',), lock=True)
        confirmed = bookings_of(db, departure, ('CONFIRMED',), lock=True)
        seats = db.scalars(select(ScheduledTripSeat).where(ScheduledTripSeat.scheduled_trip_id == departure.id,
                                                            ScheduledTripSeat.seat_status == 'HELD').order_by(ScheduledTripSeat.id)
                           .with_for_update().execution_options(populate_existing=True)).all()
        # Sales stop at once: open seat holds end (any payment still waiting for them fails; money that still
        # arrives is refunded automatically, as for any hold that ended).
        for seat in seats:
            free(seat, user.id)
        for booking in holds:
            cancel_booking(db, booking, user.id, 'The departure stopped selling seats.', moment)
            notify(db, booking.passenger_user_id, departure, 'RECONFIRMATION', 'Seat hold ended',
                   f'Departure {departure.departure_reference} stopped selling seats. Your hold ended and no money was taken.', booking)
        if not confirmed:
            # Nobody has paid: there is no protected journey to fulfil, so the departure is simply withdrawn.
            departure.status = 'CANCELLED'
            departure.cancellation_reason = body.reason
            for seat in db.scalars(select(ScheduledTripSeat).where(ScheduledTripSeat.scheduled_trip_id == departure.id)
                                   .order_by(ScheduledTripSeat.id).with_for_update().execution_options(populate_existing=True)):
                seat.seat_status = 'BLOCKED'
                touch(seat); seat.updated_by = user.id
            if run:
                run.status = 'CANCELLED'
                touch(run); run.updated_by = user.id
            reason = 'Owner withdrew a departure with no paid seats: ' + body.reason
        else:
            departure.status = 'DISRUPTED'
            for admin_id in admins(db):
                notify(db, admin_id, departure, 'ADMIN_ACTION', 'Owner cannot run a departure',
                       f'The Owner reported that {departure.departure_reference} cannot run: {body.reason} '
                       f'{len(confirmed)} paid booking(s) must be fulfilled or refunded.', action=True)
            for booking in confirmed:
                notify(db, booking.passenger_user_id, departure, 'REPLACEMENT', 'We are arranging your journey',
                       f'The operator of departure {departure.departure_reference} reported a problem. Your booking stays '
                       'confirmed while Travelly arranges your journey. If it cannot run, you get a full refund.', booking)
            reason = 'Owner reported the departure cannot run: ' + body.reason
        touch(departure); departure.updated_by = user.id
        audit(request, db, user, departure, before_version, before_status, reason)
    return departure_out(db, departure)


# --------------------------------------------------------------------------- Admin

@router.get('/admin/departures/attention')
def attention(user=Depends(admin), db: Session = Depends(get_db)):
    if escalate_missed_deadlines(db):
        db.commit()
    rows = db.scalars(select(ScheduledTrip).where(ScheduledTrip.status.in_(ATTENTION)).order_by(ScheduledTrip.departure_at)).all()
    return {'items': [departure_out(db, row) for row in rows]}


@router.post('/admin/scheduled-trips/{trip_id}/cannot-fulfil')
def cannot_fulfil(trip_id: UUID, body: DepartureProblem, request: Request, user=Depends(admin), db: Session = Depends(get_db)):
    with request.app.state.audit.coordinated():
        locked_authority(db, request, user, user.id)
        if not db.get(ScheduledTrip, trip_id):
            raise ApiError(404, 'DEPARTURE_NOT_FOUND', 'Departure not found.')
        departure = lock_trip(db, trip_id)
        if departure.version != body.expected_version:
            raise ApiError(409, 'VERSION_CONFLICT', 'The departure changed. Reload before deciding.')
        if departure.status not in ATTENTION:
            raise ApiError(409, 'DEPARTURE_NOT_ESCALATED', 'Only a departure waiting for a Travelly decision can be closed as not fulfilled.')
        run = journey(db, departure)
        if run and run.status != 'READY':
            raise ApiError(409, 'DEPARTURE_STARTED', 'This departure has already started.')
        moment = now()
        before_version, before_status = departure.version, departure.status
        bookings = bookings_of(db, departure, lock=True)
        seats = db.scalars(select(ScheduledTripSeat).where(ScheduledTripSeat.scheduled_trip_id == departure.id)
                           .order_by(ScheduledTripSeat.id).with_for_update().execution_options(populate_existing=True)).all()
        for seat in seats:
            if seat.seat_status == 'HELD':
                free(seat, user.id)
            seat.seat_status = 'BLOCKED'   # booked_booking_id stays as history
            touch(seat); seat.updated_by = user.id
        refunded = []
        for booking in bookings:
            if booking.status == 'REQUESTED':
                cancel_booking(db, booking, user.id, 'Travelly could not run this departure.', moment)
                continue
            paid = db.scalars(select(Payment).where(Payment.booking_id == booking.id, Payment.transaction_type == 'PAYMENT',
                                                    Payment.status.in_(('PAID', 'PARTIALLY_REFUNDED'))).order_by(Payment.id)
                              .with_for_update().execution_options(populate_existing=True)).all()
            for traveller in db.scalars(select(BookingTraveller).where(BookingTraveller.booking_id == booking.id,
                                                                        BookingTraveller.traveller_status == 'ACTIVE')).all():
                traveller.traveller_status = 'CANCELLED'
                touch(traveller); traveller.updated_by = user.id
            booking.status = 'CANCELLED'
            booking.cancelled_by_user_id = user.id
            booking.cancelled_at = moment
            booking.cancellation_reason = body.reason
            booking.cancellation_policy_snapshot = {**copy.deepcopy(NOT_FULFILLED), 'cancelled_at': moment.isoformat()}
            touch(booking); booking.updated_by = user.id
            total = 0
            for payment in paid:
                refund = queue_refund(db, payment, payment.amount, 'DEPARTURE_NOT_FULFILLED', user.id)
                if refund:
                    # The Admin's decision here is the approval: Sandbox money goes back now, PayHere waits in PROCESSING.
                    approve(db, refund, payment, booking, user.id)
                    total += refund.amount
                    refunded.append(refund)
            notify(db, booking.passenger_user_id, departure, 'REFUND', 'Departure cancelled - full refund',
                   f'Travelly could not run departure {departure.departure_reference}. Booking {booking.booking_reference} is '
                   f'cancelled and {format(total, ".2f")} {departure.currency} is being refunded in full.', booking)
        if run:
            run.status = 'CANCELLED'
            touch(run); run.updated_by = user.id
        departure.status = 'CANCELLED'
        departure.replacement_status = 'FAILED'
        departure.cancellation_reason = body.reason
        touch(departure); departure.updated_by = user.id
        notify(db, departure.owner_user_id, departure, 'ADMIN_ACTION', 'Departure cancelled by Travelly',
               f'Travelly closed {departure.departure_reference} as not fulfilled: {body.reason} Paid seats are refunded in full.')
        audit(request, db, user, departure, before_version, before_status, 'Travelly cannot fulfil the departure: ' + body.reason)
    return {**departure_out(db, departure), 'refunds': [{'id': str(r.id), 'booking_id': str(r.booking_id), 'amount': format(r.amount, '.2f'),
                                                         'status': r.status} for r in refunded]}


# --------------------------------------------------------------------------- slice 2: replacement vehicle

def summary(vehicle):
    return {'public_vehicle_reference': vehicle.public_vehicle_reference, 'vehicle_type_code': vehicle.vehicle_type_code,
            'make': vehicle.make, 'model': vehicle.model, 'colour': vehicle.colour, 'air_conditioned': vehicle.air_conditioned,
            'seat_capacity': vehicle.seat_capacity}


def bookable_seats(db, vehicle_id):
    version = db.scalar(select(func.max(VehicleSeat.layout_version)).where(VehicleSeat.vehicle_id == vehicle_id,
                                                                            VehicleSeat.is_active.is_(True)))
    if version is None:
        return []
    return db.scalars(select(VehicleSeat).where(VehicleSeat.vehicle_id == vehicle_id, VehicleSeat.layout_version == version,
                                                VehicleSeat.is_active.is_(True), VehicleSeat.is_bookable.is_(True))
                      .order_by(VehicleSeat.deck_number, VehicleSeat.row_number, VehicleSeat.column_number)).all()


@router.post('/scheduled-trips/{trip_id}/replacement-vehicle')
def replacement_vehicle(trip_id: UUID, body: ReplacementVehicle, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    require_role(db, user, 'OWNER')
    with request.app.state.audit.coordinated():
        locked_authority(db, request, user, user.id, require_admin=False)
        departure = owned(db, trip_id, user)
        if departure.version != body.expected_version:
            raise ApiError(409, 'VERSION_CONFLICT', 'The departure changed. Refresh before choosing a vehicle.')
        run = journey(db, departure)
        if departure.status not in ATTENTION or (run and run.status != 'READY') or departure.departure_at <= now():
            raise ApiError(409, 'REPLACEMENT_NOT_ALLOWED', 'A replacement vehicle can be set only for a departure waiting for a decision, before it starts.')
        vehicle = db.scalar(select(Vehicle).where(Vehicle.id == body.vehicle_id).with_for_update())
        if (not vehicle or vehicle.owner_user_id != user.id or vehicle.verification_status != 'APPROVED'
                or vehicle.availability_status != 'ACTIVE' or vehicle.id == departure.current_vehicle_id):
            raise ApiError(409, 'REPLACEMENT_VEHICLE_UNAVAILABLE', 'Choose another approved, active vehicle that you own.')
        moment = now()
        holds = bookings_of(db, departure, ('REQUESTED',), lock=True)
        confirmed = bookings_of(db, departure, ('CONFIRMED',), lock=True)
        old_rows = db.execute(select(ScheduledTripSeat, VehicleSeat).join(VehicleSeat, VehicleSeat.id == ScheduledTripSeat.vehicle_seat_id)
                              .where(ScheduledTripSeat.scheduled_trip_id == departure.id, VehicleSeat.vehicle_id == departure.current_vehicle_id)
                              .order_by(ScheduledTripSeat.id).with_for_update(of=ScheduledTripSeat)
                              .execution_options(populate_existing=True)).all()
        booked = sorted([(inv, seat) for inv, seat in old_rows if inv.seat_status == 'BOOKED'],
                        key=lambda pair: (pair[1].deck_number, pair[1].row_number, pair[1].column_number))
        targets = bookable_seats(db, vehicle.id)
        if len(targets) < len(booked):
            raise ApiError(409, 'REPLACEMENT_TOO_SMALL',
                           f'This vehicle has {len(targets)} bookable seats; {len(booked)} passengers are booked.')
        no_vehicle_conflict(db, vehicle.id, departure.departure_at, departure.estimated_arrival_at)
        before_version, before_status = departure.version, departure.status
        previous = db.get(Vehicle, departure.current_vehicle_id)
        # Open holds end first (sales are stopped while Travelly decides).
        for inv, _ in old_rows:
            if inv.seat_status == 'HELD':
                free(inv, user.id)
        for booking in holds:
            cancel_booking(db, booking, user.id, 'The departure changed vehicle.', moment)
        # Seat mapping: the same seat code when the replacement has it, otherwise the next free seat in order.
        by_code = {seat.seat_code: seat for seat in targets}
        taken, plan = set(), {}
        for inv, seat in booked:
            if seat.seat_code in by_code and by_code[seat.seat_code].id not in taken:
                plan[inv.id] = by_code[seat.seat_code]
                taken.add(plan[inv.id].id)
        for inv, seat in booked:
            if inv.id not in plan:
                plan[inv.id] = next(t for t in targets if t.id not in taken)
                taken.add(plan[inv.id].id)
        new_rows = {}
        for target in targets:
            owner_of = next((inv.booked_booking_id for inv, _ in booked if plan[inv.id].id == target.id), None)
            row = ScheduledTripSeat(scheduled_trip_id=departure.id, vehicle_seat_id=target.id,
                                    seat_status='BOOKED' if owner_of else 'AVAILABLE', booked_booking_id=owner_of,
                                    created_by=user.id, updated_by=user.id)
            db.add(row)
            new_rows[target.id] = row
        for inv, _ in old_rows:
            inv.seat_status = 'BLOCKED'   # the original vehicle's inventory stays as history
            touch(inv); inv.updated_by = user.id
        db.flush()
        moved = {inv.id: (seat.seat_code, plan[inv.id].seat_code, new_rows[plan[inv.id].id].id) for inv, seat in booked}
        for booking in confirmed:
            changes = []
            for traveller in db.scalars(select(BookingTraveller).where(BookingTraveller.booking_id == booking.id,
                                                                        BookingTraveller.traveller_status == 'ACTIVE')
                                        .order_by(BookingTraveller.id).with_for_update()).all():
                if traveller.scheduled_trip_seat_id in moved:
                    old_code, new_code, new_id = moved[traveller.scheduled_trip_seat_id]
                    changes.append({'full_name': traveller.full_name, 'from_seat': old_code, 'to_seat': new_code,
                                    'old_seat_id': str(traveller.scheduled_trip_seat_id), 'seat_id': str(new_id)})
                    traveller.scheduled_trip_seat_id = new_id
                    touch(traveller); traveller.updated_by = user.id
            ids = {c['old_seat_id']: c['seat_id'] for c in changes}
            snapshot = copy.deepcopy(booking.price_snapshot)
            for item in snapshot.get('seats', []):
                if item.get('seat_id') in ids:
                    item['original_seat_id'] = item.get('original_seat_id') or item['seat_id']
                    item['seat_id'] = ids[item['seat_id']]
            booking.price_snapshot = snapshot
            booking.vehicle_id = vehicle.id
            booking.pending_change = {'kind': 'REPLACEMENT_VEHICLE', 'status': 'PENDING', 'proposed_at': moment.isoformat(),
                                      'scheduled_trip_id': str(departure.id), 'previous_vehicle': summary(previous),
                                      'replacement_vehicle': summary(vehicle),
                                      'seats': [{k: v for k, v in c.items() if k != 'old_seat_id'} for c in changes],
                                      'refund_if_rejected_percent': 100, 'decided_at': None}
            touch(booking); booking.updated_by = user.id
            notify(db, booking.passenger_user_id, departure, 'REPLACEMENT', 'Your journey has a replacement vehicle',
                   f'Departure {departure.departure_reference} will run with a different vehicle '
                   f'({vehicle.vehicle_type_code.title()}, {vehicle.make} {vehicle.model}). Check your new seat. '
                   'If you do not want to travel in it, reject the change for a full refund.', booking, action=True)
        if run:
            run.vehicle_id = vehicle.id
            touch(run); run.updated_by = user.id
        departure.current_vehicle_id = vehicle.id
        departure.final_operating_owner_user_id = departure.owner_user_id
        departure.replacement_status = 'APPROVED'
        departure.status = 'COMMITTED'
        departure.committed_at = departure.committed_at or moment
        touch(departure); departure.updated_by = user.id
        for admin_id in admins(db):
            notify(db, admin_id, departure, 'ADMIN_ACTION', 'Departure resolved with a replacement vehicle',
                   f'The Owner replaced the vehicle of {departure.departure_reference}. Passengers can accept or reject the change.')
        audit(request, db, user, departure, before_version, before_status,
              f'Owner replacement vehicle {vehicle.public_vehicle_reference} instead of {previous.public_vehicle_reference}.')
    return {**departure_out(db, departure), 'moved_seats': len(booked)}


@router.post('/bookings/{booking_id}/replacement-decision')
def replacement_decision(booking_id: UUID, body: ReplacementDecision, user=Depends(current), db: Session = Depends(get_db)):
    row = db.get(Booking, booking_id)
    if not row or row.booking_type != 'TICKET_HIRE' or row.passenger_user_id != user.id:
        raise ApiError(404, 'BOOKING_NOT_FOUND', 'Booking not found.')
    departure = lock_trip(db, row.current_scheduled_trip_id)
    booking = db.scalar(select(Booking).where(Booking.id == booking_id).with_for_update().execution_options(populate_existing=True))
    change = booking.pending_change or {}
    if change.get('kind') != 'REPLACEMENT_VEHICLE' or change.get('status') != 'PENDING' or booking.status != 'CONFIRMED':
        raise ApiError(409, 'NO_PENDING_CHANGE', 'There is no vehicle change waiting for your answer.')
    if booking.version != body.expected_version:
        raise ApiError(409, 'VERSION_CONFLICT', 'The booking changed. Refresh before answering.')
    run = journey(db, departure)
    moment = now()
    if departure.departure_at <= moment or (run and run.status != 'READY'):
        raise ApiError(409, 'DEPARTURE_STARTED', 'The departure has started; the change can no longer be rejected.')
    decided = {**change, 'status': 'ACCEPTED' if body.decision == 'ACCEPT' else 'REJECTED', 'decided_at': moment.isoformat()}
    booking.pending_change = decided
    refund = None
    if body.decision == 'REJECT':
        seats = db.scalars(select(ScheduledTripSeat).where(ScheduledTripSeat.booked_booking_id == booking.id,
                                                            ScheduledTripSeat.scheduled_trip_id == departure.id,
                                                            ScheduledTripSeat.seat_status == 'BOOKED')
                           .order_by(ScheduledTripSeat.id).with_for_update().execution_options(populate_existing=True)).all()
        paid = db.scalars(select(Payment).where(Payment.booking_id == booking.id, Payment.transaction_type == 'PAYMENT',
                                                Payment.status.in_(('PAID', 'PARTIALLY_REFUNDED'))).order_by(Payment.id)
                          .with_for_update().execution_options(populate_existing=True)).all()
        for seat in seats:
            seat.seat_status, seat.booked_booking_id = 'AVAILABLE', None
            touch(seat); seat.updated_by = user.id
        for traveller in db.scalars(select(BookingTraveller).where(BookingTraveller.booking_id == booking.id,
                                                                    BookingTraveller.traveller_status == 'ACTIVE')).all():
            traveller.traveller_status = 'CANCELLED'
            touch(traveller); traveller.updated_by = user.id
        booking.status = 'CANCELLED'
        booking.cancelled_by_user_id = user.id
        booking.cancelled_at = moment
        booking.cancellation_reason = 'Passenger rejected the replacement vehicle.'
        booking.cancellation_policy_snapshot = {**copy.deepcopy(REJECTED_CHANGE), 'cancelled_at': moment.isoformat()}
        for payment in paid:
            # System computes, Admin approves (owner decision 11 Nov), as for any Passenger cancellation.
            refund = queue_refund(db, payment, payment.amount, 'REPLACEMENT_REJECTED', user.id) or refund
        notify(db, booking.passenger_user_id, departure, 'REFUND', 'Booking cancelled - full refund',
               f'You rejected the replacement vehicle for {departure.departure_reference}. Booking {booking.booking_reference} '
               'is cancelled and a full refund is on its way.', booking)
        notify(db, departure.owner_user_id, departure, 'ADMIN_ACTION', 'A passenger rejected the replacement vehicle',
               f'Booking {booking.booking_reference} on {departure.departure_reference} was cancelled with a full refund.')
    touch(booking); booking.updated_by = user.id
    db.commit()
    return {'booking_id': str(booking.id), 'status': booking.status, 'version': booking.version, 'pending_change': decided,
            'refund': None if refund is None else {'id': str(refund.id), 'amount': format(refund.amount, '.2f'), 'status': refund.status}}
