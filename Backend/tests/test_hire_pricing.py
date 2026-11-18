from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4
from types import SimpleNamespace
import pytest
from sqlalchemy import select, func
from app.models import UserRole
from app.models.review_models import Vehicle, Document
from app.models.rate_models import ServiceType, VehicleService
from app.models.hire_models import Booking, Trip, Notification, VehicleRecord
from app.services.hire_services import vehicle_evidence
from app.schemas.rate_schemas import ExampleTrip, RateRule
from app.services.rate_calculation import calculate
from app.services.hire_routing import night_distance
from conftest import signed_in, bearer, check_passenger
from test_rates import rule, rate_owner


def test_provider_outage_keeps_an_unpriced_enquiry_without_reservation(client, hire_setup, monkeypatch):
    from app.core.errors import ApiError
    c = hire_setup
    def unavailable(*args):
        raise ApiError(503, 'ROUTING_NOT_CONFIGURED', 'Trusted routing is not configured.')
    monkeypatch.setattr(client.app.state.hire_routing, 'measure', unavailable)
    row = c.create()
    assert row['status'] == 'REQUESTED' and row['proposal'] == {}
    assert not row['vehicle_committed'] and not row['accepted_quote_digest']
    assert row['total_amount'] is None


def test_legacy_passenger_uses_existing_auth_contact_policy(client, hire_setup):
    from app.models import User
    c = hire_setup
    with client.app.state.sessions() as db:
        user = db.get(User, UUID(c.passenger_id))
        user.email_login_required = False
        user.email_verified_at = None
        user.phone_verified_at = func.now()
        db.commit()
    row = c.create()
    assert row['status'] == 'REQUESTED' and row['proposal']['kind'] == 'QUOTE'


def test_quote_must_save_enabled_reusable_rules(client, hire_setup):
    c = hire_setup; row = c.create(c.itinerary(('A', 'C')))
    cfg = {**deepcopy(c.config), 'expected_version': 1, 'enabled': False}
    response = client.post(f"/api/v1/bookings/{row['id']}/quote", headers=bearer(c.owner), json={'expected_version': row['version'], 'rates': cfg})
    assert response.status_code == 422 and response.json()['code'] == 'QUOTE_REUSE_REQUIRED'
    with client.app.state.sessions() as db:
        saved = db.scalar(select(VehicleService).where(VehicleService.vehicle_id == c.vehicle_id))
        assert saved.is_enabled and saved.version == 1


def test_rate_must_cover_the_complete_reserved_interval(client, hire_setup):
    c = hire_setup
    from zoneinfo import ZoneInfo
    itinerary = c.itinerary(hours='24')
    pickup_day = datetime.fromisoformat(itinerary['start_at']).astimezone(ZoneInfo('Asia/Colombo')).date()
    cfg = {**deepcopy(c.config), 'expected_version': 1}
    cfg['rules'][0]['effective_until'] = pickup_day.isoformat()
    assert client.put(f'/api/v1/vehicles/{c.vehicle_id}/services', headers=bearer(c.owner), json=cfg).status_code == 200
    row = c.create(itinerary)
    assert row['proposal'] == {} and not row['vehicle_committed'] and row['total_amount'] is None


def test_fixed_route_change_requires_a_reusable_quote_and_passenger_acceptance(client, hire_setup):
    c = hire_setup
    fixed = deepcopy(c.rule)
    for name in ('base_charge', 'included_km', 'extra_km_rate', 'night_km_rate'):
        fixed.pop(name)
    fixed.update(method='FIXED_ROUTE', fixed_fare='2000', departure={'kind':'ANY_TIME'})
    cfg = {**deepcopy(c.config), 'expected_version': 1, 'rules': [fixed]}
    assert client.put(f'/api/v1/vehicles/{c.vehicle_id}/services', headers=bearer(c.owner), json=cfg).status_code == 200
    row = committed(client, c); initial = deepcopy(row['price']['initial'])
    changed_itinerary = c.itinerary(('A', 'Stop', 'B'), hours='4')
    proposed = client.post(f"/api/v1/bookings/{row['id']}/changes", headers=bearer(c.owner), json={'expected_version': row['version'], 'reason': 'ADDED_STOP', 'itinerary': changed_itinerary})
    assert proposed.status_code == 200, proposed.text
    row = proposed.json()
    assert row['proposal']['kind'] == 'CHANGE_REQUEST_UNPRICED' and row['total_amount'] == '2000.00'
    assert 'new_total' not in row['proposal']
    new_rule = {**deepcopy(fixed), 'id': str(uuid4()), 'fixed_fare': '2600', 'coverage': {'kind': 'ROUTE', 'places': [c.places[n] for n in ('A', 'Stop', 'B')]}}
    cfg.update(expected_version=2, rules=[fixed, new_rule])
    quoted = client.post(f"/api/v1/bookings/{row['id']}/quote", headers=bearer(c.owner), json={'expected_version': row['version'], 'rates': cfg})
    assert quoted.status_code == 200, quoted.text
    row = quoted.json(); proposal = row['proposal']
    assert proposal['manual_review_required'] and proposal['added_charge'] == '600.00'
    premature = client.post(f"/api/v1/bookings/{row['id']}/changes/review", headers=bearer(c.owner), json={'expected_version': row['version'], 'digest': proposal['digest']})
    assert premature.status_code == 409
    accepted = client.post(f"/api/v1/bookings/{row['id']}/changes/accept", headers=bearer(c.passenger), json={'expected_version': row['version'], 'digest': proposal['digest']})
    assert accepted.status_code == 200, accepted.text
    row = accepted.json(); assert row['total_amount'] == '2000.00'
    reviewed = client.post(f"/api/v1/bookings/{row['id']}/changes/review", headers=bearer(c.owner), json={'expected_version': row['version'], 'digest': proposal['digest']})
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()['price']['initial'] == initial and reviewed.json()['total_amount'] == '2600.00'
    later_itinerary = {**changed_itinerary, 'start_at': (datetime.fromisoformat(changed_itinerary['start_at']) + timedelta(days=1)).isoformat()}
    future = c.create(later_itinerary)
    assert future['proposal']['quote']['calculation']['total'] == '2600.00'


def test_request_idempotency_binds_service_and_capacity_as_well_as_itinerary(client, hire_setup):
    c = hire_setup
    body = {'vehicle_id': str(c.vehicle_id), 'service_type_id': str(c.service_id), 'itinerary': c.itinerary(),
        'passenger_count': 2, 'large_luggage_count': 1, 'small_luggage_count': 1, 'idempotency_key': uuid4().hex}
    first = client.post('/api/v1/bookings/private-hires', headers=bearer(c.passenger), json=body)
    assert first.status_code == 201, first.text
    repeated = client.post('/api/v1/bookings/private-hires', headers=bearer(c.passenger), json=body)
    assert repeated.status_code == 201 and repeated.json()['id'] == first.json()['id']
    for changed in ({'passenger_count': 3}, {'large_luggage_count': 2}, {'service_type_id': str(uuid4())}):
        collision = client.post('/api/v1/bookings/private-hires', headers=bearer(c.passenger), json={**body, **changed})
        assert collision.status_code == 409 and collision.json()['code'] == 'IDEMPOTENCY_CONFLICT'


