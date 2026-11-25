"""Call buttons: numbers are given only to the people on a live booking, and only while it is live."""
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
from conftest import bearer, signed_in
from sqlalchemy import func, select
from app.models.hire_models import Booking, Notification
from test_ticket_holds import api, person
from test_hire_pricing import hire_setup  # noqa: F401  (a fixture)
from test_rates import rate_owner  # noqa: F401  (fixture used by hire_setup)
from test_private_hire_payments import completed  # noqa: F401  (a fixture)
from test_trip_operations import running  # noqa: F401  (fixture used by completed)


def contacts(client, tokens, booking_id):
    return client.get(f'/api/v1/bookings/{booking_id}/contacts', headers=bearer(tokens))


def starts_in(client, booking_id, hours):
    with client.app.state.sessions() as db:
        db.get(Booking, UUID(booking_id)).start_at = datetime.now(timezone.utc) + timedelta(hours=hours)
        db.commit()


def stranger(client):
    person = {'full_name': 'Some Stranger', 'email': f'{uuid4().hex}@example.com', 'password': 'TravellyStrong1!', 'preferred_language': 'en',
              'phone_e164': '+9477' + str(uuid4().int % 10000000).zfill(7), 'accept_terms': True}
    return signed_in(client, person)[1]


def test_the_people_on_a_live_booking_get_each_others_numbers_and_nobody_else(client, hire_setup):
    from test_hire_pricing import committed
    c = hire_setup
    booking = committed(client, c)
    starts_in(client, booking['id'], 1)
    seen = contacts(client, c.passenger, booking['id'])
    assert seen.status_code == 200, seen.text
    body = seen.json()
    assert body['allowed'] is True and len(body['contacts']) == 1
    assert body['contacts'][0]['role'] in ('DRIVER', 'OWNER') and body['contacts'][0]['phone'].startswith('+')
    owner_view = contacts(client, c.owner, booking['id']).json()
    assert owner_view['allowed'] is True and any(x['role'] == 'PASSENGER' for x in owner_view['contacts'])
    passenger_entry = next(x for x in owner_view['contacts'] if x['role'] == 'PASSENGER')
    assert ' ' not in passenger_entry['name']   # first name only
    assert contacts(client, stranger(client), booking['id']).status_code == 404


def test_numbers_are_gone_when_the_trip_is_finished(client, completed):
    c, booking = completed.ctx, completed.booking
    for tokens in (c.passenger, c.owner):
        done = contacts(client, tokens, booking['id'])
        assert done.status_code == 200 and done.json() == {'allowed': False, 'contacts': [], 'chat': False, 'opens_at': None}


def test_numbers_show_only_inside_the_admin_window_and_the_admin_can_change_it(client, hire_setup):
    from test_hire_pricing import committed
    c = hire_setup
    booking = committed(client, c)
    starts_in(client, booking['id'], 5)
    early = contacts(client, c.passenger, booking['id']).json()
    assert early['allowed'] is False and early['contacts'] == [] and early['chat'] is True and early['opens_at']   # default window is 2 hours
    starts_in(client, booking['id'], 1.5)
    assert contacts(client, c.passenger, booking['id']).json()['allowed'] is True
    admin = person(client, 'ADMIN')
    rows = api(client, admin, 'get', '/admin/contact-settings').json()
    row = next(r for r in rows['items'] if r['id'] == str(c.service_id))
    assert row['contact_hours_before'] == 2 and rows['max_hours'] == 168
    starts_in(client, booking['id'], 5)
    saved = api(client, admin, 'patch', f"/admin/service-types/{row['id']}/contact-window", {'expected_version': row['version'], 'hours': 6})
    assert saved.status_code == 200 and saved.json()['contact_hours_before'] == 6
    assert contacts(client, c.passenger, booking['id']).json()['allowed'] is True
    stale = api(client, admin, 'patch', f"/admin/service-types/{row['id']}/contact-window", {'expected_version': row['version'], 'hours': 3})
    assert stale.status_code == 409
    assert api(client, admin, 'patch', f"/admin/service-types/{row['id']}/contact-window", {'expected_version': saved.json()['version'], 'hours': 999}).status_code == 422
    assert client.patch(f"/api/v1/admin/service-types/{row['id']}/contact-window", headers=bearer(c.passenger), json={'expected_version': 1, 'hours': 1}).status_code in (401, 403)


def test_the_people_on_a_confirmed_booking_can_chat_and_nobody_else_can_read_it(client, hire_setup):
    from test_hire_pricing import committed
    c = hire_setup
    booking = committed(client, c)
    path = f"/api/v1/bookings/{booking['id']}/messages"
    sent = client.post(path, headers=bearer(c.passenger), json={'body': '  Please wait at the main gate  '})
    assert sent.status_code == 201 and sent.json()['body'] == 'Please wait at the main gate' and sent.json()['mine'] is True
    client.post(path, headers=bearer(c.passenger), json={'body': 'Thank you'})
    seen = client.get(path, headers=bearer(c.owner)).json()
    assert [m['body'] for m in seen['items']] == ['Please wait at the main gate', 'Thank you'] and seen['can_write'] is True
    assert all(m['mine'] is False and m['role'] == 'PASSENGER' and ' ' not in m['name'] for m in seen['items'])
    with client.app.state.sessions() as db:   # two messages, one unread notice for the other person on the booking
        assert db.scalar(select(func.count(Notification.id)).where(Notification.booking_id == UUID(booking['id']), Notification.notification_type == 'CHAT')) == 1
    assert client.post(path, headers=bearer(c.owner), json={'body': 'x' * 501}).status_code == 422
    assert client.post(path, headers=bearer(c.owner), json={'body': '   '}).status_code == 422
    reply = client.post(path, headers=bearer(c.owner), json={'body': 'On my way'})
    assert reply.status_code == 201 and reply.json()['role'] in ('OWNER', 'DRIVER')
    stranger_tokens = stranger(client)
    assert client.get(path, headers=bearer(stranger_tokens)).status_code == 404
    assert client.post(path, headers=bearer(stranger_tokens), json={'body': 'hi'}).status_code == 404


def test_the_chat_is_read_only_after_the_trip(client, completed):
    c, booking = completed.ctx, completed.booking
    path = f"/api/v1/bookings/{booking['id']}/messages"
    assert client.post(path, headers=bearer(c.passenger), json={'body': 'late hello'}).json()['code'] == 'CHAT_CLOSED'
    assert client.get(path, headers=bearer(c.passenger)).json()['can_write'] is False
