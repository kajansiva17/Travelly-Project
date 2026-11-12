"""Admin payments overview and Owner settlement (payouts and cash commission) on the PRD payments table."""
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4
from sqlalchemy import select
from app.models.hire_models import Notification
from app.models.payment_models import Payment
from app.models.rate_models import ServiceType
from conftest import bearer
from test_ticket_holds import api, person, ticket, configure_hold, hold_body
from test_rates import rule, rate_owner
from test_hire_pricing import hire_setup, committed
from test_trip_operations import running
from test_private_hire_payments import completed, pay_online, accept_cash, cash
from test_payments import held, intent, outcome
from test_refunds import paid, at, cancel, refunds, decide


def make_admin(client):
    return person(client, 'ADMIN')


def paid_online(client, run):
    created = pay_online(client, run).json()
    client.post(f"/api/v1/payments/{created['id']}/sandbox-outcome", headers=bearer(run.ctx.passenger), json={'outcome': 'SUCCEEDED'})
    return created


def test_admin_pays_the_owner_and_it_is_recorded_once(client, completed):
    payment = paid_online(client, completed)
    boss = make_admin(client)
    owner_id = completed.booking['owner_user_id']
    listed = api(client, boss, 'get', '/admin/owner-settlements').json()['items']
    mine = next(i for i in listed if i['owner_user_id'] == owner_id)
    assert mine['payable_amount'] == completed.booking['total_amount'] and [p['id'] for p in mine['payable']] == [payment['id']]
    key = uuid4().hex
    url = f'/admin/owner-settlements/{owner_id}/payouts'
    done = api(client, boss, 'post', url, {'payment_ids': [payment['id']], 'bank_reference': 'BOC-TRF-001', 'idempotency_key': key})
    assert done.status_code == 201, done.text
    payout = done.json()['payouts'][0]
    assert payout['transaction_type'] == 'OWNER_PAYOUT' and payout['original_payment_id'] == payment['id']
    assert payout['amount'] == completed.booking['total_amount'] and payout['provider_reference'] == 'BOC-TRF-001'
    again = api(client, boss, 'post', url, {'payment_ids': [payment['id']], 'bank_reference': 'BOC-TRF-001', 'idempotency_key': key})
    assert again.status_code == 200 and again.json()['payouts'][0]['id'] == payout['id']
    twice = api(client, boss, 'post', url, {'payment_ids': [payment['id']], 'bank_reference': 'BOC-TRF-002', 'idempotency_key': uuid4().hex})
    assert twice.status_code == 409 and twice.json()['code'] == 'SETTLEMENT_NOT_ALLOWED'
    owner_view = client.get('/api/v1/owners/me/settlements', headers=bearer(completed.ctx.owner)).json()
    assert owner_view['payable_amount'] == '0.00' and owner_view['settled'][0]['owner_settlement_status'] == 'OWNER_PAID'
    with client.app.state.sessions() as db:
        assert db.scalar(select(Notification.id).where(Notification.recipient_user_id == UUID(owner_id), Notification.title == 'Payout sent'))
    totals = api(client, boss, 'get', '/admin/payments').json()['totals']
    assert totals['owner_paid'] == completed.booking['total_amount'] and totals['collected_online'] == completed.booking['total_amount']


