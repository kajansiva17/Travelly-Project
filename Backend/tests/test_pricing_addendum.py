"""Owner addendum: fixed-first selection, departure consent and scope isolation."""
from copy import deepcopy
from datetime import datetime, timedelta
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo
import pytest
from pydantic import ValidationError
from sqlalchemy import select, func
from app.schemas.rate_schemas import RateConfiguration, DepartureApplicability, departure_applies
from app.models.rate_models import ServiceType, VehicleService
from app.models.hire_models import Booking, Trip, VehicleRecord
from conftest import bearer
from test_rates import rate_owner
from test_hire_pricing import hire_setup, accept, committed


def fixed(c, fare='1500', names=('A', 'B'), departure=None):
    value = deepcopy(c.rule)
    for field in ('base_charge', 'included_km', 'extra_km_rate', 'night_km_rate'): value.pop(field)
    value.update(id=str(uuid4()), method='FIXED_ROUTE', fixed_fare=fare,
        coverage={'kind': 'ROUTE', 'places': [c.places[n] for n in names]},
        departure=departure or {'kind': 'ANY_TIME'})
    return value


def save(client, c, rules):
    body = {**deepcopy(c.config), 'expected_version': 1, 'rules': rules}
    response = client.put(f'/api/v1/vehicles/{c.vehicle_id}/services', headers=bearer(c.owner), json=body)
    assert response.status_code == 200, response.text
    return body


def test_fixed_first_then_distance_then_quote_and_no_duration_switch(client, hire_setup, monkeypatch):
    c = hire_setup
    start = datetime.fromisoformat(c.itinerary()['start_at']).astimezone(ZoneInfo('Asia/Colombo')).replace(hour=10, minute=0)
    f = fixed(c, departure={'kind': 'WEEKLY_WINDOW', 'weekdays': [start.weekday()], 'from_time': '09:00', 'until_time': '17:00'})
    save(client, c, [c.rule, f])
    inside = {**c.itinerary(hours='8'), 'start_at': start.isoformat()}
    def selected(itinerary):
        return client.post(f"/api/v1/search/vehicles/{c.vehicle_id}/quote", json={
            'service_type_id': str(c.service_id), 'itinerary': itinerary,
            'passenger_count': 2, 'large_luggage_count': 1, 'small_luggage_count': 1})
    response = selected(inside)
    assert response.status_code == 200, response.text
    calculation = response.json()['price']
    assert calculation['method'] == 'FIXED_ROUTE' and calculation['total'] == '1500.00'
    assert not {'BASE', 'EXTRA_KM', 'NIGHT_KM'} & {x['code'] for x in calculation['breakdown']}
    assert calculation['reserved_service_hours'] == []
    assert response.json()['owner_confirmation_required'] is True
    measured = client.app.state.hire_routing.measure
    monkeypatch.setattr(client.app.state.hire_routing, 'measure',
                        lambda *_args: (_ for _ in ()).throw(RuntimeError('fixed route must not call routing')))
    assert selected(inside).json()['price']['total'] == '1500.00'
    monkeypatch.setattr(client.app.state.hire_routing, 'measure', measured)
    outside = {**inside, 'start_at': start.replace(hour=8).isoformat()}
    assert selected(outside).json()['price']['method'] == 'DISTANCE'
    assert selected(c.itinerary(('A', 'C'))).json()['quote_required'] is True
    searched = client.post('/api/v1/search/vehicles', json={'service_type_id': str(c.service_id), 'itinerary': inside,
        'passenger_count': 2, 'large_luggage_count': 1, 'small_luggage_count': 1})
    assert searched.status_code == 200, searched.text
    entries = searched.json()['items'] + searched.json()['quote_on_request']
    assert len(entries) == 1 and entries[0]['price'] is None
    assert entries[0]['availability_status'] == 'CONFIRMATION_REQUIRED'


@pytest.mark.parametrize('reverse_fare', ['1500', '1750'])
def test_reverse_direction_requires_explicit_rule_with_equal_or_different_fare(client, hire_setup, reverse_fare):
    c = hire_setup
    save(client, c, [fixed(c), fixed(c, reverse_fare, ('B', 'A'))])
    assert c.confirm_position(c.create())['proposal']['quote']['calculation']['total'] == '1500.00'
    assert c.confirm_position(c.create(c.itinerary(('B', 'A'))))['proposal']['quote']['calculation']['total'] == reverse_fare + '.00'


