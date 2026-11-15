"""Actual isolated PostgreSQL/Redis, evidence/normalized photos and durable review."""
from io import BytesIO
from copy import deepcopy
from datetime import datetime,timedelta,timezone
from uuid import UUID,uuid4
import pytest
from PIL import Image,PngImagePlugin
from sqlalchemy import select,func
from app.models import UserRole
from app.models.review_models import Vehicle,Document
from app.models.rate_models import ServiceType,VehicleService
from app.models.hire_models import Booking
from app.core.errors import ApiError
from conftest import signed_in,bearer

FACTS={'vehicle_type_code':'CAR','make':'Test Make','model':'Test Model','manufacture_year':2020,'colour':'White',
    'power_type':'ICE','engine_fuel_type':'PETROL','seat_capacity':4,'large_luggage_capacity':1,'small_luggage_capacity':2,'registered_owner_case':'SELF'}


def image_bytes():
    stream=BytesIO();info=PngImagePlugin.PngInfo();info.add_text('GPSLocation','PRIVATE-TEST-LOCATION')
    Image.new('RGB',(640,400),(170,80,60)).save(stream,format='PNG',pnginfo=info)
    return stream.getvalue()


@pytest.fixture
def actors(client):
    result={}
    for name,role in [('owner','OWNER'),('admin','ADMIN'),('other','OWNER'),('passenger',None)]:
        user,tokens=signed_in(client,{'full_name':'Test '+name,'email':uuid4().hex+'@example.com','phone_e164':'+9477'+str(uuid4().int%10000000).zfill(7),'password':'TravellyStrong1!','accept_terms':True})
        if role:
            with client.app.state.sessions() as db:db.add(UserRole(user_id=UUID(user['id']),role_code=role,approval_status='APPROVED',approved_by=UUID(user['id']),approved_at=func.now()));db.commit()
        result[name]={'id':user['id'],'tokens':tokens}
    return result


def call(client,actors,role,method,path,body=None,**kw):
    return getattr(client,method)('/api/v1'+path,headers=bearer(actors[role]['tokens']),**({'json':body} if body is not None else {}),**kw)


def draft(client,a,case='SELF',kind='CAR'):
    response=call(client,a,'owner','post','/vehicles',{'registration_number':'TEST-'+uuid4().hex[:10]})
    assert response.status_code==201,response.text
    row=response.json()
    response=call(client,a,'owner','patch','/vehicles/'+row['id'],{'expected_version':row['version'],**FACTS,'registered_owner_case':case,'vehicle_type_code':kind})
    assert response.status_code==200,response.text
    return response.json()


def upload_evidence(client,a,row,kind,approve=True):
    result=call(client,a,'owner','post','/documents',data={'owner_type':'VEHICLE','owner_id':row['id'],'document_type':kind},files={'file':('test.png',image_bytes(),'image/png')})
    assert result.status_code==201,result.text
    doc=result.json()
    if approve:
        for decision in ('UNDER_REVIEW','APPROVED'):
            result=call(client,a,'admin','patch',f"/admin/documents/{doc['id']}/review",{'version':doc['version'],'decision':decision,'reason':None})
            assert result.status_code==200,result.text
            doc=result.json()
    return doc


def submitted(client,a,case='SELF',kind='CAR'):
    row=draft(client,a,case,kind)
    for t in ['VEHICLE_REGISTRATION','INSURANCE','REVENUE_LICENCE']+(['OWNER_AUTHORISATION'] if case!='SELF' else []):upload_evidence(client,a,row,t)
    response=call(client,a,'owner','post',f"/vehicles/{row['id']}/submit",{'expected_version':row['version']})
    assert response.status_code==200,response.text
    return response.json()


def approve(client,a,row):
    response=call(client,a,'admin','patch',f"/admin/vehicles/{row['id']}/review",{'expected_version':row['version'],'decision':'APPROVED','category':'TEST_CAR',
        'conditional_documents':{'EMISSION':False,'FITNESS':False,'ROUTE_PERMIT':False},'authorisation_required':row['registered_owner_case']!='SELF'})
    assert response.status_code==200,response.text
    return response.json()