def day_rule():
    data = rule()
    for name in ('base_charge', 'included_km'): data.pop(name)
    data.update(method='DAY_HIRE', day_charge='1000', included_km_per_day='100', included_hours_per_day='8', extra_hour_rate='200', overnight_driver_cost='100')
    return RateRule.model_validate(data)


@pytest.mark.parametrize('hours,km,expected,included,reserved', [(['4'], '50', '1000.00', '100', ['8']), (['8','2'], '100', '1500.00', '125', ['8','2']), (['8','6'], '150', '2100.00', '200', ['8','8']), (['8','10'], '200', '2500.00', '200', ['8','10'])])
def test_day_partial_full_cap_pooling_and_reservation(hours, km, expected, included, reserved):
    usage = ExampleTrip.model_validate({'distance_km': km, 'night_km': '0', 'waiting_minutes': '0', 'service_hours': hours, 'overnight_stays': len(hours)-1})
    result = calculate(day_rule(), usage)
    assert result['total'] == expected and result['included_km'] == included
    assert result['reserved_service_hours'] == reserved


@pytest.mark.parametrize('waiting_rate,expected', [('100','1400.00'), ('300','1500.00')])
def test_waiting_overtime_higher_once_after_free_allowance(waiting_rate, expected):
    data = day_rule().model_dump(mode='json'); data.update(waiting_hour_rate=waiting_rate, free_wait_minutes='60')
    usage = ExampleTrip.model_validate({'distance_km': '10', 'night_km': '0', 'waiting_minutes': '120', 'service_hours': ['10'], 'overnight_stays': 0,
        'waiting_periods': [{'day': 0, 'start_hour': '8', 'minutes': '120'}]})
    assert calculate(RateRule.model_validate(data), usage)['total'] == expected


def test_night_boundary_uses_sri_lanka_time_and_fractional_segment():
    start = datetime.fromisoformat('2026-10-28T21:30:00+05:30')
    assert night_distance(Decimal('100'), start, Decimal('3600')) == Decimal('50')
    assert night_distance(Decimal('100'), datetime.fromisoformat('2026-10-29T04:30:00+05:30'), Decimal('3600')) == Decimal('50')


@pytest.fixture
def hire_setup(client, rate_owner, monkeypatch):
    person, owner_tokens, vid, sid = rate_owner
    owner_id = UUID(person['id'])
    coords = [('A', '6.93', '79.86'), ('B', '7.29', '80.63'), ('C', '7.5', '80.8'), ('Stop', '7.1', '80.1')]
    places = {n: client.app.state.rate_locations.signed(n, lat, lon) for n, lat, lon in coords}
    start = datetime.now(timezone.utc) + timedelta(days=2)
    with client.app.state.sessions() as db:
        vehicle = db.get(Vehicle, vid)
        vehicle.vehicle_type_code='CAR';vehicle.manufacture_year=2020;vehicle.colour='White';vehicle.power_type='ICE';vehicle.engine_fuel_type='PETROL';vehicle.make = 'Test'; vehicle.model = 'Vehicle'; vehicle.seat_capacity = 4; vehicle.large_luggage_capacity = 2; vehicle.small_luggage_capacity = 2
        vehicle.media = [{'id':str(uuid4()),'category':'EXTERIOR','status':'APPROVED','privacy_confirmed':True,'genuine_vehicle_confirmed':True,'variants':{'480':{'width':480,'height':320,'sha256':'0'*64}}}]
        vehicle.verification_status = 'APPROVED'; vehicle.approved_by = owner_id; vehicle.approved_at = func.now(); vehicle.availability_status = 'ACTIVE'
        vehicle.accepts_hire_bookings = True; vehicle.base_location_label = 'A'
        vehicle.base_latitude = Decimal(places['A']['latitude']); vehicle.base_longitude = Decimal(places['A']['longitude'])
        vehicle.pickup_distance_km = Decimal('500'); vehicle.current_latitude = vehicle.base_latitude; vehicle.current_longitude = vehicle.base_longitude
        vehicle.current_location_source = 'MANUAL'; vehicle.current_location_observed_at = datetime.now(timezone.utc)
        vehicle.verified_eligibility = {'owner_declaration':{'registered_owner_case':'SELF'},'category': 'CAR', 'authorisation_required': False, 'conditional_documents': {'EMISSION': False, 'FITNESS': False, 'ROUTE_PERMIT': False}}
        db.add(UserRole(user_id=owner_id, role_code='DRIVER', approval_status='APPROVED', approved_by=owner_id, approved_at=func.now()))
        for t in ('VEHICLE_REGISTRATION', 'INSURANCE', 'REVENUE_LICENCE', 'DRIVING_LICENCE'):
            doc = Document(vehicle_id=vid if t != 'DRIVING_LICENCE' else None, user_id=owner_id if t == 'DRIVING_LICENCE' else None,
                document_type=t, status='APPROVED', submitted_at=func.now(), verified_by=owner_id, verified_at=func.now(),
                issuing_country='LK', expiry_date=(start + timedelta(days=90)).date(), storage_key=uuid4().hex, original_file_name='test-evidence.png',
                mime_type='image/png', file_size_bytes=1, file_checksum='0'*64, verified_categories=['B'] if t == 'DRIVING_LICENCE' else [])
            db.add(doc)
        service = db.get(ServiceType, sid); service.settings = {'pricing_scope':'LONG_DISTANCE', 'licence_compatibility': {'CAR': ['B']}, 'routing_profiles': {'CAR': 'driving-car'}}
        db.flush(); vehicle.verified_eligibility = {**vehicle.verified_eligibility, 'publication_fingerprint': vehicle_evidence(db, vehicle)}; vehicle.is_published = True
        db.commit()
    r = rule(); r['coverage'] = {'kind': 'ROUTE', 'places': [places['A'], places['B']]}
    config = {'service_type_id': str(sid), 'expected_version': 0, 'enabled': True, 'currency': 'LKR', 'rules': [r]}
    saved = client.put(f'/api/v1/vehicles/{vid}/services', headers=bearer(owner_tokens), json=config)
    assert saved.status_code == 200, saved.text
    def measure(itinerary, profile):
        for s in itinerary.stops: client.app.state.rate_locations.verify(s.place)
        labels = tuple(s.place.label for s in itinerary.stops)
        km = {('A','B'): '30', ('B','A'): '30', ('A','Stop','B'): '45', ('A','C'): '80'}[labels]
        waiting = sum((s.wait_minutes for s in itinerary.stops if not s.overnight_rest), Decimal('0'))
        usage = ExampleTrip.model_validate({'distance_km': km, 'night_km': '5', 'waiting_minutes': str(waiting),
            'service_hours': [str(h) for h in itinerary.service_hours], 'overnight_stays': 0})
        return {'usage': usage, 'source': 'trusted-test-provider', 'geometry': [[float(s.place.longitude),float(s.place.latitude)] for s in itinerary.stops], 'end_at': itinerary.requested_end()}
    monkeypatch.setattr(client.app.state.hire_routing, 'measure', measure)
    monkeypatch.setattr(client.app.state.hire_routing, 'travel_seconds', lambda *args: 300)
    passenger = {'full_name': 'Journey Passenger', 'email': uuid4().hex+'@example.com', 'phone_e164': '+9477'+str(uuid4().int%10000000).zfill(7), 'password': 'TravellyStrong1!', 'accept_terms': True}
    p, pt = signed_in(client, passenger)
    def itinerary(names=('A','B'), hours='3', wait='0'):
        return {'start_at': start.isoformat(), 'direction': 'ONE_WAY', 'method': 'DISTANCE', 'service_hours': [hours],
            'stops': [{'place': places[n], 'wait_minutes': wait if i == 0 else '0', 'overnight_rest': False} for i,n in enumerate(names)]}
    def create(itin=None):
        response = client.post('/api/v1/bookings/private-hires', headers=bearer(pt), json={'vehicle_id': str(vid), 'service_type_id': str(sid), 'itinerary': itin or itinerary(),
            'passenger_count': 2, 'large_luggage_count': 1, 'small_luggage_count': 1, 'idempotency_key': uuid4().hex})
        assert response.status_code == 201, response.text
        return response.json()
    return SimpleNamespace(owner=owner_tokens, passenger=pt, passenger_id=p['id'], vehicle_id=vid, service_id=sid, places=places,
        rule=r, config=config, itinerary=itinerary, create=create)


