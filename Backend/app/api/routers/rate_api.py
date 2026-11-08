"""Independent Owner rate configuration; no fabricated availability or bookings."""
from uuid import UUID
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.routers.api import current, require_role, touch
from app.dependencies.database import get_db
from app.core.errors import ApiError
from app.api.routers.review_api import locked_authority, query_values, pagination, page_result
from app.models.review_models import Vehicle
from app.models.rate_models import ServiceType, VehicleService
from app.schemas.rate_schemas import RateConfiguration, ExamplePreview
from app.services.rate_calculation import calculate
from app.services.pricing_scope import long_distance, require_long_distance

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
            'currency': row.currency, 'rules': row.owner_terms.get('rate_rules', [])}


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
    return {'items': [{'id': str(r.id), 'name': r.name, 'code': r.code, 'pricing_scope': 'LONG_DISTANCE'} for r in rows if long_distance(r)]}


@router.get('/owners/me/vehicles')
def own_vehicles(request: Request, user=Depends(current), db: Session = Depends(get_db)):
    require_role(db, user, 'OWNER')
    from app.api.routers.vehicle_api import summary
    from sqlalchemy import func
    params=query_values(request,{'page','page_size'});params.setdefault('page_size','100')
    page,size=pagination(params)
    q=select(Vehicle).where(Vehicle.owner_user_id==user.id)
    total=db.scalar(select(func.count()).select_from(q.subquery()))
    rows=db.scalars(q.order_by(Vehicle.created_at,Vehicle.id).offset((page-1)*size).limit(size)).all()
    return page_result([summary(r) for r in rows],page,size,total)


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
    require_long_distance(service)
    for rule in body.rules:
        for place in rule.coverage.places or []:
            request.app.state.rate_locations.verify(place)
    row = db.scalar(select(VehicleService).where(VehicleService.vehicle_id == vehicle_id, VehicleService.service_type_id == body.service_type_id).with_for_update())
    if body.expected_version != (row.version if row else 0):
        raise ApiError(409, 'VERSION_CONFLICT', 'Rates changed. Reload the saved rates before editing again.')
    terms = {**(row.owner_terms if row else {}), 'schema_version': 1, 'policy': 'TRAVELLY_LD_2026_10_27', 'rate_rules': [r.model_dump(mode='json') for r in body.rules]}
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
    return row


@router.post('/vehicles/{vehicle_id}/services/preview')
def example_preview(vehicle_id: UUID, body: ExamplePreview, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    owned(db, request, user, vehicle_id)
    try:
        result = calculate(body.rule, body.example)
    except ValueError as exc:
        raise ApiError(422, 'PREVIEW_UNAVAILABLE', str(exc)) from None
    return {**result, 'example_only': True, 'message': 'Owner-entered example only. This is not a booking price or availability promise.'}