def photo(client,a,row,category='EXTERIOR',moderate=True):
    result=call(client,a,'owner','post',f"/vehicles/{row['id']}/photos",data={'expected_version':str(row['version']),'category':category},files={'file':('test.png',image_bytes(),'image/png')})
    assert result.status_code==201,result.text
    row=result.json();pid=row['photos'][-1]['id']
    if moderate:
        result=call(client,a,'admin','patch',f"/admin/vehicles/{row['id']}/photos/{pid}/review",{'expected_version':row['version'],'decision':'APPROVED','privacy_confirmed':True,'genuine_vehicle_confirmed':True})
        assert result.status_code==200,result.text
        row=result.json()
    return row,pid


def test_draft_authorization_unique_registration_and_private_feedback_projection(client,actors):
    a=actors
    assert call(client,a,'passenger','post','/vehicles',{'registration_number':'TEST-ACL'}).status_code==403
    created=call(client,a,'owner','post','/vehicles',{'registration_number':'  TEST-ACL  '})
    assert created.status_code==201,created.text
    row=created.json();assert row['make'] is None and row['verification_status']=='DRAFT'
    assert call(client,a,'other','post','/vehicles',{'registration_number':'test-acl'}).status_code==409
    assert call(client,a,'other','get','/owners/me/vehicles/'+row['id']).status_code==404
    own=call(client,a,'owner','get','/owners/me/vehicles/'+row['id']);assert own.status_code==200,own.text
    assert own.json()['registration_locked'] is False and own.json()['latest_decision'] is None
    assert client.get('/api/v1/vehicles/'+row['id']).status_code in (403,404,409)
    assert call(client,a,'owner','post',f"/vehicles/{row['id']}/submit",{'expected_version':row['version']}).status_code==422
    assert call(client,a,'owner','patch','/vehicles/'+row['id'],{'expected_version':1,'seat_capacity':-1}).status_code==422
    assert call(client,a,'owner','patch','/vehicles/'+row['id'],{'expected_version':1,'vehicle_type_code':'AIRCRAFT'}).status_code==422


@pytest.mark.parametrize('kind',['CAR','VAN','BUS','THREE_WHEELER'])
def test_initial_vehicle_types_require_factual_capacity_and_submission_evidence(client,actors,kind):
    row=draft(client,actors,kind=kind)
    missing=call(client,actors,'owner','post',f"/vehicles/{row['id']}/submit",{'expected_version':row['version']})
    assert missing.status_code==422 and missing.json()['code']=='VEHICLE_EVIDENCE_REQUIRED'
    edited=call(client,actors,'owner','patch',f"/vehicles/{row['id']}",{'expected_version':row['version'],'description':'Ordinary description'})
    assert edited.status_code==200
    assert call(client,actors,'owner','patch',f"/vehicles/{row['id']}",{'expected_version':row['version'],'colour':'Blue'}).status_code==409


@pytest.mark.parametrize('case',['SELF','OTHER_PERSON','COMPANY'])
def test_owner_cases_registration_always_required_and_authorization_is_additional(client,actors,case):
    a=actors;row=submitted(client,a,case)
    detail=call(client,a,'owner','get','/owners/me/vehicles/'+row['id']).json()
    assert detail['registration_locked'] is True
    assert next(c for c in detail['checklist'] if c['type']=='VEHICLE_REGISTRATION')['requirement']=='Required'
    if case!='SELF':
        response=call(client,a,'admin','patch',f"/admin/vehicles/{row['id']}/review",{'expected_version':row['version'],'category':'TEST_CAR','conditional_documents':{'EMISSION':False,'FITNESS':False,'ROUTE_PERMIT':False},'authorisation_required':False})
        assert response.status_code==422
    row=approve(client,a,row);assert row['verification_status']=='APPROVED' and not row['published']


