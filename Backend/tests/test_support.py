"""Support chat: a ticket is a chat thread between one person and the Admins."""
from conftest import bearer
from test_hire_pricing import hire_setup  # noqa: F401  (a fixture)
from test_rates import rate_owner  # noqa: F401  (fixture used by hire_setup)
from test_ticket_holds import person


def call(client, tokens, method, path, body=None):
    kwargs = {'json': body} if body is not None else {}
    return client.request(method.upper(), '/api/v1' + path, headers=bearer(tokens), **kwargs)


def open_one(client, tokens, role='PASSENGER', **extra):
    return call(client, tokens, 'post', '/support/tickets', {'role': role, 'category': 'PAYMENT', 'subject': 'Charged twice', 'message': 'I was charged two times.', **extra})


def test_a_person_opens_a_ticket_and_chats_with_an_admin_until_it_is_closed(client, hire_setup):
    c = hire_setup
    boss = person(client, 'ADMIN')['tokens']
    made = open_one(client, c.passenger)
    assert made.status_code == 201, made.text
    ticket = made.json()
    assert ticket['status'] == 'OPEN' and ticket['unread'] is False
    inbox = call(client, boss, 'get', '/admin/support/tickets').json()['items']
    assert [x['id'] for x in inbox] == [ticket['id']] and inbox[0]['unread'] is True and inbox[0]['person']['name']
    assert call(client, c.passenger, 'get', '/admin/support/tickets').status_code == 403   # only Admins have the inbox
    assert call(client, c.owner, 'get', f"/support/tickets/{ticket['id']}").status_code == 404   # nobody else reads it
    seen = call(client, boss, 'get', f"/support/tickets/{ticket['id']}").json()
    assert [m['body'] for m in seen['messages']] == ['I was charged two times.'] and seen['messages'][0]['mine'] is False
    assert call(client, boss, 'get', '/admin/support/tickets').json()['items'][0]['unread'] is False   # reading clears the Admin's flag
    reply = call(client, boss, 'post', f"/support/tickets/{ticket['id']}/messages", {'body': 'We are checking this.'})
    assert reply.status_code == 201 and reply.json()['from_admin'] is True
    mine = call(client, c.passenger, 'get', '/me/support/tickets').json()['items'][0]
    assert mine['status'] == 'IN_PROGRESS' and mine['unread'] is True and mine['last_message'] == 'We are checking this.'
    assert any(n['title'] == 'Support replied' for n in call(client, c.passenger, 'get', '/notifications').json()['items'])
    thread = call(client, c.passenger, 'get', f"/support/tickets/{ticket['id']}").json()
    assert [(m['from_admin'], m['mine']) for m in thread['messages']] == [(False, True), (True, False)]
    assert call(client, c.passenger, 'get', '/me/support/tickets').json()['items'][0]['unread'] is False
    assert call(client, c.passenger, 'post', f"/support/tickets/{ticket['id']}/messages", {'body': 'Thank you.'}).status_code == 201
    assert call(client, boss, 'post', f"/support/tickets/{ticket['id']}/status", {'status': 'RESOLVED'}).json()['status'] == 'RESOLVED'
    assert call(client, c.passenger, 'post', f"/support/tickets/{ticket['id']}/messages", {'body': 'Still wrong.'}).status_code == 201
    assert call(client, c.passenger, 'get', '/me/support/tickets').json()['items'][0]['status'] == 'OPEN'   # a new message reopens it
    assert call(client, c.passenger, 'post', f"/support/tickets/{ticket['id']}/close", {}).json()['status'] == 'CLOSED'
    assert call(client, c.passenger, 'post', f"/support/tickets/{ticket['id']}/messages", {'body': 'Hello?'}).json()['code'] == 'TICKET_CLOSED'


def test_a_ticket_needs_the_workspace_role_an_own_booking_and_is_limited(client, hire_setup):
    c = hire_setup
    assert open_one(client, c.passenger, role='OWNER').status_code in (403, 409)   # a Passenger-only person cannot write as an Owner
    assert open_one(client, c.owner, role='OWNER', booking_id='00000000-0000-0000-0000-000000000000').status_code == 404
    for number in range(5):
        assert open_one(client, c.passenger, subject=f'Problem {number}').status_code == 201
    assert open_one(client, c.passenger).json()['code'] == 'TOO_MANY_OPEN_TICKETS'
    assert call(client, c.owner, 'post', '/support/tickets', {'role': 'OWNER', 'category': 'APP', 'subject': 'x', 'message': 'y'}).status_code == 201
