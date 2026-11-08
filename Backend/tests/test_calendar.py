from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from threading import Barrier
from uuid import UUID, uuid4
import pytest
from sqlalchemy import select, func, event
from sqlalchemy.exc import OperationalError
from app.services.availability import no_vehicle_conflict
from app.core.errors import ApiError
from app.models.hire_models import Booking, Trip, VehicleRecord, Notification, Route, ScheduledTrip
from app.models.review_models import Vehicle
from app.models import UserRole
from conftest import bearer
from test_rates import rate_owner
from test_hire_pricing import hire_setup, accept, committed, external_driver


def path(c): return f'/api/v1/vehicles/{c.vehicle_id}/availability-blocks'


def body(c, **kw):
    start = datetime.fromisoformat(c.itinerary()['start_at'])
    return {'kind': 'PERSONAL', 'start_at': start.isoformat(), 'end_at': (start+timedelta(hours=3)).isoformat(), 'reason': 'Owner personal use', **kw}


def calendar(client, c, tokens=None):
    b = body(c)
    return client.get(f'/api/v1/vehicles/{c.vehicle_id}/calendar', params={k: b[k] for k in ('start_at','end_at')}, headers=bearer(tokens or c.owner))


def block(client, c, **kw):
    result = client.post(path(c), json=body(c, **kw), headers=bearer(c.owner))
    assert result.status_code == 201, result.text
    return result.json()


def test_calendar_create_edit_withdraw_keeps_other_restrictions_and_audit(client, hire_setup):
    c=hire_setup
    first=block(client,c);second=block(client,c,kind='MAINTENANCE',reason='Scheduled repair')
    with client.app.state.sessions() as db:
        vehicle=db.get(Vehicle,c.vehicle_id);assert vehicle.availability_status=='ACTIVE' and vehicle.is_published
        with pytest.raises(ApiError):no_vehicle_conflict(db,c.vehicle_id,datetime.fromisoformat(first['start_at']),datetime.fromisoformat(first['end_at']))
    changed=client.patch(path(c)+'/'+first['id'],headers=bearer(c.owner),json={**body(c,reason='Changed plans'),'expected_version':1})
    assert changed.status_code==200 and changed.json()['version']==2
    stale=client.post(path(c)+'/'+first['id']+'/withdraw',headers=bearer(c.owner),json={'expected_version':1,'reason':'No longer needed'})
    assert stale.status_code==409 and stale.json()['code']=='VERSION_CONFLICT'
    for row,version in [(first,2),(second,1)]:
        r=client.post(path(c)+'/'+row['id']+'/withdraw',headers=bearer(c.owner),json={'expected_version':version,'reason':'Plans resolved'})
        assert r.status_code==200 and r.json()['withdrawn']
        if row==first:
            assert any(e['restricts'] for e in calendar(client,c).json()['events'])
    result=calendar(client,c).json();assert result['complete'] and len(result['events'])==2 and not any(e['restricts'] for e in result['events'])
    with client.app.state.sessions() as db:
        no_vehicle_conflict(db,c.vehicle_id,datetime.fromisoformat(first['start_at']),datetime.fromisoformat(first['end_at']))
        assert db.scalar(select(func.count()).select_from(VehicleRecord))==2
    events=client.app.state.audit.records()[0]
    writes=[e for e in events if e.get('outcome')=='committed' and e.get('target',{}).get('resource')=='vehicle_records']
    assert len(writes)==5
    evidence=writes[2]['previous_decision_evidence']
    assert evidence['before']['reason']=='Owner personal use' and evidence['after']['reason']=='Changed plans'
    assert writes[-1]['full_reason']=='Plans resolved' and writes[-1]['previous_decision_evidence']['after']['withdrawn']


@pytest.mark.parametrize('offset,duration,conflict',[(-3,3,False),(3,1,False),(-1,2,True),(2,2,True),(-1,5,True),(1,1,True)])
def test_half_open_boundaries_and_enclosing_intervals(client,hire_setup,offset,duration,conflict):
    c=hire_setup;b=block(client,c);start=datetime.fromisoformat(b['start_at'])+timedelta(hours=offset)
    with client.app.state.sessions() as db:
        if conflict:
            with pytest.raises(ApiError):no_vehicle_conflict(db,c.vehicle_id,start,start+timedelta(hours=duration))
        else:no_vehicle_conflict(db,c.vehicle_id,start,start+timedelta(hours=duration))


