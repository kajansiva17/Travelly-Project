"""Who arranges the passengers' journey after the Owner reports a problem: the Owner (another vehicle) or Travelly (the Admin)."""
from uuid import UUID
from sqlalchemy import select
from app.models.hire_models import Notification, Route, ScheduledTrip
from app.models.review_models import Vehicle
from test_ticket_holds import api, ticket  # noqa: F401  (ticket is a fixture the others build on)
from test_payments import held  # noqa: F401  (a fixture)
from test_refunds import paid  # noqa: F401  (a fixture)
from test_fulfilment import departure, other_owner_vehicle, answer


def report(client, t, arrangement=None):
    body = {'expected_version': departure(client, t).version, 'reason': 'The bus engine failed its inspection.'}
    if arrangement:
        body['arrangement'] = arrangement
    return api(client, t['owner'], 'post', f"/scheduled-trips/{t['trip']['id']}/problem", body)


def waiting_for_admin(client, t):
    items = api(client, t['admin'], 'get', '/admin/departures/attention').json()['items']
    return any(item['id'] == t['trip']['id'] for item in items)


def admin_notices(client, t):
    with client.app.state.sessions() as db:
        return db.scalars(select(Notification).where(Notification.recipient_user_id == UUID(t['admin']['id']),
                                                     Notification.notification_type == 'ADMIN_ACTION')
                          .order_by(Notification.created_at)).all()


def test_a_problem_the_owner_will_arrange_does_not_wait_for_the_admin(client, paid):
    done = report(client, paid, 'OWNER')
    assert done.status_code == 200, done.text
    assert done.json()['status'] == 'DISRUPTED' and done.json()['arrangement'] == 'OWNER'
    assert not waiting_for_admin(client, paid)
    told = [n for n in admin_notices(client, paid) if n.title == 'Owner cannot run a departure']
    assert told and 'no action is needed yet' in told[-1].body and told[-1].action_required is False


def test_asking_travelly_puts_the_departure_on_the_admin_list(client, paid):
    assert report(client, paid, 'OWNER').status_code == 200
    asked = api(client, paid['owner'], 'post', f"/scheduled-trips/{paid['trip']['id']}/ask-travelly",
                {'expected_version': departure(client, paid).version})
    assert asked.status_code == 200, asked.text
    assert asked.json()['arrangement'] == 'TRAVELLY' and waiting_for_admin(client, paid)
    told = [n for n in admin_notices(client, paid) if n.title == 'Owner asks Travelly to arrange a departure']
    assert told and told[-1].action_required is True


def test_a_problem_without_a_choice_still_goes_to_travelly(client, paid):
    done = report(client, paid)
    assert done.status_code == 200 and done.json()['arrangement'] == 'TRAVELLY'
    assert waiting_for_admin(client, paid)


def test_only_a_reported_problem_can_be_handed_to_travelly(client, paid):
    early = api(client, paid['owner'], 'post', f"/scheduled-trips/{paid['trip']['id']}/ask-travelly",
                {'expected_version': departure(client, paid).version})
    assert early.status_code == 409 and early.json()['code'] == 'DEPARTURE_NOT_DISRUPTED'
    assert api(client, paid['admin'], 'post', f"/scheduled-trips/{paid['trip']['id']}/ask-travelly",
               {'expected_version': departure(client, paid).version}).status_code == 403


# --------------------------------------------------------------------------- Travelly asks several Owners at once

def place(client, t, vehicle, lat, lng):
    with client.app.state.sessions() as db:
        row = db.get(Vehicle, UUID(vehicle['id']))
        row.base_latitude, row.base_longitude = lat, lng
        db.commit()


def pickup_at(client, t, lat, lng):
    with client.app.state.sessions() as db:
        route = db.get(Route, db.get(ScheduledTrip, UUID(t['trip']['id'])).route_id)
        route.origin_latitude, route.origin_longitude = lat, lng
        db.commit()


def candidates(client, t):
    return api(client, t['admin'], 'get', f"/admin/scheduled-trips/{t['trip']['id']}/replacement-candidates")


def ask_owners(client, t, **body):
    return api(client, t['admin'], 'post', f"/admin/scheduled-trips/{t['trip']['id']}/replacement-requests",
               {'expected_version': departure(client, t).version, **body})


def status_of(client, offer_id):
    with client.app.state.sessions() as db:
        return db.get(ScheduledTrip, UUID(offer_id)).status


