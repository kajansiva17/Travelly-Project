from datetime import datetime,timezone
from uuid import UUID
import pytest
from sqlalchemy import select,func
from app.models import UserRole
from app.models.review_models import Document
from test_admin_review import review_case,upload,doc_review,verified,role_review


@pytest.mark.parametrize('metadata,field', [({'issuing_country':'LK'},'expiry_date'),({'issuing_country':'LK','expiry_date':'2020-01-01'},'expiry_date'),({'issuing_country':'GB','expiry_date':'2030-12-31'},'issuing_country'),({'issuing_country':'LK','issue_date':'2029-01-01','expiry_date':'2030-12-31'},'issue_date')])
def test_invalid_licence_cannot_be_approved(client,review_case,metadata,field):
 c=review_case
 doc=doc_review(client,c,upload(client,c,'DRIVING_LICENCE',**metadata).json(),'UNDER_REVIEW')
 result=client.patch('/api/v1/admin/documents/'+doc['id']+'/review',headers=c['admin'],json={'decision':'APPROVED','version':doc['version']})
 assert result.status_code==422
 assert result.json()['code']=='INVALID_DRIVING_LICENCE_EVIDENCE'
 assert field in [error['field'] for error in result.json()['field_errors']]
 saved=client.get('/api/v1/documents/'+doc['id'],headers=c['owner']).json()
 assert saved['status']=='UNDER_REVIEW' and saved['verified_at'] is None and saved['version']==doc['version']
 assert role_review(client,c,c['roles']['DRIVER'],'APPROVED').status_code==409


def test_legacy_approved_null_expiry_is_replaced_reverified_and_activates_same_driver(client,review_case,passenger):
 c=review_case;role=c['roles']['DRIVER']
 identity=verified(client,c,'NIC')
 verified(client,c,'VEHICLE_REGISTRATION')
 assert role_review(client,c,c['roles']['OWNER'],'APPROVED').status_code==200
 licence=verified(client,c,'DRIVING_LICENCE',issuing_country='LK',expiry_date='2030-12-31')
 # Historical fixture only: reproduce an already-approved record lacking expiry.
 with client.app.state.sessions() as db:
  db.get(Document,UUID(licence['id'])).expiry_date=None;db.commit()
 detail=client.get('/api/v1/admin/role-requests/'+role['id'],headers=c['admin']).json()
 assert not detail['approval_readiness']['ready']
 assert 'expiry date is missing' in detail['approval_readiness']['requirements'][1]['message']
 assert next(doc for doc in detail['documents'] if doc['document_type']=='DRIVING_LICENCE')['expiry_date'] is None
 assert role_review(client,c,role,'APPROVED').status_code==409
 replacement=upload(client,c,'DRIVING_LICENCE',issuing_country='LK',expiry_date='2031-12-31').json()
 assert replacement['superseded_document_id']==licence['id'] and replacement['verified_at'] is None
 assert client.get('/api/v1/documents/'+replacement['id'],headers=c['owner']).json()['expiry_date']=='2031-12-31'
 assert role_review(client,c,role,'APPROVED').status_code==409
 doc_review(client,c,doc_review(client,c,replacement,'UNDER_REVIEW'),'APPROVED')
 assert role_review(client,c,role,'APPROVED').status_code==200
 assert client.get('/api/v1/users/me/role-requests/DRIVER/status',headers=c['owner']).json()['application']['id']==role['id']
 assert client.get('/api/v1/users/me',headers=c['owner']).json()['approved_roles']==['DRIVER','OWNER','PASSENGER']
 assert client.get('/api/v1/documents/'+licence['id'],headers=c['owner']).json()['expiry_date'] is None
 assert client.get('/api/v1/documents/'+identity['id'],headers=c['owner']).json()['status']=='APPROVED'
 with client.app.state.sessions() as db:
  assert db.get(UserRole,UUID(role['id'])).approved_by==c['admin_id']
  assert db.scalar(select(func.count()).select_from(UserRole).where(UserRole.user_id==UUID(c['person']['id']),UserRole.role_code=='DRIVER'))==1
 login=client.post('/api/v1/auth/login',json={'identifier':passenger['email'],'password':passenger['password']}).json()
 refreshed=client.post('/api/v1/auth/refresh',json={'refresh_token':login['refresh_token']})
 assert refreshed.status_code==200
 assert 'DRIVER' in client.get('/api/v1/users/me',headers={'Authorization':'Bearer '+refreshed.json()['access_token']}).json()['approved_roles']
