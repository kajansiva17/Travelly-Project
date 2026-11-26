"""Independent Owner rate configuration; no fabricated availability or bookings."""
from uuid import UUID
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.routers.api import current, require_role, touch
from app.dependencies.database import get_db
from app.services.payment_mode import mode_of
from app.core.errors import ApiError
from app.api.routers.review_api import locked_authority, query_values, pagination, page_result
from app.models.review_models import Vehicle
from app.models.rate_models import ServiceType, VehicleService
from app.schemas.rate_schemas import RateConfiguration, ExamplePreview
from app.schemas.hire_schemas import EventPackages
from app.services.rate_calculation import calculate
from app.services.airports import min_distance_km
from app.services.pricing_scope import private_hire_scope, require_supported_private_hire

router = APIRouter(prefix='/api/v1', tags=['Vehicle rates'])


def owned(db, request, user, vehicle_id, lock=False):
    if lock:
        locked_authority(db, request, user, user.id, require_admin=False)
    require_role(db, user, 'OWNER')
    query = select(Vehicle).where(Vehicle.id == vehicle_id, Vehicle.owner_user_id == user.id)
    if lock: query = query.with_for_update().execution_options(populate_existing=True)
    vehicle = db.scalar(query)
    if not vehicle:
        raise ApiError(404, 'VEHICLE_NOT_FOUND', 'Vehicle not found.')
    return vehicle


def summary(row):
    return {'service_type_id': str(row.service_type_id), 'version': row.version, 'enabled': row.is_enabled,
            'currency': row.currency, 'rules': row.owner_terms.get('rate_rules', []), 'event_packages': row.owner_terms.get('event_packages', []),
            'cash_accepted': (row.owner_terms.get('cash') or {}).get('accepted') is True, 'payment_mode': mode_of(row.owner_terms)}


def catalogue_status(service):
    if service.settings.get('catalogue_status') in ('DRAFT', 'NEEDS_REVIEW'):
        return service.settings['catalogue_status']
    if not private_hire_scope(service):
        return 'DRAFT'
    return 'ACTIVE' if service.is_active else 'INACTIVE'


def readiness(service, vehicle, row):
    missing = []
    if catalogue_status(service) != 'ACTIVE': missing.append('Admin service activation')
    if vehicle.verification_status != 'APPROVED': missing.append('Approved vehicle verification')
    if vehicle.availability_status != 'ACTIVE': missing.append('Active vehicle availability')
    if not vehicle.is_published: missing.append('Published eligible vehicle')
    if not row or not row.is_enabled: missing.append('Enabled service rate')
    configured = row.owner_terms.get('event_packages') if private_hire_scope(service) == 'EVENT' and row else row.owner_terms.get('rate_rules') if row else None
    if not configured: missing.append('At least one complete Event package' if private_hire_scope(service) == 'EVENT' else 'At least one complete rate rule')
    return missing


@router.get('/locations')
def locations(request: Request):
    values = query_values(request, {'q'})
    query = values.get('q', '').strip()
    if not 3 <= len(query) <= 150:
        raise ApiError(422, 'VALIDATION_ERROR', 'Enter 3-150 characters to find a location.')
    request.app.state.store.rate('location-ip:' + request.client.host, 30, 60)
    return request.app.state.rate_locations.search(query)


@router.get('/service-types')
def service_types(db: Session = Depends(get_db)):
    rows = db.scalars(select(ServiceType).where(ServiceType.is_active.is_(True), ServiceType.category == 'PRIVATE_HIRE').order_by(ServiceType.display_order, ServiceType.id).limit(100)).all()
    return {'items': [{'id': str(r.id), 'name': r.name, 'code': r.code, 'pricing_scope': private_hire_scope(r),
                       **({'min_distance_km': min_distance_km(r)} if private_hire_scope(r) == 'LONG_DISTANCE' else {})} for r in rows if private_hire_scope(r) in ('AIRPORT','LOCAL','LONG_DISTANCE','EVENT')]}


@router.get('/owners/me/vehicles')
def own_vehicles(request: Request, user=Depends(current), db: Session = Depends(get_db)):
    require_role(db, user, 'OWNER')
    from app.api.routers.vehicle_api import summary
    from sqlalchemy import func
    params=query_values(request,{'page','page_size','removed'});params.setdefault('page_size','100')
    removed=params.pop('removed','false')=='true'
    page,size=pagination(params)
    q=select(Vehicle).where(Vehicle.owner_user_id==user.id,Vehicle.archived_at.isnot(None) if removed else Vehicle.archived_at.is_(None))
    total=db.scalar(select(func.count()).select_from(q.subquery()))
    rows=db.scalars(q.order_by(Vehicle.created_at,Vehicle.id).offset((page-1)*size).limit(size)).all()
    return page_result([summary(r) for r in rows],page,size,total)