def test_rejection_correction_resubmission_feedback_registration_lock_and_suspension(client,actors):
    a=actors;row=submitted(client,a)
    rejected=call(client,a,'admin','patch',f"/admin/vehicles/{row['id']}/review",{'expected_version':row['version'],'decision':'REJECTED','reason':'Correct the factual passenger capacity.'})
    assert rejected.status_code==200,rejected.text
    row=rejected.json();detail=call(client,a,'owner','get','/owners/me/vehicles/'+row['id']).json()
    assert detail['latest_decision']['reason']=='Correct the factual passenger capacity.' and set(detail['latest_decision'])=={'decision','reason','decided_at'}
    corrected=call(client,a,'owner','patch','/vehicles/'+row['id'],{'expected_version':row['version'],'seat_capacity':5})
    assert corrected.status_code==200 and corrected.json()['verification_status']=='DRAFT'
    row=corrected.json()
    locked=call(client,a,'owner','patch','/vehicles/'+row['id'],{'expected_version':row['version'],'registration_number':'OTHER-PLATE'})
    assert locked.status_code==409 and locked.json()['code']=='REGISTRATION_LOCKED'
    resub=call(client,a,'owner','post',f"/vehicles/{row['id']}/submit",{'expected_version':row['version']});assert resub.status_code==200,resub.text
    row=approve(client,a,resub.json())
    suspended=call(client,a,'admin','patch',f"/admin/vehicles/{row['id']}/review",{'expected_version':row['version'],'decision':'SUSPENDED','reason':'Material evidence mismatch; support must resolve commitments.'})
    assert suspended.status_code==200
    row=suspended.json()
    assert call(client,a,'owner','patch','/vehicles/'+row['id'],{'expected_version':row['version'],'description':'Cannot reinstate'}).status_code==409
    assert call(client,a,'owner','post',f"/vehicles/{row['id']}/submit",{'expected_version':row['version']}).status_code==409


def priced(client,row):
    """Publication needs a price, so give this vehicle one active private-hire rate."""
    with client.app.state.sessions() as db:
        service=ServiceType(code=uuid4().hex,name='Test publish scope',category='PRIVATE_HIRE',is_active=True,
            default_pricing_basis='DISTANCE',settings={'pricing_scope':'LONG_DISTANCE'});db.add(service);db.flush()
        db.add(VehicleService(vehicle_id=UUID(row['id']),service_type_id=service.id,is_enabled=True,currency='LKR',pricing_basis='DISTANCE',
            owner_terms={'rate_rules':[{'id':str(uuid4()),'name':'Test rate'}]}))
        db.commit()
    return row


def test_normalized_photo_moderation_publication_privacy_and_revocation(client,actors):
    a=actors;row=approve(client,a,submitted(client,a))
    assert call(client,a,'owner','patch',f"/vehicles/{row['id']}/publish",{'expected_version':row['version'],'published':True}).status_code==409
    row,pid=photo(client,a,row,moderate=False);url=row['photos'][0]['variants'][0]['url']
    assert client.get(url).status_code in (403,404,409)
    own=call(client,a,'owner','get',url.removeprefix('/api/v1'));assert own.status_code==200,own.text
    with Image.open(BytesIO(own.content)) as image:assert image.format=='JPEG' and not image.getexif() and 'GPSLocation' not in image.info
    assert call(client,a,'other','get',url.removeprefix('/api/v1')).status_code in (403,404,409)
    bad=call(client,a,'admin','patch',f"/admin/vehicles/{row['id']}/photos/{pid}/review",{'expected_version':row['version'],'decision':'APPROVED'})
    assert bad.status_code==422
    result=call(client,a,'admin','patch',f"/admin/vehicles/{row['id']}/photos/{pid}/review",{'expected_version':row['version'],'decision':'APPROVED','privacy_confirmed':True,'genuine_vehicle_confirmed':True});assert result.status_code==200,result.text
    row=result.json();priced(client,row);published=call(client,a,'owner','patch',f"/vehicles/{row['id']}/publish",{'expected_version':row['version'],'published':True});assert published.status_code==200,published.text
    public=client.get('/api/v1/vehicles/'+row['id']);assert public.status_code==200,public.text
    assert not {'registration_number','documents','owner_name_private','verified_eligibility','default_driver_user_id'}&public.json().keys()
    assert 'storage_key' not in public.text and 'GPSLocation' not in public.text and client.get(url).status_code==200
    v=published.json()['version'];removed=call(client,a,'admin','patch',f"/admin/vehicles/{row['id']}/photos/{pid}/review",{'expected_version':v,'decision':'REMOVED','reason':'Misleading photo; upload a corrected exterior.'})
    assert removed.status_code==200 and not removed.json()['published']
    assert client.get(url).status_code==404
    assert removed.json()['verification_status']=='APPROVED'