def test_fixed_inclusions_extras_disclosed_and_rate_edit_preserves_acceptance(client, hire_setup):
    c = hire_setup; fare = fixed(c)
    cfg = save(client, c, [fare, c.rule])
    row = accept(client, c, c.create(c.itinerary(wait='80')))
    assert row['total_amount'] == '1800.00'  # 60 minutes beyond explicitly included 20.
    assert row['price']['initial']['rule']['free_wait_minutes'] == '20'
    assert any(line['code'] == 'WAIT' and line['amount'] == '300' for line in row['price']['initial']['calculation']['breakdown'])
    snapshot = deepcopy(row['price'])
    cfg['expected_version'] = 2; cfg['rules'][0]['fixed_fare'] = '1700'
    assert client.put(f'/api/v1/vehicles/{c.vehicle_id}/services', headers=bearer(c.owner), json=cfg).status_code == 200
    assert client.get(f"/api/v1/bookings/{row['id']}", headers=bearer(c.passenger)).json()['price'] == snapshot
    assert c.confirm_position(c.create())['proposal']['quote']['calculation']['total'] == '1700.00'


@pytest.mark.parametrize('scope', [None, 'UNSPECIFIED'])   # EVENT is now approved: see test_event_hire.py
def test_non_long_distance_scopes_never_inherit_the_formula(client, hire_setup, scope):
    c = hire_setup; accepted = accept(client, c, c.create())
    with client.app.state.sessions() as db:
        service = db.get(ServiceType, c.service_id)
        service.settings = {**service.settings, 'pricing_scope': scope}; db.commit()
    assert str(c.service_id) not in {s['id'] for s in client.get('/api/v1/service-types').json()['items']}
    saved = client.put(f'/api/v1/vehicles/{c.vehicle_id}/services', headers=bearer(c.owner), json={**c.config, 'expected_version': 1})
    assert saved.status_code == 409 and saved.json()['code'] == 'PRICING_POLICY_NOT_APPROVED'
    search = client.post('/api/v1/search/vehicles', json={'service_type_id': str(c.service_id), 'itinerary': c.itinerary(),
        'passenger_count': 2, 'large_luggage_count': 1, 'small_luggage_count': 1})
    assert search.status_code == 409 and search.json()['code'] == 'PRICING_POLICY_NOT_APPROVED'
    assert client.get(f"/api/v1/bookings/{accepted['id']}", headers=bearer(c.passenger)).json()['price'] == accepted['price']


@pytest.mark.parametrize('at,expected', [('2026-11-02T21:59:59+05:30', False), ('2026-11-02T22:00:00+05:30', True),
    ('2026-11-03T04:59:59+05:30', True), ('2026-11-03T05:00:00+05:30', False),
    ('2026-11-09T01:00:00+05:30', True)])
def test_weekly_departure_windows_cross_midnight_and_week_boundary(at, expected):
    window = DepartureApplicability(kind='WEEKLY_WINDOW', weekdays=[0, 6], from_time='22:00', until_time='05:00')
    assert departure_applies(window, datetime.fromisoformat(at)) is expected


def test_departure_applicability_required_and_same_priority_overlap_rejected(client, hire_setup):
    c = hire_setup; a = fixed(c); b = {**deepcopy(a), 'id': str(uuid4())}
    cfg = {**c.config, 'expected_version': 1, 'rules': [a, b]}
    with pytest.raises(ValidationError): RateConfiguration.model_validate(cfg)
    a.pop('departure'); cfg['rules'] = [a]
    with pytest.raises(ValidationError): RateConfiguration.model_validate(cfg)
    a['departure'] = {'kind': 'WEEKLY_WINDOW', 'weekdays': [0], 'from_time': '08:00', 'until_time': '12:00'}
    b['departure'] = {'kind': 'WEEKLY_WINDOW', 'weekdays': [0], 'from_time': '12:00', 'until_time': '18:00'}
    cfg['rules'] = [a, b, c.rule]
    assert len(RateConfiguration.model_validate(cfg).rules) == 3


