import copy
import hashlib
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo
from sqlalchemy import select, exists
from app.models import User, UserRole
from app.models.review_models import Document, Vehicle
from app.models.rate_models import VehicleService, ServiceType
from app.models.hire_models import Booking, Trip, VehicleRecord, ScheduledTrip, Notification
from app.schemas.rate_schemas import RateRule, covered, departure_applies, extra_mode, EXTRA_METHODS
from app.services.pricing_scope import require_supported_private_hire
from app.services.rate_calculation import calculate
from app.core.errors import ApiError
from app.api.routers.api import allowed_account, touch
from app.services.pickup_codes import MAX_ATTEMPTS

ZONE = ZoneInfo('Asia/Colombo')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()


def approved(db, uid, role):
    return bool(db.scalar(select(UserRole.id).where(UserRole.user_id == uid, UserRole.role_code == role, UserRole.approval_status == 'APPROVED')))


def current_documents(db, *, uid=None, vid=None, at=None):
    day = (at or datetime.now(timezone.utc)).astimezone(ZONE).date()
    where = Document.user_id == uid if uid else Document.vehicle_id == vid
    replacement=Document.__table__.alias('replacement')
    rows = db.scalars(select(Document).where(where, Document.status == 'APPROVED',
        ~exists(select(replacement.c.id).where(replacement.c.superseded_document_id==Document.id))).order_by(Document.verified_at.desc(), Document.id)).all()
    found = {}
    for r in rows:
        if (r.expiry_date is not None and r.expiry_date < day) or (r.issue_date is not None and r.issue_date > day): continue
        if r.document_type not in found: found[r.document_type] = r
    return found


def vehicle_evidence(db, vehicle, at=None):
    policy = vehicle.verified_eligibility
    applicability = policy.get('conditional_documents', {})
    if 'EMISSION' not in applicability or not set(applicability) <= {'EMISSION', 'FITNESS', 'ROUTE_PERMIT'} or any(type(v) is not bool for v in applicability.values()):
        raise ApiError(409, 'VEHICLE_EVIDENCE_UNKNOWN', 'Vehicle evidence applicability has not been verified.')
    if type(policy.get('authorisation_required')) is not bool or not policy.get('category'):
        raise ApiError(409, 'VEHICLE_EVIDENCE_UNKNOWN', 'The registered-owner case and vehicle category must be reviewed.')
    # A route permit is optional for every vehicle (project-owner decision), even on vehicles reviewed before that rule.
    required = {'VEHICLE_REGISTRATION', 'INSURANCE', 'REVENUE_LICENCE'} | {t for t, needed in applicability.items() if needed and t not in ('ROUTE_PERMIT', 'FITNESS')}
    if policy['authorisation_required']: required.add('OWNER_AUTHORISATION')
    docs = current_documents(db, vid=vehicle.id, at=at)
    if not required <= set(docs):
        raise ApiError(409, 'VEHICLE_DOCUMENTS_REQUIRED', 'Required vehicle evidence is missing, expired or unverified.')
    return digest({t: [str(docs[t].id), docs[t].version] for t in sorted(required)})


def eligible_vehicle(db, vehicle, *, public=False, at=None):
    owner = db.get(User, vehicle.owner_user_id)
    allowed_account(owner)
    if not approved(db, owner.id, 'OWNER') or not owner.email_verified_at or vehicle.verification_status != 'APPROVED':
        raise ApiError(409, 'VEHICLE_NOT_ELIGIBLE', 'Verified email, approved Owner and vehicle verification are required.')
    if vehicle.availability_status != 'ACTIVE':
        raise ApiError(409, 'VEHICLE_NOT_AVAILABLE', 'The vehicle is not operationally available.')
    fingerprint = vehicle_evidence(db, vehicle, at=at)
    from app.services.vehicle_rules import has_exterior, require_complete
    if public:require_complete(vehicle)
    if public and not has_exterior(vehicle):raise ApiError(404,'VEHICLE_NOT_FOUND','Vehicle not found.')
    if public and (not vehicle.is_published or fingerprint != vehicle.verified_eligibility.get('publication_fingerprint')):
        raise ApiError(404, 'VEHICLE_NOT_FOUND', 'Vehicle not found.')
    return fingerprint


