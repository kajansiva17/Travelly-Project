"""My drivers cards: the photo, whether the Driver is online, and whether they are on a trip."""
from uuid import UUID
from sqlalchemy import update
from app.models import User
from app.models.hire_models import OwnerDriver
from test_ticket_holds import api, person


def test_the_my_drivers_list_carries_the_photo_and_the_live_state(client):
    owner, driver = person(client, 'OWNER'), person(client, 'DRIVER')
    with client.app.state.sessions() as db:
        db.execute(update(User).where(User.id == UUID(driver['id'])).values(profile_image_url='https://example.com/face.jpg'))
        db.add(OwnerDriver(owner_user_id=UUID(owner['id']), driver_user_id=UUID(driver['id']), status='ACTIVE', initiated_by='OWNER'))
        db.commit()
    got = api(client, owner, 'get', '/owners/me/saved-drivers')
    assert got.status_code == 200, got.text
    item = got.json()['items'][0]
    assert item['profile_image_url'] == 'https://example.com/face.jpg'
    assert item['online'] is False and item['on_trip'] is False and item['is_driver'] is True
