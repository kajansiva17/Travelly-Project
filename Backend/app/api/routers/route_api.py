"""Routes and ordered stops (matrix 27-31) on the approved `routes` and `route_stops` tables.

Public reads expose ACTIVE routes only. Admin writes use the same coordinated, durably audited
write path as other Admin configuration changes. Stops are never hard-deleted: a stop left out of
a replacement list is deactivated and parked at an unused order so history keeps its identifiers.
"""
from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.api.routers.api import touch
from app.api.routers.review_api import admin, locked_authority
from app.core.errors import ApiError
from app.dependencies.database import get_db
from app.models.hire_models import Route, RouteStop
from app.schemas.route_schemas import RouteCreate, RoutePatch, StopsReplace

router = APIRouter(prefix='/api/v1', tags=['Routes'])

TRANSITIONS = {'DRAFT': {'ACTIVE', 'INACTIVE'}, 'ACTIVE': {'INACTIVE'}, 'INACTIVE': {'ACTIVE'}}
TEMP_ORDER = 10000      # transient stop_order while a replacement is applied
PARKED_ORDER = 20000    # first stop_order used for deactivated stops
EDITABLE = ('route_name', 'origin_name', 'destination_name', 'origin_latitude', 'origin_longitude',
            'destination_latitude', 'destination_longitude', 'estimated_distance_km', 'estimated_duration_minutes')


def text_or_none(value):
    return None if value is None else str(value)


def stop_out(stop):
    return {'id': str(stop.id), 'stop_order': stop.stop_order, 'stop_code': stop.stop_code, 'stop_name': stop.stop_name,
            'latitude': str(stop.latitude), 'longitude': str(stop.longitude), 'pickup_allowed': stop.pickup_allowed,
            'dropoff_allowed': stop.dropoff_allowed, 'scheduled_offset_minutes': stop.scheduled_offset_minutes}


def route_out(route, stops=None, admin_view=False):
    out = {'id': str(route.id), 'route_code': route.route_code, 'route_name': route.route_name,
           'origin_name': route.origin_name, 'destination_name': route.destination_name,
           'origin_latitude': text_or_none(route.origin_latitude), 'origin_longitude': text_or_none(route.origin_longitude),
           'destination_latitude': text_or_none(route.destination_latitude), 'destination_longitude': text_or_none(route.destination_longitude),
           'estimated_distance_km': text_or_none(route.estimated_distance_km), 'estimated_duration_minutes': route.estimated_duration_minutes}
    if admin_view:
        out.update({'status': route.status, 'version': route.version})
    if stops is not None:
        out['stops'] = [stop_out(s) for s in stops]
    return out


def active_stops(db, route_id):
    return db.scalars(select(RouteStop).where(RouteStop.route_id == route_id, RouteStop.is_active.is_(True))
                      .order_by(RouteStop.stop_order)).all()


def validate_stops(stops):
    """Business-neutral structural checks only; no fares, times or policies are inferred."""
    codes = [s.stop_code.lower() for s in stops if s.stop_code]
    if len(codes) != len(set(codes)):
        raise ApiError(422, 'VALIDATION_ERROR', 'Stop codes must be unique within a route.')
    ids = [s.id for s in stops if s.id]
    if len(ids) != len(set(ids)):
        raise ApiError(422, 'VALIDATION_ERROR', 'A stop can appear only once in the list.')
    offsets = [s.scheduled_offset_minutes for s in stops]
    if offsets != sorted(offsets):
        raise ApiError(422, 'VALIDATION_ERROR', 'Stop time offsets must not decrease along the route.')
    if not stops[0].pickup_allowed or not stops[-1].dropoff_allowed:
        raise ApiError(422, 'VALIDATION_ERROR', 'The first stop must allow pick-up and the last stop must allow drop-off.')


def like_pattern(value):
    return '%' + value.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'