def compatible_driver(db, driver, vehicle, service, at):
    allowed_account(driver)
    if not approved(db, driver.id, 'DRIVER'):
        raise ApiError(409, 'DRIVER_NOT_ELIGIBLE', 'The Driver must have current approved Driver membership.')
    licence = current_documents(db, uid=driver.id, at=at).get('DRIVING_LICENCE')
    from app.services.hire_defaults import accepted_licences
    accepted = accepted_licences(service.settings, vehicle)
    if not licence or licence.issuing_country != 'LK' or not licence.expiry_date or not accepted or not set(licence.verified_categories).intersection(accepted):
        raise ApiError(409, 'DRIVER_CATEGORY_MISMATCH', 'Verified current licence categories do not match this vehicle/service. Missing compatibility rules block assignment.')


def route_profile(service, vehicle):
    from app.services.hire_defaults import routing_profile_for
    profile = routing_profile_for(service.settings, vehicle)
    if profile not in ('driving-car', 'driving-hgv'):
        raise ApiError(409, 'ROUTING_PROFILE_REQUIRED', 'The reviewed vehicle/service routing profile is not configured.')
    return profile


def no_conflict(db, vehicle_id, start, end, *, exclude=None, driver_id=None):
    from app.services.availability import no_vehicle_conflict
    no_vehicle_conflict(db, vehicle_id, start, end, exclude)
    if driver_id:
        q = select(Trip.id).where(Trip.driver_user_id == driver_id, Trip.assignment_status == 'ACCEPTED', Trip.status.notin_(('COMPLETED', 'CANCELLED')), Trip.scheduled_start_at < end, Trip.scheduled_end_at > start)
        if exclude: q = q.where(Trip.booking_id != exclude)
        # A self-drive rental has no Driver: the Owner is only the operator who hands over and takes back, so it never blocks them.
        q = q.where(~exists(select(Booking.id).where(Booking.id == Trip.booking_id, Booking.booking_type == 'RENTAL')))
        if db.scalar(q.limit(1)):
            raise ApiError(409, 'DRIVER_SCHEDULE_CONFLICT', 'The Driver already has an overlapping accepted trip.')


def matches(rule, itinerary, geometry=None):
    day = itinerary.start_at.astimezone(ZONE).date()
    if (rule.method == 'DAY_HIRE') != (itinerary.method == 'DAY_HIRE') or rule.direction != itinerary.direction or day < rule.effective_from or (rule.effective_until and day > rule.effective_until): return False
    if rule.method == 'FIXED_ROUTE' and not departure_applies(rule.departure, itinerary.start_at.astimezone(ZONE)): return False
    if rule.effective_until and (itinerary.requested_end() - timedelta(microseconds=1)).astimezone(ZONE).date() > rule.effective_until: return False
    places = [s.place for s in itinerary.stops]
    if not covered(rule.pickup_area, places[0]): return False
    if rule.coverage.kind == 'ROUTE':
        return [(p.latitude, p.longitude) for p in places] == [(p.latitude, p.longitude) for p in rule.coverage.places]
    # Area rules: only the pickup must be inside the coverage area.
    # Destination and intermediate stops may be anywhere — the per-km rate covers the full distance.
    area = rule.coverage.area
    if not covered(area, places[0]): return False
    return True


def matching_rules(rules, itinerary, geometry=None):
    candidates = [r for r in rules if matches(r, itinerary, geometry)]
    if itinerary.method == 'DISTANCE' and itinerary.direction == 'ONE_WAY':
        fixed = [r for r in candidates if r.method == 'FIXED_ROUTE']
        if fixed: return fixed
    return candidates


USED = {'WAITING': ('WAIT',), 'EXTRA_KM': ('EXTRA_KM',), 'EXTRA_HOURS': ('EXTRA_HOURS_',), 'OVERNIGHT': ('OVERNIGHT',)}
EXTRA_NAMES = {'WAITING': 'waiting', 'EXTRA_KM': 'distance beyond the included km', 'EXTRA_HOURS': 'hours beyond the daily package', 'OVERNIGHT': 'overnight stays'}


def refuse_unoffered_extras(rule, result):
    """Owner decision 14 Nov 2026: an extra the Owner marked NOT_OFFERED cannot be part of the journey; the Passenger asks for a quote."""
    for key, prefixes in USED.items():
        if key in EXTRA_METHODS and rule.method in EXTRA_METHODS[key] and extra_mode(rule, key) == 'NOT_OFFERED':
            if any(line['code'].startswith(prefixes) and Decimal(line['quantity']) > 0 and line['kind'] == 'CHARGE' for line in result['breakdown']):
                raise ApiError(409, 'QUOTE_REQUIRED', f"This Owner does not offer {EXTRA_NAMES[key]} on this rate. Request an Owner quote.")