def accept(client, ctx, booking):
    snap = booking['proposal']['quote']
    result = client.post(f"/api/v1/bookings/{booking['id']}/price-acceptance", headers=bearer(ctx.passenger), json={'expected_version': booking['version'], 'digest': snap['digest']})
    assert result.status_code == 200, result.text
    return result.json()


def quote_changed_route(client, ctx, booking, names=('A', 'Stop', 'B'), expected=200):
    changed = {**deepcopy(ctx.rule), 'id': str(uuid4()),
               'coverage': {'kind': 'ROUTE', 'places': [ctx.places[name] for name in names]}}
    config = {**ctx.config, 'expected_version': 1, 'rules': [ctx.rule, changed]}
    result = client.post(f"/api/v1/bookings/{booking['id']}/quote", headers=bearer(ctx.owner),
                         json={'expected_version': booking['version'], 'rates': config})
    assert result.status_code == expected, result.text
    return result if expected != 200 else result.json()


@pytest.mark.parametrize('workspace', ['owner', 'driver'])
def test_personal_hire_is_passenger_booking_with_same_account(client, hire_setup, workspace):
    c = hire_setup
    with client.app.state.sessions() as db:
        db.add(UserRole(user_id=UUID(c.passenger_id), role_code=workspace.upper(), approval_status='APPROVED', approved_at=func.now(), approved_by=UUID(c.passenger_id)))
        db.commit()
    body = {'vehicle_id': str(c.vehicle_id), 'service_type_id': str(c.service_id), 'itinerary': c.itinerary(),
            'passenger_count': 2, 'large_luggage_count': 0, 'small_luggage_count': 0, 'idempotency_key': uuid4().hex}
    assert client.post('/api/v1/bookings/private-hires?workspace=' + workspace, headers=bearer(c.passenger), json=body).status_code == 422
    result = client.post('/api/v1/bookings/private-hires', headers=bearer(c.passenger), json=body)
    assert result.status_code == 201, result.text
    row = result.json()
    assert row['passenger_user_id'] == c.passenger_id
    assert row['owner_user_id'] != c.passenger_id
    with client.app.state.sessions() as db:
        assert db.get(Booking, UUID(row['id'])).passenger_user_id == UUID(c.passenger_id)
        assert not db.scalar(select(Trip.id).where(Trip.booking_id == UUID(row['id'])))
        membership = db.scalar(select(UserRole).where(UserRole.user_id == UUID(c.passenger_id), UserRole.role_code == 'PASSENGER'))
        membership.approval_status = 'SUSPENDED'
        membership.suspended_at = func.now()
        membership.suspension_reason = 'Test eligibility restriction'
        db.commit()
    # UI context and an approved business role cannot substitute for Passenger authority.
    body['idempotency_key'] = uuid4().hex
    assert client.post('/api/v1/bookings/private-hires', headers=bearer(c.passenger), json=body).status_code == 403


@pytest.mark.parametrize('restriction', ['role', 'licence', 'availability'])
def test_owner_context_cannot_bypass_self_drive_eligibility(client, hire_setup, restriction):
    c = hire_setup
    row = accept(client, c, c.create())
    with client.app.state.sessions() as db:
        vehicle = db.get(Vehicle, c.vehicle_id)
        if restriction == 'role':
            membership = db.scalar(select(UserRole).where(UserRole.user_id == vehicle.owner_user_id, UserRole.role_code == 'DRIVER'))
            membership.approval_status = 'SUSPENDED'
            membership.suspended_at = func.now()
            membership.suspension_reason = 'Test eligibility restriction'
        elif restriction == 'licence':
            licence = db.scalar(select(Document).where(Document.user_id == vehicle.owner_user_id, Document.document_type == 'DRIVING_LICENCE'))
            licence.expiry_date = (datetime.now(timezone.utc) - timedelta(days=1)).date()
        else:
            vehicle.availability_status = 'INACTIVE'
        db.commit()
    result = client.post(f"/api/v1/bookings/{row['id']}/self-drive", headers=bearer(c.owner), json={'expected_version': row['version']})
    assert result.status_code == 409, result.text
    with client.app.state.sessions() as db:
        assert not db.scalar(select(Trip.id).where(Trip.booking_id == UUID(row['id'])))
        assert not db.get(Booking, UUID(row['id'])).vehicle_committed


def committed(client, ctx):
    booking = accept(client, ctx, ctx.create())
    result = client.post(f"/api/v1/bookings/{booking['id']}/self-drive", headers=bearer(ctx.owner), json={'expected_version': booking['version']})
    assert result.status_code == 200, result.text
    return result.json()


def test_vehicle_list_hides_price_until_the_passenger_selects(client, hire_setup):
    c = hire_setup
    body = {'service_type_id': str(c.service_id), 'itinerary': c.itinerary(), 'passenger_count': 2,
            'large_luggage_count': 1, 'small_luggage_count': 1}
    found = client.post('/api/v1/search/vehicles', json=body)
    assert found.status_code == 200, found.text
    items = found.json()['items']
    assert items and all(item['price'] is None for item in items)
    quoted = client.post(f"/api/v1/search/vehicles/{items[0]['id']}/quote", json=body)
    assert quoted.status_code == 200, quoted.text
    assert quoted.json()['price']['total'] == '2050.00'


def test_quote_reuse_recalculates_and_rate_edit_preserves_agreed_price(client, hire_setup):
    c = hire_setup; request = c.create(c.itinerary(('A','C')))
    assert request['proposal'] == {} and request['status'] == 'REQUESTED'
    new = {**deepcopy(c.rule), 'id': str(uuid4()), 'coverage': {'kind': 'ROUTE', 'places': [c.places['A'], c.places['C']]}}
    cfg = {**c.config, 'expected_version': 1, 'rules': [c.rule, new]}
    response = client.post(f"/api/v1/bookings/{request['id']}/quote", headers=bearer(c.owner), json={'expected_version': request['version'], 'rates': cfg})
    assert response.status_code == 200, response.text
    first = accept(client, c, response.json()); snapshot = deepcopy(first['price'])
    later = c.create(c.itinerary(('A','C'), wait='80'))
    assert later['proposal']['quote']['calculation']['total'] != first['total_amount']
    cfg['expected_version'] = 2; cfg['rules'][1]['extra_km_rate'] = '90'
    assert client.put(f'/api/v1/vehicles/{c.vehicle_id}/services', headers=bearer(c.owner), json=cfg).status_code == 200
    got = client.get(f"/api/v1/bookings/{first['id']}", headers=bearer(c.passenger)).json()
    assert got['price'] == snapshot
    fresh = c.create(c.itinerary(('A','C')))
    assert fresh['proposal']['quote']['calculation']['total'] != first['total_amount']


