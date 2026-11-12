"""Private hire: reusable quotes, accepted snapshots and conflict-safe changes."""
import copy
import secrets
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, or_
from sqlalchemy.orm import Session
from app.dependencies.database import get_db
from app.models import User, UserRole
from app.api.routers.api import current, allowed_account, require_role, touch
from app.core.errors import ApiError, unauthorized
from app.api.routers.review_api import admin, locked_authority, query_values
from app.models.review_models import Vehicle, Document
from app.models.rate_models import ServiceType, VehicleService
from app.api.routers.rate_api import persist_rates
from app.schemas.rate_schemas import RateRule
from app.models.hire_models import Booking, ScheduledTrip, Trip, Notification
from app.services.vehicle_odometer import advance_odometer
from app.schemas.hire_schemas import (HireRequest, SearchRequest, Version, QuoteBody, Acceptance, Assignment,
    ChangeBody, Resolution, Compatibility, LicenceCategories, VehicleEligibility, Itinerary, StartTrip, TripLocation, Breakdown, CompleteTrip,
    PickupVerification, Publication, ServiceCreate, PricingScope, ServiceCatalogueUpdate)
from app.services.hire_services import (digest, approved, eligible_vehicle, vehicle_evidence, compatible_driver, no_conflict,
    price, saved_rules, booking_summary, trip_summary, notify, audited, matches, matching_rules)
from app.services.pickup_codes import MAX_ATTEMPTS, pin_for, same, token_for
from app.services.pricing_scope import require_supported_private_hire, private_hire_scope
from app.schemas.vehicle_schemas import VehicleDecision
from app.services.vehicle_rules import public_photos

router = APIRouter(prefix='/api/v1', tags=['Private hire pricing'])


def missing(): return ApiError(404, 'BOOKING_NOT_FOUND', 'Booking not found.')


def catalogue_status(service):
    configured = service.settings.get('catalogue_status')
    if configured in ('DRAFT', 'NEEDS_REVIEW'):
        return configured
    if not private_hire_scope(service):
        return 'DRAFT'
    return 'ACTIVE' if service.is_active else 'INACTIVE'


def ready_vehicle_service(service, vehicle, row):
    configured = row.owner_terms.get('event_packages') if private_hire_scope(service) == 'EVENT' and row else row.owner_terms.get('rate_rules') if row else None
    return bool(service.is_active and catalogue_status(service) == 'ACTIVE' and row and row.is_enabled
        and configured and vehicle.verification_status == 'APPROVED'
        and vehicle.availability_status == 'ACTIVE' and vehicle.is_published)


def service_for(db, sid, new_offer=True):
    service = db.get(ServiceType, sid)
    if not service or service.category != 'PRIVATE_HIRE' or (new_offer and not service.is_active):
        raise ApiError(409, 'SERVICE_UNAVAILABLE', 'The private-hire service is unavailable.')
    if new_offer: require_supported_private_hire(service)
    return service


def validate_service_itinerary(service, itinerary):
    scope = private_hire_scope(service)
    if scope == 'AIRPORT' and itinerary.direction == 'RETURN' and itinerary.return_start_at is None:
        raise ApiError(422, 'RETURN_INTERVAL_REQUIRED', 'Airport return journeys require a verified return pickup date and time.')
    if scope != 'AIRPORT' and itinerary.flight_number is not None:
        raise ApiError(422, 'FLIGHT_DETAILS_UNAVAILABLE', 'Flight details are available only for Airport hire.')


def visible_booking(db, bid, user, *, owner=False, passenger=False):
    row = db.get(Booking, bid)
    if not row: raise missing()
    if owner and row.owner_user_id != user.id: raise missing()
    if passenger and row.passenger_user_id != user.id: raise missing()
    if not owner and not passenger and user.id not in (row.owner_user_id, row.passenger_user_id):
        if not db.scalar(select(Trip.id).where(Trip.booking_id == row.id, Trip.driver_user_id == user.id, Trip.assignment_status.in_(('PENDING', 'ACCEPTED')))): raise missing()
    return row


def lock_booking(db, request, bid, user, expected, *, owner=False, passenger=False, driver_id=None):
    before = visible_booking(db, bid, user, owner=owner, passenger=passenger)
    if before.booking_type != 'PRIVATE_HIRE' or before.assurance_type != 'STANDARD_HIRE':
        raise ApiError(409, 'BOOKING_WORKFLOW_REQUIRED', 'This pricing action is limited to standard private hire; use the existing protected or rental workflow.')
    ids = sorted({user.id, before.owner_user_id, before.passenger_user_id, driver_id} - {None}, key=str)
    people = db.scalars(select(User).where(User.id.in_(ids)).order_by(User.id).with_for_update().execution_options(populate_existing=True)).all()
    db.scalars(select(UserRole).where(UserRole.user_id.in_(ids)).order_by(UserRole.user_id, UserRole.id).with_for_update().execution_options(populate_existing=True)).all()
    caller = next(p for p in people if p.id == user.id); allowed_account(caller)
    claims = request.state.auth_claims
    if claims.get('av', 0) != caller.auth_version: raise unauthorized()
    request.app.state.store.get(claims['sid'], claims['sub'])
    vehicle = db.scalar(select(Vehicle).where(Vehicle.id == before.vehicle_id).with_for_update().execution_options(populate_existing=True))
    row = db.scalar(select(Booking).where(Booking.id == bid).with_for_update().execution_options(populate_existing=True))
    visible_booking(db, bid, user, owner=owner, passenger=passenger)
    if row.version != expected: raise ApiError(409, 'VERSION_CONFLICT', 'Booking changed. Reload before retrying.')
    return row, vehicle


def usable_capacity(vehicle, data):
    if any(cap is None or count > cap for cap, count in [(vehicle.seat_capacity, data.passenger_count),
        (vehicle.large_luggage_capacity, data.large_luggage_count), (vehicle.small_luggage_capacity, data.small_luggage_count)]):
        raise ApiError(409, 'CAPACITY_UNAVAILABLE', 'Verified vehicle capacity does not cover the requested passengers and luggage.')


def offer(request, db, vehicle, service, itinerary, *, rules=None):
    eligible_vehicle(db, vehicle, public=True, at=itinerary.start_at)
    row, configured = saved_rules(db, vehicle.id, service.id)
    snapshot = price(request, service, vehicle, itinerary, configured if rules is None else rules)
    snapshot['rate_version'] = row.version if row else None
    for start, end in itinerary.availability_intervals():
        no_conflict(db, vehicle.id, start, end)
    snapshot['digest'] = digest(snapshot)
    return snapshot


def safe_vehicle(vehicle, owner):
    return {'id': str(vehicle.id), 'reference': vehicle.public_vehicle_reference, 'make': vehicle.make, 'model': vehicle.model,
        'category': vehicle.verified_eligibility.get('category'), 'passenger_seats': vehicle.seat_capacity,
        'large_luggage': vehicle.large_luggage_capacity, 'small_luggage': vehicle.small_luggage_capacity,
        'owner_reference': owner.public_user_reference, 'owner_name': owner.display_name or owner.public_user_reference,
        'vehicle_type_code':vehicle.vehicle_type_code,'manufacture_year':vehicle.manufacture_year,'colour':vehicle.colour,
        'air_conditioned':vehicle.air_conditioned,'description':vehicle.verified_eligibility.get('description_review',{}).get('approved_text'),
        'photos':public_photos(vehicle)}


def same_hire_request(row, body, user):
    original_itinerary = row.price_snapshot.get('initial', {}).get('itinerary') or row.itinerary_snapshot.get('itinerary')
    return (row.passenger_user_id == user.id and row.vehicle_id == body.vehicle_id
            and row.service_type_id == body.service_type_id
            and all(getattr(row, name) == getattr(body, name) for name in
                    ('passenger_count', 'large_luggage_count', 'small_luggage_count'))
            and original_itinerary == body.itinerary.model_dump(mode='json'))


@router.get('/vehicles')
def browse(request: Request, db: Session = Depends(get_db)):
    params = query_values(request, {'owner_reference'})
    rows = db.scalars(select(Vehicle).where(Vehicle.is_published.is_(True)).order_by(Vehicle.id).limit(101)).all()
    items = []
    for v in rows:
        owner = db.get(User, v.owner_user_id)
        if params.get('owner_reference') and params['owner_reference'] != owner.public_user_reference: continue
        try: eligible_vehicle(db, v, public=True)
        except ApiError: continue
        items.append(safe_vehicle(v, owner))
    return {'items': items[:100], 'has_next': len(rows) > 100}


@router.post('/search/vehicles')
def search(body: SearchRequest, request: Request, db: Session = Depends(get_db)):
    if body.itinerary.start_at <= datetime.now(timezone.utc):
        raise ApiError(422, 'ITINERARY_IN_PAST', 'Choose a future pickup time.')
    service = service_for(db, body.service_type_id)
    validate_service_itinerary(service, body.itinerary)
    items = []
    rows = db.scalars(select(Vehicle).where(Vehicle.is_published.is_(True)).order_by(Vehicle.id).limit(100)).all()
    unavailable = False
    availability_incomplete = False
    for vehicle in rows:
        try:
            usable_capacity(vehicle, body)
            snapshot = offer(request, db, vehicle, service, body.itinerary)
            # Every listed vehicle shows the Owner's own price for this itinerary, so the
            # Passenger compares before choosing. Selecting one still asks for a fresh quote.
            items.append({**safe_vehicle(vehicle, db.get(User, vehicle.owner_user_id)),
                          'price': snapshot['calculation'], 'reserved_end_at': snapshot['reserved_end_at']})
        except ApiError as exc:
            if exc.status == 503: unavailable = True
            if exc.code == 'AVAILABILITY_INCOMPLETE': availability_incomplete = True
            continue
    if availability_incomplete:
        from app.services.availability import incomplete
        raise incomplete()
    if unavailable and not items:
        raise ApiError(503, 'TRIP_PRICING_UNAVAILABLE', 'Trusted route pricing is temporarily unavailable. Browse vehicles for an Owner quote.')
    return {'items': items, 'message': 'Only vehicles with an active approved service rate and checked availability are shown. Each price comes from that Owner\u2019s saved rates; selecting a vehicle calculates a fresh quote.'}