def audit(request, db, user, route, previous_status, previous_version, evidence):
    request.app.state.audit.commit(
        db, actor=user.id, target={'resource': 'routes', 'id': str(route.id)},
        previous_status=previous_status, new_status=route.status,
        previous_version=previous_version, new_version=route.version,
        full_reason=None, previous_decision_evidence=evidence, trace_id=request.state.trace_id)


def locked_route(db, route_id, expected_version):
    route = db.scalar(select(Route).where(Route.id == route_id).with_for_update().execution_options(populate_existing=True))
    if not route:
        raise ApiError(404, 'ROUTE_NOT_FOUND', 'Route not found.')
    if route.version != expected_version:
        raise ApiError(409, 'VERSION_CONFLICT', 'The route changed. Refresh before saving.')
    return route


@router.get('/routes')
def list_routes(origin: str = Query('', max_length=100), destination: str = Query('', max_length=100),
                limit: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0, le=10000), db: Session = Depends(get_db)):
    query = select(Route).where(Route.status == 'ACTIVE')
    if origin.strip():
        query = query.where(Route.origin_name.ilike(like_pattern(origin.strip()), escape='\\'))
    if destination.strip():
        query = query.where(Route.destination_name.ilike(like_pattern(destination.strip()), escape='\\'))
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.scalars(query.order_by(Route.route_name, Route.id).limit(limit).offset(offset)).all()
    return {'items': [route_out(r) for r in rows], 'total': total, 'limit': limit, 'offset': offset}


@router.get('/routes/{route_id}')
def read_route(route_id: UUID, db: Session = Depends(get_db)):
    route = db.get(Route, route_id)
    if not route or route.status != 'ACTIVE':
        raise ApiError(404, 'ROUTE_NOT_FOUND', 'Route not found.')
    return route_out(route, active_stops(db, route.id))


@router.post('/admin/routes', status_code=201)
def create_route(body: RouteCreate, request: Request, user=Depends(admin), db: Session = Depends(get_db)):
    validate_stops(body.stops)
    with request.app.state.audit.coordinated():
        locked_authority(db, request, user, user.id)
        if db.scalar(select(Route.id).where(Route.route_code == body.route_code)):
            raise ApiError(409, 'ROUTE_CODE_EXISTS', 'A route with this code already exists.')
        status = 'ACTIVE' if body.active else 'DRAFT'
        route = Route(route_code=body.route_code, status=status, created_by=user.id, updated_by=user.id,
                      **body.model_dump(include=set(EDITABLE)))
        if status == 'ACTIVE':
            route.approved_by = user.id
            route.approved_at = datetime.now(timezone.utc)
        db.add(route)
        db.flush()
        for index, stop in enumerate(body.stops):
            db.add(RouteStop(route_id=route.id, stop_order=index, stop_code=stop.stop_code, stop_name=stop.stop_name,
                             latitude=stop.latitude, longitude=stop.longitude, pickup_allowed=stop.pickup_allowed,
                             dropoff_allowed=stop.dropoff_allowed, scheduled_offset_minutes=stop.scheduled_offset_minutes,
                             created_by=user.id, updated_by=user.id))
        db.flush()
        route_id = route.id
        route.version = 1
        request.app.state.audit.commit(
            db, actor=user.id, target={'resource': 'routes', 'id': str(route_id)}, previous_status=None, new_status=status,
            previous_version=0, new_version=1, full_reason=None, previous_decision_evidence={}, trace_id=request.state.trace_id)
    route = db.get(Route, route_id)
    return route_out(route, active_stops(db, route_id), admin_view=True)