def test_price_acceptance_required_and_owner_commit_conflict(client, hire_setup):
    c = hire_setup; first = c.create()
    assert client.post(f"/api/v1/bookings/{first['id']}/self-drive", headers=bearer(c.owner), json={'expected_version': first['version']}).status_code == 409
    first = accept(client, c, first)
    second = accept(client, c, c.create())
    response = client.post(f"/api/v1/bookings/{first['id']}/self-drive", headers=bearer(c.owner), json={'expected_version': first['version']})
    assert response.status_code == 200 and response.json()['vehicle_committed']
    assert client.post(f"/api/v1/bookings/{second['id']}/self-drive", headers=bearer(c.owner), json={'expected_version': second['version']}).status_code == 409


def test_change_passenger_acceptance_totals_and_notifications(client, hire_setup):
    c = hire_setup; booked = committed(client, c); original = deepcopy(booked['price']['initial'])
    response = client.post(f"/api/v1/bookings/{booked['id']}/changes", headers=bearer(c.owner), json={'expected_version': booked['version'], 'reason': 'ADDED_STOP', 'itinerary': c.itinerary(('A','Stop','B'), hours='4')})
    assert response.status_code == 200, response.text
    proposal = response.json(); assert proposal['price']['current']['calculation']['total'] == '2050.00'
    assert proposal['proposal']['kind'] == 'CHANGE_REQUEST_UNPRICED'
    proposal = quote_changed_route(client, c, proposal)
    assert proposal['proposal']['old_total'] == '2050.00' and proposal['proposal']['new_total'] == '2800.00'
    result = client.post(f"/api/v1/bookings/{booked['id']}/changes/accept", headers=bearer(c.passenger), json={'expected_version': proposal['version'], 'digest': proposal['proposal']['digest']})
    assert result.status_code == 200, result.text
    pending = result.json(); assert pending['proposal']['passenger_accepted'] and Decimal(pending['total_amount']) == Decimal('2050.00')
    reviewed = client.post(f"/api/v1/bookings/{booked['id']}/changes/review", headers=bearer(c.owner),
                           json={'expected_version': pending['version'], 'digest': pending['proposal']['digest']})
    assert reviewed.status_code == 200, reviewed.text
    changed = reviewed.json(); assert changed['proposal'] == {} and Decimal(changed['total_amount']) == Decimal('2800.00')
    assert changed['price']['initial'] == original
    with client.app.state.sessions() as db:
        key = db.get(Booking, UUID(booked['id'])).idempotency_key
    retry = client.post('/api/v1/bookings/private-hires', headers=bearer(c.passenger), json={'vehicle_id': str(c.vehicle_id),
        'service_type_id': str(c.service_id), 'itinerary': c.itinerary(), 'passenger_count': 2, 'large_luggage_count': 1,
        'small_luggage_count': 1, 'idempotency_key': key})
    assert retry.status_code == 201 and retry.json()['id'] == booked['id'] and retry.json()['total_amount'] == '2800.00'
    assert client.post(f"/api/v1/bookings/{booked['id']}/changes/accept", headers=bearer(c.passenger), json={'expected_version': proposal['version'], 'digest': proposal['proposal']['digest']}).status_code == 409
    assert any('Trip change confirmed' == n['title'] for n in client.get('/api/v1/notifications', headers=bearer(c.passenger)).json()['items'])


def test_conflicting_change_stays_manual_without_mutating_agreement(client, hire_setup):
    c = hire_setup; booked = committed(client, c)
    with client.app.state.sessions() as db:
        row = db.get(Booking, UUID(booked['id']))
        db.add(VehicleRecord(vehicle_id=c.vehicle_id, recorded_by_user_id=row.owner_user_id, record_type='AVAILABILITY_BLOCK', recorded_at=func.now(), start_at=row.end_at, end_at=row.end_at+timedelta(hours=2)))
        db.commit()
    response = client.post(f"/api/v1/bookings/{booked['id']}/changes", headers=bearer(c.owner), json={'expected_version': booked['version'], 'reason': 'ADDED_STOP', 'itinerary': c.itinerary(('A','Stop','B'), hours='4')}).json()
    refused = quote_changed_route(client, c, response, expected=409)
    assert refused.json()['code'] == 'VEHICLE_SCHEDULE_CONFLICT'
    row = client.get(f"/api/v1/bookings/{booked['id']}", headers=bearer(c.owner)).json()
    assert row['proposal']['kind'] == 'CHANGE_REQUEST_UNPRICED'
    assert Decimal(row['total_amount']) == Decimal('2050')


def test_missing_or_suspended_category_blocks_operation(client, hire_setup):
    c = hire_setup; row = accept(client, c, c.create())
    with client.app.state.sessions() as db:
        svc=db.get(ServiceType,c.service_id); svc.settings={**svc.settings,'licence_compatibility':{}}; db.commit()
    response=client.post(f"/api/v1/bookings/{row['id']}/self-drive",headers=bearer(c.owner),json={'expected_version':row['version']})
    assert response.status_code == 409 and response.json()['code']=='DRIVER_CATEGORY_MISMATCH'


def test_evidence_renewal_requires_explicit_republication(client, hire_setup):
    c=hire_setup
    assert client.get('/api/v1/vehicles').json()['items']
    with client.app.state.sessions() as db:
        doc=db.scalar(select(Document).where(Document.vehicle_id==c.vehicle_id,Document.document_type=='INSURANCE'))
        doc.expiry_date=(datetime.now(timezone.utc)-timedelta(days=1)).date(); db.commit()
    assert client.get('/api/v1/vehicles').json()['items']==[]
    with client.app.state.sessions() as db:
        doc=db.scalar(select(Document).where(Document.vehicle_id==c.vehicle_id,Document.document_type=='INSURANCE'))
        doc.expiry_date=(datetime.now(timezone.utc)+timedelta(days=90)).date();doc.version+=1;db.commit()
        v=db.get(Vehicle,c.vehicle_id); version=v.version
    assert client.get('/api/v1/vehicles').json()['items']==[]
    assert client.patch(f'/api/v1/vehicles/{c.vehicle_id}/publish',headers=bearer(c.owner),json={'expected_version':version}).status_code==200
    assert client.get('/api/v1/vehicles').json()['items']


def external_driver(client, c):
    data={'full_name':'External Driver','email':uuid4().hex+'@example.com','phone_e164':'+9477'+str(uuid4().int%10000000).zfill(7),'password':'TravellyStrong1!','accept_terms':True}
    user,tokens=signed_in(client,data)
    uid=UUID(user['id'])
    with client.app.state.sessions() as db:
        owner=db.get(Vehicle,c.vehicle_id).owner_user_id
        db.add(UserRole(user_id=uid,role_code='DRIVER',approval_status='APPROVED',approved_by=owner,approved_at=func.now()))
        db.add(Document(user_id=uid,document_type='DRIVING_LICENCE',status='APPROVED',submitted_at=func.now(),verified_by=owner,verified_at=func.now(),
            issuing_country='LK',expiry_date=(datetime.now(timezone.utc)+timedelta(days=90)).date(),storage_key=uuid4().hex,original_file_name='licence.png',mime_type='image/png',file_size_bytes=1,file_checksum='0'*64,verified_categories=['B']))
        db.commit()
    return user,tokens