def test_material_edits_and_retirement_guard_accepted_commitments_without_repricing(client,actors):
    a=actors;row=approve(client,a,submitted(client,a));uid=UUID(a['owner']['id'])
    with client.app.state.sessions() as db:
        service=ServiceType(code=uuid4().hex,name='Test scope',category='PRIVATE_HIRE',is_active=True,default_pricing_basis='OWNER_QUOTE',settings={'pricing_scope':'LONG_DISTANCE'});db.add(service);db.flush()
        booking=Booking(booking_reference='BKG-'+uuid4().hex[:20],passenger_user_id=UUID(a['passenger']['id']),owner_user_id=uid,vehicle_id=UUID(row['id']),service_type_id=service.id,
            booking_type='PRIVATE_HIRE',assurance_type='STANDARD_HIRE',start_at=datetime.now(timezone.utc)+timedelta(days=1),end_at=datetime.now(timezone.utc)+timedelta(days=1,hours=3),passenger_count=2,
            currency='LKR',status='CONFIRMED',vehicle_committed=True,total_amount=2500,price_snapshot={'initial':{'total':'2500.00'},'current':{'total':'2500.00'}})
        db.add(booking);db.commit();bid=booking.id
    ordinary=call(client,a,'owner','patch','/vehicles/'+row['id'],{'expected_version':row['version'],'description':'Updated valid description'});assert ordinary.status_code==200,ordinary.text
    row=ordinary.json();assert row['verification_status']=='APPROVED'
    assert call(client,a,'owner','patch','/vehicles/'+row['id'],{'expected_version':row['version'],'seat_capacity':3}).status_code==409
    assert call(client,a,'owner','patch',f"/vehicles/{row['id']}/availability",{'expected_version':row['version'],'availability_status':'INACTIVE'}).status_code==409
    with client.app.state.sessions() as db:
        booking=db.get(Booking,bid);assert str(booking.total_amount)=='2500.00' and booking.status=='CONFIRMED'
        booking.start_at=datetime.now(timezone.utc)-timedelta(hours=4);booking.end_at=datetime.now(timezone.utc)-timedelta(hours=1);booking.status='IN_PROGRESS';db.commit()
    assert call(client,a,'owner','patch',f"/vehicles/{row['id']}/availability",{'expected_version':row['version'],'availability_status':'INACTIVE'}).status_code==409
    with client.app.state.sessions() as db:
        booking=db.get(Booking,bid)
        booking.status='CANCELLED';booking.vehicle_committed=False;db.commit()
    material=call(client,a,'owner','patch','/vehicles/'+row['id'],{'expected_version':row['version'],'seat_capacity':3})
    assert material.status_code==200 and material.json()['verification_status']=='DRAFT'