@pytest.mark.parametrize('change',[{'end_at':'2020-01-01T00:00:00Z'},{'start_at':'2030-01-01T00:00:00'}, {'reason':'  '},{'kind':'REPAIR'},{'expected_version':True},{'owner_user_id':str(uuid4())}])
def test_block_validation(client,hire_setup,change):
    assert client.post(path(hire_setup),headers=bearer(hire_setup.owner),json=body(hire_setup,**change)).status_code==422


def test_authorization_legacy_and_current_role(client,hire_setup):
    c=hire_setup;b=block(client,c)
    assert calendar(client,c,c.passenger).status_code==403
    with client.app.state.sessions() as db:
        owner=db.get(Vehicle,c.vehicle_id).owner_user_id
        db.add(UserRole(user_id=UUID(c.passenger_id),role_code='OWNER',approval_status='APPROVED',approved_by=owner,approved_at=func.now()));db.commit()
    assert calendar(client,c,c.passenger).status_code==404
    assert client.post(path(c)+'/'+b['id']+'/withdraw',headers=bearer(c.passenger),json={'expected_version':1,'reason':'Alien'}).status_code==404
    with client.app.state.sessions() as db:
        row=db.get(VehicleRecord,UUID(b['id']));row.approval_status=None;db.commit()
    result=calendar(client,c).json()['events'][0];assert result['restricts'] and not result['editable']
    assert client.patch(path(c)+'/'+b['id'],headers=bearer(c.owner),json={**body(c),'expected_version':1}).json()['code']=='BLOCK_CLASSIFICATION_REQUIRED'
    with client.app.state.sessions() as db:
        role=db.scalar(select(UserRole).where(UserRole.user_id==owner,UserRole.role_code=='OWNER'));role.approval_status='SUSPENDED';role.suspended_at=func.now();role.suspension_reason='Test current role';db.commit()
    assert calendar(client,c).status_code==403


def test_emergency_preserves_booking_price_and_reservation_and_notifies_admin(client,hire_setup):
    c=hire_setup;driver,dt=external_driver(client,c);b=accept(client,c,c.create())
    b=client.post(f"/api/v1/bookings/{b['id']}/driver-assignments",headers=bearer(c.owner),json={'expected_version':b['version'],'driver_reference':driver['public_user_reference']}).json()
    assert b['status']=='AWAITING_DRIVER'
    with client.app.state.sessions() as db:
        owner=db.get(Vehicle,c.vehicle_id).owner_user_id
        db.add(UserRole(user_id=UUID(c.passenger_id),role_code='ADMIN',approval_status='APPROVED',approved_by=owner,approved_at=func.now()));db.commit()
    ordinary=client.post(path(c),json=body(c),headers=bearer(c.owner))
    assert ordinary.status_code==409 and ordinary.json()['code']=='VEHICLE_COMMITMENTS_REQUIRE_RESOLUTION'
    emergency=block(client,c,kind='EMERGENCY',reason='Unsafe to operate; repair required')
    assert emergency['affected_commitments'][0]['id']==b['id']
    detail=client.get(f"/api/v1/bookings/{b['id']}",headers=bearer(dt)).json()
    assert client.post(f"/api/v1/trips/{detail['trip']['id']}/assignment-accept",headers=bearer(dt),json={'expected_version':detail['trip']['version']}).status_code==409
    declined=client.post(f"/api/v1/trips/{detail['trip']['id']}/assignment-decline",headers=bearer(dt),json={'expected_version':detail['trip']['version']})
    assert declined.status_code==200 and declined.json()['vehicle_committed']
    r=client.post(path(c)+'/'+emergency['id']+'/withdraw',headers=bearer(c.owner),json={'expected_version':1,'reason':'Repair completed'})
    assert r.status_code==200
    with client.app.state.sessions() as db:
        booking=db.get(Booking,UUID(b['id']));assert booking.status=='OWNER_ACTION_REQUIRED' and booking.vehicle_committed and booking.price_snapshot==b['price']
        notice=db.scalar(select(Notification).where(Notification.notification_type=='ADMIN_ACTION'))
        assert notice.action_payload['block_id']==emergency['id']
        with pytest.raises(ApiError):no_vehicle_conflict(db,c.vehicle_id,booking.start_at,booking.end_at)
    assert client.post(path(c),json=body(c),headers=bearer(c.owner)).status_code==409