@router.post('/search/vehicles/{vehicle_id}/quote')
def selected_vehicle_quote(vehicle_id: UUID, body: SearchRequest, request: Request, db: Session = Depends(get_db)):
    """Calculate a fresh, non-binding quote only after vehicle selection."""
    if body.itinerary.start_at <= datetime.now(timezone.utc):
        raise ApiError(422, 'ITINERARY_IN_PAST', 'Choose a future pickup time.')
    service = service_for(db, body.service_type_id)
    validate_service_itinerary(service, body.itinerary)
    vehicle = db.scalar(select(Vehicle).where(Vehicle.id == vehicle_id, Vehicle.is_published.is_(True)))
    if not vehicle:
        raise ApiError(404, 'VEHICLE_NOT_FOUND', 'The selected published vehicle is unavailable.')
    usable_capacity(vehicle, body)
    snapshot = offer(request, db, vehicle, service, body.itinerary)
    return {**safe_vehicle(vehicle, db.get(User, vehicle.owner_user_id)), 'price': snapshot['calculation'],
            'reserved_end_at': snapshot['reserved_end_at'], 'quote_digest': snapshot['digest'],
            'rate_version': snapshot['rate_version'], 'message': 'This is a fresh quote. The accepted booking preserves this selected rate-rule version and calculation snapshot.'}


