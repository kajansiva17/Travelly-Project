"""Payment providers behind one small interface, so PayHere can be added later without touching booking code.

Owner decisions (11 November 2026): Sandbox now, PayHere later; the provider is an Admin setting per service type;
the gateway fee comes out of the Owner's share; commission is an Admin percentage per service type.

Settings live in service_types.settings (no new table):
    payment_provider     'SANDBOX' (only provider available today)
    commission_percent   '0.00'..'100.00', Travelly's share of each payment
    gateway_fee_percent  '0.00'..'100.00', the Sandbox fee; a real provider reports its own fee instead
Unset settings mean Sandbox with 0% commission and 0% fee.
"""
import hashlib
import hmac
import json
from decimal import Decimal, ROUND_HALF_UP
from app.core.config import get_settings

CENT = Decimal('0.01')
ZERO = Decimal('0')
HUNDRED = Decimal('100')


def money(value):
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def percent(settings, name):
    value = (settings or {}).get(name)
    try:
        number = Decimal(str(value)) if value is not None else ZERO
    except ArithmeticError:
        return ZERO
    return number if ZERO <= number <= HUNDRED else ZERO


def payment_settings(service):
    settings = (service.settings or {}) if service else {}
    return {'payment_provider': settings.get('payment_provider') or 'SANDBOX',
            'commission_percent': format(percent(settings, 'commission_percent'), '.2f'),
            'gateway_fee_percent': format(percent(settings, 'gateway_fee_percent'), '.2f')}


def split(amount, service, provider_fee=None):
    """Return (commission, gateway_fee, owner_net). Each is rounded once to cents; the Owner absorbs the fee."""
    settings = (service.settings or {}) if service else {}
    amount = money(amount)
    commission = money(amount * percent(settings, 'commission_percent') / HUNDRED)
    fee = money(provider_fee) if provider_fee is not None else money(amount * percent(settings, 'gateway_fee_percent') / HUNDRED)
    net = amount - commission - fee
    return commission, fee, max(net, ZERO)


class SandboxProvider:
    """No real money. Events are signed with a key derived from the application secret, like a real gateway."""
    name = 'SANDBOX'
    methods = ('SANDBOX',)

    @staticmethod
    def key():
        return hmac.new(get_settings().jwt_secret.encode(), b'travelly-sandbox-payments-v1', hashlib.sha256).digest()

    def sign(self, raw: bytes) -> str:
        return hmac.new(self.key(), raw, hashlib.sha256).hexdigest()

    def checkout(self, payment):
        return {'provider': self.name, 'mode': 'SANDBOX',
                'message': 'Sandbox payment: no real money moves. Choose success or failure to finish.'}

    def parse(self, raw: bytes, headers):
        """Verify the signature and return a normalised event, or None when the signature is wrong."""
        signature = headers.get('x-travelly-signature', '')
        if not signature or not hmac.compare_digest(signature, self.sign(raw)):
            return None
        body = json.loads(raw)
        return {'payment_reference': str(body['payment_reference']), 'provider_reference': str(body['provider_reference']),
                'outcome': str(body['outcome']), 'amount': str(body['amount']), 'currency': str(body['currency']),
                'failure_code': body.get('failure_code'), 'fee': None}

    def event(self, payment, outcome, failure_code=None):
        """Build the event a provider would send, so the Sandbox button and the webhook share one code path."""
        return {'payment_reference': payment.payment_reference, 'provider_reference': 'SBX-' + payment.payment_reference,
                'outcome': outcome, 'amount': format(payment.amount, '.2f'), 'currency': payment.currency,
                'failure_code': failure_code, 'fee': None}


PROVIDERS = {'SANDBOX': SandboxProvider()}


def provider_for(service):
    return PROVIDERS.get(payment_settings(service)['payment_provider'])
