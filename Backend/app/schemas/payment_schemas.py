"""Payment contracts (matrix 65-67) and the Admin payment settings. Strict bodies."""
import re
from decimal import Decimal
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


def amount_text(value, name):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]{1,10}(\.[0-9]{1,2})?', value):
        raise ValueError(f'Enter {name} as a number with at most two decimal places, for example 1500.00.')
    return Decimal(value)


class PaymentIntentRequest(Strict):
    amount: str
    currency: str = Field(pattern=r'^[A-Z]{3}$')
    method: Literal['CARD', 'BANK', 'MOBILE', 'SANDBOX']
    idempotency_key: str = Field(min_length=8, max_length=40, pattern=r'^[A-Za-z0-9_-]+$')

    @field_validator('amount')
    @classmethod
    def valid_amount(cls, value):
        amount_text(value, 'the amount')
        return value


class SandboxOutcome(Strict):
    outcome: Literal['SUCCEEDED', 'FAILED']


class PaymentSettings(Strict):
    expected_version: int = Field(ge=1)
    payment_provider: Literal['SANDBOX', 'PAYHERE']
    commission_percent: str
    gateway_fee_percent: str

    @field_validator('commission_percent', 'gateway_fee_percent')
    @classmethod
    def valid_percent(cls, value):
        if not isinstance(value, str) or not re.fullmatch(r'[0-9]{1,3}(\.[0-9]{1,2})?', value) or Decimal(value) > 100:
            raise ValueError('Enter a percentage from 0 to 100 with at most two decimal places.')
        return format(Decimal(value), '.2f')

