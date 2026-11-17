from copy import deepcopy
from decimal import Decimal
from uuid import UUID, uuid4
import pytest
from pydantic import ValidationError
from sqlalchemy import select, func
from app.models import UserRole
from app.models.review_models import Vehicle
from app.models.rate_models import ServiceType, VehicleService
from app.schemas.rate_schemas import RateRule, RateConfiguration, ExampleTrip
from app.services.rate_calculation import calculate
from conftest import signed_in, bearer


def rule():
    return {'id': str(uuid4()), 'label': 'Owner supplied route rate',
        'pickup_area': {'label': 'Pickup area', 'south': '6', 'north': '8', 'west': '79', 'east': '82'},
        'coverage': {'kind': 'AREA', 'area': {'label': 'Covered area', 'south': '6', 'north': '9', 'west': '79', 'east': '82'}},
        'direction': 'ONE_WAY', 'effective_from': '2026-10-27', 'method': 'DISTANCE',
        'base_charge': '1000', 'included_km': '10', 'extra_km_rate': '50', 'night_km_rate': '10',
        'free_wait_minutes': '20', 'waiting_hour_rate': '300', 'return_to_base': 'INCLUDED',
        'return_to_base_notes': 'Return included in these rates.', 'tolls': 'SEPARATE_AT_COST', 'parking': 'INCLUDED',
        'other_charges': [], 'change_limits': {'added_km': '20', 'added_hours': '2', 'added_wait_minutes': '30', 'added_amount': '2000'}}


def example(**changes):
    return ExampleTrip.model_validate({'distance_km': '30', 'night_km': '5', 'waiting_minutes': '50',
        'service_hours': ['3'], 'overnight_stays': 0, **changes})


@pytest.mark.parametrize('distance,total', [('5', '1200.00'), ('10', '1200.00'), ('30', '2200.00')])
def test_distance_included_night_and_waiting(distance, total):
    result = calculate(RateRule.model_validate(rule()), example(distance_km=distance))
    assert result['total'] == total
    assert result['included_km'] == '10'
    assert result['exclusions'] == ['Tolls: payable separately at actual cost; not part of this total.']
    assert [x['code'] for x in result['breakdown']] == ['BASE', 'EXTRA_KM', 'NIGHT_KM', 'WAIT']


def test_round_only_final_total_not_components():
    data = rule(); data.update(base_charge='0', included_km='0', extra_km_rate='0.005', night_km_rate='0.005', free_wait_minutes='0', waiting_hour_rate='0')
    result = calculate(RateRule.model_validate(data), example(distance_km='1', night_km='1', waiting_minutes='0'))
    assert result['total'] == '0.01'
    assert result['breakdown'][1]['amount'] == '0.005'


@pytest.mark.parametrize('field,value', [('base_charge', None), ('included_km', '-1'), ('extra_km_rate', True), ('night_km_rate', '1e3'), ('waiting_hour_rate', ''), ('day_charge', '10')])
def test_missing_negative_ambiguous_or_irrelevant_rates_rejected(field, value):
    with pytest.raises(ValidationError): RateRule.model_validate({**rule(), field: value})


def test_conflicting_coverage_rejected_but_distinct_effective_periods_allowed():
    a = rule(); b = {**deepcopy(a), 'id': str(uuid4())}
    config = {'service_type_id': str(uuid4()), 'expected_version': 0, 'enabled': True, 'currency': 'LKR', 'rules': [a, b]}
    with pytest.raises(ValidationError): RateConfiguration.model_validate(config)
    a['effective_until'] = '2026-10-31'; b['effective_from'] = '2026-11-01'
    assert len(RateConfiguration.model_validate(config).rules) == 2
    with pytest.raises(ValidationError): RateConfiguration.model_validate({**config, 'currency': 'USD'})


def test_general_rate_has_no_hidden_pickup_area_and_conflicts_with_duplicate_general_rate():
    general = {**rule(), 'pickup_area': None, 'coverage': {'kind': 'ANY', 'places': None, 'area': None}}
    assert RateRule.model_validate(general).coverage.kind == 'ANY'
    config = {'service_type_id': str(uuid4()), 'expected_version': 0, 'enabled': True,
              'currency': 'LKR', 'rules': [general, {**general, 'id': str(uuid4())}]}
    with pytest.raises(ValidationError): RateConfiguration.model_validate(config)


@pytest.fixture
def rate_owner(client, passenger):
    person, tokens = signed_in(client, passenger)
    uid = UUID(person['id'])
    with client.app.state.sessions() as db:
        db.add(UserRole(user_id=uid, role_code='OWNER', approval_status='APPROVED', approved_by=uid, approved_at=func.now()))
        vehicle = Vehicle(owner_user_id=uid, public_vehicle_reference='VEH-' + uuid4().hex[:16].upper(), registration_number=uuid4().hex[:20])
        service = ServiceType(code=uuid4().hex, name='Private hire test catalogue', category='PRIVATE_HIRE', is_active=True, default_pricing_basis='DISTANCE', settings={'pricing_scope':'LONG_DISTANCE'})
        db.add_all([vehicle, service]); db.commit()
        return person, tokens, vehicle.id, service.id