def extra_policies(rule):
    """What the Passenger is told before booking about every extra: not offered, free, or the rate."""
    detail = {'WAITING': lambda: {'free_minutes': str(rule.free_wait_minutes), 'hour_rate': str(rule.waiting_hour_rate)},
              'EXTRA_KM': lambda: {'km_rate': str(rule.extra_km_rate)}, 'EXTRA_HOURS': lambda: {'hour_rate': str(rule.extra_hour_rate)},
              'OVERNIGHT': lambda: {'cost': str(rule.overnight_driver_cost)}}
    out = []
    for key in detail:
        if rule.method in EXTRA_METHODS[key]:
            mode = extra_mode(rule, key)
            out.append({'code': key, 'mode': mode, **(detail[key]() if mode == 'CHARGED' else {})})
    return out


def price(request, service, vehicle, itinerary, rules, *, agreed_rule=False):
    scope = require_supported_private_hire(service)
    measurement = request.app.state.hire_routing.measure(itinerary, route_profile(service, vehicle))
    candidates = list(rules) if agreed_rule else matching_rules(rules, itinerary, measurement['geometry'])
    if len(candidates) != 1:
        raise ApiError(409, 'QUOTE_REQUIRED', 'Saved rates do not uniquely cover this complete itinerary. Request an Owner quote.')
    rule = candidates[0]
    if agreed_rule and (not covered(rule.pickup_area, itinerary.stops[0].place)):
        raise ApiError(409, 'MANUAL_REVIEW_REQUIRED', 'This change is outside the agreed pickup coverage.')
    try: result = calculate(rule, measurement['usage'])
    except ValueError as exc: raise ApiError(422, 'PRICING_UNAVAILABLE', str(exc)) from None
    if not agreed_rule: refuse_unoffered_extras(rule, result)
    end = itinerary.requested_end()
    if result['reserved_service_hours']:
        end = itinerary.start_at + timedelta(hours=24 * (len(itinerary.service_hours)-1) + float(Decimal(result['reserved_service_hours'][-1])))
    # A return has a second, separately checked interval.  The booking still
    # retains the full enclosing reservation so acceptance and later operator
    # assignment cannot release the vehicle between its two travel intervals.
    end = max(end, itinerary.requested_end())
    if not agreed_rule and rule.effective_until and (end - timedelta(microseconds=1)).astimezone(ZONE).date() > rule.effective_until:
        raise ApiError(409, 'QUOTE_REQUIRED', 'The saved rate does not cover the complete reserved interval. Request an Owner quote.')
    hours_note = {'planned_service_hours': [str(h) for h in measurement['usage'].service_hours], 'package_hours': str(rule.included_hours_per_day),
                                                                                'package_km': str(rule.included_km_per_day), 'package_days': len(measurement['usage'].service_hours)} if rule.method == 'DAY_HIRE' else {}
    return {'calculation': {**result, 'service_scope': scope, 'extra_policies': extra_policies(rule), **hours_note}, 'rule': rule.model_dump(mode='json'), 'itinerary': itinerary.model_dump(mode='json'),
            'measurement': {'source': measurement['source'], 'usage': measurement['usage'].model_dump(mode='json')},
            'reserved_end_at': end.isoformat()}


def event_price(service, row, itinerary):
    """Event hire: the Owner's fixed package price. No route measuring; the package fixes the hours."""
    packages = (row.owner_terms.get('event_packages') if row else None) or []
    package = next((p for p in packages if itinerary.event_package_id and p['id'] == str(itinerary.event_package_id)), None)
    if not package:
        raise ApiError(422, 'EVENT_PACKAGE_REQUIRED', 'Choose one of this vehicle\u2019s event packages.')
    hours = Decimal(package['hours'])
    if itinerary.direction != 'ONE_WAY' or itinerary.service_hours != [hours]:
        raise ApiError(422, 'EVENT_PACKAGE_MISMATCH', 'An event booking is one day with the package hours, with no return leg.')
    total = Decimal(package['price']).quantize(Decimal('.01'))
    end = itinerary.start_at + timedelta(hours=float(hours))
    line = {'code': 'EVENT_PACKAGE', 'label': package['name'], 'quantity': '1', 'rate': str(total), 'amount': str(total), 'kind': 'CHARGE'}
    return {'calculation': {'method': 'EVENT_PACKAGE', 'currency': 'LKR', 'breakdown': [line], 'total': format(total, '.2f'),
                            'exclusions': ['Hours or services beyond the package are agreed directly with the Owner.'],
                            'policy': 'TRAVELLY_EVENT_2026_11_14', 'included_km': None, 'reserved_service_hours': [], 'service_scope': 'EVENT',
                            'package': {'id': package['id'], 'name': package['name'], 'hours': str(hours)}},
            'rule': {'method': 'EVENT_PACKAGE', **package}, 'itinerary': itinerary.model_dump(mode='json'),
            'measurement': {'source': 'EVENT_PACKAGE', 'usage': None}, 'reserved_end_at': end.isoformat()}


