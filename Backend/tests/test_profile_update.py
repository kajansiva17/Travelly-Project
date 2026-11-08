import base64
import io
from datetime import datetime, timezone
from PIL import Image
from sqlalchemy import select
from app.models import User, UserRole
from test_admin_review import review_case


def current(client, headers):
    return client.get('/api/v1/users/me', headers=headers).json()


def payload(user, **changes):
    return {key:user[key] for key in ('version','full_name','phone_e164','profile_image_url')} | changes


def picture():
    output=io.BytesIO()
    Image.new('RGB',(500,300),'red').save(output,'PNG')
    return 'data:image/png;base64,'+base64.b64encode(output.getvalue()).decode()


def test_admin_updates_own_profile_without_changing_security_or_roles(client, review_case):
    headers=review_case['admin']
    before=current(client,headers)
    with client.app.state.sessions() as db:
        user=db.get(User,review_case['admin_id'])
        user.email_verified_at=datetime.now(timezone.utc)
        db.commit()
        security=(user.password_hash,user.auth_version,user.account_status,user.external_auth_subject)
        memberships=[(r.id,r.role_code,r.approval_status,r.version) for r in db.scalars(select(UserRole).where(UserRole.user_id==user.id)).all()]
    response=client.patch('/api/v1/users/me',headers=headers,json=payload(before,full_name=' Updated Admin ',phone_e164='+94771234567',profile_image_url=picture()))
    assert response.status_code==200,response.text
    saved=response.json()
    assert saved['id']==before['id'] and saved['full_name']=='Updated Admin'
    assert saved['approved_roles']==before['approved_roles'] and saved['email']==before['email']
    assert saved['phone_e164']=='+94771234567' and saved['phone_verified_at'] is None
    assert saved['version']==before['version']+1
    with Image.open(io.BytesIO(base64.b64decode(saved['profile_image_url'].split(',')[1]))) as image:
        assert image.format=='JPEG' and max(image.size)<=256 and not image.getexif()
    assert current(client,headers)['full_name']=='Updated Admin'
    with client.app.state.sessions() as db:
        user=db.get(User,review_case['admin_id'])
        assert (user.password_hash,user.auth_version,user.account_status,user.external_auth_subject)==security
        assert memberships==[(r.id,r.role_code,r.approval_status,r.version) for r in db.scalars(select(UserRole).where(UserRole.user_id==user.id)).all()]
    removed=client.patch('/api/v1/users/me',headers=headers,json=payload(saved,profile_image_url=None))
    assert removed.status_code==200 and removed.json()['profile_image_url'] is None


def test_profile_rejects_stale_privilege_contact_and_image_mutations(client,review_case):
    headers=review_case['admin'];before=current(client,headers)
    assert client.patch('/api/v1/users/me',json=payload(before)).status_code==401
    assert client.patch('/api/v1/users/me',headers=review_case['owner'],json=payload(before)).status_code==403
    for changes,status in [({'approved_roles':['ADMIN']},422),({'email':'other@example.com'},422),({'version':before['version']+1},409),({'full_name':'   '},422),({'phone_e164':'0771234567'},422),({'profile_image_url':'https://example.com/private.jpg'},422),({'profile_image_url':'data:image/png;base64,aGVsbG8='},422),({'profile_image_url':'data:image/svg+xml;base64,PHN2Zy8+'},422),({'phone_e164':review_case['person']['phone_e164']},409)]:
        response=client.patch('/api/v1/users/me',headers=headers,json=payload(before,**changes))
        assert response.status_code==status,(changes.keys(),response.text)
        assert current(client,headers)==before


def test_changed_phone_does_not_inherit_verified_status(client,review_case):
    headers=review_case['admin']
    with client.app.state.sessions() as db:
        user=db.get(User,review_case['admin_id'])
        user.phone_e164='+94771234567';user.phone_verified_at=datetime.now(timezone.utc);user.account_status='ACTIVE'
        db.commit()
    before=current(client,headers)
    blocked=client.patch('/api/v1/users/me',headers=headers,json=payload(before,phone_e164='+94771234568'))
    assert blocked.status_code==409 and blocked.json()['code']=='EMAIL_VERIFICATION_REQUIRED'
    assert current(client,headers)['phone_verified_at']==before['phone_verified_at']
    with client.app.state.sessions() as db:
        user=db.get(User,review_case['admin_id']);user.email_verified_at=datetime.now(timezone.utc);db.commit()
    changed=client.patch('/api/v1/users/me',headers=headers,json=payload(before,phone_e164='+94771234568'))
    assert changed.status_code==200 and changed.json()['phone_verified_at'] is None
