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
import secrets
from datetime import datetime, timezone
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, Request
from sqlalchemy import and_, func, or_, select
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
from app.schemas.scheduled_trip_schemas import AdminReplacementAsk, DepartureCommit, DepartureProblem, ReplacementAnswer, ReplacementDecision, ReplacementVehicle
from app.services.airports import km_between
from app.services.availability import no_vehicle_conflict
from app.services import payhere_refunds
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
            'cancellation_reason': departure.cancellation_reason, 'arrangement': departure.arrangement,
            'pending_offers': pending_offers(db, departure)}


# --------------------------------------------------------------------------- missed deadline -> Admin (D08)

def pending_offers(db, departure):
    """Replacement offers still waiting for another Owner's answer (Travelly may have asked several at once)."""
    return db.scalar(select(func.count()).select_from(ScheduledTrip).where(ScheduledTrip.offer_for_scheduled_trip_id == departure.id,
                                                                           ScheduledTrip.status == 'DRAFT')) or 0


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
        if departure.replacement_status == 'AWAITING_OTHER_OWNER':
            raise ApiError(409, 'REPLACEMENT_PENDING', 'Another Owner is still answering a replacement request for this departure.')
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
            departure.arrangement = body.arrangement
            for admin_id in admins(db):
                if body.arrangement == 'TRAVELLY':
                    notify(db, admin_id, departure, 'ADMIN_ACTION', 'Owner cannot run a departure',
                           f'The Owner reported that {departure.departure_reference} cannot run: {body.reason} '
                           f'{len(confirmed)} paid booking(s) must be fulfilled or refunded. The Owner asks Travelly to arrange the journey.', action=True)
                else:
                    notify(db, admin_id, departure, 'ADMIN_ACTION', 'Owner cannot run a departure',
                           f'The Owner reported that {departure.departure_reference} cannot run: {body.reason} '
                           f'{len(confirmed)} paid booking(s) are affected. The Owner is arranging another vehicle, so no action is needed yet.')
            for booking in confirmed:
                notify(db, booking.passenger_user_id, departure, 'REPLACEMENT', 'We are arranging your journey',
                       f'The operator of departure {departure.departure_reference} reported a problem. Your booking stays '
                       'confirmed while Travelly arranges your journey. If it cannot run, you get a full refund.', booking)
            reason = 'Owner reported the departure cannot run: ' + body.reason
        touch(departure); departure.updated_by = user.id
        audit(request, db, user, departure, before_version, before_status, reason)
    return departure_out(db, departure)


