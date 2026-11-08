from test_admin_review import review_case, upload, doc_review, verified, role_review


def detail(client, case, role='DRIVER'):
    return client.get('/api/v1/admin/role-requests/'+case['roles'][role]['id'],headers=case['admin']).json()


def test_readiness_tracks_same_application_through_document_review_and_approval(client,review_case):
    c=review_case;role=c['roles']['DRIVER']
    initial=detail(client,c)
    assert initial['approval_readiness']['ready'] is False
    assert all(item['message']=='Not submitted by the applicant.' for item in initial['approval_readiness']['requirements'])
    identity=upload(client,c).json()
    licence=upload(client,c,'DRIVING_LICENCE',issuing_country='LK',expiry_date='2030-12-31').json()
    for doc in [identity,licence]:
        assert detail(client,c)['approval_readiness']['ready'] is False
        pending=doc_review(client,c,doc,'UNDER_REVIEW')
        doc_review(client,c,pending,'APPROVED')
    ready=detail(client,c)
    assert ready['application']['id']==role['id'] and ready['approval_readiness']['ready'] is True
    assert role_review(client,c,role,'APPROVED').status_code==200
    assert client.get('/api/v1/users/me',headers=c['owner']).json()['approved_roles']==['DRIVER','PASSENGER']
    assert detail(client,c)['application']['id']==role['id']
    assert client.post('/api/v1/users/me/role-requests',headers=c['owner'],json={'role_code':'DRIVER'}).status_code==409
    assert client.get('/api/v1/admin/role-requests/'+role['id'],headers=c['owner']).status_code==403


def test_readiness_does_not_waive_current_licence_or_owner_evidence(client,review_case):
    c=review_case
    verified(client,c,'NIC')
    upload(client,c,'DRIVING_LICENCE',issuing_country='GB',expiry_date='2030-12-31')
    assert detail(client,c)['approval_readiness']['ready'] is False
    assert role_review(client,c,c['roles']['DRIVER'],'APPROVED').status_code==409
    upload(client,c,'DRIVING_LICENCE',issuing_country='LK',expiry_date='2020-01-01')
    assert detail(client,c)['approval_readiness']['ready'] is False
    assert detail(client,c,'OWNER')['approval_readiness']['ready'] is False
    verified(client,c,'OWNER_AUTHORISATION')
    assert detail(client,c,'OWNER')['approval_readiness']['ready'] is True


def test_owner_submitted_reviewed_approval_and_current_session_access(client, review_case, passenger):
    from uuid import UUID
    from app.models import UserRole
    c = review_case
    role = c['roles']['OWNER']
    assert client.get('/api/v1/owners/me/vehicles', headers=c['owner']).status_code == 403
    documents = [upload(client, c, kind).json() for kind in ('NIC', 'VEHICLE_REGISTRATION')]
    for doc in documents:
        readiness = detail(client, c, 'OWNER')['approval_readiness']
        assert readiness['ready'] is False
        assert any('SUBMITTED' in item['message'] and 'Start review' in item['message'] for item in readiness['requirements'])
        assert role_review(client, c, role, 'APPROVED').json()['code'] == 'REQUIRED_EVIDENCE_NOT_VERIFIED'
        # No direct SUBMITTED -> APPROVED bypass.
        assert client.patch('/api/v1/admin/documents/'+doc['id']+'/review', headers=c['admin'], json={'decision':'APPROVED','version':doc['version']}).status_code == 409
        pending = doc_review(client, c, doc, 'UNDER_REVIEW')
        assert any('UNDER_REVIEW' in item['message'] for item in detail(client,c,'OWNER')['approval_readiness']['requirements'])
        doc_review(client, c, pending, 'APPROVED')
    assert detail(client,c,'OWNER')['approval_readiness']['ready'] is True
    approved = role_review(client, c, role, 'APPROVED')
    assert approved.status_code == 200 and approved.json()['id'] == role['id']
    with client.app.state.sessions() as db:
        saved = db.get(UserRole, UUID(role['id']))
        assert saved.approval_status == 'APPROVED' and saved.approved_by == c['admin_id']
    assert client.get('/api/v1/users/me',headers=c['owner']).json()['approved_roles'] == ['OWNER','PASSENGER']
    assert client.get('/api/v1/owners/me/vehicles', headers=c['owner']).status_code == 200
    login = client.post('/api/v1/auth/login', json={'identifier':passenger['email'],'password':passenger['password']}).json()
    refreshed = client.post('/api/v1/auth/refresh',json={'refresh_token':login['refresh_token']})
    assert refreshed.status_code == 200
    assert client.get('/api/v1/owners/me/vehicles', headers={'Authorization':'Bearer '+refreshed.json()['access_token']}).status_code == 200
    assert client.post('/api/v1/users/me/role-requests', headers=c['owner'],json={'role_code':'OWNER'}).status_code == 409