def test_driver_decline_retains_vehicle_until_explicit_resolution(client, hire_setup):
    c=hire_setup;driver,dt=external_driver(client,c);b=accept(client,c,c.create())
    result=client.post(f"/api/v1/bookings/{b['id']}/driver-assignments",headers=bearer(c.owner),json={'expected_version':b['version'],'driver_reference':driver['public_user_reference']})
    assert result.status_code==200,result.text
    b=result.json();assert b['status']=='AWAITING_DRIVER' and b['vehicle_committed']
    detail=client.get(f"/api/v1/bookings/{b['id']}",headers=bearer(dt)).json()
    assert detail['trip']['assignment_status'] == 'PENDING'
    owner_acceptance = client.post(f"/api/v1/trips/{detail['trip']['id']}/assignment-accept", headers=bearer(c.owner), json={'expected_version': detail['trip']['version']})
    assert owner_acceptance.status_code == 404
    assert client.get(f"/api/v1/bookings/{b['id']}", headers=bearer(dt)).json()['trip']['assignment_status'] == 'PENDING'
    declined=client.post(f"/api/v1/trips/{detail['trip']['id']}/assignment-decline",headers=bearer(dt),json={'expected_version':detail['trip']['version']})
    assert declined.status_code==200,declined.text
    b=declined.json();assert b['status']=='OWNER_ACTION_REQUIRED' and b['vehicle_committed']
    assert any('remains reserved' in n['body'] for n in client.get('/api/v1/notifications',headers=bearer(dt)).json()['items'])
    with client.app.state.sessions() as db:
        from app.services.hire_services import no_conflict
        from app.core.errors import ApiError
        row=db.get(Booking,UUID(b['id']))
        with pytest.raises(ApiError): no_conflict(db,c.vehicle_id,row.start_at,row.end_at)
    resolved=client.post(f"/api/v1/bookings/{b['id']}/cancel",headers=bearer(c.owner),json={'expected_version':b['version'],'reason':'Cannot provide an eligible operator; resolving this unfunded pending request.'})
    assert resolved.status_code==200 and not resolved.json()['vehicle_committed']
    with client.app.state.sessions() as db:assert db.get(Trip,UUID(detail['trip']['id'])).assignment_status=='REJECTED'


def test_day_hire_reserves_full_first_package_in_booking(client,hire_setup):
    c=hire_setup
    day=day_rule().model_dump(mode='json');day['coverage']={'kind':'ROUTE','places':[c.places['A'],c.places['B']]}
    cfg={**c.config,'expected_version':1,'rules':[c.rule,day]}
    assert client.put(f'/api/v1/vehicles/{c.vehicle_id}/services',headers=bearer(c.owner),json=cfg).status_code==200
    itin=c.itinerary(hours='4');itin['method']='DAY_HIRE'
    b=c.create(itin)
    quote=b['proposal']['quote'];assert quote['calculation']['reserved_service_hours']==['8']
    assert datetime.fromisoformat(quote['reserved_end_at'])-datetime.fromisoformat(itin['start_at'])==timedelta(hours=8)


def test_failed_quote_rolls_back_reusable_rate_write(client,hire_setup,monkeypatch):
    from app.core.errors import ApiError
    c=hire_setup;b=c.create(c.itinerary(('A','C')))
    new={**deepcopy(c.rule),'id':str(uuid4()),'coverage':{'kind':'ROUTE','places':[c.places['A'],c.places['C']]}}
    def unavailable(*args):raise ApiError(503,'ROUTING_UNAVAILABLE','Route service unavailable.')
    monkeypatch.setattr(client.app.state.hire_routing,'measure',unavailable)
    response=client.post(f"/api/v1/bookings/{b['id']}/quote",headers=bearer(c.owner),json={'expected_version':b['version'],'rates':{**c.config,'expected_version':1,'rules':[c.rule,new]}})
    assert response.status_code==503
    with client.app.state.sessions() as db:
        saved=db.scalar(select(VehicleService).where(VehicleService.vehicle_id==c.vehicle_id))
        assert saved.version==1 and len(saved.owner_terms['rate_rules'])==1


def test_fixed_route_fare_has_no_automatic_night_charge():
    data=rule()
    for key in ('base_charge','included_km','extra_km_rate','night_km_rate'):data.pop(key)
    data.update(method='FIXED_ROUTE',fixed_fare='2500',coverage={'kind':'ROUTE','places':[
        {'label':'A','latitude':'6','longitude':'80','token':'a'*43},{'label':'B','latitude':'7','longitude':'80','token':'b'*43}]})
    usage=ExampleTrip.model_validate({'distance_km':'30','night_km':'30','waiting_minutes':'0','service_hours':['3'],'overnight_stays':0})
    result=calculate(RateRule.model_validate(data),usage)
    assert result['total']=='2500.00' and 'NIGHT_KM' not in [p['code'] for p in result['breakdown']]


@pytest.mark.parametrize('fault',['category','expiry','unverified','suspended'])
def test_trip_start_rechecks_current_category_evidence_and_role(client,hire_setup,monkeypatch,fault):
    import app.api.routers.hire_api as module
    c=hire_setup;b=committed(client,c)
    detail=client.get(f"/api/v1/bookings/{b['id']}",headers=bearer(c.owner)).json()
    with client.app.state.sessions() as db:
        row=db.get(Booking,UUID(b['id']));owner_id=row.owner_user_id;start=row.start_at
        doc=db.scalar(select(Document).where(Document.user_id==owner_id,Document.document_type=='DRIVING_LICENCE'))
        if fault=='category':doc.verified_categories=['WRONG']
        elif fault=='expiry':doc.expiry_date=(start-timedelta(days=1)).date()
        elif fault=='unverified':doc.status='UNDER_REVIEW'
        else:
            role=db.scalar(select(UserRole).where(UserRole.user_id==owner_id,UserRole.role_code=='DRIVER'))
            role.approval_status='SUSPENDED';role.suspended_at=func.now();role.suspension_reason='Eligibility review'
        db.commit()
    class Clock(datetime):
        @classmethod
        def now(cls,tz=None):return (start+timedelta(minutes=1)).astimezone(tz or timezone.utc)
    monkeypatch.setattr(module,'datetime',Clock)
    result=client.post(f"/api/v1/trips/{detail['trip']['id']}/start",headers=bearer(c.owner),json={'expected_version':detail['trip']['version'],'start_odometer_km':'1234.5','checklist_confirmed':True})
    assert result.status_code==409,result.text
    assert client.get(f"/api/v1/bookings/{b['id']}",headers=bearer(c.passenger)).json()['status']=='CONFIRMED'


