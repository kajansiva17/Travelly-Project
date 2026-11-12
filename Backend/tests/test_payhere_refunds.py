"""PayHere Refund API (https://support.payhere.lk/api-&-mobile-sdk/refund-api). The network is faked: no real calls."""
from uuid import UUID, uuid4
import httpx
import pytest
from app.models.payment_models import Payment
from app.services import payhere_refunds
from test_ticket_holds import api, person, ticket
from test_payhere import payhere, intent, notify


class Answer:
    def __init__(self, body, status=200):
        self.body, self.status_code = body, status

    def json(self):
        return self.body


class FakePayHere:
    def __init__(self, *refund_answers):
        self.answers, self.calls = list(refund_answers), []

    def __call__(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if url.endswith('/oauth/token'):
            return Answer({'access_token': 'tok-' + uuid4().hex[:6], 'token_type': 'bearer', 'expires_in': 599})
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer

    def refunds(self):
        return [kwargs['json'] for url, kwargs in self.calls if url.endswith('/payment/refund')]


@pytest.fixture
def paid_card(client, payhere, monkeypatch):
    monkeypatch.setenv('PAYHERE_APP_ID', 'test-app-id')
    monkeypatch.setenv('PAYHERE_APP_SECRET', 'test-app-secret')
    payhere_refunds._token.update(value=None)
    payment = intent(client, payhere).json()
    assert notify(client, payment['payment_reference'], method='VISA').json()['status'] == 'PAID'
    with client.app.state.sessions() as db:
        reference = db.get(Payment, UUID(payment['id'])).provider_reference
    return {**payhere, 'payment': payment, 'payhere_id': reference}


def refund(client, t, full=True, amount=None):
    body = {'full': full, 'reason': 'Customer service gesture.', 'idempotency_key': uuid4().hex[:20]}
    if amount:
        body['amount'] = amount
    return api(client, t['admin'], 'post', f"/payments/{t['payment']['id']}/refunds", body)


def original(client, t):
    with client.app.state.sessions() as db:
        return db.get(Payment, UUID(t['payment']['id']))


def test_an_approved_card_refund_goes_back_through_payhere(client, paid_card, monkeypatch):
    fake = FakePayHere(Answer({'status': 1, 'msg': 'Successfully processed', 'data': 160000123}))
    monkeypatch.setattr(payhere_refunds, 'post', fake)
    done = refund(client, paid_card)
    assert done.status_code == 201, done.text
    body = done.json()
    assert body['status'] == 'PAID' and body['provider_reference'] == 'PHR-160000123' and body['failure_code'] is None
    assert fake.refunds() == [{'payment_id': paid_card['payhere_id'], 'description': f"Travelly refund {body['payment_reference']}"}]
    token_call = fake.calls[0]
    assert token_call[0] == 'https://sandbox.payhere.lk/merchant/v1/oauth/token'
    assert token_call[1]['headers']['Authorization'].startswith('Basic ') and token_call[1]['data'] == {'grant_type': 'client_credentials'}
    assert original(client, paid_card).status == 'REFUNDED'


def test_a_partial_refund_sends_the_amount(client, paid_card, monkeypatch):
    fake = FakePayHere(Answer({'status': 1, 'msg': 'ok', 'data': 160000124}))
    monkeypatch.setattr(payhere_refunds, 'post', fake)
    done = refund(client, paid_card, full=False, amount='1500.00')
    assert done.json()['status'] == 'PAID' and fake.refunds()[0]['amount'] == 1500.0
    assert original(client, paid_card).status == 'PARTIALLY_REFUNDED'


def test_a_refused_refund_can_be_sent_again(client, paid_card, monkeypatch):
    fake = FakePayHere(Answer({'status': -1, 'msg': 'Error processing refund'}), Answer({'status': 1, 'msg': 'ok', 'data': 7}))
    monkeypatch.setattr(payhere_refunds, 'post', fake)
    first = refund(client, paid_card).json()
    assert first['status'] == 'PROCESSING' and first['failure_code'] == 'PAYHERE_REFUND_FAILED'
    assert first['failure_message'] == 'Error processing refund' and original(client, paid_card).status == 'PAID'
    again = api(client, paid_card['admin'], 'post', f"/admin/refunds/{first['id']}/payhere", {})
    assert again.status_code == 200, again.text
    assert again.json()['status'] == 'PAID' and again.json()['provider_reference'] == 'PHR-7'
    assert api(client, paid_card['admin'], 'post', f"/admin/refunds/{first['id']}/payhere", {}).json()['code'] == 'REFUND_NOT_RETRYABLE'


def test_no_answer_is_never_sent_twice(client, paid_card, monkeypatch):
    fake = FakePayHere(httpx.ReadTimeout('timed out'))
    monkeypatch.setattr(payhere_refunds, 'post', fake)
    first = refund(client, paid_card).json()
    assert first['status'] == 'PROCESSING' and first['failure_code'] == 'PAYHERE_REFUND_FAILED'
    # A crash between sending and recording leaves PAYHERE_REQUESTED: the API never sends that refund again.
    with client.app.state.sessions() as db:
        db.get(Payment, UUID(first['id'])).failure_code = 'PAYHERE_REQUESTED'
        db.commit()
    blocked = api(client, paid_card['admin'], 'post', f"/admin/refunds/{first['id']}/payhere", {})
    assert blocked.status_code == 409 and len(fake.refunds()) == 1
    # The Admin checks the portal and records it, as before.
    with client.app.state.sessions() as db:
        version = db.get(Payment, UUID(first['id'])).version
    done = api(client, paid_card['admin'], 'post', f"/admin/refunds/{first['id']}/complete",
               {'expected_version': version, 'provider_reference': 'PORTAL-1'})
    assert done.status_code == 200 and done.json()['status'] == 'PAID'


def test_wallet_payments_need_a_manual_refund(client, payhere, monkeypatch):
    monkeypatch.setenv('PAYHERE_APP_ID', 'test-app-id')
    monkeypatch.setenv('PAYHERE_APP_SECRET', 'test-app-secret')
    fake = FakePayHere()
    monkeypatch.setattr(payhere_refunds, 'post', fake)
    payment = intent(client, payhere).json()
    notify(client, payment['payment_reference'], method='GENIE')
    done = refund(client, {**payhere, 'payment': payment}).json()
    assert done['status'] == 'PROCESSING' and done['failure_code'] == 'PAYHERE_MANUAL_REQUIRED' and not fake.calls
    assert api(client, payhere['admin'], 'post', f"/admin/refunds/{done['id']}/payhere", {}).status_code == 409


def test_without_app_credentials_refunds_stay_manual(client, payhere, monkeypatch):
    fake = FakePayHere()
    monkeypatch.setattr(payhere_refunds, 'post', fake)
    payment = intent(client, payhere).json()
    notify(client, payment['payment_reference'], method='VISA')
    done = refund(client, {**payhere, 'payment': payment}).json()
    assert done['status'] == 'PROCESSING' and done['failure_code'] is None and not fake.calls
    assert api(client, payhere['admin'], 'post', f"/admin/refunds/{done['id']}/payhere", {}).json()['code'] == 'PAYHERE_REFUND_API_OFF'
