"""Review extras: notices for reviews and replies, the Driver's own reviews, the public rating of a vehicle, and Admin hiding."""
from uuid import UUID
from sqlalchemy import select
from app.api.routers.trip_review_api import vehicle_ratings
from app.models.hire_models import Trip
from conftest import bearer
from test_hire_pricing import hire_setup  # noqa: F401  (a fixture)
from test_rates import rate_owner  # noqa: F401  (fixture used by hire_setup)
from test_private_hire_payments import completed  # noqa: F401  (a fixture)
from test_trip_operations import running  # noqa: F401  (fixture used by completed)
from test_ticket_holds import person


def call(client, tokens, method, path, body=None):
    kwargs = {'json': body} if body is not None else {}
    return client.request(method.upper(), '/api/v1' + path, headers=bearer(tokens), **kwargs)


def notices(client, tokens):
    return [n for n in call(client, tokens, 'get', '/notifications').json()['items'] if n['notification_type'] == 'REVIEW']


def trip_of(client, c, booking):
    return call(client, c.passenger, 'get', f"/bookings/{booking['id']}").json()['trip']['id']


def test_the_owner_hears_about_a_review_and_the_passenger_about_the_reply(client, completed):
    c, booking = completed.ctx, completed.booking
    trip_id = trip_of(client, c, booking)
    assert notices(client, c.owner) == []
    assert call(client, c.passenger, 'post', f'/trips/{trip_id}/review', {'rating': 5, 'comment': 'Lovely'}).status_code == 201
    heard = notices(client, c.owner)
    assert len(heard) == 1 and heard[0]['title'] == 'New review' and '5 out of 5' in heard[0]['body'] and heard[0]['booking_id'] == booking['id']
    review = call(client, c.owner, 'get', '/owners/me/reviews').json()['items'][0]
    assert notices(client, c.passenger) == []
    assert call(client, c.owner, 'post', f"/reviews/{review['id']}/reply", {'text': 'Thank you for riding with us.'}).status_code == 200
    told = notices(client, c.passenger)
    assert len(told) == 1 and told[0]['title'] == 'The Owner replied to your review' and told[0]['booking_id'] == booking['id']


def test_the_driver_sees_the_driver_ratings_and_only_those(client, completed):
    c, booking = completed.ctx, completed.booking
    trip_id = trip_of(client, c, booking)
    driver = person(client, 'DRIVER')
    with client.app.state.sessions() as db:
        run = db.get(Trip, UUID(trip_id))
        run.driver_user_id = UUID(driver['id'])
        db.commit()
    assert call(client, c.passenger, 'get', '/drivers/me/reviews').status_code == 403
    assert call(client, driver['tokens'], 'get', '/drivers/me/reviews').json() == {'count': 0, 'average': None, 'items': []}
    assert call(client, c.passenger, 'post', f'/trips/{trip_id}/review', {'rating': 4, 'driver_rating': 5, 'comment': 'Careful driver'}).status_code == 201
    seen = call(client, driver['tokens'], 'get', '/drivers/me/reviews').json()
    assert seen['count'] == 1 and seen['average'] == '5.0' and seen['items'][0]['driver_rating'] == 5 and seen['items'][0]['comment'] == 'Careful driver'
    assert 'rating' not in seen['items'][0]   # the vehicle rating is the Owner's business
    assert [n['title'] for n in notices(client, driver['tokens'])] == ['New review']


def test_an_admin_hides_a_review_and_it_leaves_the_averages(client, completed):
    c, booking = completed.ctx, completed.booking
    trip_id = trip_of(client, c, booking)
    assert call(client, c.passenger, 'post', f'/trips/{trip_id}/review', {'rating': 2, 'comment': 'Rude words here'}).status_code == 201
    boss = person(client, 'ADMIN')['tokens']
    assert call(client, c.owner, 'get', '/admin/reviews').status_code == 403
    listed = call(client, boss, 'get', '/admin/reviews').json()['items']
    assert len(listed) == 1 and listed[0]['hidden_at'] is None
    review_id = listed[0]['id']
    with client.app.state.sessions() as db:
        vehicle_id = db.scalar(select(Trip.vehicle_id).where(Trip.id == UUID(trip_id)))
        assert vehicle_ratings(db, [vehicle_id])[vehicle_id] == {'average': '2.0', 'count': 1}
    assert call(client, boss, 'post', f'/admin/reviews/{review_id}/hide', {}).status_code == 422   # a reason is required
    assert call(client, c.owner, 'post', f'/admin/reviews/{review_id}/hide', {'note': 'x'}).status_code == 403
    hidden = call(client, boss, 'post', f'/admin/reviews/{review_id}/hide', {'note': 'Abusive language'})
    assert hidden.status_code == 200 and hidden.json()['hidden_note'] == 'Abusive language'
    assert call(client, c.owner, 'get', '/owners/me/reviews').json()['count'] == 0
    with client.app.state.sessions() as db:
        assert vehicle_ratings(db, [vehicle_id]) == {}
    assert call(client, boss, 'get', '/admin/reviews').json()['items'][0]['hidden_note'] == 'Abusive language'
    assert call(client, boss, 'post', f'/admin/reviews/{review_id}/unhide', {}).status_code == 200
    assert call(client, c.owner, 'get', '/owners/me/reviews').json()['count'] == 1