def test_personal_booking_detail_reflects_external_driver_acceptance(client,hire_setup):
    c=hire_setup
    driver,driver_tokens=external_driver(client,c)
    booking=accept(client,c,c.create())
    assigned=client.post(f"/api/v1/bookings/{booking['id']}/driver-assignments",headers=bearer(c.owner),json={'expected_version':booking['version'],'driver_reference':driver['public_user_reference']})
    assert assigned.status_code==200,assigned.text
    before=client.get(f"/api/v1/bookings/{booking['id']}",headers=bearer(c.passenger))
    assert before.status_code==200 and before.json()['status']=='AWAITING_DRIVER'
    trip=before.json()['trip']
    accepted=client.post(f"/api/v1/trips/{trip['id']}/assignment-accept",headers=bearer(driver_tokens),json={'expected_version':trip['version']})
    assert accepted.status_code==200,accepted.text
    after=client.get(f"/api/v1/bookings/{booking['id']}",headers=bearer(c.passenger))
    assert after.status_code==200 and after.json()['status']=='CONFIRMED'
    assert after.json()['trip']['assignment_status']=='ACCEPTED'
    assert after.json()['version']>before.json()['version']


def test_started_trip_change_and_three_party_notifications(client,hire_setup,monkeypatch):
    import app.api.routers.hire_api as module
    c=hire_setup;driver,dt=external_driver(client,c);b=accept(client,c,c.create())
    result=client.post(f"/api/v1/bookings/{b['id']}/driver-assignments",headers=bearer(c.owner),json={'expected_version':b['version'],'driver_reference':driver['public_user_reference']})
    assert result.status_code==200,result.text
    detail=client.get(f"/api/v1/bookings/{b['id']}",headers=bearer(dt)).json();trip=detail['trip']
    accepted=client.post(f"/api/v1/trips/{trip['id']}/assignment-accept",headers=bearer(dt),json={'expected_version':trip['version']})
    assert accepted.status_code==200,accepted.text
    detail=client.get(f"/api/v1/bookings/{b['id']}",headers=bearer(dt)).json();start=datetime.fromisoformat(detail['start_at'])
    class Clock(datetime):
        @classmethod
        def now(cls,tz=None):return (start+timedelta(minutes=1)).astimezone(tz or timezone.utc)
    check_passenger(client,c.passenger,dt,trip['id'],detail['trip']['version'])
    monkeypatch.setattr(module,'datetime',Clock)
    started=client.post(f"/api/v1/trips/{trip['id']}/start",headers=bearer(dt),json={'expected_version':detail['trip']['version'],'start_odometer_km':'1234.5','checklist_confirmed':True})
    assert started.status_code==200 and started.json()['status']=='IN_PROGRESS',started.text
    b=started.json()
    proposed=client.post(f"/api/v1/bookings/{b['id']}/changes",headers=bearer(dt),json={'expected_version':b['version'],'reason':'ADDED_STOP','itinerary':c.itinerary(('A','Stop','B'),hours='4')})
    assert proposed.status_code==200,proposed.text
    b=quote_changed_route(client,c,proposed.json());changed=client.post(f"/api/v1/bookings/{b['id']}/changes/accept",headers=bearer(c.passenger),json={'expected_version':b['version'],'digest':b['proposal']['digest']})
    assert changed.status_code==200 and changed.json()['proposal']['passenger_accepted'],changed.text
    b=changed.json();reviewed=client.post(f"/api/v1/bookings/{b['id']}/changes/review",headers=bearer(c.owner),json={'expected_version':b['version'],'digest':b['proposal']['digest']})
    assert reviewed.status_code==200 and reviewed.json()['proposal']=={},reviewed.text
    for tokens in (c.owner,c.passenger,dt):
        assert any(n['title']=='Trip change confirmed' for n in client.get('/api/v1/notifications',headers=bearer(tokens)).json()['items'])


def test_admin_reviewed_matrix_and_licence_categories_are_not_owner_editable(client,hire_setup):
    c=hire_setup
    data={'full_name':'Review Admin','email':uuid4().hex+'@example.com','phone_e164':'+9477'+str(uuid4().int%10000000).zfill(7),'password':'TravellyStrong1!','accept_terms':True}
    person,tokens=signed_in(client,data)
    with client.app.state.sessions() as db:
        db.add(UserRole(user_id=UUID(person['id']),role_code='ADMIN',approval_status='APPROVED',approved_at=func.now()));db.commit()
        svc=db.get(ServiceType,c.service_id);version=svc.version
        doc=db.scalar(select(Document).where(Document.document_type=='DRIVING_LICENCE'));docid=doc.id;docversion=doc.version
    body={'expected_version':version,'matrix':{'CAR':['B']},'routing_profiles':{'CAR':'driving-car'}}
    assert client.put(f'/api/v1/admin/service-types/{c.service_id}/licence-compatibility',headers=bearer(c.owner),json=body).status_code==403
    review=client.put(f'/api/v1/admin/service-types/{c.service_id}/licence-compatibility',headers=bearer(tokens),json=body)
    assert review.status_code==200,review.text
    assert client.patch(f'/api/v1/admin/documents/{docid}/licence-categories',headers=bearer(c.owner),json={'expected_version':docversion,'categories':['B']}).status_code==403
    result=client.patch(f'/api/v1/admin/documents/{docid}/licence-categories',headers=bearer(tokens),json={'expected_version':docversion,'categories':['B']})
    assert result.status_code==200,result.text
    created=client.post('/api/v1/admin/service-types',headers=bearer(tokens),json={'code':'TEST_'+uuid4().hex[:10].upper(),'name':'Reviewed private-hire catalogue','default_pricing_basis':'DISTANCE','is_active':True,'pricing_scope':'LONG_DISTANCE'})
    assert created.status_code==201,created.text
    scope_path=f"/api/v1/admin/service-types/{created.json()['id']}/pricing-scope"
    scope={'expected_version':created.json()['version'],'pricing_scope':'UNSPECIFIED'}
    assert client.patch(scope_path,headers=bearer(c.owner),json=scope).status_code==403
    classified=client.patch(scope_path,headers=bearer(tokens),json=scope)
    assert classified.status_code==200,classified.text
    assert client.patch(scope_path,headers=bearer(tokens),json=scope).status_code==409
    assert created.json()['id'] not in {s['id'] for s in client.get('/api/v1/service-types').json()['items']}
    assert client.patch(scope_path,headers=bearer(tokens),json={'expected_version':classified.json()['version'],'pricing_scope':'LONG_DISTANCE'}).status_code==200



def test_search_lists_free_vehicles_without_a_saved_price_as_ask_the_owner(client, hire_setup):
    c = hire_setup
    body = {'service_type_id': str(c.service_id), 'itinerary': c.itinerary(('A', 'C')), 'passenger_count': 2,
            'large_luggage_count': 1, 'small_luggage_count': 1}      # A -> C has no saved rate (only A -> B)
    found = client.post('/api/v1/search/vehicles', json=body)
    assert found.status_code == 200, found.text
    data = found.json()
    assert data['items'] == [] and len(data['quote_on_request']) == 1 and data['quote_on_request'][0]['quote_required'] is True
    assert data['quote_on_request'][0]['price'] is None and 'rules' not in data['quote_on_request'][0]
    priced = client.post('/api/v1/search/vehicles', json={**body, 'itinerary': c.itinerary(('A', 'B'))}).json()
    assert len(priced['items']) == 1 and priced['quote_on_request'] == []


