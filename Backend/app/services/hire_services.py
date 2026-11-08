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
from app.schemas.rate_schemas import RateRule, covered, departure_applies
from app.services.pricing_scope import require_long_distance
from app.services.rate_calculation import calculate
from app.core.errors import ApiError
from app.api.routers.api import allowed_account, touch

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
    if set(applicability) != {'EMISSION', 'FITNESS', 'ROUTE_PERMIT'} or any(type(v) is not bool for v in applicability.values()):
        raise ApiError(409, 'VEHICLE_EVIDENCE_UNKNOWN', 'Vehicle evidence applicability has not been verified.')
    if type(policy.get('authorisation_required')) is not bool or not policy.get('category'):
        raise ApiError(409, 'VEHICLE_EVIDENCE_UNKNOWN', 'The registered-owner case and vehicle category must be reviewed.')
    required = {'VEHICLE_REGISTRATION', 'INSURANCE', 'REVENUE_LICENCE'} | {t for t, needed in applicability.items() if needed}
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
    category = vehicle.verified_eligibility.get('category')
    accepted = service.settings.get('licence_compatibility', {}).get(category)
    if not licence or licence.issuing_country != 'LK' or not licence.expiry_date or not accepted or not set(licence.verified_categories).intersection(accepted):
        raise ApiError(409, 'DRIVER_CATEGORY_MISMATCH', 'Verified current licence categories do not match this vehicle/service. Missing compatibility rules block assignment.')


def route_profile(service, vehicle):
    profile = service.settings.get('routing_profiles', {}).get(vehicle.verified_eligibility.get('category'))
    if profile not in ('driving-car', 'driving-hgv'):
        raise ApiError(409, 'ROUTING_PROFILE_REQUIRED', 'The reviewed vehicle/service routing profile is not configured.')
    return profile


def no_conflict(db, vehicle_id, start, end, *, exclude=None, driver_id=None):
    from app.services.availability import no_vehicle_conflict
    no_vehicle_conflict(db, vehicle_id, start, end, exclude)
    if driver_id:
        q = select(Trip.id).where(Trip.driver_user_id == driver_id, Trip.assignment_status == 'ACCEPTED', Trip.status.notin_(('COMPLETED', 'CANCELLED')), Trip.scheduled_start_at < end, Trip.scheduled_end_at > start)
        if exclude: q = q.where(Trip.booking_id != exclude)
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
    area = rule.coverage.area
    if not all(covered(area, p) for p in places): return False
    if geometry:
        return all(area.west <= Decimal(str(p[0])) <= area.east and area.south <= Decimal(str(p[1])) <= area.north for p in geometry)
    return True


def matching_rules(rules, itinerary, geometry=None):
    candidates = [r for r in rules if matches(r, itinerary, geometry)]
    if itinerary.method == 'DISTANCE' and itinerary.direction == 'ONE_WAY':
        fixed = [r for r in candidates if r.method == 'FIXED_ROUTE']
        if fixed: return fixed
    return candidates


def price(request, service, vehicle, itinerary, rules, *, agreed_rule=False):
    require_long_distance(service)
    measurement = request.app.state.hire_routing.measure(itinerary, route_profile(service, vehicle))
    candidates = list(rules) if agreed_rule else matching_rules(rules, itinerary, measurement['geometry'])
    if len(candidates) != 1:
        raise ApiError(409, 'QUOTE_REQUIRED', 'Saved rates do not uniquely cover this complete itinerary. Request an Owner quote.')
    rule = candidates[0]
    if agreed_rule and (not covered(rule.pickup_area, itinerary.stops[0].place)):
        raise ApiError(409, 'MANUAL_REVIEW_REQUIRED', 'This change is outside the agreed pickup coverage.')
    try: result = calculate(rule, measurement['usage'])
    except ValueError as exc: raise ApiError(422, 'PRICING_UNAVAILABLE', str(exc)) from None
    end = itinerary.requested_end()
    if result['reserved_service_hours']:
        end = itinerary.start_at + timedelta(hours=24 * (len(itinerary.service_hours)-1) + float(Decimal(result['reserved_service_hours'][-1])))
    if not agreed_rule and rule.effective_until and (end - timedelta(microseconds=1)).astimezone(ZONE).date() > rule.effective_until:
        raise ApiError(409, 'QUOTE_REQUIRED', 'The saved rate does not cover the complete reserved interval. Request an Owner quote.')
    return {'calculation': result, 'rule': rule.model_dump(mode='json'), 'itinerary': itinerary.model_dump(mode='json'),
            'measurement': {'source': measurement['source'], 'usage': measurement['usage'].model_dump(mode='json')},
            'reserved_end_at': end.isoformat()}


def saved_rules(db, vid, sid):
    row = db.scalar(select(VehicleService).where(VehicleService.vehicle_id == vid, VehicleService.service_type_id == sid, VehicleService.is_enabled.is_(True)))
    return row, [RateRule.model_validate(r) for r in row.owner_terms.get('rate_rules', [])] if row else []


def booking_summary(row):
    return {'id': str(row.id), 'reference': row.booking_reference, 'vehicle_id': str(row.vehicle_id), 'owner_user_id': str(row.owner_user_id),
            'passenger_user_id': str(row.passenger_user_id), 'service_type_id': str(row.service_type_id), 'status': row.status, 'version': row.version,
            'start_at': row.start_at.isoformat(), 'end_at': row.end_at.isoformat(), 'passenger_count': row.passenger_count,
            'large_luggage_count': row.large_luggage_count, 'small_luggage_count': row.small_luggage_count,
            'itinerary': row.itinerary_snapshot, 'price': row.price_snapshot, 'proposal': row.pending_change,
            'accepted_quote_digest': row.accepted_quote_digest, 'vehicle_committed': row.vehicle_committed,
            'total_amount': str(row.total_amount) if row.total_amount is not None else None, 'currency': row.currency}


def notify(db, booking, title, body, driver_id=None):
    for uid in sorted({booking.passenger_user_id, booking.owner_user_id, driver_id} - {None}, key=str):
        db.add(Notification(recipient_user_id=uid, booking_id=booking.id, notification_type='RECONFIRMATION', channel='IN_APP',
            title=title, body=body, action_required=True, action_payload={'booking_id': str(booking.id)}, status='QUEUED'))


def audited(request, db, user, row, previous, reason):
    touch(row); row.updated_by = user.id
    request.app.state.audit.commit(db, actor=user.id, target={'resource': 'bookings', 'id': str(row.id)},
        previous_status=previous['status'], new_status=row.status, previous_version=previous['version'], new_version=row.version,
        full_reason=reason, previous_decision_evidence=previous, trace_id=request.state.trace_id)