def test_admin_self_review_exclusion_correction_and_durable_failure(client,actors,monkeypatch):
    a=actors;row=submitted(client,a)
    with client.app.state.sessions() as db:db.add(UserRole(user_id=UUID(a['owner']['id']),role_code='ADMIN',approval_status='APPROVED',approved_at=func.now()));db.commit()
    assert call(client,a,'owner','get','/admin/vehicles').json()['total']==0
    assert call(client,a,'owner','get','/admin/vehicles/'+row['id']).status_code==403
    fixed=call(client,a,'admin','patch',f"/admin/vehicles/{row['id']}/registration",{'expected_version':row['version'],'registration_number':'TEST-CORRECTED','reason':'Correct a transcription error verified from registration.'})
    assert fixed.status_code==200 and fixed.json()['verification_status']=='DRAFT'
    row=fixed.json()
    def fail(*args,**kwargs):raise OSError('simulated durable flush failure')
    monkeypatch.setattr(client.app.state.audit,'append',fail)
    response=call(client,a,'owner','patch','/vehicles/'+row['id'],{'expected_version':row['version'],'description':'Must roll back'})
    assert response.status_code==503
    with client.app.state.sessions() as db:assert db.get(Vehicle,UUID(row['id'])).description is None


def test_document_correction_does_not_reject_vehicle_and_replacement_can_finish_review(client,actors):
    a=actors;row=draft(client,a);docs={t:upload_evidence(client,a,row,t,approve=False) for t in ('VEHICLE_REGISTRATION','INSURANCE','REVENUE_LICENCE')}
    result=call(client,a,'owner','post',f"/vehicles/{row['id']}/submit",{'expected_version':row['version']});assert result.status_code==200;row=result.json()
    doc=docs['INSURANCE']
    reviewed=call(client,a,'admin','patch',f"/admin/documents/{doc['id']}/review",{'version':doc['version'],'decision':'UNDER_REVIEW'});assert reviewed.status_code==200
    corrected=call(client,a,'admin','patch',f"/admin/documents/{doc['id']}/review",{'version':reviewed.json()['version'],'decision':'NEEDS_CORRECTION','reason':'Upload the complete insurance page.'});assert corrected.status_code==200
    assert call(client,a,'owner','get','/owners/me/vehicles/'+row['id']).json()['verification_status']=='SUBMITTED'
    replacement=upload_evidence(client,a,row,'INSURANCE')
    assert replacement['superseded_document_id']==doc['id']
    for t in ('VEHICLE_REGISTRATION','REVENUE_LICENCE'):
        d=docs[t]
        first=call(client,a,'admin','patch',f"/admin/documents/{d['id']}/review",{'version':d['version'],'decision':'UNDER_REVIEW'})
        assert call(client,a,'admin','patch',f"/admin/documents/{d['id']}/review",{'version':first.json()['version'],'decision':'APPROVED'}).status_code==200
    assert approve(client,a,row)['verification_status']=='APPROVED'


def test_preferred_driver_minimal_lookup_and_preference_never_assigns_a_trip(client,actors):
    from app.models.hire_models import Trip
    a=actors;row=approve(client,a,submitted(client,a));driver=call(client,a,'other','get','/users/me').json()
    with client.app.state.sessions() as db:
        uid=UUID(a['other']['id']);db.add(UserRole(user_id=uid,role_code='DRIVER',approval_status='APPROVED',approved_by=UUID(a['admin']['id']),approved_at=func.now()))
        licence=Document(user_id=uid,document_type='DRIVING_LICENCE',status='APPROVED',issuing_country='LK',expiry_date=(datetime.now(timezone.utc)+timedelta(days=30)).date(),
            verified_categories=['B'],submitted_at=func.now(),verified_at=func.now(),verified_by=UUID(a['admin']['id']),storage_key=uuid4().hex,original_file_name='test.png',mime_type='image/png',file_size_bytes=1,file_checksum='0'*64)
        svc=ServiceType(code=uuid4().hex,name='Test preference service',category='PRIVATE_HIRE',is_active=True,default_pricing_basis='DISTANCE',
            settings={'pricing_scope':'LONG_DISTANCE','licence_compatibility':{'TEST_CAR':['B']},'routing_profiles':{'TEST_CAR':'driving-car'}})
        db.add_all([licence,svc]);db.commit();sid=str(svc.id);lid=licence.id
    body={'vehicle_id':row['id'],'service_type_id':sid,'driver_reference':driver['public_user_reference']}
    lookup=call(client,a,'owner','post','/drivers/eligible-lookup',body);assert lookup.status_code==200,lookup.text
    assert set(lookup.json())=={'reference','display_name','eligible','message'}
    assert call(client,a,'other','post','/drivers/eligible-lookup',body).status_code==404
    selected=call(client,a,'owner','patch',f"/vehicles/{row['id']}/preferred-driver",{'expected_version':row['version'],'driver_reference':driver['public_user_reference'],'service_type_id':sid})
    assert selected.status_code==200 and selected.json()['preferred_driver_id']==a['other']['id']
    with client.app.state.sessions() as db:
        assert db.scalar(select(func.count()).select_from(Trip))==0
        d=db.get(Document,lid);d.expiry_date=(datetime.now(timezone.utc)-timedelta(days=1)).date();db.commit()
    assert call(client,a,'owner','post','/drivers/eligible-lookup',body).status_code==409
    cleared=call(client,a,'owner','patch',f"/vehicles/{row['id']}/preferred-driver",{'expected_version':selected.json()['version'],'driver_reference':None})
    assert cleared.status_code==200 and cleared.json()['preferred_driver_id'] is None