def test_a_passenger_waits_for_at_most_three_owner_prices_and_unanswered_ones_lapse(client, hire_setup):
    from app.services.reminders import run_reminders
    c = hire_setup
    rows = [c.create(c.itinerary(('A', 'C'))) for _ in range(3)]
    assert all(r['status'] == 'REQUESTED' and r['proposal'] == {} for r in rows)
    body = {'vehicle_id': str(c.vehicle_id), 'service_type_id': str(c.service_id), 'itinerary': c.itinerary(('A', 'C')),
            'passenger_count': 2, 'large_luggage_count': 1, 'small_luggage_count': 1, 'idempotency_key': uuid4().hex}
    fourth = client.post('/api/v1/bookings/private-hires', headers=bearer(c.passenger), json=body)
    assert fourth.status_code == 409 and fourth.json()['code'] == 'TOO_MANY_OPEN_REQUESTS'
    with client.app.state.sessions() as db:
        out = run_reminders(db, client.app.state.settings, None, datetime.now(timezone.utc) + timedelta(hours=25)); db.commit()
        assert out['expired_requests'] == 3
        assert {db.get(Booking, UUID(r['id'])).status for r in rows} == {'CANCELLED'}
    assert client.post('/api/v1/bookings/private-hires', headers=bearer(c.passenger), json={**body, 'idempotency_key': uuid4().hex}).status_code == 201


def test_extra_the_owner_does_not_offer_sends_the_passenger_to_ask_for_a_quote(client, hire_setup):
    c = hire_setup
    r = deepcopy(c.rule); r.update(extra_policy={'WAITING': 'NOT_OFFERED'}, free_wait_minutes='0', waiting_hour_rate='0')
    cfg = {**deepcopy(c.config), 'expected_version': 1, 'rules': [r]}
    assert client.put(f'/api/v1/vehicles/{c.vehicle_id}/services', headers=bearer(c.owner), json=cfg).status_code == 200
    search = lambda wait: client.post('/api/v1/search/vehicles', json={'service_type_id': str(c.service_id), 'itinerary': c.itinerary(('A', 'B'), wait=wait),
                                      'passenger_count': 2, 'large_luggage_count': 1, 'small_luggage_count': 1}).json()
    plain = search('0')
    assert len(plain['items']) == 1 and plain['quote_on_request'] == []
    selected = client.post(f"/api/v1/search/vehicles/{plain['items'][0]['id']}/quote", json={
        'service_type_id': str(c.service_id), 'itinerary': c.itinerary(wait='0'), 'passenger_count': 2,
        'large_luggage_count': 1, 'small_luggage_count': 1}).json()
    policies = {p['code']: p for p in selected['price']['extra_policies']}
    assert policies['WAITING']['mode'] == 'NOT_OFFERED' and policies['EXTRA_KM']['mode'] == 'CHARGED' and policies['EXTRA_KM']['km_rate'] == '50'
    waiting = search('30')
    assert waiting['items'] == [] and len(waiting['quote_on_request']) == 1


