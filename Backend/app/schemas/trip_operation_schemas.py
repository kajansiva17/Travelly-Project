from datetime import datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel,Field,field_validator

class Version(BaseModel): expected_version:int=Field(gt=0)
class DutyStart(Version): departure_odometer_km:Decimal=Field(ge=0,le=Decimal('99999999999.9'));fuel_level_percent:Decimal=Field(ge=0,le=100)
class PickupVerify(Version): method:Literal['QR','PIN'];credential:str=Field(min_length=4,max_length=512);pickup_odometer_km:Decimal=Field(ge=0,le=Decimal('99999999999.9'))
class WaitingStart(Version): note:str|None=Field(default=None,max_length=500)
class WaitingStop(Version): note:str|None=Field(default=None,max_length=500)
class ExtraStop(Version): place_label:str=Field(min_length=1,max_length=150);latitude:Decimal|None=Field(default=None,ge=-90,le=90);longitude:Decimal|None=Field(default=None,ge=-180,le=180)
class ExtraStopDecision(Version): decision:Literal['APPROVED','REJECTED'];reason:str|None=Field(default=None,max_length=500)
class ExpenseCreate(Version): expense_type:Literal['FUEL','TOLL','PARKING','OTHER'];amount:Decimal=Field(ge=0);odometer_km:Decimal|None=Field(default=None,ge=0);recorded_at:datetime;note:str|None=Field(default=None,max_length=2000)
class ExpenseReview(Version): decision:Literal['APPROVED','REJECTED'];reimbursement_status:Literal['NOT_REQUESTED','REQUESTED','APPROVED','PAID','NOT_APPLICABLE']='NOT_REQUESTED';reason:str|None=Field(default=None,max_length=500)
class DestinationArrival(Version): dropoff_odometer_km:Decimal=Field(ge=0,le=Decimal('99999999999.9'))
class ReturnGarage(Version): return_odometer_km:Decimal=Field(ge=0,le=Decimal('99999999999.9'))
class FareFinalize(Version): calculation_id:str