def test_owner_rejection_needs_reason_and_does_not_grant_access(client, review_case):
    c = review_case; role = c['roles']['OWNER']
    assert role_review(client,c,role,'REJECTED').status_code == 422
    assert role_review(client,c,role,'REJECTED','Ownership evidence is unreadable.').status_code == 200
    roles = client.get('/api/v1/users/me/roles',headers=c['owner']).json()['items']
    owner = next(item for item in roles if item['role_code']=='OWNER')
    assert owner['id'] == role['id'] and owner['rejection_reason'] == 'Ownership evidence is unreadable.'
    assert client.get('/api/v1/owners/me/vehicles',headers=c['owner']).status_code == 403


def test_readiness_explains_invalid_metadata_and_correction():
    from types import SimpleNamespace
    from datetime import date
    from uuid import uuid4
    from app.api.routers.review_api import evidence_review_guidance
    applicant, reviewer = uuid4(), uuid4()
    base = dict(id=uuid4(), document_type='PASSPORT',status='APPROVED',verified_by=reviewer,verified_at=True,expiry_date=date(2030,1,1),issue_date=None,issuing_country='LK')
    row = SimpleNamespace(user_id=applicant)
    for changes, message in [({'expiry_date':date(2020,1,1)},'expired'),({'expiry_date':None},'expiry date is missing'),({'issue_date':date(2031,1,1)},'in the future'),({'verified_by':applicant},'independent verification is missing'),({'status':'NEEDS_CORRECTION'},'corrected evidence'),({'document_type':'DRIVING_LICENCE','issuing_country':'GB'},'Sri Lanka-issued')]:
        result = evidence_review_guidance(SimpleNamespace(**(base | changes)),row,date(2026,11,6))
        assert message in result['message']
        assert set(result) == {'document_id','status','message'}


import pytest


@pytest.mark.parametrize('role_code,other', [('OWNER','VEHICLE_REGISTRATION'),('DRIVER','DRIVING_LICENCE')])
def test_own_status_is_fresh_safe_and_distinguishes_documents_from_role(client, review_case, role_code, other):
    c = review_case; url = '/api/v1/users/me/role-requests/'+role_code+'/status'
    assert client.get(url).status_code == 401
    # Another authenticated account gets its own status, never this applicant's.
    assert client.get(url,headers=c['admin']).json()['application'] is None
    response = client.get(url,headers=c['owner'])
    assert response.headers['cache-control'] == 'no-store'
    first = response.json()
    assert first['application']['approval_status'] == 'PENDING'
    assert all('Missing evidence' in item['message'] for item in first['approval_readiness']['requirements'])
    metadata = {'issuing_country':'LK','expiry_date':'2030-12-31'} if other == 'DRIVING_LICENCE' else {}
    verified(client,c,'NIC'); verified(client,c,other,**metadata)
    pending = client.get(url,headers=c['owner']).json()
    assert pending['application']['approval_status'] == 'PENDING'
    assert pending['approval_readiness']['ready'] is True
    assert all('final role decision is still awaiting' in item['message'] for item in pending['approval_readiness']['requirements'])
    assert role_review(client,c,c['roles'][role_code],'APPROVED').status_code == 200
    approved = client.get(url,headers=c['owner']).json()
    assert approved['application']['id'] == c['roles'][role_code]['id']
    assert approved['application']['approval_status'] == 'APPROVED'
    assert approved['approval_readiness'] is None
    assert role_code in client.get('/api/v1/users/me',headers=c['owner']).json()['approved_roles']
    forbidden = {'verified_by','approved_by','updated_by','storage_key','file_checksum','email','phone_e164'}
    assert not forbidden.intersection(approved['application'])