@router.get('/owners/me/service-readiness')
def owner_service_readiness(request: Request, user=Depends(current), db: Session = Depends(get_db)):
    require_role(db, user, 'OWNER')
    vehicles = db.scalars(select(Vehicle).where(Vehicle.owner_user_id == user.id).order_by(Vehicle.created_at, Vehicle.id).limit(100)).all()
    services = db.scalars(select(ServiceType).where(ServiceType.category == 'PRIVATE_HIRE').order_by(ServiceType.display_order, ServiceType.id).limit(100)).all()
    supported = [service for service in services if private_hire_scope(service) in ('AIRPORT', 'LOCAL', 'LONG_DISTANCE', 'EVENT')]
    rows = db.scalars(select(VehicleService).where(VehicleService.vehicle_id.in_([vehicle.id for vehicle in vehicles]) if vehicles else False)).all() if vehicles else []
    by_pair = {(row.vehicle_id, row.service_type_id): row for row in rows}
    items = []
    for vehicle in vehicles:
        entries = []
        for service in supported:
            row = by_pair.get((vehicle.id, service.id)); missing = readiness(service, vehicle, row)
            entries.append({'service_type_id': str(service.id), 'name': service.name, 'pricing_scope': private_hire_scope(service),
                'admin_status': catalogue_status(service), 'enabled': bool(row and row.is_enabled), 'rate_version': row.version if row else None,
                'rate_rule_count': len((row.owner_terms.get('event_packages') if private_hire_scope(service) == 'EVENT' else row.owner_terms.get('rate_rules', []))) if row else 0, 'missing': missing, 'ready': not missing})
        items.append({'vehicle_id': str(vehicle.id), 'vehicle_label': vehicle.display_name or vehicle.public_vehicle_reference, 'vehicle_status': vehicle.verification_status,
            'availability_status': vehicle.availability_status, 'published': vehicle.is_published, 'services': entries})
    return {'items': items}


