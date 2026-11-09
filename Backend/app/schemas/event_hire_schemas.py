from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field
from app.schemas.rate_schemas import Place

class Strict(BaseModel): model_config={'extra':'forbid'}
class EventPackage(Strict):
    id:str=Field(min_length=1,max_length=64)
    label:str=Field(min_length=1,max_length=120)
    package_price:Decimal=Field(gt=0,max_digits=12,decimal_places=2)
    included_hours:Decimal=Field(gt=0,le=24,max_digits=5,decimal_places=2)
    included_km:Decimal=Field(ge=0,max_digits=8,decimal_places=2)
    overtime_hour_rate:Decimal=Field(ge=0,max_digits=10,decimal_places=2)
    extra_km_rate:Decimal=Field(ge=0,max_digits=10,decimal_places=2)
    waiting_hour_rate:Decimal=Field(ge=0,max_digits=10,decimal_places=2)
    extra_stop_charge:Decimal=Field(ge=0,max_digits=10,decimal_places=2)
    venue_parking:Literal['INCLUDED','SEPARATE_AT_COST']
    tolls:Literal['INCLUDED','SEPARATE_AT_COST']
class EventRateConfig(Strict):
    service_type_id:UUID
    expected_version:int=Field(ge=0)
    enabled:bool
    packages:list[EventPackage]=Field(min_length=1,max_length=20)
class EventSearch(Strict):
    service_type_id:UUID
    event_type:str=Field(min_length=1,max_length=100)
    venue:Place
    pickup_locations:list[Place]=Field(min_length=1,max_length=12)
    event_start_at:datetime
    expected_hours:Decimal=Field(gt=0,le=24,max_digits=5,decimal_places=2)
    vehicles_required:int=Field(ge=1,le=20)
    passenger_count:int=Field(ge=1,le=2000)
    accessibility_required:bool=False
class EventRequest(EventSearch):
    owner_user_reference:str=Field(pattern=r'^USR-[0-9A-F]{16}$')
    idempotency_key:str=Field(min_length=16,max_length=80,pattern=r'^[A-Za-z0-9_-]+$')
class Version(Strict): expected_version:int=Field(ge=1)
class EventAccept(Version): digest:str=Field(pattern=r'^[0-9a-f]{64}$')
class EventAssignments(Version):
    allocations:list[dict]=Field(min_length=1,max_length=20)
