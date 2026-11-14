"""Payment contracts (matrix 65-67) and the Admin payment settings. Strict bodies."""
import re
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.schemas import email_address


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


def amount_text(value, name):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]{1,10}(\.[0-9]{1,2})?', value):
        raise ValueError(f'Enter {name} as a number with at most two decimal places, for example 1500.00.')
    return Decimal(value)


class PayerDetails(Strict):
    """Passed straight to PayHere for this payment and never stored by Travelly (owner decision, 11 Nov 2026)."""
    address: Optional[str] = Field(None, min_length=1, max_length=100)
    city: Optional[str] = Field(None, min_length=1, max_length=50)
    phone: Optional[str] = Field(None, pattern=r'^\+[1-9][0-9]{7,14}$')
    email: Optional[str] = Field(None, max_length=254)

    @field_validator('email')
    @classmethod
    def valid_email(cls, value):
        return email_address(value) if value is not None else value


class PaymentIntentRequest(Strict):
    amount: str
    currency: str = Field(pattern=r'^[A-Z]{3}$')
    method: Literal['CARD', 'BANK', 'MOBILE', 'SANDBOX']
    idempotency_key: str = Field(min_length=8, max_length=40, pattern=r'^[A-Za-z0-9_-]+$')
    payer: Optional[PayerDetails] = None

    @field_validator('amount')
    @classmethod
    def valid_amount(cls, value):
        amount_text(value, 'the amount')
        return value


class CheckoutRequest(Strict):
    payer: Optional[PayerDetails] = None


class SandboxOutcome(Strict):
    outcome: Literal['SUCCEEDED', 'FAILED']


class PaymentSettings(Strict):
    expected_version: int = Field(ge=1)
    payment_provider: Literal['SANDBOX', 'PAYHERE']
    commission_percent: str
    gateway_fee_percent: str
    multi_day_commission_percent: Optional[str] = None

    @field_validator('commission_percent', 'gateway_fee_percent', 'multi_day_commission_percent')
    @classmethod
    def valid_percent(cls, value):
        if value is None:
            return value
        if not isinstance(value, str) or not re.fullmatch(r'[0-9]{1,3}(\.[0-9]{1,2})?', value) or Decimal(value) > 100:
            raise ValueError('Enter a percentage from 0 to 100 with at most two decimal places.')
        return format(Decimal(value), '.2f')



class CashReceipt(Strict):
    """Matrix 70. Each side confirms its own part: the Passenger that they paid, the collector that they received it."""
    amount: str
    currency: str = Field(pattern=r'^[A-Z]{3}$')
    collection_stage: Literal['START', 'END']
    collector_user_id: UUID
    passenger_confirmation: bool
    collector_confirmation: bool
    idempotency_key: str = Field(min_length=8, max_length=40, pattern=r'^[A-Za-z0-9_-]+$')

    @field_validator('amount')
    @classmethod
    def valid_amount(cls, value):
        amount_text(value, 'the amount')
        return value


class PaymentOptions(Strict):
    """The Owner's choice per vehicle service: accept cash at the end of the trip or not (owner decision, 11 Nov 2026)."""
    expected_version: int = Field(ge=1)
    cash_accepted: bool


class TicketCancellation(Strict):
    """A Passenger cancels a paid ticket; the refund follows the owner-approved schedule (11 Nov 2026)."""
    expected_version: Optional[int] = Field(None, ge=1)
    reason: str = Field(min_length=1, max_length=500)


class RefundDecision(Strict):
    expected_version: int = Field(ge=1)
    decision: Literal['APPROVE', 'REJECT']
    reason: Optional[str] = Field(None, min_length=1, max_length=2000)


class RefundCompletion(Strict):
    """For providers the Admin refunds by hand (PayHere portal until its Refund API is connected)."""
    expected_version: int = Field(ge=1)
    provider_reference: str = Field(min_length=1, max_length=200)


class RefundRequest(Strict):
    """Matrix 68: an Admin refunds a payment directly (full, or a stated part), with a reason."""
    full: bool
    amount: Optional[str] = None
    reason: str = Field(min_length=1, max_length=2000)
    idempotency_key: str = Field(min_length=8, max_length=40, pattern=r'^[A-Za-z0-9_-]+$')

    @field_validator('amount')
    @classmethod
    def valid_amount(cls, value):
        if value is not None:
            amount_text(value, 'the amount')
        return value