def test_search_orders_vehicles_by_where_they_most_likely_are(client, hire_setup):
    c = hire_setup
    ask = lambda names: client.post('/api/v1/search/vehicles', json={'service_type_id': str(c.service_id), 'itinerary': c.itinerary(names),
        'passenger_count': 2, 'large_luggage_count': 1, 'small_luggage_count': 1}).json()['items'][0]
    first = ask(('A', 'B'))
    assert first['location_source'] == 'BASE_LOCATION' and first['distance_km'] == 0.0 and first['near'] is True
    row = committed(client, c)                                        # booked A -> B; the vehicle finishes at B
    with client.app.state.sessions() as db:
        trip = db.scalar(select(Trip).where(Trip.booking_id == UUID(row['id'])))
        trip.status = 'COMPLETED'; trip.actual_end_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db.get(Booking, UUID(row['id'])).status = 'COMPLETED'; db.commit()
    later = client.post('/api/v1/search/vehicles', json={'service_type_id': str(c.service_id), 'itinerary': {**c.itinerary(('B', 'A')), 'start_at': (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()},
                                                         'passenger_count': 2, 'large_luggage_count': 1, 'small_luggage_count': 1}).json()
    entry = (later['items'] + later['quote_on_request'])[0]
    assert entry['location_source'] == 'BASE_LOCATION' and entry['distance_km'] > 50 and entry['near'] is False


def test_owner_can_offer_another_time_and_the_booking_moves_only_when_the_passenger_accepts(client, hire_setup):
    c = hire_setup; request = c.create()
    asked = datetime.fromisoformat(request['start_at'])
    offered = asked + timedelta(days=2)
    cfg = {**deepcopy(c.config), 'expected_version': 1}
    response = client.post(f"/api/v1/bookings/{request['id']}/quote", headers=bearer(c.owner),
                           json={'expected_version': request['version'], 'rates': cfg, 'proposed_start_at': offered.isoformat()})
    assert response.status_code == 200, response.text
    quoted = response.json()
    assert datetime.fromisoformat(quoted['proposal']['quote']['itinerary']['start_at']) == offered
    assert datetime.fromisoformat(quoted['start_at']) == asked  # nothing moves before the Passenger agrees
    accepted = accept(client, c, quoted)
    assert datetime.fromisoformat(accepted['start_at']) == offered
    assert datetime.fromisoformat(accepted['end_at']) > offered


def test_a_proposed_time_in_the_past_is_refused(client, hire_setup):
    c = hire_setup; request = c.create()
    cfg = {**deepcopy(c.config), 'expected_version': 1}
    response = client.post(f"/api/v1/bookings/{request['id']}/quote", headers=bearer(c.owner),
                           json={'expected_version': request['version'], 'rates': cfg,
                                 'proposed_start_at': (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()})
    assert response.status_code == 422


def test_old_finished_bookings_move_to_history_by_themselves(client, hire_setup):
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import text
    c = hire_setup; b = c.create()
    client.post(f"/api/v1/bookings/{b['id']}/cancel", headers=bearer(c.passenger), json={'expected_version': b['version'], 'reason': 'test'})
    h = bearer(c.passenger)
    assert any(x['id'] == b['id'] for x in client.get('/api/v1/bookings?as=passenger', headers=h).json()['items'])
    with client.app.state.sessions() as db:
        db.execute(text("update bookings set created_at = :t, updated_at = :t where id = :i"), {'t': datetime.now(timezone.utc) - timedelta(days=31), 'i': b['id']}); db.commit()
    assert not any(x['id'] == b['id'] for x in client.get('/api/v1/bookings?as=passenger', headers=h).json()['items'])
    assert any(x['id'] == b['id'] for x in client.get('/api/v1/bookings?as=passenger&hidden=true', headers=h).json()['items'])


def test_passenger_keeps_favourite_vehicles_and_removes_them(client, hire_setup):
    c = hire_setup; h = bearer(c.passenger); vid = str(c.vehicle_id)
    assert client.get('/api/v1/me/favourite-vehicles', headers=h).json()['items'] == []
    assert client.put(f'/api/v1/me/favourite-vehicles/{vid}', headers=h, json={}).status_code == 200
    assert client.put(f'/api/v1/me/favourite-vehicles/{vid}', headers=h, json={}).status_code == 200   # saving twice keeps one
    listed = client.get('/api/v1/me/favourite-vehicles', headers=h).json()
    assert [i['id'] for i in listed['items']] == [vid] and listed['items'][0]['available'] is True and listed['ids'] == [vid]
    assert client.get('/api/v1/me/favourite-vehicles', headers=bearer(c.owner)).json()['items'] == []   # each person sees only their own
    assert client.delete(f'/api/v1/me/favourite-vehicles/{vid}', headers=h).status_code == 200
    assert client.get('/api/v1/me/favourite-vehicles', headers=h).json()['items'] == []
    assert client.put(f'/api/v1/me/favourite-vehicles/{uuid4()}', headers=h, json={}).status_code == 404
    assert client.get('/api/v1/me/favourite-vehicles').status_code == 401


def test_passenger_cancels_confirmed_hire_until_three_hours_before_start_and_everyone_is_told(client, hire_setup):
    c = hire_setup
    b = committed(client, c)
    assert b['status'] == 'CONFIRMED'
    with client.app.state.sessions() as db:                      # too late: starts in 2 hours
        row = db.get(Booking, UUID(b['id']))
        keep = (row.start_at, row.end_at)
        row.start_at = datetime.now(timezone.utc) + timedelta(hours=2); row.end_at = row.start_at + timedelta(hours=3); db.commit()
    late = client.post(f"/api/v1/bookings/{b['id']}/cancel", headers=bearer(c.passenger), json={'expected_version': b['version'], 'reason': 'late'})
    assert late.status_code == 409 and late.json()['code'] == 'CANCELLATION_TOO_LATE'
    with client.app.state.sessions() as db:                      # back to the original (far) time
        row = db.get(Booking, UUID(b['id'])); row.start_at, row.end_at = keep; db.commit()
    done = client.post(f"/api/v1/bookings/{b['id']}/cancel", headers=bearer(c.passenger), json={'expected_version': b['version'], 'reason': 'Plans changed'})
    assert done.status_code == 200, done.text
    assert done.json()['status'] == 'CANCELLED' and not done.json()['vehicle_committed']
    assert any('Passenger cancelled' in n['body'] for n in client.get('/api/v1/notifications', headers=bearer(c.owner)).json()['items'])


def test_my_drivers_needs_a_request_or_invitation_that_the_other_side_accepts(client, hire_setup):
    c = hire_setup
    driver, dt = external_driver(client, c)
    oh, dh = bearer(c.owner), bearer(dt)
    first = client.get('/api/v1/owners/me/saved-drivers', headers=oh).json()
    assert first['items'] == [] and first['my_reference'].startswith('USR-')
    assert client.post('/api/v1/owners/me/saved-drivers', headers=oh, json={'driver_reference': 'USR-0000000000000000'}).status_code == 404
    # Driver asks the Owner by the Owner's reference; the Owner accepts
    assert client.post('/api/v1/drivers/me/owner-links', headers=dh, json={'owner_reference': 'USR-0000000000000000'}).status_code == 404
    asked = client.post('/api/v1/drivers/me/owner-links', headers=dh, json={'owner_reference': first['my_reference']})
    assert asked.status_code == 201 and asked.json()['status'] == 'DRIVER_REQUESTED', asked.text
    waiting = client.get('/api/v1/owners/me/saved-drivers', headers=oh).json()['items']
    assert len(waiting) == 1 and waiting[0]['status'] == 'DRIVER_REQUESTED'
    assert any('asked to join' in n['title'] for n in client.get('/api/v1/notifications', headers=oh).json()['items'])
    # the Driver cannot accept their own request
    assert client.post(f"/api/v1/owners/me/saved-drivers/{waiting[0]['id']}/accept", headers=dh, json={}).status_code in (403, 404)   # the Driver cannot accept their own request
    ok = client.post(f"/api/v1/owners/me/saved-drivers/{waiting[0]['id']}/accept", headers=oh, json={})
    assert ok.status_code == 200 and ok.json()['status'] == 'ACTIVE'
    assert client.get('/api/v1/owners/me/saved-drivers', headers=oh).json()['items'][0]['status'] == 'ACTIVE'
    mine = client.get('/api/v1/drivers/me/owner-links', headers=dh).json()['items']
    assert len(mine) == 1 and mine[0]['status'] == 'ACTIVE'
    # the Owner removes the link; it can be re-made by an invitation the Driver accepts
    assert client.request('DELETE', f"/api/v1/owners/me/saved-drivers/{waiting[0]['id']}", headers=oh, json={}).status_code == 200
    invited = client.post('/api/v1/owners/me/saved-drivers', headers=oh, json={'driver_reference': driver['public_user_reference'], 'nickname': 'Kumar'})
    assert invited.status_code == 201 and invited.json()['status'] == 'OWNER_INVITED'
    link = client.get('/api/v1/drivers/me/owner-links', headers=dh).json()['items'][0]
    assert link['status'] == 'OWNER_INVITED'
    assert client.post(f"/api/v1/drivers/me/owner-links/{link['id']}/decline", headers=dh, json={}).json()['status'] == 'DECLINED'
    assert client.get('/api/v1/owners/me/saved-drivers', headers=oh).json()['items'] == []     # declined links are not listed
    assert client.get('/api/v1/owners/me/saved-drivers', headers=bearer(c.passenger)).status_code in (403, 404)


def test_driver_finds_an_owner_by_name_or_full_plate_unless_the_owner_hides(client, hire_setup):
    c = hire_setup
    driver, dt = external_driver(client, c)
    oh, dh = bearer(c.owner), bearer(dt)
    mine = client.get('/api/v1/owners/me/saved-drivers', headers=oh).json()
    assert mine['findable'] is True
    me = client.get('/api/v1/users/me', headers=oh).json()
    first = me['full_name'][:4]
    assert client.get('/api/v1/drivers/me/owner-search?q=ab', headers=dh).status_code == 422          # too short
    named = client.get(f'/api/v1/drivers/me/owner-search?q={first}', headers=dh)
    assert named.status_code == 200, named.text
    by_name = named.json()['items']
    assert any(i['reference'] == mine['my_reference'] for i in by_name)
    assert all(set(i) == {'reference', 'name', 'vehicles', 'link_status', 'link_id'} for i in by_name)   # no phone, email or plate
    by_ref = client.get(f"/api/v1/drivers/me/owner-search?q={mine['my_reference']}", headers=dh).json()['items']
    assert [i['reference'] for i in by_ref] == [mine['my_reference']]
    with client.app.state.sessions() as db:
        plate = str(db.get(Vehicle, c.vehicle_id).registration_number)
    exact = client.get(f'/api/v1/drivers/me/owner-search?q={plate}', headers=dh).json()['items']
    assert any(i['reference'] == mine['my_reference'] for i in exact)
    assert not any(plate in str(i) for i in exact)                                                    # the plate itself is never shown
    # the Owner hides from search: name no longer finds them, the reference still does
    assert client.put('/api/v1/owners/me/findable', headers=oh, json={'findable': False}).json() == {'findable': False}
    assert not any(i['reference'] == mine['my_reference'] for i in client.get(f'/api/v1/drivers/me/owner-search?q={first}', headers=dh).json()['items'])
    assert len(client.get(f"/api/v1/drivers/me/owner-search?q={mine['my_reference']}", headers=dh).json()['items']) == 1
    assert client.get(f'/api/v1/drivers/me/owner-search?q={first}', headers=bearer(c.passenger)).status_code in (403, 404)   # only a Driver searches