def test_search_quote_fallback_and_commitment_observe_blocks(client,hire_setup,monkeypatch):
    c=hire_setup;b=accept(client,c,c.create());block(client,c)
    search={'service_type_id':str(c.service_id),'itinerary':c.itinerary(),'passenger_count':2,'large_luggage_count':1,'small_luggage_count':1}
    assert client.post('/api/v1/search/vehicles',json=search).json()['items']==[]
    result=client.post(f"/api/v1/bookings/{b['id']}/self-drive",headers=bearer(c.owner),json={'expected_version':b['version']})
    assert result.status_code==409 and result.json()['code']=='VEHICLE_SCHEDULE_CONFLICT'
    def outage(*args):raise ApiError(503,'ROUTING_NOT_CONFIGURED','Unavailable')
    monkeypatch.setattr(client.app.state.hire_routing,'measure',outage)
    result=client.post('/api/v1/bookings/private-hires',headers=bearer(c.passenger),json={**search,'vehicle_id':str(c.vehicle_id),'idempotency_key':uuid4().hex})
    assert result.status_code==409


def test_missing_source_is_explicit_and_blocks_reads_writes_search_and_commit(client,hire_setup):
    c=hire_setup;b=accept(client,c,c.create())
    def fail(conn,cursor,statement,parameters,context,executemany):
        if 'UNION ALL' in statement and 'scheduled_trips' in statement:
            raise OperationalError('unavailable occupancy source',{},Exception('test outage'))
    event.listen(client.app.state.engine,'before_cursor_execute',fail)
    try:
        responses=[calendar(client,c),client.post(path(c),headers=bearer(c.owner),json=body(c)),
            client.post(f"/api/v1/bookings/{b['id']}/self-drive",headers=bearer(c.owner),json={'expected_version':b['version']}),
            client.post('/api/v1/search/vehicles',json={'service_type_id':str(c.service_id),'itinerary':c.itinerary(),'passenger_count':2,'large_luggage_count':0,'small_luggage_count':0})]
        assert all(r.status_code==503 and r.json()['code']=='AVAILABILITY_INCOMPLETE' for r in responses),[(r.status_code,r.text) for r in responses]
    finally:event.remove(client.app.state.engine,'before_cursor_execute',fail)
    assert calendar(client,c).json()['events']==[]


def test_concurrent_block_and_commitment_cannot_both_win(client,hire_setup):
    c=hire_setup;b=accept(client,c,c.create());gate=Barrier(2)
    def write_block():
        gate.wait();return client.post(path(c),headers=bearer(c.owner),json=body(c))
    def commit():
        gate.wait();return client.post(f"/api/v1/bookings/{b['id']}/self-drive",headers=bearer(c.owner),json={'expected_version':b['version']})
    with ThreadPoolExecutor(max_workers=2) as pool:
        a=pool.submit(write_block);d=pool.submit(commit);responses=[a.result(timeout=30),d.result(timeout=30)]
    assert sorted(r.status_code for r in responses) in ([200,409],[201,409]),[r.text for r in responses]


def test_concurrent_edits_have_one_winner_and_audit_failure_rolls_back(client,hire_setup,monkeypatch):
    c=hire_setup;b=block(client,c);gate=Barrier(2)
    def edit(reason):
        gate.wait();return client.patch(path(c)+'/'+b['id'],headers=bearer(c.owner),json={**body(c,reason=reason),'expected_version':1})
    with ThreadPoolExecutor(max_workers=2) as pool:
        a=pool.submit(edit,'First');d=pool.submit(edit,'Second');responses=[a.result(timeout=30),d.result(timeout=30)]
    assert sorted(r.status_code for r in responses)==[200,409]
    def fail(*args):raise OSError('Test durable writer outage')
    monkeypatch.setattr(client.app.state.audit,'append',fail)
    response=client.post(path(c)+'/'+b['id']+'/withdraw',headers=bearer(c.owner),json={'expected_version':2,'reason':'Withdraw'})
    assert response.status_code==503
    with client.app.state.sessions() as db:
        row=db.get(VehicleRecord,UUID(b['id']));assert row.version==2 and row.approval_status=='PERSONAL'