@router.post('/scheduled-trips/{trip_id}/ask-travelly')
def ask_travelly(trip_id: UUID, body: DepartureCommit, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    """The Owner reported a problem and was arranging another vehicle, but now asks Travelly to arrange the journey."""
    require_role(db, user, 'OWNER')
    with request.app.state.audit.coordinated():
        locked_authority(db, request, user, user.id, require_admin=False)
        departure = owned(db, trip_id, user)
        if departure.version != body.expected_version:
            raise ApiError(409, 'VERSION_CONFLICT', 'The departure changed. Refresh before asking Travelly.')
        if departure.status != 'DISRUPTED':
            raise ApiError(409, 'DEPARTURE_NOT_DISRUPTED', 'Only a departure whose problem was reported can be handed to Travelly.')
        if departure.replacement_status == 'AWAITING_OTHER_OWNER':
            raise ApiError(409, 'REPLACEMENT_PENDING', 'Another Owner is still answering a replacement request for this departure.')
        if departure.departure_at <= now():
            raise ApiError(409, 'DEPARTURE_STARTED', 'The departure time has passed.')
        before_version, before_status = departure.version, departure.status
        departure.arrangement = 'TRAVELLY'
        touch(departure); departure.updated_by = user.id
        for admin_id in admins(db):
            notify(db, admin_id, departure, 'ADMIN_ACTION', 'Owner asks Travelly to arrange a departure',
                   f'The Owner of {departure.departure_reference} could not arrange another vehicle and asks Travelly to arrange the journey.', action=True)
        audit(request, db, user, departure, before_version, before_status, 'Owner asked Travelly to arrange the journey.')
    return departure_out(db, departure)


# --------------------------------------------------------------------------- Admin

@router.get('/admin/departures/attention')
def attention(user=Depends(admin), db: Session = Depends(get_db)):
    if escalate_missed_deadlines(db):
        db.commit()
    # A disrupted departure is the Admin's job only when the Owner asked Travelly to arrange it (older ones have no choice recorded).
    waiting = or_(ScheduledTrip.status == 'DECISION_REQUIRED',
                  and_(ScheduledTrip.status == 'DISRUPTED', or_(ScheduledTrip.arrangement.is_(None), ScheduledTrip.arrangement == 'TRAVELLY')))
    rows = db.scalars(select(ScheduledTrip).where(waiting).order_by(ScheduledTrip.departure_at)).all()
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
        withdraw_offers(db, departure, user.id, 'Travelly closed the original departure as not fulfilled.')
        departure.status = 'CANCELLED'
        departure.replacement_status = 'FAILED'
        departure.cancellation_reason = body.reason
        touch(departure); departure.updated_by = user.id
        notify(db, departure.owner_user_id, departure, 'ADMIN_ACTION', 'Departure cancelled by Travelly',
               f'Travelly closed {departure.departure_reference} as not fulfilled: {body.reason} Paid seats are refunded in full.')
        audit(request, db, user, departure, before_version, before_status, 'Travelly cannot fulfil the departure: ' + body.reason)
    # PayHere refunds go out through the Refund API after the decision is committed (when it is set up).
    waiting = [r.id for r in refunded if r.status == 'PROCESSING' and r.provider_name == 'PAYHERE']
    if waiting:
        payhere_refunds.push_many(request.app.state.sessions, waiting, user.id)
        for r in refunded:
            db.refresh(r)
    return {**departure_out(db, departure), 'refunds': [{'id': str(r.id), 'booking_id': str(r.booking_id), 'amount': format(r.amount, '.2f'),
                                                         'status': r.status, 'failure_code': r.failure_code} for r in refunded]}


# --------------------------------------------------------------------------- slice 2: replacement vehicle

def summary(vehicle, owner=None):
    out = {'public_vehicle_reference': vehicle.public_vehicle_reference, 'vehicle_type_code': vehicle.vehicle_type_code,
           'make': vehicle.make, 'model': vehicle.model, 'display_name': vehicle.display_name, 'colour': vehicle.colour, 'air_conditioned': vehicle.air_conditioned,
           'seat_capacity': vehicle.seat_capacity}
    if owner is not None:
        out['operator_name'] = owner.display_name or owner.full_name
    return out


def bookable_seats(db, vehicle_id):
    version = db.scalar(select(func.max(VehicleSeat.layout_version)).where(VehicleSeat.vehicle_id == vehicle_id,
                                                                            VehicleSeat.is_active.is_(True)))
    if version is None:
        return []
    return db.scalars(select(VehicleSeat).where(VehicleSeat.vehicle_id == vehicle_id, VehicleSeat.layout_version == version,
                                                VehicleSeat.is_active.is_(True), VehicleSeat.is_bookable.is_(True))
                      .order_by(VehicleSeat.deck_number, VehicleSeat.row_number, VehicleSeat.column_number)).all()


def booked_count(db, departure):
    return counts(db, departure)[0]


def vehicle_fits(db, vehicle, departure, needed, *, other_owner):
    """None when the vehicle can take this departure, otherwise (code, message)."""
    if (not vehicle or vehicle.verification_status != 'APPROVED' or vehicle.availability_status != 'ACTIVE'
            or vehicle.id == departure.current_vehicle_id
            or (vehicle.owner_user_id == departure.owner_user_id) == other_owner
            or (other_owner and not vehicle.is_published)):
        return ('REPLACEMENT_VEHICLE_UNAVAILABLE', 'Choose another approved, active vehicle.' if other_owner
                else 'Choose another approved, active vehicle that you own.')
    original = db.get(Vehicle, departure.current_vehicle_id)
    if original is not None and original.air_conditioned is True and vehicle.air_conditioned is not True:
        return ('REPLACEMENT_NOT_AIR_CONDITIONED', 'The booked vehicle is air-conditioned, so the replacement must be too.')
    seats = len(bookable_seats(db, vehicle.id))
    if seats < needed:
        return ('REPLACEMENT_TOO_SMALL', f'This vehicle has {seats} bookable seats; {needed} passengers are booked.')
    try:
        no_vehicle_conflict(db, vehicle.id, departure.departure_at, departure.estimated_arrival_at)
    except ApiError as exc:
        return (exc.code, exc.message)
    return None


def require_fit(db, vehicle, departure, needed, *, other_owner):
    problem_found = vehicle_fits(db, vehicle, departure, needed, other_owner=other_owner)
    if problem_found:
        raise ApiError(409, problem_found[0], problem_found[1])


def waiting_for_travelly(departure, run):
    if departure.status not in ATTENTION or (run and run.status != 'READY') or departure.departure_at <= now():
        raise ApiError(409, 'REPLACEMENT_NOT_ALLOWED', 'A replacement vehicle can be set only for a departure waiting for a decision, before it starts.')
    if departure.replacement_status == 'AWAITING_OTHER_OWNER':
        raise ApiError(409, 'REPLACEMENT_PENDING', 'Another Owner is still answering a replacement request for this departure.')


def move_passengers(db, actor, source, target, vehicle, moment):
    """Move every paid passenger of `source` onto `vehicle`, running as departure `target` (the same departure for the
    Owner's own vehicle, a new one for another Owner's vehicle). Seats: the same seat code when the vehicle has it,
    otherwise the next free seat, front to back. The source inventory stays as BLOCKED history; open holds end.
    Returns the number of moved seats. Lock order: departures already locked -> bookings -> seats."""
    holds = bookings_of(db, source, ('REQUESTED',), lock=True)
    confirmed = bookings_of(db, source, ('CONFIRMED',), lock=True)
    old_rows = db.execute(select(ScheduledTripSeat, VehicleSeat).join(VehicleSeat, VehicleSeat.id == ScheduledTripSeat.vehicle_seat_id)
                          .where(ScheduledTripSeat.scheduled_trip_id == source.id, VehicleSeat.vehicle_id == source.current_vehicle_id)
                          .order_by(ScheduledTripSeat.id).with_for_update(of=ScheduledTripSeat)
                          .execution_options(populate_existing=True)).all()
    booked = sorted([(inv, seat) for inv, seat in old_rows if inv.seat_status == 'BOOKED'],
                    key=lambda pair: (pair[1].deck_number, pair[1].row_number, pair[1].column_number))
    targets = bookable_seats(db, vehicle.id)
    if len(targets) < len(booked):
        raise ApiError(409, 'REPLACEMENT_TOO_SMALL', f'This vehicle has {len(targets)} bookable seats; {len(booked)} passengers are booked.')
    previous = db.get(Vehicle, source.current_vehicle_id)
    operator = db.get(User, target.owner_user_id) if target.owner_user_id != source.owner_user_id else None
    for inv, _ in old_rows:
        if inv.seat_status == 'HELD':
            free(inv, actor)
    for booking in holds:
        cancel_booking(db, booking, actor, 'The departure changed vehicle.', moment)
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
    for item in targets:
        owner_of = next((inv.booked_booking_id for inv, _ in booked if plan[inv.id].id == item.id), None)
        row = ScheduledTripSeat(scheduled_trip_id=target.id, vehicle_seat_id=item.id, seat_status='BOOKED' if owner_of else 'AVAILABLE',
                                booked_booking_id=owner_of, created_by=actor, updated_by=actor)
        db.add(row)
        new_rows[item.id] = row
    for inv, _ in old_rows:
        inv.seat_status = 'BLOCKED'
        touch(inv); inv.updated_by = actor
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
                touch(traveller); traveller.updated_by = actor
        ids = {c['old_seat_id']: c['seat_id'] for c in changes}
        snapshot = copy.deepcopy(booking.price_snapshot)
        for item in snapshot.get('seats', []):
            if item.get('seat_id') in ids:
                item['original_seat_id'] = item.get('original_seat_id') or item['seat_id']
                item['seat_id'] = ids[item['seat_id']]
        booking.price_snapshot = snapshot
        booking.vehicle_id = vehicle.id
        booking.requested_owner_user_id = booking.requested_owner_user_id or booking.owner_user_id  # the Owner first chosen
        booking.current_scheduled_trip_id = target.id
        booking.owner_user_id = target.owner_user_id
        booking.pending_change = {'kind': 'REPLACEMENT_VEHICLE', 'status': 'PENDING', 'proposed_at': moment.isoformat(),
                                  'scheduled_trip_id': str(target.id), 'operator_changed': operator is not None,
                                  'previous_vehicle': summary(previous), 'replacement_vehicle': summary(vehicle, operator),
                                  'seats': [{k: v for k, v in c.items() if k != 'old_seat_id'} for c in changes],
                                  'refund_if_rejected_percent': 100, 'decided_at': None}
        touch(booking); booking.updated_by = actor
        if operator is not None:
            reallocate(db, booking, target.owner_user_id, target, actor)
        notify(db, booking.passenger_user_id, target, 'REPLACEMENT', 'Your journey has a replacement vehicle',
               f'Your departure will run with a different vehicle ({vehicle.vehicle_type_code.title()}, {vehicle.display_name or str(vehicle.make) + " " + str(vehicle.model)})'
               + (f' operated by {operator.display_name or operator.full_name}' if operator else '')
               + '. Check your new seat. If you do not want to travel in it, reject the change for a full refund.', booking, action=True)
    return len(booked)


def reallocate(db, booking, new_owner_id, target, actor):
    """PRD: append linked reallocation events, never rewrite captured payments. The Owner share of each paid seat payment
    moves to the Owner who now runs the journey; Travelly's Admin pays it out as usual after completion (no automatic
    cross-owner settlement). The row it replaces is marked REALLOCATED."""
    rows = db.scalars(select(Payment).where(Payment.booking_id == booking.id, Payment.transaction_type.in_(('PAYMENT', 'REALLOCATION')),
                                            Payment.status.in_(('PAID', 'PARTIALLY_REFUNDED')), Payment.owner_settlement_status.is_(None))
                      .order_by(Payment.id).with_for_update().execution_options(populate_existing=True)).all()
    for row in rows:
        captured = row.original_payment_id if row.transaction_type == 'REALLOCATION' else row.id
        row.owner_settlement_status = 'REALLOCATED'
        touch(row); row.updated_by = actor
        db.add(Payment(payment_reference='RAL-' + uuid4().hex[:20].upper(), booking_id=booking.id, original_payment_id=captured,
                       payee_owner_user_id=new_owner_id, transaction_type='REALLOCATION', payment_method=row.payment_method,
                       provider_name=row.provider_name, provider_reference=row.provider_reference,
                       idempotency_key=f'reallocation:{captured}:{target.id}', amount=row.amount,
                       commission_amount=row.commission_amount, owner_net_amount=row.owner_net_amount, currency=row.currency,
                       status=row.status, captured_at=row.captured_at, created_by=actor, updated_by=actor))


@router.post('/scheduled-trips/{trip_id}/replacement-vehicle')
def replacement_vehicle(trip_id: UUID, body: ReplacementVehicle, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    require_role(db, user, 'OWNER')
    with request.app.state.audit.coordinated():
        locked_authority(db, request, user, user.id, require_admin=False)
        departure = owned(db, trip_id, user)
        if departure.version != body.expected_version:
            raise ApiError(409, 'VERSION_CONFLICT', 'The departure changed. Refresh before choosing a vehicle.')
        run = journey(db, departure)
        waiting_for_travelly(departure, run)
        vehicle = db.scalar(select(Vehicle).where(Vehicle.id == body.vehicle_id).with_for_update())
        require_fit(db, vehicle, departure, booked_count(db, departure), other_owner=False)
        moment = now()
        before_version, before_status = departure.version, departure.status
        previous = db.get(Vehicle, departure.current_vehicle_id)
        moved = move_passengers(db, user.id, departure, departure, vehicle, moment)
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
                   f'The Owner replaced the vehicle of {departure.departure_reference}: {vehicle.public_vehicle_reference} instead of '
                   f'{previous.public_vehicle_reference}, {moved} seat(s) moved. Passengers can accept or reject the change.')
        audit(request, db, user, departure, before_version, before_status,
              f'Owner replacement vehicle {vehicle.public_vehicle_reference} instead of {previous.public_vehicle_reference}.')
    return {**departure_out(db, departure), 'moved_seats': moved}


# --------------------------------------------------------------------------- slice 3: another Owner's vehicle

@router.get('/scheduled-trips/{trip_id}/replacement-options')
def replacement_options(trip_id: UUID, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    """Vehicles that can take this departure: the Owner's own and other Owners' published ones. `reference` narrows the
    list to one vehicle the Owner knows (its public vehicle reference)."""
    require_role(db, user, 'OWNER')
    departure = db.get(ScheduledTrip, trip_id)
    if not departure or departure.owner_user_id != user.id:
        raise ApiError(404, 'DEPARTURE_NOT_FOUND', 'Departure not found.')
    reference = (request.query_params.get('reference') or '').strip().upper()
    needed = booked_count(db, departure)
    query = select(Vehicle).where(Vehicle.verification_status == 'APPROVED', Vehicle.availability_status == 'ACTIVE',
                                  Vehicle.id != departure.current_vehicle_id,
                                  (Vehicle.owner_user_id == user.id) | Vehicle.is_published.is_(True))
    if reference:
        query = query.where(func.upper(Vehicle.public_vehicle_reference) == reference)
    items = []
    for vehicle in db.scalars(query.order_by(Vehicle.owner_user_id != user.id, Vehicle.public_vehicle_reference).limit(200)):
        own = vehicle.owner_user_id == user.id
        if vehicle_fits(db, vehicle, departure, needed, other_owner=not own):
            continue
        owner = db.get(User, vehicle.owner_user_id)
        items.append({'vehicle_id': str(vehicle.id), 'own': own, **summary(vehicle),
                      'bookable_seats': len(bookable_seats(db, vehicle.id)),
                      'owner_name': None if own else (owner.display_name or owner.full_name)})
        if len(items) >= 30:
            break
    return {'scheduled_trip_id': str(departure.id), 'booked_seats': needed, 'items': items}


def pickup_of(db, departure):
    route = db.get(Route, departure.route_id)
    if route is not None and route.origin_latitude is not None and route.origin_longitude is not None:
        return float(route.origin_latitude), float(route.origin_longitude)
    return None


def vehicle_distance(vehicle, pickup):
    """Kilometres from where the vehicle is now (or its base) to the pickup point; None when either is unknown."""
    if pickup is None:
        return None
    if vehicle.current_latitude is not None:
        where = (vehicle.current_latitude, vehicle.current_longitude)
    elif vehicle.base_latitude is not None:
        where = (vehicle.base_latitude, vehicle.base_longitude)
    else:
        return None
    return km_between(where[0], where[1], pickup[0], pickup[1])


def candidate_list(db, departure):
    """Vehicles of other Owners that can take this departure: approved, active, published, enough seats, air-conditioned
    when the booked vehicle is, and free at that time. Nearest to the pickup first; vehicles without a location last."""
    needed = booked_count(db, departure)
    pickup = pickup_of(db, departure)
    asked = set(db.scalars(select(ScheduledTrip.current_vehicle_id).where(ScheduledTrip.offer_for_scheduled_trip_id == departure.id,
                                                                          ScheduledTrip.status == 'DRAFT')).all())
    found = []
    query = select(Vehicle).where(Vehicle.verification_status == 'APPROVED', Vehicle.availability_status == 'ACTIVE',
                                  Vehicle.is_published.is_(True), Vehicle.owner_user_id != departure.owner_user_id,
                                  Vehicle.id != departure.current_vehicle_id).order_by(Vehicle.public_vehicle_reference).limit(300)
    for vehicle in db.scalars(query):
        if vehicle_fits(db, vehicle, departure, needed, other_owner=True):
            continue
        owner = db.get(User, vehicle.owner_user_id)
        km = vehicle_distance(vehicle, pickup)
        found.append({'vehicle_id': str(vehicle.id), **summary(vehicle), 'bookable_seats': len(bookable_seats(db, vehicle.id)),
                      'owner_name': (owner.display_name or owner.full_name) if owner else None,
                      'location_label': vehicle.base_location_label, 'distance_km': None if km is None else round(km, 1),
                      'already_asked': vehicle.id in asked})
    found.sort(key=lambda item: (item['distance_km'] is None, item['distance_km'] or 0, item['public_vehicle_reference']))
    return found, needed


def admin_departure(db, trip_id):
    if not db.get(ScheduledTrip, trip_id):
        raise ApiError(404, 'DEPARTURE_NOT_FOUND', 'Departure not found.')
    return lock_trip(db, trip_id)


@router.get('/admin/scheduled-trips/{trip_id}/replacement-candidates')
def replacement_candidates(trip_id: UUID, user=Depends(admin), db: Session = Depends(get_db)):
    departure = db.get(ScheduledTrip, trip_id)
    if not departure:
        raise ApiError(404, 'DEPARTURE_NOT_FOUND', 'Departure not found.')
    items, needed = candidate_list(db, departure)
    return {'scheduled_trip_id': str(departure.id), 'booked_seats': needed, 'pending_offers': pending_offers(db, departure), 'items': items}


@router.post('/admin/scheduled-trips/{trip_id}/replacement-requests', status_code=201)
def ask_replacement_owners(trip_id: UUID, body: AdminReplacementAsk, request: Request, user=Depends(admin), db: Session = Depends(get_db)):
    """Travelly asks the Owners of the chosen vehicles (or of every listed vehicle) to run the departure. All the
    requests stay open; the first Owner to accept takes the passengers and the others are withdrawn."""
    if body.send_to_all == bool(body.vehicle_ids):
        raise ApiError(422, 'VEHICLES_REQUIRED', 'Choose vehicles, or ask every listed vehicle.')
    with request.app.state.audit.coordinated():
        locked_authority(db, request, user, user.id)
        departure = admin_departure(db, trip_id)
        if departure.version != body.expected_version:
            raise ApiError(409, 'VERSION_CONFLICT', 'The departure changed. Reload before asking.')
        waiting_for_admin = departure.status in ATTENTION and (departure.arrangement in (None, 'TRAVELLY') or departure.status == 'DECISION_REQUIRED')
        run = journey(db, departure)
        if not waiting_for_admin or (run and run.status != 'READY') or departure.departure_at <= now():
            raise ApiError(409, 'REPLACEMENT_NOT_ALLOWED', 'A replacement can be asked for only a departure waiting for Travelly, before it starts.')
        listed, needed = candidate_list(db, departure)
        chosen = [item for item in listed if body.send_to_all or UUID(item['vehicle_id']) in set(body.vehicle_ids)]
        chosen = [item for item in chosen if not item['already_asked']]
        if not chosen:
            raise ApiError(409, 'NO_VEHICLE_TO_ASK', 'None of these vehicles can be asked now. Reload the list.')
        before_version, before_status = departure.version, departure.status
        for item in chosen:
            vehicle = db.scalar(select(Vehicle).where(Vehicle.id == UUID(item['vehicle_id'])).with_for_update())
            require_fit(db, vehicle, departure, needed, other_owner=True)
            offer = make_offer(db, departure, vehicle, user.id, needed)
            notify(db, vehicle.owner_user_id, offer, 'REPLACEMENT', 'Can you run a departure?',
                   f'Travelly asks you to run departure {departure.departure_reference} with {vehicle.public_vehicle_reference} '
                   f'on {departure.departure_at.isoformat()} for {needed} booked passenger(s) at the same seat price. '
                   'Other Owners may be asked too; the first to accept runs it. Accept or decline.', action=True)
        departure.replacement_status = 'AWAITING_OTHER_OWNER'
        touch(departure); departure.updated_by = user.id
        notify(db, departure.owner_user_id, departure, 'REPLACEMENT', 'Travelly is finding a replacement vehicle',
               f'Travelly asked {len(chosen)} vehicle Owner(s) to run {departure.departure_reference}. You will be told when one accepts.')
        audit(request, db, user, departure, before_version, before_status, f'Travelly asked {len(chosen)} vehicle Owner(s) to run the departure.')
    return {**departure_out(db, departure), 'asked': len(chosen)}


def eligible_driver(db, owner_id, driver_id):
    from app.api.routers.scheduled_trip_api import has_role
    driver_id = driver_id or (owner_id if has_role(db, owner_id, 'DRIVER') else None)
    if not driver_id or not has_role(db, driver_id, 'DRIVER'):
        raise ApiError(422, 'DRIVER_NOT_ELIGIBLE', 'Choose an approved Driver (or be an approved Driver yourself).')
    return driver_id


@router.post('/scheduled-trips/{trip_id}/replacement-request', status_code=201)
def replacement_request(trip_id: UUID, body: ReplacementVehicle, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    """The Owner asks another Owner to run this departure with that Owner's vehicle. The price stays the same. A draft
    departure is made for the other Owner (linked through replacement_scheduled_trip_id); nothing moves until they accept."""
    require_role(db, user, 'OWNER')
    with request.app.state.audit.coordinated():
        locked_authority(db, request, user, user.id, require_admin=False)
        departure = owned(db, trip_id, user)
        if departure.version != body.expected_version:
            raise ApiError(409, 'VERSION_CONFLICT', 'The departure changed. Refresh before choosing a vehicle.')
        waiting_for_travelly(departure, journey(db, departure))
        vehicle = db.scalar(select(Vehicle).where(Vehicle.id == body.vehicle_id).with_for_update())
        require_fit(db, vehicle, departure, booked_count(db, departure), other_owner=True)
        before_version, before_status = departure.version, departure.status
        offer = make_offer(db, departure, vehicle, user.id, booked_count(db, departure))
        departure.replacement_scheduled_trip_id = offer.id
        departure.replacement_status = 'AWAITING_OTHER_OWNER'
        touch(departure); departure.updated_by = user.id
        needed = booked_count(db, departure)
        notify(db, vehicle.owner_user_id, offer, 'REPLACEMENT', 'Can you run a departure?',
               f'Another Owner asks you to run departure {departure.departure_reference} with {vehicle.public_vehicle_reference} '
               f'on {departure.departure_at.isoformat()} for {needed} booked passenger(s) at the same seat price. Accept or decline.',
               action=True)
        for admin_id in admins(db):
            notify(db, admin_id, departure, 'ADMIN_ACTION', 'Replacement requested from another Owner',
                   f'{departure.departure_reference}: the Owner asked the owner of {vehicle.public_vehicle_reference} to run it.')
        audit(request, db, user, departure, before_version, before_status,
              f'Owner asked another Owner to run the departure with {vehicle.public_vehicle_reference}.')
    return {**departure_out(db, departure), 'replacement_request': request_out(db, departure, offer)}


def original_of(db, offer):
    """The departure that an offer would replace (offers made before several could wait have it through the other link)."""
    original_id = offer.offer_for_scheduled_trip_id or db.scalar(select(ScheduledTrip.id).where(ScheduledTrip.replacement_scheduled_trip_id == offer.id))
    return original_id


def withdraw_offers(db, departure, actor, reason, keep=None):
    """Cancel every offer still waiting for an answer about this departure, telling each Owner who was asked."""
    others = db.scalars(select(ScheduledTrip.id).where(ScheduledTrip.offer_for_scheduled_trip_id == departure.id,
                                                       ScheduledTrip.status == 'DRAFT').order_by(ScheduledTrip.id)).all()
    for offer_id in others:
        if keep is not None and offer_id == keep:
            continue
        offer = lock_trip(db, offer_id)
        if offer and offer.status == 'DRAFT':
            offer.status = 'CANCELLED'
            offer.cancellation_reason = reason
            touch(offer); offer.updated_by = actor
            notify(db, offer.owner_user_id, offer, 'REPLACEMENT', 'Replacement request closed', reason)


def make_offer(db, departure, vehicle, actor, needed):
    offer = ScheduledTrip(departure_reference='DEP-' + uuid4().hex[:16].upper(), owner_user_id=vehicle.owner_user_id,
                          service_type_id=departure.service_type_id, route_id=departure.route_id,
                          original_vehicle_id=vehicle.id, current_vehicle_id=vehicle.id,
                          departure_at=departure.departure_at, estimated_arrival_at=departure.estimated_arrival_at,
                          booking_cutoff_at=departure.booking_cutoff_at, fare_per_seat=departure.fare_per_seat,
                          currency=departure.currency, fulfilment_policy='FIXED_GUARANTEED',
                          accepted_time_window_minutes=departure.accepted_time_window_minutes,
                          accepted_replacement_terms=copy.deepcopy(departure.accepted_replacement_terms or {}),
                          status='DRAFT', replacement_status='NOT_REQUIRED', offer_for_scheduled_trip_id=departure.id,
                          created_by=actor, updated_by=actor)
    db.add(offer)
    db.flush()
    return offer


def request_out(db, departure, offer):
    vehicle = db.get(Vehicle, offer.current_vehicle_id)
    route = db.get(Route, departure.route_id)
    requester = db.get(User, departure.owner_user_id)
    return {'id': str(offer.id), 'departure_reference': offer.departure_reference, 'status': offer.status, 'version': offer.version,
            'original_scheduled_trip_id': str(departure.id), 'original_departure_reference': departure.departure_reference,
            'requested_by': requester.display_name or requester.full_name if requester else None,
            'vehicle': summary(vehicle) if vehicle else None,
            'route': {'route_name': route.route_name, 'origin_name': route.origin_name, 'destination_name': route.destination_name} if route else None,
            'departure_at': offer.departure_at.isoformat(), 'estimated_arrival_at': offer.estimated_arrival_at.isoformat(),
            'fare_per_seat': format(offer.fare_per_seat, '.2f'), 'currency': offer.currency, 'booked_seats': booked_count(db, departure),
            'answer_pending': departure.replacement_status == 'AWAITING_OTHER_OWNER' and offer.status == 'DRAFT'}


@router.get('/owners/me/replacement-requests')
def my_replacement_requests(user=Depends(current), db: Session = Depends(get_db)):
    require_role(db, user, 'OWNER')
    waiting = select(ScheduledTrip.id).where(ScheduledTrip.replacement_status == 'AWAITING_OTHER_OWNER')
    offers = db.scalars(select(ScheduledTrip).where(ScheduledTrip.owner_user_id == user.id, ScheduledTrip.status == 'DRAFT',
                                                    ScheduledTrip.offer_for_scheduled_trip_id.in_(waiting))
                        .order_by(ScheduledTrip.departure_at)).all()
    items = [request_out(db, db.get(ScheduledTrip, offer.offer_for_scheduled_trip_id), offer) for offer in offers]
    return {'items': items}


@router.post('/scheduled-trips/{trip_id}/replacement-answer')
def replacement_answer(trip_id: UUID, body: ReplacementAnswer, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    """The other Owner accepts (choosing the Driver) or declines. Accepting moves every paid passenger to the new departure,
    makes the new Owner the operating Owner, and reallocates the Owner share of the seat payments to them."""
    require_role(db, user, 'OWNER')
    with request.app.state.audit.coordinated():
        locked_authority(db, request, user, user.id, require_admin=False)
        offer_row = db.get(ScheduledTrip, trip_id)
        if not offer_row or offer_row.owner_user_id != user.id:
            raise ApiError(404, 'DEPARTURE_NOT_FOUND', 'Departure not found.')
        original_id = original_of(db, offer_row)
        if original_id is None:
            raise ApiError(404, 'DEPARTURE_NOT_FOUND', 'Departure not found.')
        original = lock_trip(db, original_id)       # lock order: the original departure, then the offer
        offer = lock_trip(db, offer_row.id)
        if offer.version != body.expected_version:
            raise ApiError(409, 'VERSION_CONFLICT', 'The request changed. Refresh before answering.')
        if original.replacement_status != 'AWAITING_OTHER_OWNER' or original_of(db, offer) != original.id or offer.status != 'DRAFT':
            raise ApiError(409, 'NO_REPLACEMENT_REQUEST', 'This replacement request is no longer waiting for an answer.')
        before_version, before_status = original.version, original.status
        moment = now()
        if body.decision == 'DECLINE':
            offer.status = 'CANCELLED'
            offer.cancellation_reason = body.reason or 'Declined by the Owner.'
            touch(offer); offer.updated_by = user.id
            others_waiting = db.scalar(select(func.count()).select_from(ScheduledTrip).where(
                ScheduledTrip.offer_for_scheduled_trip_id == original.id, ScheduledTrip.status == 'DRAFT', ScheduledTrip.id != offer.id)) or 0
            if not others_waiting:
                original.replacement_status = 'REJECTED'
            touch(original); original.updated_by = user.id
            text = f'The other Owner declined to run {original.departure_reference}.' + (f' Reason: {body.reason}' if body.reason else '')
            if others_waiting:
                text += f' {others_waiting} other request(s) are still waiting for an answer.'
            else:
                notify(db, original.owner_user_id, original, 'REPLACEMENT', 'Replacement declined', text, action=True)
            for admin_id in admins(db):
                notify(db, admin_id, original, 'ADMIN_ACTION', 'Replacement declined', text, action=not others_waiting)
            audit(request, db, user, original, before_version, before_status, 'Other Owner declined the replacement request.')
            return {**departure_out(db, original), 'replacement_request': request_out(db, original, offer)}
        run = journey(db, original)
        if original.status not in ATTENTION or (run and run.status != 'READY') or original.departure_at <= moment:
            raise ApiError(409, 'REPLACEMENT_NOT_ALLOWED', 'This departure can no longer be replaced.')
        vehicle = db.scalar(select(Vehicle).where(Vehicle.id == offer.current_vehicle_id).with_for_update())
        require_fit(db, vehicle, original, booked_count(db, original), other_owner=True)
        driver_id = eligible_driver(db, user.id, body.operator_driver_user_id)
        moved = move_passengers(db, user.id, original, offer, vehicle, moment)
        if run:
            run.status = 'CANCELLED'
            touch(run); run.updated_by = user.id
        db.add(Trip(trip_reference='TRP-' + secrets.token_hex(10).upper(), scheduled_trip_id=offer.id, vehicle_id=vehicle.id,
                    operating_owner_user_id=user.id, driver_user_id=driver_id,
                    assignment_type='OWNER_SELF_DRIVE' if driver_id == user.id else 'EXTERNAL_DRIVER',
                    assignment_status='ACCEPTED' if driver_id == user.id else 'PENDING', status='READY',
                    scheduled_start_at=offer.departure_at, scheduled_end_at=offer.estimated_arrival_at,
                    created_by=user.id, updated_by=user.id))
        offer.operator_driver_user_id = driver_id
        offer.status = 'COMMITTED'
        offer.committed_at = moment
        offer.final_operating_owner_user_id = user.id
        touch(offer); offer.updated_by = user.id
        original.status = 'CANCELLED'
        original.replacement_status = 'APPROVED'
        original.replacement_scheduled_trip_id = offer.id
        withdraw_offers(db, original, user.id, f'Another Owner accepted first, so {original.departure_reference} no longer needs a replacement.', keep=offer.id)
        original.final_operating_owner_user_id = user.id
        original.cancellation_reason = f'Replaced by departure {offer.departure_reference} run by another Owner.'
        touch(original); original.updated_by = user.id
        notify(db, original.owner_user_id, original, 'REPLACEMENT', 'Another Owner will run your departure',
               f'{offer.departure_reference} now carries the passengers of {original.departure_reference}. Their seat payments '
               'go to the Owner who runs it.')
        for admin_id in admins(db):
            notify(db, admin_id, original, 'ADMIN_ACTION', 'Departure moved to another Owner',
                   f'{original.departure_reference} is now run as {offer.departure_reference}. Owner shares were reallocated.')
        audit(request, db, user, original, before_version, before_status,
              f'Other Owner accepted; passengers moved to {offer.departure_reference} ({vehicle.public_vehicle_reference}).')
    return {**departure_out(db, offer), 'moved_seats': moved, 'original_scheduled_trip_id': str(original.id)}


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