def test_old_unaccepted_fixed_quote_needs_applicability_but_accepted_snapshots_stay_unchanged(client, hire_setup):
    c = hire_setup; save(client, c, [fixed(c)])
    row = c.confirm_position(c.create())   # the Owner confirms the vehicle position first; the quote follows
    with client.app.state.sessions() as db:
        booking = db.get(Booking, UUID(row['id']))
        pending = deepcopy(booking.pending_change); pending['quote']['rule'].pop('departure')
        booking.pending_change = pending; db.commit()
    response = client.post(f"/api/v1/bookings/{row['id']}/price-acceptance", headers=bearer(c.passenger),
        json={'expected_version': row['version'], 'digest': row['proposal']['quote']['digest']})
    assert response.status_code == 409 and response.json()['code'] == 'QUOTE_REVIEW_REQUIRED'


@pytest.mark.parametrize('conflict', [False, True])
def test_owner_departure_change_requires_new_quote_passenger_consent_and_feasibility(client, hire_setup, conflict):
    c = hire_setup; fare = fixed(c, '2000'); cfg = save(client, c, [fare])
    row = committed(client, c); initial = deepcopy(row['price']['initial']); old_start = row['start_at']
    itinerary = c.itinerary(); itinerary['start_at'] = (datetime.fromisoformat(itinerary['start_at']) + timedelta(hours=2)).isoformat()
    body = {'expected_version': row['version'], 'reason': 'DEPARTURE_TIME_CHANGE', 'itinerary': itinerary}
    assert client.post(f"/api/v1/bookings/{row['id']}/changes", headers=bearer(c.passenger), json=body).status_code == 403
    proposed = client.post(f"/api/v1/bookings/{row['id']}/changes", headers=bearer(c.owner), json=body)
    assert proposed.status_code == 200, proposed.text
    row = proposed.json(); assert row['start_at'] == old_start and row['price']['initial'] == initial
    cfg['expected_version'] = 2; cfg['rules'][0]['fixed_fare'] = '2200'
    quoted = client.post(f"/api/v1/bookings/{row['id']}/quote", headers=bearer(c.owner), json={'expected_version': row['version'], 'rates': cfg})
    assert quoted.status_code == 200, quoted.text
    row = quoted.json(); proposal = row['proposal']; assert proposal['old_departure'] == old_start
    assert proposal['added_charge'] == '200.00' and proposal['new_total'] == '2200.00'
    review_body = {'expected_version': row['version'], 'digest': proposal['digest']}
    assert client.post(f"/api/v1/bookings/{row['id']}/changes/review", headers=bearer(c.owner), json=review_body).status_code == 409
    accepted = client.post(f"/api/v1/bookings/{row['id']}/changes/accept", headers=bearer(c.passenger), json=review_body)
    assert accepted.status_code == 200, accepted.text
    row = accepted.json(); assert row['start_at'] == old_start and row['total_amount'] == '2000.00'
    if conflict:
        with client.app.state.sessions() as db:
            booking = db.get(Booking, UUID(row['id']))
            db.add(VehicleRecord(vehicle_id=c.vehicle_id, recorded_by_user_id=booking.owner_user_id, record_type='AVAILABILITY_BLOCK',
                recorded_at=func.now(), start_at=booking.end_at, end_at=booking.end_at + timedelta(hours=1))); db.commit()
    reviewed = client.post(f"/api/v1/bookings/{row['id']}/changes/review", headers=bearer(c.owner), json={'expected_version': row['version'], 'digest': proposal['digest']})
    if conflict:
        assert reviewed.status_code == 409 and reviewed.json()['code'] == 'CHANGE_NOT_FEASIBLE'
        current = client.get(f"/api/v1/bookings/{row['id']}", headers=bearer(c.passenger)).json()
        assert current['start_at'] == old_start and current['price']['initial'] == initial
    else:
        assert reviewed.status_code == 200, reviewed.text
        updated = reviewed.json(); assert updated['total_amount'] == '2200.00' and updated['price']['initial'] == initial
        assert datetime.fromisoformat(updated['start_at']) == datetime.fromisoformat(itinerary['start_at'])
        with client.app.state.sessions() as db:
            trip = db.scalar(select(Trip).where(Trip.booking_id == UUID(row['id']), Trip.status != 'CANCELLED'))
            assert trip.scheduled_start_at == datetime.fromisoformat(itinerary['start_at'])