def test_departure_and_independent_accepted_trip_remain_after_withdrawal(client,hire_setup):
    c=hire_setup;start=datetime.fromisoformat(body(c)['start_at']);end=start+timedelta(hours=3)
    with client.app.state.sessions() as db:
        owner=db.get(Vehicle,c.vehicle_id).owner_user_id
        route=Route(route_code=uuid4().hex,route_name='Test route',origin_name='A',destination_name='B');db.add(route);db.flush()
        departure=ScheduledTrip(departure_reference='DEP-'+uuid4().hex[:16],owner_user_id=owner,service_type_id=c.service_id,route_id=route.id,
            original_vehicle_id=c.vehicle_id,current_vehicle_id=c.vehicle_id,departure_at=start,estimated_arrival_at=end,
            booking_cutoff_at=start,fare_per_seat=100,currency='LKR',fulfilment_policy='FIXED_GUARANTEED',status='DISRUPTED')
        db.add(departure);db.flush()
        trip=Trip(trip_reference='TRP-'+uuid4().hex[:16],scheduled_trip_id=departure.id,vehicle_id=c.vehicle_id,operating_owner_user_id=owner,
            driver_user_id=owner,assignment_status='ACCEPTED',status='ASSISTANCE_REQUIRED',scheduled_start_at=start,scheduled_end_at=end)
        db.add(trip);db.commit();did=departure.id;tid=trip.id
    assert client.post(path(c),headers=bearer(c.owner),json=body(c)).status_code==409
    b=block(client,c,kind='EMERGENCY');assert {e['source'] for e in b['affected_commitments']}=={'DEPARTURE','TRIP'}
    assert client.post(path(c)+'/'+b['id']+'/withdraw',headers=bearer(c.owner),json={'expected_version':1,'reason':'Repair done'}).status_code==200
    events=calendar(client,c).json()['events'];assert {e['source'] for e in events if e['restricts']}=={'DEPARTURE','TRIP'}
    with client.app.state.sessions() as db:
        assert db.get(ScheduledTrip,did).status=='DISRUPTED' and db.get(Trip,tid).status=='ASSISTANCE_REQUIRED'


def test_emergency_blocks_start_without_cancelling_and_admin_can_inspect(client,hire_setup):
    c=hire_setup;b=committed(client,c);now=datetime.now(timezone.utc)
    with client.app.state.sessions() as db:
        booking=db.get(Booking,UUID(b['id']));booking.start_at=now-timedelta(minutes=10);booking.end_at=now+timedelta(hours=2)
        trip=db.scalar(select(Trip).where(Trip.booking_id==booking.id));trip.scheduled_start_at=booking.start_at;trip.scheduled_end_at=booking.end_at
        tid=trip.id;version=trip.version
        db.add(UserRole(user_id=UUID(c.passenger_id),role_code='ADMIN',approval_status='APPROVED',approved_at=func.now()));db.commit()
    block(client,c,kind='EMERGENCY',start_at=(now-timedelta(minutes=1)).isoformat(),end_at=(now+timedelta(hours=1)).isoformat())
    result=client.post(f'/api/v1/trips/{tid}/start',headers=bearer(c.owner),json={'expected_version':version,'start_odometer_km':'1000','checklist_confirmed':True})
    assert result.status_code==409 and result.json()['code']=='VEHICLE_SCHEDULE_CONFLICT'
    admin_path=f'/api/v1/admin/vehicles/{c.vehicle_id}/calendar'
    params={'start_at':(now-timedelta(days=1)).isoformat(),'end_at':(now+timedelta(days=1)).isoformat()}
    result=client.get(admin_path,params=params,headers=bearer(c.passenger))
    assert result.status_code==200 and not any(e['editable'] for e in result.json()['events'])
    assert any(e.get('affected_commitments') for e in result.json()['events'])
    assert client.get(admin_path,params=params,headers=bearer(c.owner)).status_code==403
    notices=client.get('/api/v1/notifications',headers=bearer(c.passenger)).json()['items']
    assert any(n['support_vehicle_id']==str(c.vehicle_id) for n in notices)
    with client.app.state.sessions() as db:
        assert db.get(Booking,UUID(b['id'])).status=='CONFIRMED' and db.get(Trip,tid).status=='READY'


