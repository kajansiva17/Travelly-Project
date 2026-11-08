from datetime import datetime
from decimal import Decimal
from uuid import UUID
import re
from typing import Annotated
from typing import Literal
from pydantic import Field, StrictBool, model_validator, field_validator, BeforeValidator
from app.schemas.rate_schemas import RateModel, Amount
from app.schemas.hire_schemas import Version, VehicleEligibility


def odometer(value):
    if not isinstance(value,str) or not re.fullmatch(r'[0-9]{1,11}(?:\.[0-9])?',value):
        raise ValueError('Use actual nonnegative odometer km with at most one decimal place.')
    return Decimal(value)
Odometer=Annotated[Decimal,BeforeValidator(odometer)]


class VehicleCreate(RateModel):
    registration_number: str = Field(min_length=1, max_length=40)
    @field_validator('registration_number')
    @classmethod
    def registration(cls, value):
        value = value.strip()
        if not value or any(ord(c) < 32 for c in value): raise ValueError('Enter the real registration number.')
        return value


class VehicleFacts(RateModel):
    vehicle_type_code: Literal['CAR', 'VAN', 'BUS', 'THREE_WHEELER'] | None = None
    make: str | None = Field(default=None, min_length=1, max_length=80)
    model: str | None = Field(default=None, min_length=1, max_length=80)
    manufacture_year: int | None = Field(default=None, strict=True, ge=1, le=datetime.now().year)
    colour: str | None = Field(default=None, min_length=1, max_length=40)
    power_type: Literal['ICE', 'MHEV', 'HEV', 'PHEV', 'BEV'] | None = None
    engine_fuel_type: Literal['PETROL', 'DIESEL'] | None = None
    seat_capacity: int | None = Field(default=None, strict=True, ge=0, le=32767)
    large_luggage_capacity: int | None = Field(default=None, strict=True, ge=0, le=32767)
    small_luggage_capacity: int | None = Field(default=None, strict=True, ge=0, le=32767)
    current_odometer_km: Odometer | None = None
    transmission_type: str | None = Field(default=None, min_length=1, max_length=40)
    air_conditioned: StrictBool | None = None
    description: str | None = Field(default=None, max_length=4000)
    registered_owner_case: Literal['SELF', 'OTHER_PERSON', 'COMPANY'] | None = None

    @field_validator('make', 'model', 'colour', 'transmission_type', 'description', mode='before')
    @classmethod
    def strings(cls, value):
        if isinstance(value, str):
            value = value.strip()
            if any(ord(c) < 32 and c not in '\n\r\t' for c in value): raise ValueError('Use plain text without control characters.')
        return value

    @model_validator(mode='after')
    def power(self):
        if (self.power_type == 'BEV' and self.engine_fuel_type is not None) or (self.power_type not in (None, 'BEV') and self.engine_fuel_type is None):
            raise ValueError('Choose the power and applicable fuel together; BEV has no engine fuel.')
        if self.current_odometer_km is not None and (self.current_odometer_km > Decimal('99999999999.9') or self.current_odometer_km % Decimal('.1')):
            raise ValueError('Odometer needs a nonnegative value with at most one decimal place.')
        return self


class VehiclePatch(VehicleFacts):
    expected_version: int = Field(strict=True, ge=1)
    registration_number: str | None = Field(default=None, min_length=1, max_length=40)
    # Validate the merged row's power/fuel, rather than guessing missing PATCH fields.
    @model_validator(mode='after')
    def power(self):
        if self.current_odometer_km is not None and (self.current_odometer_km > Decimal('99999999999.9') or self.current_odometer_km % Decimal('.1')):
            raise ValueError('Odometer needs a nonnegative value with at most one decimal place.')
        return self


class Availability(Version):
    availability_status: Literal['ACTIVE', 'INACTIVE']


class VehicleDecision(RateModel):
    expected_version: int = Field(strict=True, ge=1)
    decision: Literal['APPROVED', 'REJECTED', 'SUSPENDED'] = 'APPROVED'
    reason: str | None = Field(default=None, min_length=1, max_length=2000)
    category: str | None = None
    conditional_documents: dict | None = None
    authorisation_required: StrictBool | None = None
    @model_validator(mode='after')
    def decision_fields(self):
        if self.decision == 'APPROVED':
            VehicleEligibility.model_validate({k: getattr(self, k) for k in ('expected_version','category','conditional_documents','authorisation_required')})
            if self.reason is not None: raise ValueError('Approval does not require a negative decision reason.')
        elif not self.reason or not self.reason.strip(): raise ValueError('Explain the rejection or suspension to the Owner.')
        elif any(v is not None for v in (self.category,self.conditional_documents,self.authorisation_required)):
            raise ValueError('Do not change eligibility authority with a negative decision.')
        return self


class RegistrationCorrection(VehicleCreate):
    expected_version: int = Field(strict=True, ge=1)
    reason: str = Field(min_length=1, max_length=2000)


class DriverLookup(RateModel):
    vehicle_id: UUID
    service_type_id: UUID
    driver_reference: str = Field(pattern=r'^USR-[0-9A-F]{16}$')


class PreferredDriver(Version):
    driver_reference: str | None = Field(default=None, pattern=r'^USR-[0-9A-F]{16}$')
    service_type_id: UUID | None = None
    @model_validator(mode='after')
    def service(self):
        if self.driver_reference and not self.service_type_id: raise ValueError('Select the service for the eligibility check.')
        return self


class PhotoDecision(Version):
    decision: Literal['APPROVED', 'REJECTED', 'REMOVED']
    reason: str | None = Field(default=None, min_length=1, max_length=500)
    privacy_confirmed: StrictBool = False
    genuine_vehicle_confirmed: StrictBool = False
    @model_validator(mode='after')
    def moderation(self):
        if self.decision == 'APPROVED' and not (self.privacy_confirmed and self.genuine_vehicle_confirmed):
            raise ValueError('Confirm genuine vehicle content and no visible plates/private information before public approval.')
        if self.decision != 'APPROVED' and (not self.reason or not self.reason.strip()): raise ValueError('Give the Owner an actionable photo reason.')
        return self


class DescriptionDecision(Version):
    decision: Literal['APPROVED','REJECTED','REMOVED']
    reason: str | None = Field(default=None,min_length=1,max_length=500)
    privacy_confirmed: StrictBool = False
    @model_validator(mode='after')
    def review(self):
        if self.decision=='APPROVED' and not self.privacy_confirmed:raise ValueError('Confirm that description has no plates, contact details or precise private location.')
        if self.decision!='APPROVED' and (not self.reason or not self.reason.strip()):raise ValueError('Give the Owner an actionable content correction reason.')
        return self