@router.post('/bookings/private-hires', status_code=201)
def request_hire(body: HireRequest, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    require_role(db, user, 'PASSENGER')
    if body.itinerary.start_at <= datetime.now(timezone.utc): raise ApiError(422, 'ITINERARY_IN_PAST', 'Choose a future pickup time.')
    existing = db.scalar(select(Booking).where(Booking.idempotency_key == body.idempotency_key))
    if existing:
        if not same_hire_request(existing, body, user):
            raise ApiError(409, 'IDEMPOTENCY_CONFLICT', 'This request identifier was already used for a different request.')
        return booking_summary(existing)
    with request.app.state.audit.coordinated():
        locked_authority(db, request, user, user.id, require_admin=False)
        require_role(db, user, 'PASSENGER')
        if user.email_login_required and not user.email_verified_at:
            raise ApiError(403, 'EMAIL_VERIFICATION_REQUIRED', 'Verify your email before signing in.')
        vehicle = db.scalar(select(Vehicle).where(Vehicle.id == body.vehicle_id).with_for_update())
        if not vehicle: raise ApiError(404, 'VEHICLE_NOT_FOUND', 'Vehicle not found.')
        existing = db.scalar(select(Booking).where(Booking.idempotency_key == body.idempotency_key))
        if existing:
            if not same_hire_request(existing, body, user):
                raise ApiError(409, 'IDEMPOTENCY_CONFLICT', 'The request identifier belongs to a different request.')
            return booking_summary(existing)
        eligible_vehicle(db, vehicle, public=True, at=body.itinerary.start_at); usable_capacity(vehicle, body)
        service = service_for(db, body.service_type_id); validate_service_itinerary(service, body.itinerary)
        snapshot = None
        for stop in body.itinerary.stops: request.app.state.rate_locations.verify(stop.place)
        try: snapshot = offer(request, db, vehicle, service, body.itinerary)
        except ApiError as exc:
            if exc.code not in ('QUOTE_REQUIRED', 'ROUTING_PROFILE_REQUIRED', 'ROUTING_UNAVAILABLE', 'ROUTING_NOT_CONFIGURED'): raise
        if snapshot is None:
            for start, end in body.itinerary.availability_intervals():
                no_conflict(db, vehicle.id, start, end)
        row = Booking(booking_reference='BKG-' + secrets.token_hex(10).upper(), passenger_user_id=user.id, booking_type='PRIVATE_HIRE',
            service_type_id=service.id, requested_owner_user_id=vehicle.owner_user_id, owner_user_id=vehicle.owner_user_id,
            vehicle_id=vehicle.id, origin_text=body.itinerary.stops[0].place.label, destination_text=body.itinerary.stops[-1].place.label,
            start_at=body.itinerary.start_at, end_at=datetime.fromisoformat(snapshot['reserved_end_at']) if snapshot else body.itinerary.requested_end(),
            passenger_count=body.passenger_count, large_luggage_count=body.large_luggage_count, small_luggage_count=body.small_luggage_count,
            status='REQUESTED', assurance_type='STANDARD_HIRE', currency='LKR', idempotency_key=body.idempotency_key,
            itinerary_snapshot={'itinerary': body.itinerary.model_dump(mode='json')}, created_by=user.id, updated_by=user.id,
            pending_change={'kind': 'QUOTE', 'quote': snapshot} if snapshot else {})
        db.add(row); db.flush(); notify(db, row, 'Private-hire request', 'A Passenger requested this itinerary. Any quote saves reusable route rates.')
        request.app.state.audit.commit(db, actor=user.id, target={'resource': 'bookings', 'id': str(row.id)}, previous_status=None,
            new_status='REQUESTED', previous_version=0, new_version=1, full_reason=None, previous_decision_evidence={}, trace_id=request.state.trace_id)
    return booking_summary(row)


@router.get('/bookings')
def bookings(request: Request, user=Depends(current), db: Session = Depends(get_db)):
    """Every booking the caller takes part in. Each item says how (`viewer_roles`: PASSENGER = booked it, OWNER = runs it,
    DRIVER = drives it), so one workspace can show its own trips, its vehicles' bookings and its driving together.
    `?as=passenger|owner|driver` narrows the list to one of those."""
    view = (request.query_params.get('as') or '').upper()
    if view and view not in ('PASSENGER', 'OWNER', 'DRIVER'):
        raise ApiError(422, 'VALIDATION_ERROR', 'as must be passenger, owner or driver.', [{'field': 'as', 'message': 'passenger, owner or driver'}])
    driven = set(db.scalars(select(Trip.booking_id).where(Trip.driver_user_id == user.id, Trip.booking_id.is_not(None),
                                                          Trip.assignment_status.in_(('PENDING', 'ACCEPTED', 'NOT_REQUIRED')),
                                                          Trip.status != 'CANCELLED')).all())
    ticket_driven = select(Booking.id).where(Booking.current_scheduled_trip_id.in_(
        select(Trip.scheduled_trip_id).where(Trip.driver_user_id == user.id, Trip.scheduled_trip_id.is_not(None), Trip.status != 'CANCELLED')))
    driven |= set(db.scalars(ticket_driven).all())
    conditions = {'PASSENGER': Booking.passenger_user_id == user.id, 'OWNER': Booking.owner_user_id == user.id,
                  'DRIVER': Booking.id.in_(driven) if driven else Booking.id.is_(None)}
    where = conditions[view] if view else or_(*conditions.values())
    rows = db.scalars(select(Booking).where(where).order_by(Booking.created_at.desc()).limit(100)).all()

    def roles(r):
        return [name for name, yes in (('PASSENGER', r.passenger_user_id == user.id), ('OWNER', r.owner_user_id == user.id),
                                        ('DRIVER', r.id in driven)) if yes]
    return {'items': [{**booking_summary(r), 'viewer_roles': roles(r)} for r in rows]}


@router.get('/bookings/{booking_id}')
def booking_detail(booking_id: UUID, user=Depends(current), db: Session = Depends(get_db)):
    row = visible_booking(db, booking_id, user)
    result = booking_summary(row)
    trip = db.scalar(select(Trip).where(Trip.booking_id == row.id, Trip.status != 'CANCELLED').order_by(Trip.created_at.desc()).limit(1))
    result['trip'] = trip_summary(trip) if trip else None
    return result


@router.post('/bookings/{booking_id}/quote')
def quote(booking_id: UUID, body: QuoteBody, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    with request.app.state.audit.coordinated():
        row, vehicle = lock_booking(db, request, booking_id, user, body.expected_version, owner=True)
        require_role(db, user, 'OWNER')
        if not body.rates.enabled: raise ApiError(422, 'QUOTE_REUSE_REQUIRED', 'A structured quote must save enabled reusable rules for future matching requests.')
        manual_change = row.pending_change.get('kind') == 'CHANGE_REQUEST_UNPRICED' and row.status in ('CONFIRMED', 'IN_PROGRESS')
        if not manual_change and (row.status != 'REQUESTED' or row.accepted_quote_digest): raise ApiError(409, 'QUOTE_STATE_CONFLICT', 'An accepted booking uses change proposals, not a replacement quote.')
        if body.rates.service_type_id != row.service_type_id: raise ApiError(422, 'SERVICE_MISMATCH', 'Quote rates must use the requested service.')
        itinerary = Itinerary.model_validate(row.pending_change['itinerary'] if manual_change else row.itinerary_snapshot['itinerary'])
        if manual_change and row.pending_change['reason'] == 'DEPARTURE_TIME_CHANGE' and (row.status != 'CONFIRMED' or itinerary.start_at <= datetime.now(timezone.utc)):
            raise ApiError(409, 'DEPARTURE_CHANGE_UNAVAILABLE', 'Only an unstarted confirmed booking can receive a future departure quote.')
        matching = matching_rules(body.rates.rules, itinerary)
        if len(matching) != 1 or matching[0].coverage.kind != 'ROUTE':
            raise ApiError(422, 'QUOTE_COVERAGE_REQUIRED', 'The quote needs one explicit matching route rule; it cannot silently become an area or nationwide rate.')
        previous = booking_summary(row)
        rate = persist_rates(vehicle.id, body.rates, request, user, db)
        snapshot = price(request, service_for(db, row.service_type_id, not manual_change), vehicle, itinerary, matching) if manual_change else offer(request, db, vehicle, service_for(db, row.service_type_id), itinerary, rules=body.rates.rules)
        snapshot['rate_version'] = rate.version; snapshot.pop('digest', None); snapshot['digest'] = digest(snapshot)
        if manual_change:
            old_total = row.price_snapshot['current']['calculation']['total']
            row.pending_change = {'kind': 'CHANGE', 'reason': row.pending_change['reason'], 'quote': snapshot,
                'old_total': old_total, 'added_charge': format(Decimal(snapshot['calculation']['total']) - Decimal(old_total), '.2f'),
                'new_total': snapshot['calculation']['total'], 'manual_review_required': True, 'passenger_accepted': False}
            if row.pending_change['reason'] == 'DEPARTURE_TIME_CHANGE':
                row.pending_change = {**row.pending_change, 'old_departure': row.start_at.isoformat(), 'new_departure': itinerary.start_at.isoformat()}
            row.pending_change = {**row.pending_change, 'digest': digest(row.pending_change)}
            assigned = db.scalar(select(Trip).where(Trip.booking_id == row.id, Trip.assignment_status == 'ACCEPTED', Trip.status != 'CANCELLED'))
            notify(db, row, 'Changed-route quote is ready', 'Review old total, added charge and proposed total. Passenger acceptance and feasible Owner review are required.', assigned.driver_user_id if assigned else None)
        else:
            row.pending_change = {'kind': 'QUOTE', 'quote': snapshot}; row.quoted_amount = Decimal(snapshot['calculation']['total'])
            notify(db, row, 'Your trip quote is ready', 'Review and accept the itinerary price before the Owner can commit.')
        audited(request, db, user, row, previous, 'Structured quote saved as reusable route rates')
    return booking_summary(row)


@router.post('/bookings/{booking_id}/price-acceptance')
def accept_price(booking_id: UUID, body: Acceptance, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    with request.app.state.audit.coordinated():
        row, vehicle = lock_booking(db, request, booking_id, user, body.expected_version, passenger=True)
        proposal = row.pending_change
        snapshot = proposal.get('quote') if proposal.get('kind') == 'QUOTE' else None
        if row.status != 'REQUESTED' or not snapshot or snapshot['digest'] != body.digest: raise ApiError(409, 'QUOTE_CHANGED', 'Reload the current quote before accepting.')
        service_for(db, row.service_type_id)
        quote_itinerary = Itinerary.model_validate(snapshot['itinerary'])
        if quote_itinerary.start_at <= datetime.now(timezone.utc):
            raise ApiError(409, 'QUOTE_REVIEW_REQUIRED', 'The quoted departure is no longer in the future. Request a new quote.')
        if snapshot['rule']['method'] == 'FIXED_ROUTE' and not snapshot['rule'].get('departure'):
            raise ApiError(409, 'QUOTE_REVIEW_REQUIRED', 'This older fixed quote needs explicit departure applicability before acceptance.')
        previous = booking_summary(row)
        no_conflict(db, row.vehicle_id, row.start_at, datetime.fromisoformat(snapshot['reserved_end_at']), exclude=row.id)
        row.price_snapshot = {'initial': copy.deepcopy(snapshot), 'current': copy.deepcopy(snapshot)}
        row.itinerary_snapshot = {'itinerary': snapshot['itinerary'], 'measurement': snapshot['measurement']}
        row.accepted_quote_digest = body.digest; row.total_amount = row.quoted_amount = Decimal(snapshot['calculation']['total'])
        row.end_at = datetime.fromisoformat(snapshot['reserved_end_at']); row.accepted_at = datetime.now(timezone.utc); row.pending_change = {}
        notify(db, row, 'Trip price accepted', 'The Passenger accepted this price. The Owner must still confirm operational availability.')
        audited(request, db, user, row, previous, 'Passenger accepted the exact price and itinerary')
    return booking_summary(row)


def commit_operator(booking_id, body, request, user, db, self_drive):
    driver = user if self_drive else db.scalar(select(User).where(User.public_user_reference == body.driver_reference))
    if not driver: raise ApiError(409, 'DRIVER_NOT_ELIGIBLE', 'That Driver reference is unavailable.')
    with request.app.state.audit.coordinated():
        row, vehicle = lock_booking(db, request, booking_id, user, body.expected_version, owner=True, driver_id=driver.id)
        require_role(db, user, 'OWNER')
        if row.status not in ('REQUESTED', 'OWNER_ACTION_REQUIRED') or not row.accepted_quote_digest: raise ApiError(409, 'PRICE_ACCEPTANCE_REQUIRED', 'Passenger price acceptance is required before Owner commitment.')
        eligible_vehicle(db, vehicle, at=row.end_at)
        service = service_for(db, row.service_type_id, new_offer=False)
        compatible_driver(db, driver, vehicle, service, row.end_at)
        no_conflict(db, vehicle.id, row.start_at, row.end_at, exclude=row.id, driver_id=driver.id)
        previous = booking_summary(row)
        existing = db.scalars(select(Trip).where(Trip.booking_id == row.id, Trip.status != 'CANCELLED').with_for_update()).all()
        for old in existing:
            if old.assignment_status == 'ACCEPTED': raise ApiError(409, 'ASSIGNMENT_EXISTS', 'This booking already has an accepted Driver.')
            old.status = 'CANCELLED'
            if old.assignment_status == 'PENDING': old.assignment_status = 'CANCELLED'
            touch(old)
        trip = Trip(trip_reference='TRP-' + secrets.token_hex(10).upper(), booking_id=row.id, vehicle_id=vehicle.id, operating_owner_user_id=user.id,
            driver_user_id=driver.id, assignment_type='OWNER_SELF_DRIVE' if self_drive else 'EXTERNAL_DRIVER', assignment_status='ACCEPTED' if self_drive else 'PENDING',
            status='READY', scheduled_start_at=row.start_at, scheduled_end_at=row.end_at, created_by=user.id, updated_by=user.id)
        db.add(trip); row.vehicle_committed = True; row.status = 'CONFIRMED' if self_drive else 'AWAITING_DRIVER'
        if self_drive: row.confirmed_at = datetime.now(timezone.utc)
        notify(db, row, 'Trip operator update', 'Self-drive confirmed.' if self_drive else 'Driver acceptance is pending; the vehicle is reserved.', driver.id)
        audited(request, db, user, row, previous, 'Owner committed vehicle after Passenger price acceptance')
    return booking_summary(row)


@router.post('/bookings/{booking_id}/self-drive')
def self_drive(booking_id: UUID, body: Version, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    return commit_operator(booking_id, body, request, user, db, True)


@router.post('/bookings/{booking_id}/driver-assignments')
def assign_driver(booking_id: UUID, body: Assignment, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    return commit_operator(booking_id, body, request, user, db, False)


def assignment_decision(trip_id, body, request, user, db, accept):
    trip = db.get(Trip, trip_id)
    if not trip or trip.driver_user_id != user.id: raise missing()
    with request.app.state.audit.coordinated():
        before = db.get(Booking, trip.booking_id)
        row, vehicle = lock_booking(db, request, before.id, user, before.version, driver_id=user.id)
        trip = db.scalar(select(Trip).where(Trip.id == trip_id).with_for_update().execution_options(populate_existing=True))
        if trip.version != body.expected_version or trip.assignment_status != 'PENDING': raise ApiError(409, 'ASSIGNMENT_CHANGED', 'Reload the current assignment.')
        previous = booking_summary(row)
        if accept:
            eligible_vehicle(db, vehicle, at=row.end_at); compatible_driver(db, user, vehicle, service_for(db, row.service_type_id, False), row.end_at)
            no_conflict(db, vehicle.id, row.start_at, row.end_at, exclude=row.id, driver_id=user.id)
            trip.assignment_status = 'ACCEPTED'; row.status = 'CONFIRMED'; row.confirmed_at = datetime.now(timezone.utc)
        else:
            trip.assignment_status = 'REJECTED'; row.status = 'OWNER_ACTION_REQUIRED'
            # Keep the vehicle reservation while the Owner finds another operator.
        touch(trip); trip.updated_by = user.id
        notify(db, row, 'Driver assignment response', 'Driver accepted.' if accept else 'Driver declined. The vehicle remains reserved pending Owner resolution.', user.id)
        audited(request, db, user, row, previous, 'Driver accepted' if accept else 'Driver declined; commitment retained')
    return booking_summary(row)


@router.post('/trips/{trip_id}/assignment-accept')
def assignment_accept(trip_id: UUID, body: Version, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    return assignment_decision(trip_id, body, request, user, db, True)


@router.post('/trips/{trip_id}/assignment-decline')
def assignment_decline(trip_id: UUID, body: Version, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    return assignment_decision(trip_id, body, request, user, db, False)


@router.post('/trips/{trip_id}/start')
def start_trip(trip_id: UUID, body: StartTrip, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    trip = db.get(Trip, trip_id)
    if not trip or trip.driver_user_id != user.id: raise missing()
    departure = departure_of(db, trip)
    if departure is not None: return start_departure(db, trip, departure, body, user, request)
    with request.app.state.audit.coordinated():
        before = db.get(Booking, trip.booking_id)
        row, vehicle = lock_booking(db, request, before.id, user, before.version, driver_id=user.id)
        trip = db.scalar(select(Trip).where(Trip.id == trip_id).with_for_update().execution_options(populate_existing=True))
        if trip.version != body.expected_version or trip.assignment_status != 'ACCEPTED' or row.status != 'CONFIRMED' or trip.status != 'READY': raise ApiError(409, 'TRIP_NOT_READY', 'Only a confirmed accepted assignment can start.')
        if datetime.now(timezone.utc) < row.start_at: raise ApiError(409, 'TRIP_NOT_READY', 'The scheduled pickup time has not arrived.')
        if datetime.now(timezone.utc) >= row.end_at: raise ApiError(409, 'TRIP_NOT_READY', 'The reserved interval has ended. Resolve the itinerary before starting; no reservation was released.')
        eligible_vehicle(db, vehicle); compatible_driver(db, user, vehicle, service_for(db, row.service_type_id, False), datetime.now(timezone.utc))
        odometer_rules(request, trip, vehicle, 'START', body.start_odometer_km)
        no_conflict(db, vehicle.id, row.start_at, row.end_at, exclude=row.id, driver_id=user.id)
        previous = booking_summary(row); row.status = 'IN_PROGRESS'; trip.status = 'IN_PROGRESS'; trip.actual_start_at = datetime.now(timezone.utc); trip.start_odometer_km = body.start_odometer_km; touch(trip)
        notify(db, row, 'Trip started', 'The assigned Driver started this confirmed journey.', user.id)
        audited(request, db, user, row, previous, 'Assigned eligible Driver started the trip')
    return booking_summary(row)


def odometer_rules(request, trip, vehicle, stage, km):
    """Owner decision 13 Nov 2026: the start reading is never below the vehicle's last odometer, and start/finish need a
    fresh live photo for exactly this reading (app/services/odometer_proof.py)."""
    from app.services import odometer_proof
    if stage == 'START':
        odometer_proof.below_last(vehicle, km)
    if request is not None:
        odometer_proof.require_proof(request.app.state.settings, trip, stage, km)


def driving_trip(db, trip_id, user):
    """Only the operator assigned to this trip may record what happens on it."""
    trip = db.get(Trip, trip_id)
    if not trip or trip.driver_user_id != user.id: raise missing()
    return trip


def departure_of(db, trip, *, lock=False):
    """The published departure a trip runs, or None when the trip belongs to a private hire."""
    if not trip.scheduled_trip_id: return None
    query = select(ScheduledTrip).where(ScheduledTrip.id == trip.scheduled_trip_id)
    if lock: query = query.with_for_update().execution_options(populate_existing=True)
    return db.scalar(query)


def riding_on(db, departure, user):
    """True when this person holds a seat on the departure, so they may follow the journey."""
    from app.models.seat_models import ScheduledTripSeat
    return bool(db.scalar(select(Booking.id)
                          .join(ScheduledTripSeat, ScheduledTripSeat.booked_booking_id == Booking.id)
                          .where(ScheduledTripSeat.scheduled_trip_id == departure.id,
                                 Booking.passenger_user_id == user.id).limit(1)))


def locked_trip(db, trip_id, expected):
    trip = db.scalar(select(Trip).where(Trip.id == trip_id).with_for_update().execution_options(populate_existing=True))
    if trip.version != expected: raise ApiError(409, 'VERSION_CONFLICT', 'Trip changed. Reload before retrying.')
    return trip


def running(trip):
    if trip.status not in ('IN_PROGRESS', 'BREAKDOWN', 'ASSISTANCE_REQUIRED'):
        raise ApiError(409, 'TRIP_NOT_READY', 'The trip has not started or has already finished.')


def start_departure(db, trip, departure, body, user, request=None):
    """A published departure starts the same way a private hire does, against the departure itself."""
    from app.models.rate_models import ServiceType as Service
    locked_departure = departure_of(db, trip, lock=True)
    locked = locked_trip(db, trip.id, body.expected_version)
    if locked.assignment_status != 'ACCEPTED' or locked.status != 'READY' or locked_departure.status not in ('PUBLISHED', 'COMMITTED', 'READY'):
        raise ApiError(409, 'TRIP_NOT_READY', 'Only an accepted assignment on a published departure can start.')
    moment = datetime.now(timezone.utc)
    if moment < locked_departure.departure_at:
        raise ApiError(409, 'TRIP_NOT_READY', 'The departure time has not arrived.')
    if moment >= locked_departure.estimated_arrival_at:
        raise ApiError(409, 'TRIP_NOT_READY', 'The arrival time has passed. Resolve the departure before starting it.')
    vehicle = db.scalar(select(Vehicle).where(Vehicle.id == locked.vehicle_id).with_for_update().execution_options(populate_existing=True))
    eligible_vehicle(db, vehicle)
    compatible_driver(db, user, vehicle, db.get(Service, locked_departure.service_type_id), moment)
    odometer_rules(request, locked, vehicle, 'START', body.start_odometer_km)
    # The departure itself holds this vehicle's slot, so only the Driver's own calendar is rechecked.
    clash = db.scalar(select(Trip.id).where(Trip.driver_user_id == user.id, Trip.assignment_status == 'ACCEPTED',
                                            Trip.status.notin_(('COMPLETED', 'CANCELLED')), Trip.id != locked.id,
                                            Trip.scheduled_start_at < locked_departure.estimated_arrival_at,
                                            Trip.scheduled_end_at > locked_departure.departure_at).limit(1))
    if clash:
        raise ApiError(409, 'DRIVER_SCHEDULE_CONFLICT', 'The Driver already has an overlapping accepted trip.')
    locked.status = 'IN_PROGRESS'
    locked.actual_start_at = moment
    locked.start_odometer_km = body.start_odometer_km
    touch(locked); locked.updated_by = user.id
    locked_departure.status = 'IN_PROGRESS'
    touch(locked_departure); locked_departure.updated_by = user.id
    db.commit()
    return trip_summary(locked)


def breakdown_departure(db, trip, body, user):
    locked = locked_trip(db, trip.id, body.expected_version)
    running(locked)
    locked.status = body.kind
    locked.breakdown_details = body.details
    touch(locked); locked.updated_by = user.id
    db.commit()
    return {'trip': trip_summary(locked)}


def complete_departure(db, trip, body, user, request=None):
    """Finishing the journey closes the departure and the travellers who boarded it."""
    from app.models.seat_models import BookingTraveller, ScheduledTripSeat
    locked_departure = departure_of(db, trip, lock=True)
    locked = locked_trip(db, trip.id, body.expected_version)
    running(locked)
    if locked.start_odometer_km is None or body.end_odometer_km < locked.start_odometer_km:
        raise ApiError(422, 'VALIDATION_ERROR', 'The closing odometer cannot be lower than the odometer recorded at the start.')
    odometer_rules(request, locked, None, 'END', body.end_odometer_km)
    locked.actual_end_at = datetime.now(timezone.utc)
    locked.end_odometer_km = body.end_odometer_km
    locked.calculated_distance_km = body.end_odometer_km - locked.start_odometer_km
    advance_odometer(db, locked.vehicle_id, body.end_odometer_km, user.id, locked.actual_end_at)  # PRD: finish updates the odometer
    locked.completion_notes = body.completion_notes
    locked.status = 'COMPLETED'
    locked.tracking_status = 'ENDED'
    touch(locked); locked.updated_by = user.id
    locked_departure.status = 'COMPLETED'
    touch(locked_departure); locked_departure.updated_by = user.id
    seats = select(ScheduledTripSeat.id).where(ScheduledTripSeat.scheduled_trip_id == locked_departure.id)
    for traveller in db.scalars(select(BookingTraveller).where(BookingTraveller.scheduled_trip_seat_id.in_(seats),
                                                               BookingTraveller.traveller_status == 'BOARDED')):
        traveller.traveller_status = 'COMPLETED'
        touch(traveller); traveller.updated_by = user.id
    # PRD 6.6: Owner payout only after completion. Seat payments of this departure become payable to the Owner now.
    from app.models.payment_models import Payment
    paid_here = select(Booking.id).where(Booking.current_scheduled_trip_id == locked_departure.id)
    # A reallocated payment (another Owner took over the journey) is paid out through its REALLOCATION row.
    for payment in db.scalars(select(Payment).where(Payment.booking_id.in_(paid_here), Payment.transaction_type.in_(('PAYMENT', 'REALLOCATION')),
                                                    Payment.status.in_(('PAID', 'PARTIALLY_REFUNDED')),  # partial: paid out pro rata
                                                    Payment.owner_settlement_status.is_(None),
                                                    Payment.failure_code.is_(None)).order_by(Payment.id).with_for_update()):
        payment.owner_settlement_status = 'OWNER_PAYABLE'
        payment.owner_payable_at = locked.actual_end_at
        touch(payment); payment.updated_by = user.id
    db.commit()
    return {'trip': trip_summary(locked)}


@router.get('/trips/{trip_id}')
def trip_detail(trip_id: UUID, user=Depends(current), db: Session = Depends(get_db)):
    trip = db.get(Trip, trip_id)
    if not trip: raise missing()
    reviewer = db.scalar(select(UserRole.id).where(UserRole.user_id == user.id, UserRole.role_code == 'ADMIN',
                                                   UserRole.approval_status == 'APPROVED'))
    departure = departure_of(db, trip)
    if departure is not None:
        if not reviewer and user.id not in (departure.owner_user_id, trip.driver_user_id) and not riding_on(db, departure, user):
            raise missing()
    else:
        row = db.get(Booking, trip.booking_id)
        if not row: raise missing()
        if not reviewer and user.id not in (row.owner_user_id, row.passenger_user_id, trip.driver_user_id): raise missing()
    return trip_summary(trip)


@router.get('/trips/{trip_id}/map')
def trip_map(trip_id: UUID, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    """What the live trip map draws (owner decision 13 Nov 2026): the stops from start to end, the road line between
    them when the route service answers (cached 12 hours), and the latest position. Same people as GET /trips/{id}."""
    trip_detail(trip_id, user, db)
    trip = db.get(Trip, trip_id)
    departure = departure_of(db, trip)
    points = []
    if departure is not None:
        from app.models.hire_models import Route, RouteStop
        route = db.get(Route, departure.route_id)
        points.append({'label': route.origin_name, 'latitude': str(route.origin_latitude), 'longitude': str(route.origin_longitude), 'kind': 'START'})
        for stop in db.scalars(select(RouteStop).where(RouteStop.route_id == route.id, RouteStop.is_active.is_(True)).order_by(RouteStop.stop_order)):
            points.append({'label': stop.stop_name, 'latitude': str(stop.latitude), 'longitude': str(stop.longitude), 'kind': 'STOP'})
        points.append({'label': route.destination_name, 'latitude': str(route.destination_latitude), 'longitude': str(route.destination_longitude), 'kind': 'END'})
    else:
        stops = (db.get(Booking, trip.booking_id).itinerary_snapshot.get('itinerary') or {}).get('stops') or []
        for index, stop in enumerate(stops):
            place = stop['place']
            kind = 'START' if index == 0 else 'END' if index == len(stops) - 1 else 'STOP'
            points.append({'label': place['label'], 'latitude': str(place['latitude']), 'longitude': str(place['longitude']), 'kind': kind})
    return {'trip_id': str(trip.id), 'status': trip.status, 'points': points, 'line': road_line(request, trip.id, points),
            'position': None if trip.current_latitude is None else {
                'latitude': str(trip.current_latitude), 'longitude': str(trip.current_longitude),
                'updated_at': trip.location_updated_at.isoformat() if trip.location_updated_at else None}}


def road_line(request, trip_id, points):
    """[[lng, lat], ...] along the roads, or None (the map then draws straight lines between the points)."""
    import json as _json
    import httpx
    settings, store = request.app.state.settings, request.app.state.store
    if len(points) < 2 or not settings.routing_api_key:
        return None
    key = store.key(f'trip-map-line:{trip_id}')
    cached = store.client.get(key)
    if cached:
        return _json.loads(cached)
    try:
        reply = httpx.post(settings.routing_base_url.rstrip('/') + '/openrouteservice/v2/directions/driving-car/geojson',
                           headers={'Authorization': settings.routing_api_key}, timeout=10,
                           json={'coordinates': [[float(p['longitude']), float(p['latitude'])] for p in points][:50]})
        reply.raise_for_status()
        line = reply.json()['features'][0]['geometry']['coordinates']
        if not line or len(line) > 100000: return None
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError):
        return None
    store.client.set(key, _json.dumps(line), ex=43200)
    return line


@router.patch('/trips/{trip_id}/location')
def trip_location(trip_id: UUID, body: TripLocation, user=Depends(current), db: Session = Depends(get_db)):
    driving_trip(db, trip_id, user)
    allowed_account(user)
    trip = locked_trip(db, trip_id, body.expected_version)
    running(trip)
    trip.current_latitude = body.latitude
    trip.current_longitude = body.longitude
    trip.location_accuracy_m = body.accuracy_m
    trip.current_speed_kph = body.speed_kph
    trip.location_updated_at = datetime.now(timezone.utc)
    trip.tracking_status = 'ACTIVE'
    touch(trip); trip.updated_by = user.id
    db.commit()
    return trip_summary(trip)


@router.post('/trips/{trip_id}/breakdown')
def trip_breakdown(trip_id: UUID, body: Breakdown, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    first = driving_trip(db, trip_id, user)
    if first.scheduled_trip_id: return breakdown_departure(db, first, body, user)
    with request.app.state.audit.coordinated():
        before = db.get(Booking, first.booking_id)
        row, vehicle = lock_booking(db, request, before.id, user, before.version, driver_id=user.id)
        trip = locked_trip(db, trip_id, body.expected_version)
        running(trip)
        previous = booking_summary(row)
        trip.status = body.kind
        trip.breakdown_details = body.details
        touch(trip); trip.updated_by = user.id
        notify(db, row, 'The trip needs help', body.details, user.id)
        audited(request, db, user, row, previous,
                'Assigned Driver reported ' + ('a breakdown' if body.kind == 'BREAKDOWN' else 'that assistance is required'))
    return {**booking_summary(row), 'trip': trip_summary(trip)}


@router.post('/trips/{trip_id}/complete')
def complete_trip(trip_id: UUID, body: CompleteTrip, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    first = driving_trip(db, trip_id, user)
    if first.scheduled_trip_id: return complete_departure(db, first, body, user, request)
    with request.app.state.audit.coordinated():
        before = db.get(Booking, first.booking_id)
        row, vehicle = lock_booking(db, request, before.id, user, before.version, driver_id=user.id)
        trip = locked_trip(db, trip_id, body.expected_version)
        running(trip)
        if row.status != 'IN_PROGRESS': raise ApiError(409, 'TRIP_NOT_READY', 'Only a started booking can be completed.')
        if trip.start_odometer_km is None or body.end_odometer_km < trip.start_odometer_km:
            raise ApiError(422, 'VALIDATION_ERROR', 'The closing odometer cannot be lower than the odometer recorded at the start.')
        odometer_rules(request, trip, None, 'END', body.end_odometer_km)
        previous = booking_summary(row)
        trip.actual_end_at = datetime.now(timezone.utc)
        trip.end_odometer_km = body.end_odometer_km
        trip.calculated_distance_km = body.end_odometer_km - trip.start_odometer_km
        advance_odometer(db, trip.vehicle_id, body.end_odometer_km, user.id, trip.actual_end_at)  # PRD: finish updates the odometer
        trip.completion_notes = body.completion_notes
        trip.status = 'COMPLETED'
        trip.tracking_status = 'ENDED'
        row.status = 'COMPLETED'
        touch(trip); trip.updated_by = user.id
        notify(db, row, 'Trip completed', 'The assigned Driver completed this journey.', user.id)
        audited(request, db, user, row, previous, 'Assigned Driver completed the trip')
    return {**booking_summary(row), 'trip': trip_summary(trip)}


def pickup_party(db, trip_id, user, *, passenger):
    """The pickup code belongs to the Passenger; only the assigned operator may check it."""
    trip = db.get(Trip, trip_id)
    if not trip or not trip.booking_id: raise missing()
    row = db.get(Booking, trip.booking_id)
    if not row: raise missing()
    if passenger and row.passenger_user_id != user.id: raise missing()
    if not passenger and trip.driver_user_id != user.id: raise missing()
    allowed_account(user)
    return trip, row


def pickup_out(trip):
    """The Passenger's own copy: the code is recalculated, never read from a stored value."""
    return {'trip_id': str(trip.id), 'pin': pin_for(trip.id, trip.pickup_code_version),
            'qr_token': token_for(trip.id, trip.pickup_code_version),
            'issued_at': trip.pickup_code_issued_at.isoformat() if trip.pickup_code_issued_at else None,
            'verified_at': trip.pickup_verified_at.isoformat() if trip.pickup_verified_at else None,
            'attempts_left': max(0, MAX_ATTEMPTS - (trip.pickup_failed_attempts or 0))}


def open_trip(trip):
    if trip.status in ('COMPLETED', 'CANCELLED'):
        raise ApiError(409, 'TRIP_NOT_READY', 'This trip has finished, so a pickup code is no longer used.')


@router.get('/trips/{trip_id}/pickup-code')
def pickup_code(trip_id: UUID, user=Depends(current), db: Session = Depends(get_db)):
    """Issued on the Passenger's first look and shown again whenever they come back."""
    trip, _ = pickup_party(db, trip_id, user, passenger=True)
    open_trip(trip)
    if not trip.pickup_code_version:
        trip = db.scalar(select(Trip).where(Trip.id == trip.id).with_for_update().execution_options(populate_existing=True))
        if not trip.pickup_code_version:
            # The trip version is left alone: issuing a code is not a change the Driver has to reload for.
            trip.pickup_code_version = 1
            trip.pickup_code_issued_at = datetime.now(timezone.utc)
            trip.pickup_failed_attempts = 0
            db.commit()
    return pickup_out(trip)


@router.post('/trips/{trip_id}/pickup-code/reissue')
def reissue_pickup_code(trip_id: UUID, user=Depends(current), db: Session = Depends(get_db)):
    """A new code: the previous one stops working at once."""
    first, _ = pickup_party(db, trip_id, user, passenger=True)
    open_trip(first)
    trip = db.scalar(select(Trip).where(Trip.id == first.id).with_for_update().execution_options(populate_existing=True))
    if trip.pickup_verified_at:
        raise ApiError(409, 'PICKUP_ALREADY_VERIFIED', 'The Driver already checked this pickup, so the code is finished with.')
    trip.pickup_code_version += 1
    trip.pickup_code_issued_at = datetime.now(timezone.utc)
    trip.pickup_failed_attempts = 0
    db.commit()
    return pickup_out(trip)


@router.post('/trips/{trip_id}/pickup-verifications')
def verify_pickup(trip_id: UUID, body: PickupVerification, user=Depends(current), db: Session = Depends(get_db)):
    """The Driver checks the Passenger at the pickup: the scanned code, or the six digits under it."""
    first, _ = pickup_party(db, trip_id, user, passenger=False)
    trip = db.scalar(select(Trip).where(Trip.id == first.id).with_for_update().execution_options(populate_existing=True))
    if trip.version != body.expected_version:
        raise ApiError(409, 'VERSION_CONFLICT', 'Trip changed. Reload before retrying.')
    if trip.status not in ('READY', 'IN_PROGRESS'):
        raise ApiError(409, 'TRIP_NOT_READY', 'Check the Passenger when you reach the pickup, before the trip finishes.')
    if trip.pickup_verified_at:
        return {'verified_at': trip.pickup_verified_at.isoformat(), 'trip': trip_summary(trip)}
    if not trip.pickup_code_version:
        raise ApiError(409, 'PICKUP_CODE_NOT_ISSUED', 'Ask the Passenger to open their pickup code first.')
    if (trip.pickup_failed_attempts or 0) >= MAX_ATTEMPTS:
        raise ApiError(409, 'PICKUP_CODE_LOCKED', 'Too many wrong tries. Ask the Passenger to get a new code.')
    expected = token_for(trip.id, trip.pickup_code_version) if body.qr_token else pin_for(trip.id, trip.pickup_code_version)
    if not same(body.qr_token or body.pin, expected):
        trip.pickup_failed_attempts = (trip.pickup_failed_attempts or 0) + 1
        left = max(0, MAX_ATTEMPTS - trip.pickup_failed_attempts)
        db.commit()
        raise ApiError(422, 'PICKUP_CODE_INVALID', f'That code does not match. {left} tries left before the Passenger needs a new code.')
    trip.pickup_verified_at = datetime.now(timezone.utc)
    trip.pickup_failed_attempts = 0
    db.commit()
    return {'verified_at': trip.pickup_verified_at.isoformat(), 'trip': trip_summary(trip)}


def validate_change(old, new, reason):
    if (old.start_at != new.start_at and reason != 'DEPARTURE_TIME_CHANGE') or old.method != new.method or old.direction != new.direction:
        raise ApiError(422, 'INVALID_TRIP_CHANGE', 'A trip change cannot replace pickup time, direction or the agreed pricing method.')
    before = [(s.place.latitude, s.place.longitude) for s in old.stops]
    after = [(s.place.latitude, s.place.longitude) for s in new.stops]
    if reason == 'DEPARTURE_TIME_CHANGE':
        if old.start_at == new.start_at or old.stops != new.stops or old.service_hours != new.service_hours:
            raise ApiError(422, 'INVALID_TRIP_CHANGE', 'A departure-time proposal changes only departure, retaining the agreed route, waiting and service durations.')
    if reason == 'ADDED_STOP':
        cursor = iter(after)
        if len(after) <= len(before) or any(not any(p == wanted for p in cursor) for wanted in before):
            raise ApiError(422, 'INVALID_TRIP_CHANGE', 'Added-stop changes must retain the agreed stops in their original order.')
    elif reason == 'DESTINATION_CHANGE' and (before[:-1] != after[:-1] or before[-1] == after[-1]):
        raise ApiError(422, 'INVALID_TRIP_CHANGE', 'A destination change retains the existing pickup and intermediate stops.')
    elif reason == 'EXTRA_WAIT' and before != after:
        raise ApiError(422, 'INVALID_TRIP_CHANGE', 'A waiting change cannot silently change the route.')


def prepare_change(row, body, request, db, vehicle):
    initial = row.price_snapshot.get('current')
    if not initial: raise ApiError(409, 'PRICE_ACCEPTANCE_REQUIRED', 'This booking has no agreed price.')
    old = Itinerary.model_validate(initial['itinerary'])
    validate_change(old, body.itinerary, body.reason)
    rule = RateRule.model_validate(initial['rule'])
    if body.reason == 'DEPARTURE_TIME_CHANGE':
        if rule.method != 'FIXED_ROUTE' or row.status != 'CONFIRMED' or body.itinerary.start_at <= datetime.now(timezone.utc):
            raise ApiError(409, 'DEPARTURE_CHANGE_UNAVAILABLE', 'Departure changes require an unstarted confirmed fixed-fare booking and a future departure.')
        return {'kind': 'CHANGE_REQUEST_UNPRICED', 'reason': body.reason, 'itinerary': body.itinerary.model_dump(mode='json'),
                'old_total': initial['calculation']['total'], 'old_departure': old.start_at.isoformat(),
                'new_departure': body.itinerary.start_at.isoformat(), 'manual_review_required': True,
                'message': 'The Owner proposed a departure change. A new disclosed reusable quote, Passenger acceptance and feasible manual confirmation are required; the current departure and price stay agreed.'}
    if rule.method == 'FIXED_ROUTE' and [(s.place.latitude, s.place.longitude) for s in old.stops] != [(s.place.latitude, s.place.longitude) for s in body.itinerary.stops]:
        return {'kind': 'CHANGE_REQUEST_UNPRICED', 'reason': body.reason, 'itinerary': body.itinerary.model_dump(mode='json'),
                'old_total': initial['calculation']['total'], 'manual_review_required': True,
                'message': 'The fixed fare covers the agreed exact route. The Owner must quote reusable rules for this changed route before any added/new total can be accepted.'}
    snapshot = price(request, service_for(db, row.service_type_id, False), vehicle, body.itinerary, [rule], agreed_rule=True)
    old_total = Decimal(initial['calculation']['total']); new_total = Decimal(snapshot['calculation']['total'])
    old_usage = initial['measurement']['usage']; usage = snapshot['measurement']['usage']
    delta = {'added_km': str(max(Decimal('0'), Decimal(usage['distance_km']) - Decimal(old_usage['distance_km']))),
        'added_hours': str(max(Decimal('0'), sum(map(Decimal, usage['service_hours'])) - sum(map(Decimal, old_usage['service_hours'])))),
        'added_wait_minutes': str(max(Decimal('0'), Decimal(usage['waiting_minutes']) - Decimal(old_usage['waiting_minutes']))),
        'added_amount': str(new_total - old_total)}
    limits = rule.change_limits
    over = any(Decimal(value) > getattr(limits, field) for field, value in delta.items())
    proposal = {'kind': 'CHANGE', 'reason': body.reason, 'quote': snapshot, 'old_total': format(old_total, '.2f'),
        'added_charge': format(new_total - old_total, '.2f'), 'new_total': format(new_total, '.2f'), 'delta': delta,
        'manual_review_required': over or new_total < old_total, 'passenger_accepted': False}
    proposal['digest'] = digest(proposal)
    return proposal


@router.post('/bookings/{booking_id}/changes')
def propose_change(booking_id: UUID, body: ChangeBody, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    with request.app.state.audit.coordinated():
        row, vehicle = lock_booking(db, request, booking_id, user, body.expected_version)
        if user.id != row.passenger_user_id:
            require_role(db, user, 'OWNER' if user.id == row.owner_user_id else 'DRIVER')
        if row.status not in ('CONFIRMED', 'IN_PROGRESS'): raise ApiError(409, 'TRIP_CHANGE_UNAVAILABLE', 'Trip changes require a confirmed or active booking.')
        if body.reason == 'DEPARTURE_TIME_CHANGE' and user.id != row.owner_user_id:
            raise ApiError(403, 'OWNER_REQUIRED', 'Only the booking Owner can propose this departure change.')
        if body.reason == 'DEPARTURE_TIME_CHANGE': require_role(db, user, 'OWNER')
        previous = booking_summary(row)
        row.pending_change = prepare_change(row, body, request, db, vehicle)
        trip = db.scalar(select(Trip).where(Trip.booking_id == row.id, Trip.assignment_status == 'ACCEPTED', Trip.status != 'CANCELLED'))
        notify(db, row, 'Trip change proposed', f"Old total LKR {row.pending_change['old_total']}; " + (row.pending_change['message'] if row.pending_change['kind'] == 'CHANGE_REQUEST_UNPRICED' else f"added charge {row.pending_change['added_charge']}; proposed total {row.pending_change['new_total']}. Passenger acceptance is required."), trip.driver_user_id if trip else None)
        audited(request, db, user, row, previous, 'Itinerary change proposed; agreed snapshot unchanged')
    return booking_summary(row)


def apply_change(db, request, row, vehicle, user, *, manual=False):
    proposal = row.pending_change
    snapshot = proposal['quote']
    if Decimal(proposal['added_charge']) < 0:
        return 'A reduced total requires the financial adjustment workflow; no automatic refund or price mutation was made.'
    if proposal['manual_review_required'] and not manual:
        return 'The proposal exceeds pre-authorized limits and requires Owner review.'
    trip = db.scalar(select(Trip).where(Trip.booking_id == row.id, Trip.assignment_status == 'ACCEPTED', Trip.status != 'CANCELLED').with_for_update())
    if not trip: return 'An accepted Driver is required to confirm this operational change.'
    end = datetime.fromisoformat(snapshot['reserved_end_at'])
    start = datetime.fromisoformat(snapshot['itinerary']['start_at'])
    if proposal['reason'] == 'DEPARTURE_TIME_CHANGE' and (row.status != 'CONFIRMED' or start <= datetime.now(timezone.utc)):
        return 'The departure proposal is no longer a future change to an unstarted confirmed booking.'
    try:
        # Serialize across ALL accepted trips of the same Driver as well as the vehicle.
        db.scalars(select(User).where(User.id == trip.driver_user_id).with_for_update()).all()
        require_supported_private_hire(service_for(db, row.service_type_id, False))
        eligible_vehicle(db, vehicle, at=start); eligible_vehicle(db, vehicle, at=end)
        compatible_driver(db, db.get(User, trip.driver_user_id), vehicle, service_for(db, row.service_type_id, False), end)
        no_conflict(db, vehicle.id, start, end, exclude=row.id, driver_id=trip.driver_user_id)
    except ApiError as exc:
        return exc.message
    row.price_snapshot = {**row.price_snapshot, 'current': snapshot}
    row.itinerary_snapshot = {'itinerary': snapshot['itinerary'], 'measurement': snapshot['measurement']}
    row.accepted_quote_digest = digest(snapshot); row.total_amount = Decimal(snapshot['calculation']['total'])
    row.start_at = start; row.end_at = end; row.destination_text = snapshot['itinerary']['stops'][-1]['place']['label']; row.pending_change = {}
    trip.scheduled_start_at = start; trip.scheduled_end_at = end; touch(trip)
    departure_notice = f" Departure changed from {proposal['old_departure']} to {proposal['new_departure']}." if proposal.get('new_departure') else ''
    notify(db, row, 'Trip change confirmed', f"Old LKR {proposal['old_total']}; added {proposal['added_charge']}; new LKR {proposal['new_total']}. The Passenger accepted the change." + departure_notice, trip.driver_user_id)
    return None


@router.post('/bookings/{booking_id}/changes/accept')
def accept_change(booking_id: UUID, body: Acceptance, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    visible = visible_booking(db, booking_id, user, passenger=True)
    assigned = db.scalar(select(Trip).where(Trip.booking_id == visible.id, Trip.assignment_status == 'ACCEPTED', Trip.status != 'CANCELLED'))
    with request.app.state.audit.coordinated():
        row, vehicle = lock_booking(db, request, booking_id, user, body.expected_version, passenger=True, driver_id=assigned.driver_user_id if assigned else None)
        proposal = row.pending_change
        if row.status not in ('CONFIRMED', 'IN_PROGRESS') or proposal.get('kind') != 'CHANGE' or proposal.get('digest') != body.digest:
            raise ApiError(409, 'PROPOSAL_CHANGED', 'Reload the current change proposal before accepting.')
        previous = booking_summary(row)
        row.pending_change = {**proposal, 'passenger_accepted': True}
        reason = apply_change(db, request, row, vehicle, user)
        if reason:
            row.pending_change = {**row.pending_change, 'manual_review_required': True, 'manual_review_reason': reason}
            notify(db, row, 'Trip change needs manual review', reason, assigned.driver_user_id if assigned else None)
        audited(request, db, user, row, previous, 'Passenger accepted change; manual review required' if reason else 'Passenger accepted and feasible change confirmed')
    return booking_summary(row)


@router.post('/bookings/{booking_id}/changes/review')
def review_change(booking_id: UUID, body: Acceptance, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    visible = visible_booking(db, booking_id, user, owner=True)
    assigned = db.scalar(select(Trip).where(Trip.booking_id == visible.id, Trip.assignment_status == 'ACCEPTED', Trip.status != 'CANCELLED'))
    with request.app.state.audit.coordinated():
        row, vehicle = lock_booking(db, request, booking_id, user, body.expected_version, owner=True, driver_id=assigned.driver_user_id if assigned else None)
        require_role(db, user, 'OWNER')
        proposal = row.pending_change
        if proposal.get('kind') != 'CHANGE' or proposal.get('digest') != body.digest or not proposal.get('passenger_accepted'):
            raise ApiError(409, 'PASSENGER_ACCEPTANCE_REQUIRED', 'A current Passenger-accepted proposal is required.')
        previous = booking_summary(row)
        reason = apply_change(db, request, row, vehicle, user, manual=True)
        if reason: raise ApiError(409, 'CHANGE_NOT_FEASIBLE', reason)
        audited(request, db, user, row, previous, 'Owner confirmed Passenger-accepted feasible change after manual review')
    return booking_summary(row)


@router.post('/bookings/{booking_id}/cancel')
def resolve_request(booking_id: UUID, body: Resolution, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    with request.app.state.audit.coordinated():
        row, vehicle = lock_booking(db, request, booking_id, user, body.expected_version)
        if user.id != row.passenger_user_id: require_role(db, user, 'OWNER')
        if user.id not in (row.owner_user_id, row.passenger_user_id) or row.status not in ('REQUESTED', 'OWNER_ACTION_REQUIRED', 'AWAITING_DRIVER'):
            raise ApiError(409, 'CANCELLATION_REVIEW_REQUIRED', 'Confirmed/in-progress journeys require the approved cancellation/financial workflow; no silent release was made.')
        if row.booking_type != 'PRIVATE_HIRE' or row.assurance_type != 'STANDARD_HIRE' or row.payment_status_snapshot not in (None, 'PENDING', 'FAILED'):
            raise ApiError(409, 'CANCELLATION_REVIEW_REQUIRED', 'Protected or funded journeys require their cancellation/financial workflow; no automatic release was made.')
        previous = booking_summary(row); row.status = 'CANCELLED'; row.vehicle_committed = False
        row.cancelled_by_user_id = user.id; row.cancelled_at = datetime.now(timezone.utc); row.cancellation_reason = body.reason
        for trip in db.scalars(select(Trip).where(Trip.booking_id == row.id).with_for_update()):
            trip.status = 'CANCELLED'
            if trip.assignment_status != 'REJECTED': trip.assignment_status = 'CANCELLED'
            touch(trip)
        notify(db, row, 'Booking resolved', 'The pending booking was explicitly cancelled and its reservation released.')
        audited(request, db, user, row, previous, body.reason)
    return booking_summary(row)


@router.get('/notifications')
def own_notifications(user=Depends(current), db: Session = Depends(get_db)):
    rows = db.scalars(select(Notification).where(Notification.recipient_user_id == user.id).order_by(Notification.created_at.desc()).limit(100)).all()
    return {'items': [notification_out(r) for r in rows]}


def notification_out(r):
    """One notification for its recipient. The UI picks wording and links from notification_type and action_payload."""
    text = lambda v: str(v) if v is not None else None
    when = lambda v: v.isoformat() if v else None
    return {'id': str(r.id), 'notification_type': r.notification_type, 'channel': r.channel, 'title': r.title, 'body': r.body,
            'status': r.status, 'action_required': r.action_required, 'action_payload': dict(r.action_payload or {}),
            'booking_id': text(r.booking_id), 'scheduled_trip_id': text(r.scheduled_trip_id), 'trip_id': text(r.trip_id),
            'response_code': r.response_code, 'created_at': when(r.created_at), 'read_at': when(r.read_at),
            'expires_at': when(r.expires_at),
            # kept for screens built before notification_type was returned
            'support_vehicle_id': (r.action_payload or {}).get('vehicle_id') if r.notification_type == 'ADMIN_ACTION' else None}


@router.put('/admin/service-types/{service_id}/licence-compatibility')
def compatibility(service_id: UUID, body: Compatibility, request: Request, user=Depends(admin), db: Session = Depends(get_db)):
    with request.app.state.audit.coordinated():
        locked_authority(db, request, user, user.id)
        row = db.scalar(select(ServiceType).where(ServiceType.id == service_id).with_for_update())
        if not row or row.category != 'PRIVATE_HIRE': raise ApiError(404, 'SERVICE_NOT_FOUND', 'Service not found.')
        if row.version != body.expected_version: raise ApiError(409, 'VERSION_CONFLICT', 'Service configuration changed.')
        old = copy.deepcopy(row.settings); before = row.version
        row.settings = {**row.settings, 'licence_compatibility': body.matrix, 'routing_profiles': body.routing_profiles}; touch(row); row.updated_by = user.id
        request.app.state.audit.commit(db, actor=user.id, target={'resource': 'service_types', 'id': str(row.id)}, previous_status=None, new_status=None,
            previous_version=before, new_version=row.version, full_reason=None, previous_decision_evidence={'settings': old}, trace_id=request.state.trace_id)
    return {'id': str(row.id), 'version': row.version, 'matrix': body.matrix, 'routing_profiles': body.routing_profiles}


@router.patch('/admin/documents/{document_id}/licence-categories')
def licence_categories(document_id: UUID, body: LicenceCategories, request: Request, user=Depends(admin), db: Session = Depends(get_db)):
    import re
    if len(set(body.categories)) != len(body.categories) or any(not re.fullmatch(r'[A-Z0-9_-]{1,20}', c) for c in body.categories):
        raise ApiError(422, 'VALIDATION_ERROR', 'Enter explicit unique licence category codes from the reviewed evidence.')
    record = db.get(Document, document_id)
    if not record or record.document_type != 'DRIVING_LICENCE' or record.user_id == user.id: raise ApiError(403, 'REVIEW_FORBIDDEN', 'Self-review or non-licence category editing is not allowed.')
    with request.app.state.audit.coordinated():
        locked_authority(db, request, user, record.user_id)
        row = db.scalar(select(Document).where(Document.id == document_id).with_for_update().execution_options(populate_existing=True))
        if row.version != body.expected_version: raise ApiError(409, 'VERSION_CONFLICT', 'Licence evidence changed.')
        if row.status not in ('UNDER_REVIEW', 'APPROVED') or row.issuing_country != 'LK' or not row.expiry_date:
            raise ApiError(409, 'LICENCE_REVIEW_REQUIRED', 'Review Sri Lanka-issued current licence evidence before recording categories.')
        previous = list(row.verified_categories); version = row.version; row.verified_categories = body.categories; touch(row); row.updated_by = user.id
        request.app.state.audit.commit(db, actor=user.id, target={'resource': 'documents', 'id': str(row.id)}, previous_status=row.status, new_status=row.status,
            previous_version=version, new_version=row.version, full_reason=None, previous_decision_evidence={'verified_categories': previous}, trace_id=request.state.trace_id)
    return {'id': str(row.id), 'version': row.version, 'categories': row.verified_categories}


@router.patch('/admin/vehicles/{vehicle_id}/review')
def vehicle_review(vehicle_id: UUID, body: VehicleDecision, request: Request, user=Depends(admin), db: Session = Depends(get_db)):
    from app.api.routers.vehicle_api import decide_vehicle
    return decide_vehicle(vehicle_id,body,request,user,db)


def priced_for_publication(db, vehicle):
    """A published vehicle must carry a price a Passenger can see.

    Private hire needs saved rate rules (or event packages). Ticket and rental services
    price each departure or agreement separately, so enabling the service is enough."""
    rows = db.scalars(select(VehicleService).where(VehicleService.vehicle_id == vehicle.id,
                                                   VehicleService.is_enabled.is_(True))).all()
    for row in rows:
        service = db.get(ServiceType, row.service_type_id)
        if not service or not service.is_active:
            continue
        if service.category != 'PRIVATE_HIRE':
            return True
        terms = row.owner_terms or {}
        if terms.get('rate_rules') or terms.get('event_packages'):
            return True
    return False


@router.patch('/vehicles/{vehicle_id}/publish')
def publish_vehicle(vehicle_id: UUID, body: Publication, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    from app.api.routers.rate_api import owned
    with request.app.state.audit.coordinated():
        row = owned(db, request, user, vehicle_id, lock=True)
        if row.version != body.expected_version: raise ApiError(409, 'VERSION_CONFLICT', 'Vehicle changed. Reload before publishing.')
        fingerprint = eligible_vehicle(db, row) if body.published else None
        from app.services.vehicle_rules import has_exterior, require_complete
        if body.published:require_complete(row)
        if body.published and not has_exterior(row):raise ApiError(409,'EXTERIOR_PHOTO_REQUIRED','Approve at least one genuine exterior photo with no visible plates/private information before publication.')
        if body.published and not priced_for_publication(db, row):
            raise ApiError(409, 'VEHICLE_PRICES_REQUIRED', 'Add your prices for at least one active service before publishing. Passengers only see a vehicle that already has a price.')
        before = row.version; old = copy.deepcopy(row.verified_eligibility)
        was_published = row.is_published
        row.verified_eligibility = {**row.verified_eligibility, 'publication_fingerprint': fingerprint}; row.is_published = body.published; touch(row); row.updated_by = user.id
        request.app.state.audit.commit(db, actor=user.id, target={'resource': 'vehicles', 'id': str(row.id)}, previous_status=was_published, new_status=body.published,
            previous_version=before, new_version=row.version, full_reason=None, previous_decision_evidence=old, trace_id=request.state.trace_id)
    return {'id': str(row.id), 'version': row.version, 'published': row.is_published}


@router.get('/admin/service-types')
def admin_services(user=Depends(admin), db: Session = Depends(get_db)):
    rows = db.scalars(select(ServiceType).where(ServiceType.category == 'PRIVATE_HIRE').order_by(ServiceType.code).limit(100)).all()
    vehicles = db.scalars(select(Vehicle).order_by(Vehicle.id).limit(1000)).all()
    services = db.scalars(select(VehicleService).order_by(VehicleService.id).limit(5000)).all()
    by_service = {}
    for service_row in services:
        by_service.setdefault(service_row.service_type_id, {})[service_row.vehicle_id] = service_row
    items = []
    for row in rows:
        scope = private_hire_scope(row)
        if scope not in ('AIRPORT', 'LOCAL', 'LONG_DISTANCE', 'EVENT'):
            continue
        ready = [vehicle for vehicle in vehicles if ready_vehicle_service(row, vehicle, by_service.get(row.id, {}).get(vehicle.id))]
        items.append({'id': str(row.id), 'code': row.code, 'name': row.name, 'is_active': row.is_active,
            'version': row.version, 'default_pricing_basis': row.default_pricing_basis, 'pricing_scope': scope,
            'status': catalogue_status(row), 'ready_vehicle_count': len(ready),
            'ready_owner_count': len({vehicle.owner_user_id for vehicle in ready}),
            'ready_vehicles': [{'vehicle_reference': vehicle.public_vehicle_reference,
                'owner_reference': db.get(User, vehicle.owner_user_id).public_user_reference} for vehicle in ready[:100]]})
    return {'items': items}


@router.patch('/admin/service-types/{service_id}/catalogue')
def update_service_catalogue(service_id: UUID, body: ServiceCatalogueUpdate, request: Request, user=Depends(admin), db: Session = Depends(get_db)):
    with request.app.state.audit.coordinated():
        locked_authority(db, request, user, user.id)
        row = db.scalar(select(ServiceType).where(ServiceType.id == service_id, ServiceType.category == 'PRIVATE_HIRE').with_for_update().execution_options(populate_existing=True))
        if not row:
            raise ApiError(404, 'SERVICE_NOT_FOUND', 'Private-hire service not found.')
        if row.version != body.expected_version:
            raise ApiError(409, 'VERSION_CONFLICT', 'Service configuration changed. Reload before saving.')
        before, old_status, old_scope = row.version, catalogue_status(row), private_hire_scope(row)
        row.settings = {**row.settings, 'pricing_scope': body.pricing_scope, 'catalogue_status': body.status}
        row.is_active = body.status == 'ACTIVE'
        touch(row); row.updated_by = user.id
        request.app.state.audit.commit(db, actor=user.id, target={'resource': 'service_types', 'id': str(row.id)}, previous_status=old_status,
            new_status=body.status, previous_version=before, new_version=row.version, full_reason=None,
            previous_decision_evidence={'pricing_scope': old_scope}, trace_id=request.state.trace_id)
    return {'id': str(row.id), 'version': row.version, 'pricing_scope': body.pricing_scope, 'status': body.status, 'is_active': row.is_active}


@router.patch('/admin/service-types/{service_id}/pricing-scope')
def classify_pricing(service_id: UUID, body: PricingScope, request: Request, user=Depends(admin), db: Session = Depends(get_db)):
    with request.app.state.audit.coordinated():
        locked_authority(db, request, user, user.id)
        row = db.scalar(select(ServiceType).where(ServiceType.id == service_id).with_for_update().execution_options(populate_existing=True))
        if not row or row.category != 'PRIVATE_HIRE': raise ApiError(404, 'SERVICE_NOT_FOUND', 'Private-hire service not found.')
        if row.version != body.expected_version: raise ApiError(409, 'VERSION_CONFLICT', 'Service configuration changed.')
        old = copy.deepcopy(row.settings); before = row.version
        row.settings = {**row.settings, 'pricing_scope': body.pricing_scope}; touch(row); row.updated_by = user.id
        request.app.state.audit.commit(db, actor=user.id, target={'resource': 'service_types', 'id': str(row.id)}, previous_status=None, new_status=None,
            previous_version=before, new_version=row.version, full_reason=None, previous_decision_evidence={'settings': old}, trace_id=request.state.trace_id)
    return {'id': str(row.id), 'version': row.version, 'pricing_scope': body.pricing_scope}


@router.post('/admin/service-types', status_code=201)
def create_service(body: ServiceCreate, request: Request, user=Depends(admin), db: Session = Depends(get_db)):
    from sqlalchemy.exc import IntegrityError
    with request.app.state.audit.coordinated():
        locked_authority(db, request, user, user.id)
        row = ServiceType(code=body.code, name=body.name, category='PRIVATE_HIRE', is_active=body.is_active,
            default_pricing_basis=body.default_pricing_basis, settings={'pricing_scope': body.pricing_scope}, created_by=user.id, updated_by=user.id)
        db.add(row)
        try: db.flush()
        except IntegrityError:
            db.rollback(); raise ApiError(409, 'SERVICE_CODE_EXISTS', 'This service code is already configured.') from None
        request.app.state.audit.commit(db, actor=user.id, target={'resource': 'service_types', 'id': str(row.id)}, previous_status=None,
            new_status='ACTIVE' if body.is_active else 'INACTIVE', previous_version=0, new_version=1, full_reason=None, previous_decision_evidence={}, trace_id=request.state.trace_id)
    return {'id': str(row.id), 'version': row.version, 'code': row.code, 'name': row.name, 'is_active': row.is_active}