def test_own_pending_status_explains_real_metadata_blockers(client, review_case):
    c = review_case
    upload(client,c,'NIC',issue_date='2035-01-01')
    upload(client,c,'DRIVING_LICENCE',issuing_country='GB',expiry_date='2020-01-01')
    result = client.get('/api/v1/users/me/role-requests/DRIVER/status',headers=c['owner']).json()
    text = ' '.join(item['message'] for item in result['approval_readiness']['requirements'])
    assert 'in the future' in text and 'has expired' in text and 'Sri Lanka-issued' in text
    assert 'Awaiting Super Admin document verification' in text
    assert not result['approval_readiness']['ready']
    assert 'documents' not in result['approval_readiness']['requirements'][0]
    assert client.get('/api/v1/users/me/role-requests/ADMIN/status',headers=c['owner']).status_code == 422


@pytest.mark.parametrize('code,other', [('OWNER','VEHICLE_REGISTRATION'),('DRIVER','DRIVING_LICENCE')])
def test_rejected_replacement_resubmission_new_review_preserves_audit_and_activates_same_role(client, review_case, code, other):
    from sqlalchemy import select,func
    from uuid import UUID
    from app.models import UserRole
    c=review_case; original=c['roles'][code]
    identity=verified(client,c,'NIC')
    old=upload(client,c,other,**({'issuing_country':'LK','expiry_date':'2030-12-31'} if code=='DRIVER' else {})).json()
    reviewing=doc_review(client,c,old,'UNDER_REVIEW')
    rejected_doc=doc_review(client,c,reviewing,'REJECTED','Evidence is unreadable.')
    rejected=role_review(client,c,original,'REJECTED','Correct and resubmit the evidence.').json()
    replacements=[upload(client,c,'NIC').json(),upload(client,c,other,**({'issuing_country':'LK','expiry_date':'2030-12-31'} if code=='DRIVER' else {})).json()]
    assert replacements[0]['superseded_document_id']==identity['id']
    assert replacements[1]['superseded_document_id']==old['id']
    assert all(doc['status']=='SUBMITTED' and doc['verified_at'] is None for doc in replacements)
    response=client.post('/api/v1/users/me/role-requests',headers=c['owner'],json={'role_code':code})
    assert response.status_code==201
    latest=response.json()
    assert latest['id']==original['id'] and latest['approval_status']=='PENDING'
    assert latest['version']==rejected['version']+1 and latest['rejection_reason'] is None
    assert latest['requested_at']>=rejected['requested_at']
    for stale in (original,rejected):
        assert role_review(client,c,stale,'APPROVED').json()['code']=='VERSION_CONFLICT'
    detail_response=detail(client,c,code)
    assert {d['id'] for d in detail_response['documents']}=={d['id'] for d in replacements}
    blocked=role_review(client,c,latest,'APPROVED')
    assert blocked.status_code==409 and 'SUBMITTED' in blocked.json()['message']
    for doc in replacements:
        assert not detail(client,c,code)['approval_readiness']['ready']
        doc_review(client,c,doc_review(client,c,doc,'UNDER_REVIEW'),'APPROVED')
    assert detail(client,c,code)['approval_readiness']['ready']
    approved=role_review(client,c,latest,'APPROVED')
    assert approved.status_code==200 and approved.json()['id']==original['id']
    assert code in client.get('/api/v1/users/me',headers=c['owner']).json()['approved_roles']
    assert client.get('/api/v1/users/me/role-requests/'+code+'/status',headers=c['owner']).json()['application']['approval_status']=='APPROVED'
    assert client.get('/api/v1/documents/'+old['id'],headers=c['owner']).json()['rejection_reason']==rejected_doc['rejection_reason']
    assert client.get('/api/v1/documents/'+old['id']+'/file',headers=c['owner']).status_code==200
    with client.app.state.sessions() as db:
        assert db.scalar(select(func.count()).select_from(UserRole).where(UserRole.user_id==UUID(c['person']['id']),UserRole.role_code==code))==1
        assert db.get(UserRole,UUID(original['id'])).approved_by==c['admin_id']
    records,_,_=client.app.state.audit.records()
    events=[r for r in records if r.get('target',{}).get('id')==original['id'] and r.get('outcome')=='committed']
    assert any(r.get('previous_status')=='PENDING' and r.get('new_status')=='REJECTED' and r.get('full_reason')=='Correct and resubmit the evidence.' for r in events)
    assert any(r.get('previous_status')=='REJECTED' and r.get('new_status')=='PENDING' and r.get('previous_decision_evidence',{}).get('rejection_reason')=='Correct and resubmit the evidence.' for r in events)