@router.get('/vehicles/{vehicle_id}/services')
def own_rates(vehicle_id: UUID, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    owned(db, request, user, vehicle_id)
    rows = db.scalars(select(VehicleService).where(VehicleService.vehicle_id == vehicle_id).order_by(VehicleService.id)).all()
    return {'items': [summary(r) for r in rows]}


@router.put('/vehicles/{vehicle_id}/services')
def save_rates(vehicle_id: UUID, body: RateConfiguration, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    owned(db, request, user, vehicle_id, lock=True)
    row = persist_rates(vehicle_id, body, request, user, db)
    db.commit()
    return {**summary(row), 'message': 'Reusable rates saved. Future matching requests calculate a fresh price; accepted booking prices stay preserved.'}


def persist_rates(vehicle_id, body, request, user, db):
    service = db.get(ServiceType, body.service_type_id)
    if not service or service.category != 'PRIVATE_HIRE' or not service.is_active:
        raise ApiError(422, 'SERVICE_UNAVAILABLE', 'Choose an active private-hire service.')
    scope = require_supported_private_hire(service)
    if scope == 'EVENT':
        raise ApiError(422, 'EVENT_PACKAGES_REQUIRED', 'Event hire uses event packages, not route rates. Save them with PUT /vehicles/{id}/event-packages.')
    for rule in body.rules:
        for place in rule.coverage.places or []:
            request.app.state.rate_locations.verify(place)
    row = db.scalar(select(VehicleService).where(VehicleService.vehicle_id == vehicle_id, VehicleService.service_type_id == body.service_type_id).with_for_update())
    if body.expected_version != (row.version if row else 0):
        raise ApiError(409, 'VERSION_CONFLICT', 'Rates changed. Reload the saved rates before editing again.')
    terms = {**(row.owner_terms if row else {}), 'schema_version': 2, 'service_scope': scope, 'policy': 'TRAVELLY_PRIVATE_HIRE_2026_11_08', 'rate_rules': [r.model_dump(mode='json') for r in body.rules]}
    basis = {'DISTANCE': 'DISTANCE', 'DAY_HIRE': 'TIME', 'FIXED_ROUTE': 'FIXED'}
    methods = {r.method for r in body.rules}
    # A collection may contain different conditional methods; the canonical rules
    # select exactly one. OWNER_QUOTE never substitutes the first quote's total.
    pricing_basis = basis[next(iter(methods))] if len(methods) == 1 else 'OWNER_QUOTE'
    if row:
        row.is_enabled, row.owner_terms, row.pricing_basis = body.enabled, terms, pricing_basis
        row.base_price = row.price_per_km = row.price_per_hour = None
        row.minimum_hire_hours = row.minimum_hire_km = None
        row.currency = 'LKR'; row.updated_by = user.id; touch(row)
    else:
        row = VehicleService(vehicle_id=vehicle_id, service_type_id=body.service_type_id,
            is_enabled=body.enabled, pricing_basis=pricing_basis, currency='LKR', owner_terms=terms, created_by=user.id, updated_by=user.id)
        db.add(row)
    db.flush()
    if scope == 'LOCAL': sync_event_package(db, vehicle_id, user, row)
    return row


def sync_event_package(db, vehicle_id, user, local_row):
    """Owner decision 24 Nov 2026: Event hire has no price of its own. It uses the vehicle's Local one-day package (hours, included km, price),
    so saving that package keeps the vehicle's Event offer in step. Removing the package switches the Event offer off."""
    events = [s for s in db.scalars(select(ServiceType).where(ServiceType.category == 'PRIVATE_HIRE', ServiceType.is_active.is_(True)).limit(100)).all()
              if private_hire_scope(s) == 'EVENT']
    rule = next((r for r in (local_row.owner_terms or {}).get('rate_rules', []) if r.get('method') == 'DAY_HIRE'), None) if local_row.is_enabled else None
    package = [{'id': rule['id'], 'name': 'Day package', 'hours': rule['included_hours_per_day'], 'price': rule['day_charge'], 'notes': None}] if rule else []
    for service in events:
        row = db.scalar(select(VehicleService).where(VehicleService.vehicle_id == vehicle_id, VehicleService.service_type_id == service.id).with_for_update())
        terms = {**(row.owner_terms if row else {}), 'schema_version': 2, 'service_scope': 'EVENT', 'policy': 'TRAVELLY_EVENT_2026_11_14', 'event_packages': package}
        if row:
            row.is_enabled, row.owner_terms, row.pricing_basis = bool(package), terms, 'FIXED'
            row.currency = 'LKR'; row.updated_by = user.id; touch(row)
        elif package:
            db.add(VehicleService(vehicle_id=vehicle_id, service_type_id=service.id, is_enabled=True, pricing_basis='FIXED', currency='LKR',
                                  owner_terms=terms, created_by=user.id, updated_by=user.id))
    db.flush()


@router.put('/vehicles/{vehicle_id}/event-packages')
def save_event_packages(vehicle_id: UUID, body: EventPackages, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    owned(db, request, user, vehicle_id, lock=True)
    service = db.get(ServiceType, body.service_type_id)
    if not service or not service.is_active or private_hire_scope(service) != 'EVENT':
        raise ApiError(422, 'SERVICE_UNAVAILABLE', 'Choose an active Event service.')
    row = db.scalar(select(VehicleService).where(VehicleService.vehicle_id == vehicle_id, VehicleService.service_type_id == body.service_type_id).with_for_update())
    if body.expected_version != (row.version if row else 0):
        raise ApiError(409, 'VERSION_CONFLICT', 'Packages changed. Reload them before editing again.')
    terms = {**(row.owner_terms if row else {}), 'schema_version': 2, 'service_scope': 'EVENT', 'policy': 'TRAVELLY_EVENT_2026_11_14',
             'event_packages': [p.model_dump(mode='json') for p in body.packages]}
    if row:
        row.is_enabled, row.owner_terms, row.pricing_basis = body.enabled, terms, 'FIXED'
        row.base_price = row.price_per_km = row.price_per_hour = None
        row.minimum_hire_hours = row.minimum_hire_km = None
        row.currency = 'LKR'; row.updated_by = user.id; touch(row)
    else:
        row = VehicleService(vehicle_id=vehicle_id, service_type_id=body.service_type_id, is_enabled=body.enabled, pricing_basis='FIXED',
                             currency='LKR', owner_terms=terms, created_by=user.id, updated_by=user.id)
        db.add(row)
    db.commit()
    return {**summary(row), 'message': 'Event packages saved. Future bookings use these prices; accepted bookings keep theirs.'}


@router.post('/vehicles/{vehicle_id}/services/preview')
def example_preview(vehicle_id: UUID, body: ExamplePreview, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    owned(db, request, user, vehicle_id)
    try:
        result = calculate(body.rule, body.example)
    except ValueError as exc:
        raise ApiError(422, 'PREVIEW_UNAVAILABLE', str(exc)) from None
    return {**result, 'example_only': True, 'message': 'Owner-entered example only. This is not a booking price or availability promise.'}
