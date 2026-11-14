"""Long-distance commission: one percent for a one-service-day booking, another for two or more (owner decision 14 Nov 2026)."""
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID, uuid4
from sqlalchemy import func, select
from app.models import UserRole
from app.models.hire_models import Booking
from app.models.rate_models import ServiceType
from app.services.payment_providers import payment_settings, service_days, split
from conftest import bearer
from test_rates import rate_owner  # noqa: F401
from test_hire_pricing import hire_setup, signed_in  # noqa: F401
from test_rental import accepted, bring_forward, post, setup_rental


def service(**settings):
    return SimpleNamespace(settings={'commission_percent': '10', 'gateway_fee_percent': '2', **settings})


def test_service_days_are_the_24_hour_blocks_not_calendar_dates():
    one = SimpleNamespace(itinerary_snapshot={'itinerary': {'service_hours': ['22']}})   # 6 pm to 4 pm next day is one service day
    two = SimpleNamespace(itinerary_snapshot={'itinerary': {'service_hours': ['24', '3']}})
    assert service_days(one) == 1 and service_days(two) == 2 and service_days(SimpleNamespace(itinerary_snapshot={})) == 1


def test_split_uses_the_multi_day_percent_only_from_the_second_day_and_only_when_set():
    both = service(multi_day_commission_percent='6')
    assert split(Decimal('50000'), both, None, 1)[0] == Decimal('5000.00')
    commission, fee, net = split(Decimal('50000'), both, None, 2)
    assert (commission, fee, net) == (Decimal('3000.00'), Decimal('1000.00'), Decimal('46000.00'))
    assert split(Decimal('50000'), service(), None, 3)[0] == Decimal('5000.00')            # not set: the normal percent
    assert payment_settings(both)['multi_day_commission_percent'] == '6.00' and payment_settings(service())['multi_day_commission_percent'] is None


def test_admin_sets_multi_day_commission_only_on_a_long_distance_service(client, hire_setup):
    c = hire_setup
    person, tokens = signed_in(client, {'full_name': 'Pay Admin', 'email': uuid4().hex + '@example.com', 'phone_e164': '+9477' + str(uuid4().int % 10000000).zfill(7),
                                        'password': 'TravellyStrong1!', 'accept_terms': True})
    with client.app.state.sessions() as db:
        db.add(UserRole(user_id=UUID(person['id']), role_code='ADMIN', approval_status='APPROVED', approved_at=func.now()))
        db.commit()
    path = f'/api/v1/admin/service-types/{c.service_id}/payment-settings'
    row = next(i for i in client.get('/api/v1/admin/payment-settings', headers=bearer(tokens)).json()['items'] if i['id'] == str(c.service_id))
    assert row['supports_multi_day_commission'] is True and row['multi_day_commission_percent'] is None
    body = {'expected_version': row['version'], 'payment_provider': 'SANDBOX', 'commission_percent': '8', 'gateway_fee_percent': '2', 'multi_day_commission_percent': '5'}
    saved = client.patch(path, headers=bearer(tokens), json=body)
    assert saved.status_code == 200 and saved.json()['multi_day_commission_percent'] == '5.00' and saved.json()['commission_percent'] == '8.00'
    assert client.patch(path, headers=bearer(tokens), json={**body, 'expected_version': saved.json()['version'], 'multi_day_commission_percent': '99'}).status_code == 422
    assert client.patch(path, headers=bearer(tokens), json={**body, 'expected_version': saved.json()['version'], 'multi_day_commission_percent': '1.234'}).status_code == 422
    cleared = client.patch(path, headers=bearer(tokens), json={'expected_version': saved.json()['version'], 'payment_provider': 'SANDBOX', 'commission_percent': '8', 'gateway_fee_percent': '2'})
    assert cleared.status_code == 200 and cleared.json()['multi_day_commission_percent'] is None
    with client.app.state.sessions() as db:   # a service that is not Long-distance refuses the field
        other = ServiceType(code='X' + uuid4().hex[:8].upper(), name='Other', category='RENTAL', default_pricing_basis='TIME', settings={}, created_by=UUID(person['id']), updated_by=UUID(person['id']))
        db.add(other); db.commit(); other_id, version = other.id, other.version
    refused = client.patch(f'/api/v1/admin/service-types/{other_id}/payment-settings', headers=bearer(tokens),
                           json={'expected_version': version, 'payment_provider': 'SANDBOX', 'commission_percent': '8', 'gateway_fee_percent': '2', 'multi_day_commission_percent': '5'})
    assert refused.status_code == 422 and refused.json()['code'] == 'MULTI_DAY_COMMISSION_NOT_ALLOWED'


def test_a_paid_booking_takes_the_commission_for_its_own_service_days(client, hire_setup):
    """Uses a rental booking whose service type is given the setting directly, to prove capture passes the booking's days."""
    c = hire_setup; setup_rental(client, c)
    row = accepted(client, c, days=1); bring_forward(client, row['id'])
    row = client.get(f"/api/v1/bookings/{row['id']}", headers=bearer(c.owner)).json()
    row = post(client, c.owner, f"/rentals/{row['id']}/handover", {'expected_version': row['version'], 'start_odometer_km': '10', 'licence_checked': True}).json()
    row = post(client, c.owner, f"/rentals/{row['id']}/return", {'expected_version': row['version'], 'end_odometer_km': '60'}).json()
    with client.app.state.sessions() as db:
        booking = db.get(Booking, UUID(row['id']))
        svc = db.get(ServiceType, booking.service_type_id)
        svc.settings = {**svc.settings, 'commission_percent': '10', 'multi_day_commission_percent': '5'}
        booking.itinerary_snapshot = {**booking.itinerary_snapshot, 'itinerary': {'service_hours': ['24', '5']}}   # two service days
        db.commit()
    intent = post(client, c.passenger, f"/bookings/{row['id']}/payment-intents", {'amount': '8000.00', 'currency': 'LKR', 'method': 'SANDBOX', 'idempotency_key': uuid4().hex})
    assert intent.status_code == 201, intent.text
    assert post(client, c.passenger, f"/payments/{intent.json()['id']}/sandbox-outcome", {'outcome': 'SUCCEEDED'}).status_code == 200
    mine = client.get(f"/api/v1/bookings/{row['id']}/payments", headers=bearer(c.owner)).json()['items'][0]
    assert mine['commission_amount'] == '400.00'                      # 5% of 8000, not 10%