def test_edit_rechecks_protected_commitments_and_timezone_equivalence(client,hire_setup):
    c=hire_setup;b=committed(client,c);start=datetime.fromisoformat(b['end_at'])
    later=block(client,c,start_at=start.isoformat(),end_at=(start+timedelta(hours=2)).isoformat())
    rejected=client.patch(path(c)+'/'+later['id'],headers=bearer(c.owner),json={**body(c),'expected_version':1})
    assert rejected.status_code==409
    offset=timezone(timedelta(hours=5,minutes=30))
    result=client.get(f'/api/v1/vehicles/{c.vehicle_id}/calendar',headers=bearer(c.owner),params={'start_at':start.astimezone(offset).isoformat(),'end_at':(start+timedelta(hours=2)).astimezone(offset).isoformat()})
    assert result.status_code==200 and [e['id'] for e in result.json()['events']]==[later['id']]
    with client.app.state.sessions() as db:assert db.get(VehicleRecord,UUID(later['id'])).version==1


def test_concurrent_owner_commitments_have_one_winner(client,hire_setup):
    c=hire_setup;bookings=[accept(client,c,c.create()),accept(client,c,c.create())];gate=Barrier(2)
    def commit(b):
        gate.wait();return client.post(f"/api/v1/bookings/{b['id']}/self-drive",headers=bearer(c.owner),json={'expected_version':b['version']})
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses=list(pool.map(commit,bookings))
    assert sorted(r.status_code for r in responses)==[200,409]


def test_ended_reservation_cannot_start_past_a_current_emergency(client,hire_setup):
    c=hire_setup;b=committed(client,c);now=datetime.now(timezone.utc)
    with client.app.state.sessions() as db:
        booking=db.get(Booking,UUID(b['id']));booking.start_at=now-timedelta(hours=3);booking.end_at=now-timedelta(hours=1)
        trip=db.scalar(select(Trip).where(Trip.booking_id==booking.id));trip.scheduled_start_at=booking.start_at;trip.scheduled_end_at=booking.end_at
        tid=trip.id;version=trip.version;db.commit()
    block(client,c,kind='EMERGENCY',start_at=(now-timedelta(minutes=1)).isoformat(),end_at=(now+timedelta(hours=1)).isoformat())
    response=client.post(f'/api/v1/trips/{tid}/start',headers=bearer(c.owner),json={'expected_version':version,'start_odometer_km':'1000','checklist_confirmed':True})
    assert response.status_code==409 and response.json()['code']=='TRIP_NOT_READY'
    with client.app.state.sessions() as db:
        assert db.get(Trip,tid).status=='READY' and db.get(Booking,UUID(b['id'])).vehicle_committed


def test_owner_can_correct_and_withdraw_historical_block_without_affecting_today(client,hire_setup):
    c=hire_setup;start=datetime.now(timezone.utc)-timedelta(days=3)
    payload=body(c,start_at=start.isoformat(),end_at=(start+timedelta(hours=1)).isoformat())
    result=client.post(path(c),headers=bearer(c.owner),json=payload)
    assert result.status_code==201,result.text
    bid=result.json()['id']
    edited=client.patch(path(c)+'/'+bid,headers=bearer(c.owner),json={**payload,'expected_version':1,'reason':'Corrected historical reason'})
    assert edited.status_code==200
    withdrawn=client.post(path(c)+'/'+bid+'/withdraw',headers=bearer(c.owner),json={'expected_version':2,'reason':'Recorded on wrong date'})
    assert withdrawn.status_code==200 and withdrawn.json()['withdrawn']
    with client.app.state.sessions() as db:
        no_vehicle_conflict(db,c.vehicle_id,datetime.now(timezone.utc),datetime.now(timezone.utc)+timedelta(hours=1))