def test_candidates_are_fitting_vehicles_nearest_to_the_pickup_first(client, paid):
    assert report(client, paid).status_code == 200
    pickup_at(client, paid, 6.9271, 79.8612)
    _, far = other_owner_vehicle(client, paid, ['A1', 'A2'])
    _, near = other_owner_vehicle(client, paid, ['A1', 'A2', 'A3'])
    _, unknown = other_owner_vehicle(client, paid, ['A1', 'A2'])
    place(client, paid, far, 7.2906, 80.6337)
    place(client, paid, near, 6.9, 79.86)
    got = candidates(client, paid)
    assert got.status_code == 200, got.text
    ids = [i['vehicle_id'] for i in got.json()['items']]
    assert ids == [near['id'], far['id'], unknown['id']] and got.json()['booked_seats'] == 2
    assert got.json()['items'][0]['distance_km'] < got.json()['items'][1]['distance_km'] and got.json()['items'][2]['distance_km'] is None
    assert api(client, paid['owner'], 'get', f"/admin/scheduled-trips/{paid['trip']['id']}/replacement-candidates").status_code == 403


def test_admin_asks_selected_owners_and_the_first_to_accept_wins(client, paid):
    assert report(client, paid).status_code == 200
    first, car1 = other_owner_vehicle(client, paid, ['A1', 'A2'])
    second, car2 = other_owner_vehicle(client, paid, ['A1', 'A2'])
    _, car3 = other_owner_vehicle(client, paid, ['A1', 'A2'])
    sent = ask_owners(client, paid, vehicle_ids=[car1['id'], car2['id']])
    assert sent.status_code == 201, sent.text
    assert sent.json()['asked'] == 2 and sent.json()['pending_offers'] == 2 and sent.json()['replacement_status'] == 'AWAITING_OTHER_OWNER'
    again = ask_owners(client, paid, vehicle_ids=[car1['id']])
    assert again.status_code == 409 and again.json()['code'] == 'NO_VEHICLE_TO_ASK'
    inbox1 = api(client, first, 'get', '/owners/me/replacement-requests').json()['items']
    inbox2 = api(client, second, 'get', '/owners/me/replacement-requests').json()['items']
    assert len(inbox1) == 1 and len(inbox2) == 1
    assert not [i for i in candidates(client, paid).json()['items'] if i['vehicle_id'] == car3['id'] and i['already_asked']]
    won = answer(client, second, inbox2[0], 'ACCEPT')
    assert won.status_code == 200, won.text
    assert status_of(client, inbox1[0]['id']) == 'CANCELLED' and status_of(client, inbox2[0]['id']) == 'COMMITTED'
    late = answer(client, first, inbox1[0], 'ACCEPT')
    assert late.status_code == 409
    assert api(client, first, 'get', '/owners/me/replacement-requests').json()['items'] == []
    assert any(n.title == 'Replacement request closed' for n in notices_of(client, first))


def notices_of(client, user):
    with client.app.state.sessions() as db:
        return db.scalars(select(Notification).where(Notification.recipient_user_id == UUID(user['id']))).all()


def test_a_decline_keeps_waiting_while_other_requests_are_open(client, paid):
    assert report(client, paid).status_code == 200
    first, car1 = other_owner_vehicle(client, paid, ['A1', 'A2'])
    second, car2 = other_owner_vehicle(client, paid, ['A1', 'A2'])
    assert ask_owners(client, paid, send_to_all=True).json()['asked'] == 2
    one = api(client, first, 'get', '/owners/me/replacement-requests').json()['items'][0]
    two = api(client, second, 'get', '/owners/me/replacement-requests').json()['items'][0]
    declined = answer(client, first, one, 'DECLINE', reason='Booked.')
    assert declined.status_code == 200 and declined.json()['replacement_status'] == 'AWAITING_OTHER_OWNER'
    last = answer(client, second, two, 'DECLINE')
    assert last.status_code == 200 and last.json()['replacement_status'] == 'REJECTED'
    assert waiting_for_admin(client, paid)


def test_asking_needs_a_choice_and_an_open_departure(client, paid):
    early = ask_owners(client, paid, send_to_all=True)
    assert early.status_code == 409 and early.json()['code'] == 'REPLACEMENT_NOT_ALLOWED'
    assert report(client, paid).status_code == 200
    none = ask_owners(client, paid)
    assert none.status_code == 422 and none.json()['code'] == 'VEHICLES_REQUIRED'
    assert ask_owners(client, paid, send_to_all=True).status_code == 409   # nobody else has a vehicle yet
    assert api(client, paid['owner'], 'post', f"/admin/scheduled-trips/{paid['trip']['id']}/replacement-requests",
               {'expected_version': departure(client, paid).version, 'send_to_all': True}).status_code == 403
