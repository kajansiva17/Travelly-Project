from typing import Literal
from uuid import UUID
from pydantic import BaseModel,Field
class Version(BaseModel):expected_version:int=Field(gt=0)
class VehicleTypeRequest(BaseModel):code:str=Field(pattern=r'^[A-Z0-9_]{1,40}$');display_name:str=Field(min_length=1,max_length=100)
class VehicleTypeReview(Version):decision:Literal['APPROVED','REJECTED'];reason:str|None=Field(default=None,max_length=2000)
class ManualFulfilmentEvent(BaseModel):booking_id:UUID|None=None;trip_id:UUID|None=None;vehicle_id:UUID|None=None;event_type:Literal['EXCEPTION_REVIEW','VEHICLE_SUPPORT','SAFETY_ESCALATION','PAYMENT_DISPUTE'];summary:str=Field(min_length=1,max_length=300);details:str=Field(min_length=1,max_length=5000)
class ManualFulfilmentClose(Version):
 reason:str=Field(min_length=1,max_length=2000)
