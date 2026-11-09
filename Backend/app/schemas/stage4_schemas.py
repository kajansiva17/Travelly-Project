from datetime import date
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel,Field
class Version(BaseModel):expected_version:int=Field(gt=0)
class CashReceived(Version):amount:Decimal=Field(ge=0)
class ProviderCallback(BaseModel):provider_reference:str=Field(min_length=8,max_length=120);callback_token:str=Field(min_length=32,max_length=128);status:Literal['SUCCEEDED','FAILED'];provider_fee_amount:Decimal=Field(default=Decimal('0.00'),ge=0)
class MaintenanceSchedule(Version):maintenance_type:Literal['OIL_CHANGE','TYRE_CHANGE','CUSTOM_SERVICE'];custom_label:str|None=Field(default=None,max_length=120);interval_km:Decimal|None=Field(default=None,gt=0);interval_days:int|None=Field(default=None,gt=0);next_due_odometer_km:Decimal|None=Field(default=None,ge=0);next_due_date:date|None=None
class MaintenanceRecord(Version):record_type:Literal['OIL_CHANGE','TYRE_CHANGE','GENERAL_SERVICE','BRAKE_SERVICE','BATTERY_SERVICE','REPAIR'];odometer_km:Decimal=Field(ge=0);amount:Decimal=Field(ge=0);recorded_at:str;service_provider:str|None=Field(default=None,max_length=150);notes:str|None=Field(default=None,max_length=2000)