def test_owner_rate_save_preview_edit_and_version_protection(client, rate_owner):
    _, tokens, vid, sid = rate_owner; headers = bearer(tokens)
    payload = {'service_type_id': str(sid), 'expected_version': 0, 'enabled': True, 'currency': 'LKR', 'rules': [rule()]}
    path = f'/api/v1/vehicles/{vid}/services'
    saved = client.put(path, headers=headers, json=payload)
    assert saved.status_code == 200, saved.text
    assert saved.json()['version'] == 1 and saved.json()['rules'][0]['base_charge'] == '1000'
    assert 'Future matching' in saved.json()['message']
    assert client.put(path, headers=headers, json=payload).status_code == 409
    data = {'rule': payload['rules'][0], 'example': {'distance_km': '30', 'night_km': '5', 'waiting_minutes': '50', 'service_hours': ['3'], 'overnight_stays': 0}}
    preview = client.post(path + '/preview', headers=headers, json=data)
    assert preview.status_code == 200, preview.text
    assert preview.json()['total'] == '2200.00' and preview.json()['example_only']
    payload['expected_version'] = 1; payload['rules'][0]['extra_km_rate'] = '60'
    assert client.put(path, headers=headers, json=payload).json()['version'] == 2
    with client.app.state.sessions() as db:
        row = db.scalar(select(VehicleService))
        assert row.owner_terms['rate_rules'][0]['extra_km_rate'] == '60'
        assert row.base_price is None and row.price_per_km is None


def test_passenger_and_other_owner_cannot_access_vehicle_rates(client, passenger, rate_owner):
    _, _, vid, sid = rate_owner
    other = {**passenger, 'email': 'other-' + uuid4().hex + '@example.com', 'phone_e164': '+9477' + str(uuid4().int % 10000000).zfill(7)}
    user, tokens = signed_in(client, other); headers = bearer(tokens)
    assert client.get(f'/api/v1/vehicles/{vid}/services', headers=headers).status_code == 403
    with client.app.state.sessions() as db:
        db.add(UserRole(user_id=UUID(user['id']), role_code='OWNER', approval_status='APPROVED', approved_by=UUID(user['id']), approved_at=func.now()))
        db.commit()
    assert client.get(f'/api/v1/vehicles/{vid}/services', headers=headers).status_code == 404
    assert client.get(f'/api/v1/vehicles/{vid}/services').status_code == 401


def test_location_proofs_prevent_browser_coordinate_substitution(client, rate_owner):
    _, tokens, vid, sid = rate_owner
    places = [client.app.state.rate_locations.signed('Colombo', '6.9271', '79.8612'), client.app.state.rate_locations.signed('Kandy', '7.2906', '80.6337')]
    data = rule(); data['coverage'] = {'kind': 'ROUTE', 'places': places}
    payload = {'service_type_id': str(sid), 'expected_version': 0, 'enabled': True, 'currency': 'LKR', 'rules': [data]}
    assert client.put(f'/api/v1/vehicles/{vid}/services', headers=bearer(tokens), json=payload).status_code == 200
    payload['expected_version'] = 1; places[0]['latitude'] = '8'
    assert client.put(f'/api/v1/vehicles/{vid}/services', headers=bearer(tokens), json=payload).status_code == 422


def test_unconfigured_location_provider_is_honest(client):
    client.app.state.settings.routing_api_key = ''
    result = client.get('/api/v1/locations?q=Colombo')
    assert result.status_code == 503 and result.json()['code'] == 'ROUTING_NOT_CONFIGURED'


def policy_rule(**policy):
    data = rule()
    data['extra_policy'] = policy
    return data


def test_extra_policy_needs_zero_rates_unless_charged_and_only_for_used_extras():
    ok = policy_rule(WAITING='NOT_OFFERED'); ok.update(free_wait_minutes='0', waiting_hour_rate='0')
    assert RateRule.model_validate(ok).extra_policy == {'WAITING': 'NOT_OFFERED'}
    with pytest.raises(Exception, match='enter 0'):
        RateRule.model_validate(policy_rule(WAITING='FREE'))                         # still has a waiting rate
    with pytest.raises(Exception, match='not used'):
        RateRule.model_validate(policy_rule(EXTRA_HOURS='FREE'))                     # DISTANCE rule has no extra hours
    assert RateRule.model_validate(rule()).extra_policy == {}                        # older rules mean CHARGED