def test_invalid_photo_content_and_missing_review_applicability_fail_closed(client,actors):
    a=actors;row=draft(client,a)
    for name,mime,content in [('bad.png','image/png',b'not an image'),('file.pdf','application/pdf',b'%PDF-'),('../x.png','image/png',image_bytes())]:
        response=call(client,a,'owner','post',f"/vehicles/{row['id']}/photos",data={'category':'EXTERIOR','expected_version':str(row['version'])},files={'file':(name,content,mime)})
        assert response.status_code==422,response.text
    assert call(client,a,'owner','get','/owners/me/vehicles/'+row['id']).json()['photos']==[]
    invalid=call(client,a,'admin','patch',f"/admin/vehicles/{row['id']}/review",{'expected_version':row['version'],'category':'TEST_CAR','conditional_documents':{'FITNESS':False},'authorisation_required':False})
    assert invalid.status_code==422


def test_owner_list_pagination_retains_pricing_picker_defaults_and_private_facts_are_rejected(client,actors):
    a=actors;row=draft(client,a);second=draft(client,a)
    legacy=call(client,a,'owner','get','/owners/me/vehicles').json()
    assert len(legacy['items'])==2 and legacy['page_size']==100
    bounded=call(client,a,'owner','get','/owners/me/vehicles?page=1&page_size=1').json()
    assert len(bounded['items'])==1 and bounded['has_next']
    for value in ('contact@example.com','+94 77 123 4567',row['registration_number']):
        bad=call(client,a,'owner','patch','/vehicles/'+row['id'],{'expected_version':row['version'],'colour':value})
        assert bad.status_code==422 and bad.json()['code']=='PRIVATE_INFO_IN_VEHICLE_FACTS'


def test_publication_needs_a_price_so_a_listed_vehicle_always_shows_one(client,actors):
    a=actors;row=approve(client,a,submitted(client,a));row,pid=photo(client,a,row)
    refused=call(client,a,'owner','patch',f"/vehicles/{row['id']}/publish",{'expected_version':row['version'],'published':True})
    assert refused.status_code==409 and refused.json()['code']=='VEHICLE_PRICES_REQUIRED',refused.text
    priced(client,row)
    published=call(client,a,'owner','patch',f"/vehicles/{row['id']}/publish",{'expected_version':row['version'],'published':True})
    assert published.status_code==200,published.text
    assert published.json()['published']