def test_cash_commission_is_owed_then_recorded_as_received(client, completed):
    accept_cash(client, completed)
    with client.app.state.sessions() as db:
        service = db.get(ServiceType, completed.ctx.service_id)
        service.settings = {**service.settings, 'commission_percent': '10.00'}
        db.commit()
    first = cash(client, completed, completed.ctx.passenger, passenger=True).json()
    cash(client, completed, completed.ctx.owner, passenger=False)
    boss = make_admin(client)
    owner_id = completed.booking['owner_user_id']
    mine = next(i for i in api(client, boss, 'get', '/admin/owner-settlements').json()['items'] if i['owner_user_id'] == owner_id)
    assert mine['commission_due'][0]['id'] == first['id'] and mine['commission_due_amount'] != '0.00'
    assert api(client, boss, 'get', '/admin/payments').json()['totals']['commission_due_from_owners'] == mine['commission_due_amount']
    url = f'/admin/owner-settlements/{owner_id}/commission-receipts'
    got = api(client, boss, 'post', url, {'payment_ids': [first['id']], 'reference': 'Cash deposit 12 Nov', 'idempotency_key': uuid4().hex})
    assert got.status_code == 200 and got.json()['payments'][0]['owner_settlement_status'] == 'COMMISSION_PAID'
    again = api(client, boss, 'post', url, {'payment_ids': [first['id']], 'reference': 'Cash deposit 12 Nov', 'idempotency_key': uuid4().hex})
    assert again.status_code == 200
    payout = api(client, boss, 'post', f'/admin/owner-settlements/{owner_id}/payouts',
                 {'payment_ids': [first['id']], 'bank_reference': 'X', 'idempotency_key': uuid4().hex})
    assert payout.status_code == 409  # cash is never paid out: the Owner already holds it


def payable_now(client, t):
    """What finishing the departure does to its paid seat payments."""
    with client.app.state.sessions() as db:
        row = db.get(Payment, UUID(t['payment']['id']))
        row.owner_settlement_status = 'OWNER_PAYABLE'
        db.commit()
        return row.owner_net_amount


def owner_row(client, t):
    return next(i for i in api(client, t['admin'], 'get', '/admin/owner-settlements').json()['items']
                if i['owner_user_id'] == t['owner']['id'])


def test_a_partly_refunded_payment_is_paid_out_pro_rata(client, paid, monkeypatch):
    """Owner decision 12 Nov 2026: the Owner gets the Owner share in proportion to the money Travelly keeps."""
    at(monkeypatch, paid, 48)
    cancel(client, paid)                         # 50% refund queued, not decided yet
    net = payable_now(client, paid)
    waiting = owner_row(client, paid)
    assert [p['id'] for p in waiting['needs_review']] == [paid['payment']['id']] and waiting['payable'] == []
    url = f"/admin/owner-settlements/{paid['owner']['id']}/payouts"
    blocked = api(client, paid['admin'], 'post', url, {'payment_ids': [paid['payment']['id']], 'bank_reference': 'X', 'idempotency_key': uuid4().hex})
    assert blocked.status_code == 409            # never pay out while a refund is still open
    decide(client, paid, refunds(client, paid)['items'][0])     # Sandbox: half goes back now
    ready = owner_row(client, paid)
    half = (net / 2).quantize(Decimal('0.01'))
    assert ready['needs_review'] == [] and ready['payable_amount'] == format(half, '.2f')
    assert ready['payable'][0]['payable_amount'] == format(half, '.2f') and ready['payable'][0]['status'] == 'PARTIALLY_REFUNDED'
    done = api(client, paid['admin'], 'post', url, {'payment_ids': [paid['payment']['id']], 'bank_reference': 'BANK-9', 'idempotency_key': uuid4().hex})
    assert done.status_code == 201, done.text
    assert done.json()['total'] == format(half, '.2f') and done.json()['payouts'][0]['amount'] == format(half, '.2f')


def test_a_fully_refunded_payment_is_never_paid_out(client, paid, monkeypatch):
    at(monkeypatch, paid, 100)
    cancel(client, paid)
    decide(client, paid, refunds(client, paid)['items'][0])
    payable_now(client, paid)
    row = owner_row(client, paid) if any(i['owner_user_id'] == paid['owner']['id'] for i in
                                         api(client, paid['admin'], 'get', '/admin/owner-settlements').json()['items']) else None
    assert row is None or (row['payable'] == [] and row['payable_amount'] == '0.00')


def test_only_admins_see_everything_and_owners_see_their_own(client, completed):
    assert client.get('/api/v1/admin/payments', headers=bearer(completed.ctx.owner)).status_code == 403
    assert client.get('/api/v1/admin/owner-settlements', headers=bearer(completed.ctx.passenger)).status_code == 403
    assert client.get('/api/v1/owners/me/settlements', headers=bearer(completed.ctx.passenger)).status_code == 403
