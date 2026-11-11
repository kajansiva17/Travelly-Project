"""Payment providers behind one small interface, so PayHere can be added later without touching booking code.

Owner decisions (11 November 2026): Sandbox now, PayHere later; the provider is an Admin setting per service type;
the gateway fee comes out of the Owner's share; commission is an Admin percentage per service type.

Settings live in service_types.settings (no new table):
    payment_provider     'SANDBOX' or 'PAYHERE' (PAYHERE only when its credentials are configured)
    commission_percent   '0.00'..'100.00', Travelly's share of each payment
    gateway_fee_percent  '0.00'..'100.00', the Sandbox fee; a real provider reports its own fee instead
Unset settings mean Sandbox with 0% commission and 0% fee.
"""
import hashlib
import hmac
import json
from urllib.parse import parse_qs
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
    webhook_media = 'application/json'

    @staticmethod
    def key():
        return hmac.new(get_settings().jwt_secret.encode(), b'travelly-sandbox-payments-v1', hashlib.sha256).digest()

    def sign(self, raw: bytes) -> str:
        return hmac.new(self.key(), raw, hashlib.sha256).hexdigest()

    def payer_required(self, user):
        return []

    def checkout(self, payment, booking=None, payer=None):
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
                'failure_code': body.get('failure_code'), 'fee': None, 'method': None}

    def event(self, payment, outcome, failure_code=None):
        """Build the event a provider would send, so the Sandbox button and the webhook share one code path."""
        return {'payment_reference': payment.payment_reference, 'provider_reference': 'SBX-' + payment.payment_reference,
                'outcome': outcome, 'amount': format(payment.amount, '.2f'), 'currency': payment.currency,
                'failure_code': failure_code, 'fee': None, 'method': None}


def md5_upper(text):
    return hashlib.md5(text.encode()).hexdigest().upper()


class PayHereProvider:
    """PayHere hosted checkout (https://support.payhere.lk/api-&-mobile-sdk/checkout-api).

    The browser posts a form to PayHere with fields this server prepares, including the hash, so the merchant secret
    never leaves the server. PayHere then posts a form to notify_url; only a notification whose md5sig matches and
    whose status_code is 2 marks the payment PAID. The browser coming back to return_url proves nothing.
    Address and city are asked on the Pay screen and passed straight to PayHere; Travelly does not store them.
    """
    name = 'PAYHERE'
    methods = ('CARD', 'BANK', 'MOBILE')
    webhook_media = 'application/x-www-form-urlencoded'
    CARDS = {'VISA', 'MASTER', 'MASTERCARD', 'AMEX', 'DISCOVER', 'DINERS', 'TEST'}
    BANKS = {'HELAPAY', 'VISHWA', 'BANK'}

    @staticmethod
    def config():
        settings = get_settings()
        return settings.payhere_merchant_id.strip(), settings.payhere_merchant_secret.strip(), settings.payhere_mode, \
            settings.public_api_url.rstrip('/'), settings.frontend_url.rstrip('/')

    @classmethod
    def available(cls):
        merchant, secret, _, public, _ = cls.config()
        return bool(merchant and secret and public.startswith('https://'))

    def payer_required(self, user):
        """PayHere needs these for every payment; ask on the Pay screen whatever the account does not have."""
        needed = ['address', 'city']
        if not user.phone_e164:
            needed.append('phone')
        if not user.email:
            needed.append('email')
        return needed

    def checkout(self, payment, booking, payer):
        merchant, secret, mode, public, frontend = self.config()
        amount = format(payment.amount, '.2f')
        names = (payer['full_name'] or '').split()
        first, last = (names[0], ' '.join(names[1:]) or names[0]) if names else ('Passenger', 'Passenger')
        page = f"{frontend}/travel/book/tickets?booking={booking.id}"
        fields = {'merchant_id': merchant, 'return_url': page + '&payment=returned', 'cancel_url': page + '&payment=cancelled',
                  'notify_url': f'{public}/api/v1/payments/webhooks/payhere', 'order_id': payment.payment_reference,
                  'items': f'Travelly booking {booking.booking_reference}', 'currency': payment.currency, 'amount': amount,
                  'first_name': first[:50], 'last_name': last[:50], 'email': payer['email'], 'phone': payer['phone'],
                  'address': payer['address'], 'city': payer['city'], 'country': 'Sri Lanka',
                  'custom_1': str(booking.id),
                  'hash': md5_upper(merchant + payment.payment_reference + amount + payment.currency + md5_upper(secret))}
        host = 'https://sandbox.payhere.lk' if mode == 'sandbox' else 'https://www.payhere.lk'
        return {'provider': self.name, 'mode': mode.upper(), 'action': host + '/pay/checkout', 'method': 'POST',
                'fields': fields, 'message': 'You will be taken to PayHere to pay. Your seats are confirmed only after PayHere reports success.'}

    def parse(self, raw: bytes, headers):
        merchant, secret, *_ = self.config()
        form = {k: v[0] for k, v in parse_qs(raw.decode('utf-8'), keep_blank_values=True).items()}
        expected = md5_upper(form['merchant_id'] + form['order_id'] + form['payhere_amount'] + form['payhere_currency']
                             + form['status_code'] + md5_upper(secret))
        if not merchant or form['merchant_id'] != merchant or not hmac.compare_digest(expected, form.get('md5sig', '').upper()):
            return None
        code = form['status_code']
        outcome = {'2': 'SUCCEEDED', '-1': 'FAILED', '-2': 'FAILED'}.get(code)  # 0 pending and -3 chargeback change nothing here
        method = (form.get('method') or '').upper()
        return {'payment_reference': form['order_id'], 'provider_reference': form['payment_id'], 'outcome': outcome,
                'amount': form['payhere_amount'], 'currency': form['payhere_currency'],
                'failure_code': {'-1': 'PAYHERE_CANCELLED', '-2': 'PAYHERE_FAILED'}.get(code), 'fee': None,
                'method': 'CARD' if method in self.CARDS else 'BANK' if method in self.BANKS else 'MOBILE' if method else None}


SANDBOX = SandboxProvider()
PAYHERE = PayHereProvider()


def providers():
    """Providers that can take money right now. PayHere appears only when its credentials and public URL are set."""
    found = {'SANDBOX': SANDBOX}
    if PayHereProvider.available():
        found['PAYHERE'] = PAYHERE
    return found


def provider_for(service):
    return providers().get(payment_settings(service)['payment_provider'])