def saved_rules(db, vid, sid):
    row = db.scalar(select(VehicleService).where(VehicleService.vehicle_id == vid, VehicleService.service_type_id == sid, VehicleService.is_enabled.is_(True)))
    return row, [RateRule.model_validate(r) for r in row.owner_terms.get('rate_rules', [])] if row else []


def booking_summary(row):
    return {'id': str(row.id), 'reference': row.booking_reference, 'booking_type': row.booking_type, 'vehicle_id': str(row.vehicle_id), 'owner_user_id': str(row.owner_user_id),
            'passenger_user_id': str(row.passenger_user_id), 'service_type_id': str(row.service_type_id), 'status': row.status, 'version': row.version,
            'start_at': row.start_at.isoformat(), 'end_at': row.end_at.isoformat(), 'passenger_count': row.passenger_count,
            'large_luggage_count': row.large_luggage_count, 'small_luggage_count': row.small_luggage_count,
            'itinerary': row.itinerary_snapshot, 'price': row.price_snapshot, 'proposal': row.pending_change,
            'accepted_quote_digest': row.accepted_quote_digest, 'vehicle_committed': row.vehicle_committed,
            'total_amount': str(row.total_amount) if row.total_amount is not None else None, 'currency': row.currency,
            'origin_text': row.origin_text, 'destination_text': row.destination_text}


def trip_summary(trip):
    """Trip facts for the assigned Driver, the booking Passenger, the booking Owner and Admin.
    Live coordinates are reported only while tracking is on; completion and cancellation end it."""
    live = trip.tracking_status in ('ACTIVE', 'STALE') and trip.location_updated_at is not None
    return {'id': str(trip.id), 'booking_id': str(trip.booking_id) if trip.booking_id else None,
            # A departure carries many Travellers, so the operator boards them one by one instead of checking one pickup code.
            'scheduled_trip_id': str(trip.scheduled_trip_id) if trip.scheduled_trip_id else None,
            'driver_user_id': str(trip.driver_user_id) if trip.driver_user_id else None,
            'assignment_type': trip.assignment_type, 'assignment_status': trip.assignment_status,
            'status': trip.status, 'version': trip.version,
            'scheduled_start_at': trip.scheduled_start_at.isoformat(), 'scheduled_end_at': trip.scheduled_end_at.isoformat(),
            'actual_start_at': trip.actual_start_at.isoformat() if trip.actual_start_at else None,
            'actual_end_at': trip.actual_end_at.isoformat() if trip.actual_end_at else None,
            'start_odometer_km': str(trip.start_odometer_km) if trip.start_odometer_km is not None else None,
            'end_odometer_km': str(trip.end_odometer_km) if trip.end_odometer_km is not None else None,
            'calculated_distance_km': str(trip.calculated_distance_km) if trip.calculated_distance_km is not None else None,
            'tracking_status': trip.tracking_status,
            'location': {'latitude': str(trip.current_latitude), 'longitude': str(trip.current_longitude),
                         'accuracy_m': str(trip.location_accuracy_m) if trip.location_accuracy_m is not None else None,
                         'speed_kph': str(trip.current_speed_kph) if trip.current_speed_kph is not None else None,
                         'updated_at': trip.location_updated_at.isoformat()} if live else None,
            'breakdown_details': trip.breakdown_details, 'completion_notes': trip.completion_notes,
            'pickup': {'code_issued': bool(trip.pickup_code_version),
                       'verified_at': trip.pickup_verified_at.isoformat() if trip.pickup_verified_at else None,
                       'attempts_left': max(0, MAX_ATTEMPTS - (trip.pickup_failed_attempts or 0))}}


def notify(db, booking, title, body, driver_id=None):
    for uid in sorted({booking.passenger_user_id, booking.owner_user_id, driver_id} - {None}, key=str):
        db.add(Notification(recipient_user_id=uid, booking_id=booking.id, notification_type='RECONFIRMATION', channel='IN_APP',
            title=title, body=body, action_required=True, action_payload={'booking_id': str(booking.id)}, status='QUEUED'))


def audited(request, db, user, row, previous, reason):
    touch(row); row.updated_by = user.id
    request.app.state.audit.commit(db, actor=user.id, target={'resource': 'bookings', 'id': str(row.id)},
        previous_status=previous['status'], new_status=row.status, previous_version=previous['version'], new_version=row.version,
        full_reason=reason, previous_decision_evidence=previous, trace_id=request.state.trace_id)