def test_independent_description_moderation_preserves_verification_and_last_approved_text(client,actors):
    a=actors;row=approve(client,a,submitted(client,a));row,pid=photo(client,a,row);priced(client,row)
    published=call(client,a,'owner','patch',f"/vehicles/{row['id']}/publish",{'expected_version':row['version'],'published':True});assert published.status_code==200;row=published.json()
    first='A comfortable vehicle for this journey.'
    edited=call(client,a,'owner','patch','/vehicles/'+row['id'],{'expected_version':row['version'],'description':first});assert edited.status_code==200;row=edited.json()
    assert row['verification_status']=='APPROVED' and row['published'] and row['description_review']['status']=='PENDING'
    assert client.get('/api/v1/vehicles/'+row['id']).json()['description'] is None
    path=f"/admin/vehicles/{row['id']}/description/review"
    body={'expected_version':row['version'],'decision':'APPROVED','privacy_confirmed':True}
    assert call(client,a,'owner','patch',path,body).status_code==403
    assert call(client,a,'admin','patch',path,{**body,'privacy_confirmed':False}).status_code==422
    accepted=call(client,a,'admin','patch',path,body);assert accepted.status_code==200,accepted.text
    assert call(client,a,'admin','patch',path,body).status_code==409
    row=accepted.json();assert row['verification_status']=='APPROVED' and row['published']
    assert client.get('/api/v1/vehicles/'+row['id']).json()['description']==first
    edited=call(client,a,'owner','patch','/vehicles/'+row['id'],{'expected_version':row['version'],'description':'A newer unreviewed proposal.'});assert edited.status_code==200;row=edited.json()
    assert client.get('/api/v1/vehicles/'+row['id']).json()['description']==first
    rejected=call(client,a,'admin','patch',path,{'expected_version':row['version'],'decision':'REJECTED','reason':'Revise the proposal without private information.'});assert rejected.status_code==200;row=rejected.json()
    assert row['description_review']['reason']=='Revise the proposal without private information.'
    assert client.get('/api/v1/vehicles/'+row['id']).json()['description']==first
    removed=call(client,a,'admin','patch',path,{'expected_version':row['version'],'decision':'REMOVED','reason':'Withdraw the published content for correction.'});assert removed.status_code==200;row=removed.json()
    assert client.get('/api/v1/vehicles/'+row['id']).json()['description'] is None and row['verification_status']=='APPROVED'


def test_retirement_review_preserves_inactive_and_workflow_states_and_overdue_commitments(client,actors):
    a=actors;row=submitted(client,a)
    inactive=call(client,a,'owner','patch',f"/vehicles/{row['id']}/availability",{'expected_version':row['version'],'availability_status':'INACTIVE'})
    assert inactive.status_code==200,inactive.text
    row=approve(client,a,inactive.json());assert row['availability_status']=='INACTIVE'
    with client.app.state.sessions() as db:
        v=db.get(Vehicle,UUID(row['id']));v.availability_status='ON_TRIP';db.commit()
    response=call(client,a,'owner','patch',f"/vehicles/{row['id']}/availability",{'expected_version':row['version'],'availability_status':'ACTIVE'})
    assert response.status_code==409 and response.json()['code']=='AVAILABILITY_WORKFLOW_CONTROLLED'


def test_multibyte_description_audit_stays_bounded_and_withdrawal_is_immediate(client,actors):
    a=actors;row=draft(client,a);text='\u8eca'*2000
    changed=call(client,a,'owner','patch','/vehicles/'+row['id'],{'expected_version':row['version'],'description':text});assert changed.status_code==200,changed.text;row=changed.json()
    approved=call(client,a,'admin','patch',f"/admin/vehicles/{row['id']}/description/review",{'expected_version':row['version'],'decision':'APPROVED','privacy_confirmed':True})
    assert approved.status_code==200,approved.text;row=approved.json()
    cleared=call(client,a,'owner','patch','/vehicles/'+row['id'],{'expected_version':row['version'],'description':None})
    assert cleared.status_code==200 and cleared.json()['description_review']['approved_text'] is None
    assert call(client,a,'owner','get','/owners/me/vehicles/'+row['id']).status_code==200
    previous,_,_=client.app.state.audit.records()
    with client.app.state.audit.coordinated():
        with pytest.raises(ApiError):client.app.state.audit.append({'correlation_id':str(uuid4()),'outcome':'history_read','payload':'\u8eca'*30000})
        with pytest.raises(ApiError):client.app.state.audit.append({'correlation_id':str(uuid4()),'outcome':'intent','payload':'x'*64000})
    records,_,_=client.app.state.audit.records();assert len(records)==len(previous)
