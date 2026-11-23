"""Trip reviews: the Passenger rates a finished trip once; the Owner reads the reviews and replies once."""
from conftest import bearer
from test_hire_pricing import hire_setup  # noqa: F401  (a fixture)
from test_rates import rate_owner  # noqa: F401  (fixture used by hire_setup)
from test_private_hire_payments import completed  # noqa: F401  (a fixture)
from test_trip_operations import running  # noqa: F401  (fixture used by completed)


def call(client, tokens, method, path, body=None):
    kwargs = {'json': body} if body is not None else {}
    return client.request(method.upper(), '/api/v1' + path, headers=bearer(tokens), **kwargs)


def test_a_passenger_reviews_a_finished_trip_once_and_the_owner_replies_once(client, completed):
    c, booking = completed.ctx, completed.booking
    trip_id = call(client, c.passenger, 'get', f"/bookings/{booking['id']}").json()['trip']['id']
    state = call(client, c.passenger, 'get', f'/trips/{trip_id}/review').json()
    assert state['review'] is None and state['can_review'] is True
    assert call(client, c.owner, 'post', f'/trips/{trip_id}/review', {'rating': 5}).status_code == 404   # only the Passenger writes
    assert call(client, c.passenger, 'post', f'/trips/{trip_id}/review', {'rating': 6}).status_code == 422
    made = call(client, c.passenger, 'post', f'/trips/{trip_id}/review', {'rating': 4, 'comment': '  Clean car, on time.  '})
    assert made.status_code == 201, made.text
    assert made.json()['comment'] == 'Clean car, on time.' and made.json()['reply'] is None
    assert call(client, c.passenger, 'post', f'/trips/{trip_id}/review', {'rating': 5}).json()['code'] == 'REVIEW_EXISTS'
    assert call(client, c.passenger, 'get', f'/trips/{trip_id}/review').json()['can_review'] is False
    mine = call(client, c.owner, 'get', '/owners/me/reviews').json()
    assert mine['count'] == 1 and mine['average'] == '4.0' and mine['vehicles'][0]['count'] == 1
    review = mine['items'][0]
    assert review['rating'] == 4 and review['passenger'] and review['vehicle'] and review['trip_reference']
    assert call(client, c.passenger, 'post', f"/reviews/{review['id']}/reply", {'text': 'Thank you'}).status_code == 404
    replied = call(client, c.owner, 'post', f"/reviews/{review['id']}/reply", {'text': 'Thank you for riding with us.'})
    assert replied.status_code == 200 and replied.json()['reply'] == 'Thank you for riding with us.'
    again = call(client, c.owner, 'post', f"/reviews/{review['id']}/reply", {'text': 'Safe travels.'})
    assert again.status_code == 200 and again.json()['reply'] == 'Safe travels.'   # the Owner may change the reply
    assert call(client, c.passenger, 'get', '/owners/me/reviews').status_code == 403


def test_an_unfinished_trip_cannot_be_reviewed(client, hire_setup):
    from test_hire_pricing import committed
    c = hire_setup
    booking = committed(client, c)
    trip_id = call(client, c.passenger, 'get', f"/bookings/{booking['id']}").json()['trip']['id']
    assert call(client, c.passenger, 'get', f'/trips/{trip_id}/review').json()['can_review'] is False
    assert call(client, c.passenger, 'post', f'/trips/{trip_id}/review', {'rating': 5}).json()['code'] == 'TRIP_NOT_FINISHED'


def test_the_passenger_changes_or_deletes_a_review_for_seven_days_then_it_is_locked(client, completed):
    from datetime import datetime, timedelta, timezone
    from uuid import UUID
    from app.models.trip_review_models import TripReview
    c, booking = completed.ctx, completed.booking
    trip_id = call(client, c.passenger, 'get', f"/bookings/{booking['id']}").json()['trip']['id']
    assert call(client, c.passenger, 'put', f'/trips/{trip_id}/review', {'rating': 3}).status_code == 404   # nothing to change yet
    assert call(client, c.passenger, 'post', f'/trips/{trip_id}/review', {'rating': 2, 'comment': 'Late'}).status_code == 201
    assert call(client, c.passenger, 'get', f'/trips/{trip_id}/review').json()['can_edit'] is True
    assert call(client, c.owner, 'put', f'/trips/{trip_id}/review', {'rating': 5}).status_code == 404
    changed = call(client, c.passenger, 'put', f'/trips/{trip_id}/review', {'rating': 4, 'comment': ''})
    assert changed.status_code == 200 and changed.json()['rating'] == 4 and changed.json()['comment'] is None and changed.json()['edited_at']
    assert call(client, c.owner, 'get', '/owners/me/reviews').json()['items'][0]['edited_at']
    review_id = call(client, c.owner, 'get', '/owners/me/reviews').json()['items'][0]['id']
    assert call(client, c.owner, 'post', f'/reviews/{review_id}/reply', {'text': 'Thanks'}).status_code == 200
    removed = call(client, c.owner, 'delete', f'/reviews/{review_id}/reply')
    assert removed.status_code == 200 and removed.json()['reply'] is None
    with client.app.state.sessions() as db:
        row = db.get(TripReview, UUID(review_id))
        row.created_at = datetime.now(timezone.utc) - timedelta(days=8)
        db.commit()
    state = call(client, c.passenger, 'get', f'/trips/{trip_id}/review').json()
    assert state['can_edit'] is False and state['review']['rating'] == 4
    assert call(client, c.passenger, 'put', f'/trips/{trip_id}/review', {'rating': 1}).json()['code'] == 'REVIEW_LOCKED'
    assert call(client, c.passenger, 'delete', f'/trips/{trip_id}/review').json()['code'] == 'REVIEW_LOCKED'
    with client.app.state.sessions() as db:
        row = db.get(TripReview, UUID(review_id))
        row.created_at = datetime.now(timezone.utc)
        db.commit()
    assert call(client, c.passenger, 'delete', f'/trips/{trip_id}/review').json() == {'deleted': True}
    assert call(client, c.passenger, 'get', f'/trips/{trip_id}/review').json()['can_review'] is True   # may write it again
    assert call(client, c.owner, 'get', '/owners/me/reviews').json()['count'] == 0
