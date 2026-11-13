"""Cash commission overdue rule (owner decision 13 Nov 2026): 14 days free, 14-18 grace, then no NEW bookings."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4
import pytest
from sqlalchemy import select
from app.models.hire_models import Notification
from app.models.payment_models import Payment
from app.models.rate_models import ServiceType
from app.services import commission_overdue
from app.services.reminders import run_reminders
from conftest import bearer
from test_ticket_holds import api, person, ticket, hold_body
from test_rates import rule, rate_owner
from test_hire_pricing import hire_setup, committed
from test_trip_operations import running
from test_private_hire_payments import completed, accept_cash, cash


@pytest.fixture
def debt(client, completed):
    """The Owner collected cash and owes commission. Returns helpers to age that debt."""
    accept_cash(client, completed)
    with client.app.state.sessions() as db:
        service = db.get(ServiceType, completed.ctx.service_id)
        service.settings = {**service.settings, 'commission_percent': '10.00'}
        db.commit()
    first = cash(client, completed, completed.ctx.passenger, passenger=True).json()
    cash(client, completed, completed.ctx.owner, passenger=False)
    owner_id = completed.booking['owner_user_id']

    def age(days):
        with client.app.state.sessions() as db:
            row = db.get(Payment, UUID(first['id']))
            row.captured_at = datetime.now(timezone.utc) - timedelta(days=days, minutes=1)
            db.commit()
    return type('Debt', (), {'run': completed, 'payment': first, 'owner_id': owner_id, 'age': staticmethod(age)})


def standing(client, debt):
    return client.get('/api/v1/owners/me/settlements', headers=bearer(debt.run.ctx.owner)).json()['commission_standing']


def listed(client, debt):
    return str(debt.run.ctx.vehicle_id) in [v['id'] for v in client.get('/api/v1/vehicles').json()['items']]


def test_days_decide_free_grace_and_blocked_and_paying_opens_it_again(client, debt):
    assert standing(client, debt)['stage'] == 'FREE' and listed(client, debt)
    debt.age(13)
    assert standing(client, debt)['stage'] == 'FREE' and not standing(client, debt)['blocked']
    debt.age(15)
    s = standing(client, debt)
    assert s['stage'] == 'GRACE' and not s['blocked'] and s['days_open'] == 15 and listed(client, debt)
    debt.age(19)
    s = standing(client, debt)
    assert s['stage'] == 'BLOCKED' and s['blocked'] and s['amount_due'] != '0.00'
    assert not listed(client, debt)                              # hidden from the vehicle list
    import app.api.routers.hire_api as hire      # the gate behind every new quote / booking request
    from app.core.errors import ApiError
    from app.models.review_models import Vehicle
    with client.app.state.sessions() as db:
        with pytest.raises(ApiError) as stopped:
            hire.commission_gate(type('R', (), {'app': client.app}), db, db.get(Vehicle, debt.run.ctx.vehicle_id))
        assert stopped.value.status == 409 and stopped.value.code == 'VEHICLE_NOT_AVAILABLE'
    # bookings already made are untouched
    kept = client.get(f"/api/v1/bookings/{debt.run.booking['id']}", headers=bearer(debt.run.ctx.owner))
    assert kept.status_code == 200 and kept.json()['status'] != 'CANCELLED'
    boss = person(client, 'ADMIN')
    overdue = api(client, boss, 'get', '/admin/owner-settlements?overdue=true').json()['items']
    assert [i['owner_user_id'] for i in overdue] == [debt.owner_id] and overdue[0]['commission_standing']['stage'] == 'BLOCKED'
    got = api(client, boss, 'post', f'/admin/owner-settlements/{debt.owner_id}/commission-receipts',
              {'payment_ids': [debt.payment['id']], 'reference': 'Cash deposit', 'idempotency_key': uuid4().hex})
    assert got.status_code == 200, got.text
    assert standing(client, debt)['stage'] == 'NONE' and listed(client, debt)        # active again by itself
    with client.app.state.sessions() as db:
        assert db.scalar(select(Notification.id).where(Notification.recipient_user_id == UUID(debt.owner_id),
                                                         Notification.title == 'Bookings are open again'))
    assert api(client, boss, 'get', '/admin/owner-settlements?overdue=true').json()['items'] == []


def test_admin_can_give_extra_days_and_it_ends_on_time(client, debt):
    debt.age(20)
    assert standing(client, debt)['blocked']
    boss = person(client, 'ADMIN')
    url = f'/admin/owner-settlements/{debt.owner_id}/commission-extension'
    assert api(client, boss, 'post', url, {'days': 0, 'reason': 'x'}).status_code == 422
    assert api(client, person(client), 'post', url, {'days': 3, 'reason': 'Bank holiday'}).status_code == 403
    done = api(client, boss, 'post', url, {'days': 3, 'reason': 'Bank holiday'})
    assert done.status_code == 200, done.text
    assert done.json()['stage'] == 'BLOCKED' and not done.json()['blocked'] and done.json()['extended_until'] and listed(client, debt)
    with client.app.state.sessions() as db:   # when the extra days pass the block is back
        later = datetime.now(timezone.utc) + timedelta(days=4)
        assert commission_overdue.is_blocked(db, client.app.state.settings, UUID(debt.owner_id), later)
        assert not commission_overdue.is_blocked(db, client.app.state.settings, UUID(debt.owner_id))


def test_reminders_follow_the_days_and_never_repeat(client, debt):
    owner = UUID(debt.owner_id)

    def titles():
        with client.app.state.sessions() as db:
            return [n.title for n in db.scalars(select(Notification).where(
                Notification.recipient_user_id == owner, Notification.channel == 'IN_APP',
                Notification.action_payload['reminder_key'].astext.like('commission:%')).order_by(Notification.created_at))]

    def run():
        with client.app.state.sessions() as db:
            counts = run_reminders(db, client.app.state.settings)
            db.commit()
            return counts['commission']
    debt.age(5)
    assert run() == 0
    debt.age(11)
    assert run() == 1 and run() == 0 and titles() == ['Commission due soon']
    debt.age(14)
    assert run() == 1 and titles()[-1] == 'Your commission is due'
    debt.age(16)
    assert run() == 1 and titles()[-1] == 'Pay your commission'
    debt.age(17)
    assert run() == 1 and titles()[-1] == 'Last day to pay your commission'
    debt.age(18)
    assert run() == 1 and titles()[-1] == 'New bookings are stopped' and run() == 0



def test_payout_can_take_the_commission_out_of_it(client, debt):
    boss = person(client, 'ADMIN')
    url = f'/admin/owner-settlements/{debt.owner_id}/payouts'
    cash_row = api(client, boss, 'post', url, {'payment_ids': [debt.payment['id']], 'bank_reference': 'X',
                                               'idempotency_key': uuid4().hex, 'settle_commission': True})
    assert cash_row.status_code == 409     # cash itself is never paid out
    with client.app.state.sessions() as db:   # online money Travelly holds for the same Owner
        cash_payment = db.get(Payment, UUID(debt.payment['id']))
        online = Payment(payment_reference='PAY-' + uuid4().hex[:12].upper(), booking_id=cash_payment.booking_id,
                         payee_owner_user_id=cash_payment.payee_owner_user_id, transaction_type='PAYMENT', payment_method='SANDBOX',
                         provider_name='SANDBOX', amount=Decimal('5000.00'), currency=cash_payment.currency, status='PAID',
                         captured_at=datetime.now(timezone.utc), commission_amount=Decimal('500.00'), owner_net_amount=Decimal('4500.00'),
                         owner_settlement_status='OWNER_PAYABLE', idempotency_key=uuid4().hex)
        db.add(online)
        db.commit()
        online_id = str(online.id)
        owed = cash_payment.commission_amount
    debt.age(19)
    assert standing(client, debt)['blocked']
    done = api(client, boss, 'post', url, {'payment_ids': [online_id], 'bank_reference': 'BOC-1', 'idempotency_key': uuid4().hex,
                                           'settle_commission': True})
    assert done.status_code == 201, done.text
    out = done.json()
    assert out['total'] == '4500.00' and out['commission_payments'] == [debt.payment['id']]
    assert Decimal(out['commission_set_off']) == owed and Decimal(out['bank_transfer_total']) == Decimal('4500.00') - owed
    assert standing(client, debt)['stage'] == 'NONE' and listed(client, debt)      # paid by the payout, so bookings are open again
    with client.app.state.sessions() as db:
        assert db.get(Payment, UUID(debt.payment['id'])).owner_settlement_status == 'COMMISSION_PAID'
        assert db.get(Payment, UUID(online_id)).owner_settlement_status == 'OWNER_PAID'


def test_a_blocked_owner_takes_no_new_ticket_holds_and_the_departure_is_not_listed(client, ticket, monkeypatch):
    owner = UUID(ticket['owner']['id'])
    seen = lambda: [d['id'] for d in client.get('/api/v1/scheduled-trips').json()['items']]
    assert ticket['trip']['id'] in seen()
    monkeypatch.setattr(commission_overdue, 'blocked_owner_ids', lambda db, settings, now=None: {owner})
    monkeypatch.setattr(commission_overdue, 'is_blocked', lambda db, settings, o, now=None: o == owner)
    assert ticket['trip']['id'] not in seen()
    held = api(client, person(client), 'post', '/bookings/ticket-holds', hold_body(ticket, ['A1']))
    assert held.status_code == 409 and held.json()['code'] == 'DEPARTURE_NOT_AVAILABLE'
