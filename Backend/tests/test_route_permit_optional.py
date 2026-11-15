"""Project-owner decision (9 Nov 2026): a route permit is optional, system-checked and never Admin-reviewed."""
from datetime import date,timedelta
from uuid import UUID
from app.models.review_models import Vehicle
from app.services.hire_services import vehicle_evidence
from test_vehicles import actors,call,submitted,image_bytes  # noqa: F401  (fixture reuse)


def decide(client,a,row,conditions):
    return call(client,a,'admin','patch',f"/admin/vehicles/{row['id']}/review",{'expected_version':row['version'],'decision':'APPROVED',
        'category':'TEST_CAR','conditional_documents':conditions,'authorisation_required':False})


def permit(client,a,row,**fields):
    data={'owner_type':'VEHICLE','owner_id':row['id'],'document_type':'ROUTE_PERMIT',**fields}
    return call(client,a,'owner','post','/documents',data=data,files={'file':('permit.png',image_bytes(),'image/png')})


def test_admin_is_not_asked_about_route_permit_and_it_is_never_required(client,actors):
    a=actors;row=submitted(client,a)
    response=decide(client,a,row,{'EMISSION':False,'FITNESS':False})
    assert response.status_code==200,response.text
    with client.app.state.sessions() as db:
        assert db.get(Vehicle,UUID(row['id'])).verified_eligibility['conditional_documents']=={'EMISSION':False,'FITNESS':False,'ROUTE_PERMIT':False}
    detail=call(client,a,'owner','get','/owners/me/vehicles/'+row['id']).json()
    assert next(c for c in detail['checklist'] if c['type']=='ROUTE_PERMIT')['requirement'].startswith('Optional')
    assert detail['route_permit']=={'uploaded':False,'current':False,'expiry_date':None}


def test_old_client_cannot_make_route_permit_required(client,actors):
    a=actors;row=submitted(client,a)
    response=decide(client,a,row,{'EMISSION':False,'FITNESS':False,'ROUTE_PERMIT':True})
    assert response.status_code==200,response.text
    with client.app.state.sessions() as db:
        assert db.get(Vehicle,UUID(row['id'])).verified_eligibility['conditional_documents']['ROUTE_PERMIT'] is False


def test_emission_still_needs_an_admin_answer(client,actors):
    a=actors;row=submitted(client,a)
    assert decide(client,a,row,{'FITNESS':True}).status_code==422


def test_fitness_certificate_is_optional_and_never_required(client,actors):
    a=actors;row=submitted(client,a)
    assert decide(client,a,row,{'EMISSION':False,'FITNESS':True}).status_code==200
    with client.app.state.sessions() as db:
        assert db.get(Vehicle,UUID(row['id'])).verified_eligibility['conditional_documents']['FITNESS'] is False
    detail=call(client,a,'owner','get','/owners/me/vehicles/'+row['id']).json()
    assert next(c for c in detail['checklist'] if c['type']=='FITNESS')['requirement'].startswith('Optional')


def test_vehicle_reviewed_before_the_rule_does_not_need_a_permit(client,actors):
    a=actors;row=submitted(client,a)
    assert decide(client,a,row,{'EMISSION':False,'FITNESS':False}).status_code==200
    with client.app.state.sessions() as db:
        vehicle=db.get(Vehicle,UUID(row['id']))
        vehicle.verified_eligibility={**vehicle.verified_eligibility,'conditional_documents':{'EMISSION':False,'FITNESS':False,'ROUTE_PERMIT':True}}
        db.commit();db.refresh(vehicle)
        assert vehicle_evidence(db,vehicle)  # no ROUTE_PERMIT document, still eligible


def test_route_permit_details_are_checked_by_the_system(client,actors):
    a=actors;row=submitted(client,a);future=(date.today()+timedelta(days=200)).isoformat()
    missing=permit(client,a,row)
    assert missing.status_code==422 and missing.json()['code']=='ROUTE_PERMIT_DETAILS_INVALID'
    assert {f['field'] for f in missing.json()['field_errors']}=={'number','expiry_date','vehicle_number'}
    expired=permit(client,a,row,number='RP-1',expiry_date=(date.today()-timedelta(days=1)).isoformat(),vehicle_number=row['registration_number'])
    assert expired.status_code==422 and expired.json()['field_errors'][0]['field']=='expiry_date'
    wrong=permit(client,a,row,number='RP-1',expiry_date=future,vehicle_number='WP-ZZ-0000')
    assert wrong.status_code==422 and wrong.json()['field_errors'][0]['field']=='vehicle_number'
    spaced=row['registration_number'].lower().replace('-',' ')
    ok=permit(client,a,row,number='RP-1',expiry_date=future,vehicle_number=spaced)
    assert ok.status_code==201,ok.text
    doc=ok.json();assert doc['status']=='SUBMITTED'
    detail=call(client,a,'owner','get','/owners/me/vehicles/'+row['id']).json()
    assert detail['route_permit']=={'uploaded':True,'current':True,'expiry_date':future}
    # No Admin review: the decision is refused and the Admin queue leaves it out.
    refused=call(client,a,'admin','patch',f"/admin/documents/{doc['id']}/review",{'version':doc['version'],'decision':'UNDER_REVIEW','reason':None})
    assert refused.status_code==409 and refused.json()['code']=='ROUTE_PERMIT_SYSTEM_CHECKED'
    queue=call(client,a,'admin','get','/documents?status=SUBMITTED&page_size=100').json()['items']
    assert doc['id'] not in {d['id'] for d in queue}


def test_vehicle_number_is_only_for_route_permits(client,actors):
    a=actors;row=submitted(client,a)
    response=call(client,a,'owner','post','/documents',data={'owner_type':'VEHICLE','owner_id':row['id'],'document_type':'INSURANCE','vehicle_number':'X'},
        files={'file':('i.png',image_bytes(),'image/png')})
    assert response.status_code==422