@router.patch('/admin/routes/{route_id}')
def update_route(route_id: UUID, body: RoutePatch, request: Request, user=Depends(admin), db: Session = Depends(get_db)):
    changes = body.model_dump(exclude_unset=True, exclude={'expected_version'})
    if not changes:
        raise ApiError(422, 'VALIDATION_ERROR', 'Provide at least one field to change.')
    with request.app.state.audit.coordinated():
        locked_authority(db, request, user, user.id)
        route = locked_route(db, route_id, body.expected_version)
        previous_status, previous_version = route.status, route.version
        evidence = {name: text_or_none(getattr(route, name)) for name in changes}
        new_status = changes.pop('status', None)
        for name in changes:
            if name in ('route_name', 'origin_name', 'destination_name') and changes[name] is None:
                raise ApiError(422, 'VALIDATION_ERROR', 'Names cannot be empty.')
            setattr(route, name, changes[name])
        if new_status and new_status != route.status:
            if new_status not in TRANSITIONS[route.status]:
                raise ApiError(409, 'INVALID_ROUTE_TRANSITION', 'This status change is not allowed.')
            if new_status == 'ACTIVE':
                if len(active_stops(db, route.id)) < 2:
                    raise ApiError(409, 'ROUTE_STOPS_REQUIRED', 'A route needs at least two stops to be active.')
                route.approved_by = user.id
                route.approved_at = datetime.now(timezone.utc)
            route.status = new_status
        touch(route)
        route.updated_by = user.id
        audit(request, db, user, route, previous_status, previous_version, evidence)
    route = db.get(Route, route_id)
    return route_out(route, active_stops(db, route_id), admin_view=True)


@router.put('/admin/routes/{route_id}/stops')
def replace_stops(route_id: UUID, body: StopsReplace, request: Request, user=Depends(admin), db: Session = Depends(get_db)):
    validate_stops(body.stops)
    with request.app.state.audit.coordinated():
        locked_authority(db, request, user, user.id)
        route = locked_route(db, route_id, body.expected_version)
        existing = db.scalars(select(RouteStop).where(RouteStop.route_id == route.id).order_by(RouteStop.id)
                              .with_for_update().execution_options(populate_existing=True)).all()
        by_id = {s.id: s for s in existing}
        for stop in body.stops:
            if stop.id and stop.id not in by_id:
                raise ApiError(422, 'VALIDATION_ERROR', 'A listed stop does not belong to this route.')
        evidence = {'stops': [{'id': str(s.id), 'stop_order': s.stop_order, 'stop_code': s.stop_code,
                               'stop_name': s.stop_name, 'is_active': s.is_active} for s in existing]}
        kept = {s.id for s in body.stops if s.id}
        parked = max([s.stop_order for s in existing if s.stop_order >= PARKED_ORDER] + [PARKED_ORDER - 1]) + 1
        for stop in sorted((s for s in existing if s.id not in kept), key=lambda s: s.stop_order):
            stop.stop_order, parked = parked, parked + 1
            stop.stop_code = None  # frees the code for reuse; the previous code stays in the audit evidence
            stop.is_active = False
            touch(stop)
            stop.updated_by = user.id
        db.flush()
        for index, stop in enumerate(body.stops):
            if stop.id:
                by_id[stop.id].stop_order = TEMP_ORDER + index
                by_id[stop.id].stop_code = None  # avoids transient code collisions while stops are re-ordered
        db.flush()
        for index, stop in enumerate(body.stops):
            values = dict(stop_code=stop.stop_code, stop_name=stop.stop_name, latitude=stop.latitude, longitude=stop.longitude,
                          pickup_allowed=stop.pickup_allowed, dropoff_allowed=stop.dropoff_allowed,
                          scheduled_offset_minutes=stop.scheduled_offset_minutes, is_active=True)
            if stop.id:
                row = by_id[stop.id]
                for name, value in values.items():
                    setattr(row, name, value)
                row.stop_order = index
                touch(row)
                row.updated_by = user.id
            else:
                db.add(RouteStop(route_id=route.id, stop_order=index, created_by=user.id, updated_by=user.id, **values))
        db.flush()
        previous_version = route.version
        touch(route)
        route.updated_by = user.id
        audit(request, db, user, route, route.status, previous_version, evidence)
    route = db.get(Route, route_id)
    return route_out(route, active_stops(db, route_id), admin_view=True)
