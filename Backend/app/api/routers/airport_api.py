"""Airport hire and Long distance rules (owner decisions 15 Nov 2026).

GET /airports                                       the airports a Passenger can choose (each one as a signed place for the normal itinerary)
PUT /admin/service-types/{id}/airports              Admin replaces the airport list of an Airport service
PATCH /admin/service-types/{id}/distance-rule       Admin sets the minimum trip distance of a Long distance service (default 100 km, 0 = no minimum)
"""
import copy
from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter, Depends, Request
from pydantic import Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.routers.api import touch
from app.api.routers.review_api import admin, locked_authority
from app.core.errors import ApiError
from app.dependencies.database import get_db
from app.models.rate_models import ServiceType
from app.schemas.hire_schemas import Version
from app.schemas.rate_schemas import RateModel
from app.services.airports import MAX_AIRPORTS, active_airports, airports_of, min_distance_km
from app.services.pricing_scope import private_hire_scope

router = APIRouter(prefix='/api/v1', tags=['Airports and distance rules'])


class AirportItem(RateModel):
    code: str = Field(pattern=r'^[A-Z0-9]{2,6}$')
    name: str = Field(min_length=3, max_length=120)
    latitude: Decimal = Field(ge=5, le=10, max_digits=9, decimal_places=6)
    longitude: Decimal = Field(ge=79, le=82.5, max_digits=9, decimal_places=6)
    is_active: bool = Field(strict=True)

    @field_validator('name')
    @classmethod
    def clean(cls, value):
        return ' '.join(value.split())


class AirportList(Version):
    airports: list[AirportItem] = Field(max_length=MAX_AIRPORTS)

    @model_validator(mode='after')
    def unique_codes(self):
        codes = [a.code for a in self.airports]
        if len(codes) != len(set(codes)):
            raise ValueError('Each airport code can be used once.')
        return self


class DistanceRule(Version):
    min_distance_km: int = Field(strict=True, ge=0, le=2000)


@router.get('/airports')
def airports(request: Request, db: Session = Depends(get_db)):
    signer = request.app.state.rate_locations
    return {'items': [{'code': a['code'], 'name': a['name'], 'place': signer.signed(a['name'], a['latitude'], a['longitude'])} for a in active_airports(db)]}


def locked_service(db, request, user, service_id, body, scope):
    locked_authority(db, request, user, user.id)
    row = db.scalar(select(ServiceType).where(ServiceType.id == service_id, ServiceType.category == 'PRIVATE_HIRE').with_for_update().execution_options(populate_existing=True))
    if not row: raise ApiError(404, 'SERVICE_NOT_FOUND', 'Private-hire service not found.')
    if row.version != body.expected_version: raise ApiError(409, 'VERSION_CONFLICT', 'Service configuration changed. Reload before saving.')
    return row


@router.put('/admin/service-types/{service_id}/airports')
def save_airports(service_id: UUID, body: AirportList, request: Request, user=Depends(admin), db: Session = Depends(get_db)):
    with request.app.state.audit.coordinated():
        row = locked_service(db, request, user, service_id, body, 'AIRPORT')
        if private_hire_scope(row) != 'AIRPORT':
            raise ApiError(422, 'AIRPORTS_NOT_ALLOWED', 'The airport list belongs to an Airport hire service.')
        old, before = copy.deepcopy(row.settings), row.version
        row.settings = {**row.settings, 'airports': [{'code': a.code, 'name': a.name, 'latitude': format(a.latitude, '.6f'), 'longitude': format(a.longitude, '.6f'), 'is_active': a.is_active} for a in body.airports]}
        touch(row); row.updated_by = user.id
        request.app.state.audit.commit(db, actor=user.id, target={'resource': 'service_types', 'id': str(row.id)}, previous_status=None, new_status=None,
            previous_version=before, new_version=row.version, full_reason=None, previous_decision_evidence={'airports': old.get('airports')}, trace_id=request.state.trace_id)
    return {'id': str(row.id), 'version': row.version, 'airports': airports_of(row)}


@router.patch('/admin/service-types/{service_id}/distance-rule')
def save_distance_rule(service_id: UUID, body: DistanceRule, request: Request, user=Depends(admin), db: Session = Depends(get_db)):
    with request.app.state.audit.coordinated():
        row = locked_service(db, request, user, service_id, body, 'LONG_DISTANCE')
        if private_hire_scope(row) != 'LONG_DISTANCE':
            raise ApiError(422, 'DISTANCE_RULE_NOT_ALLOWED', 'The minimum trip distance belongs to a Long distance service.')
        old, before = copy.deepcopy(row.settings), row.version
        row.settings = {**row.settings, 'min_distance_km': body.min_distance_km}
        touch(row); row.updated_by = user.id
        request.app.state.audit.commit(db, actor=user.id, target={'resource': 'service_types', 'id': str(row.id)}, previous_status=None, new_status=None,
            previous_version=before, new_version=row.version, full_reason=None, previous_decision_evidence={'min_distance_km': old.get('min_distance_km')}, trace_id=request.state.trace_id)
    return {'id': str(row.id), 'version': row.version, 'min_distance_km': min_distance_km(row)}
