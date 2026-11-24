"""Travel Reels and social (PRD tables 18-19; owner decisions 13 Nov 2026)."""
import io
from uuid import UUID
from PIL import Image
from app.models import User
from app.models.hire_models import Trip
from conftest import bearer
from test_ticket_holds import person, api
from test_rates import rule, rate_owner
from test_hire_pricing import hire_setup, committed
from test_trip_operations import running

MP4 = b'\x00\x00\x00\x18ftypmp42' + b'\x00' * 2048


def jpeg(color=(200, 120, 40)):
    out = io.BytesIO()
    Image.new('RGB', (80, 60), color).save(out, 'JPEG')
    return out.getvalue()


def post(client, who, tokens=None, files=None, **fields):
    data = {'visibility': 'PUBLIC', **fields}
    headers = bearer(tokens or who['tokens']) if (tokens or who) else {}
    parts = {k: (None, v) for k, v in data.items()} | (files or {})   # always multipart, like the app
    return client.post('/api/v1/social/posts', headers=headers, files=parts)


def reel(client, who, **fields):
    return post(client, who, files={'file': ('trip.mp4', MP4, 'video/mp4'), 'thumbnail': ('t.jpg', jpeg(), 'image/jpeg')},
                post_type='REEL', duration_seconds='42', caption='Ella train ride #Ella #trainride', **fields)


def reference(client, who):
    with client.app.state.sessions() as db:
        return db.get(User, UUID(who['id'])).public_user_reference


def test_anyone_signed_in_posts_a_reel_that_is_public_at_once(client):
    author = person(client)
    made = reel(client, author, location_name='Ella', latitude='6.8667', longitude='81.0466')
    assert made.status_code == 201, made.text
    body = made.json()
    assert body['moderation_status'] == 'APPROVED' and body['published_at'] and body['hashtags'] == ['ella', 'trainride']
    assert body['media_url'] == f"/api/v1/social/posts/{body['id']}/media" and body['duration_seconds'] == 42
    feed = client.get('/api/v1/social/feed?type=REEL')          # signed out: public feed
    assert feed.status_code == 200 and feed.json()['items'][0]['id'] == body['id']
    video = client.get(body['media_url'])
    assert video.status_code == 200 and video.headers['content-type'] == 'video/mp4' and video.content == MP4
    part = client.get(body['media_url'], headers={'Range': 'bytes=0-9'})
    assert part.status_code == 206 and part.content == MP4[:10]   # video players can seek
    assert client.get(body['thumbnail_url']).headers['content-type'] == 'image/jpeg'
    assert client.get('/api/v1/social/feed?hashtag=ella').json()['items'][0]['id'] == body['id']


def test_reel_limits_and_bad_files(client):
    author = person(client)
    long = reel(client, author, **{}) if False else post(client, author, files={'file': ('a.mp4', MP4, 'video/mp4')},
                                                          post_type='REEL', duration_seconds='61')
    assert long.status_code == 422 and long.json()['code'] == 'REEL_TOO_LONG'
    fake = post(client, author, files={'file': ('a.mp4', b'not a video at all', 'video/mp4')}, post_type='REEL', duration_seconds='10')
    assert fake.status_code == 422 and fake.json()['code'] == 'INVALID_MEDIA'
    client.app.state.settings = client.app.state.settings.model_copy(update={'social_reel_max_mb': 5})
    big = post(client, author, files={'file': ('a.mp4', MP4 + b'\x00' * (6 * 1024 * 1024), 'video/mp4')}, post_type='REEL', duration_seconds='10')
    assert big.status_code == 413
    nobody = post(client, None, post_type='PHOTO')
    assert nobody.status_code == 401
    photo = post(client, author, files={'file': ('p.png', jpeg(), 'image/jpeg')}, post_type='PHOTO', visibility='PRIVATE')
    assert photo.status_code == 201 and '?t=' in photo.json()['media_url']   # private media needs a signed link
    assert client.get(photo.json()['media_url'].split('?')[0]).status_code == 404
    assert client.get(photo.json()['media_url']).status_code == 200


def test_likes_comments_views_shares_saves_and_follow(client):
    author, fan, other = person(client), person(client), person(client)
    made = reel(client, author).json()
    path = f"/social/posts/{made['id']}"
    assert api(client, fan, 'post', path + '/like', {'active': True}).json()['like_count'] == 1
    assert api(client, fan, 'post', path + '/like', {'active': True}).json()['like_count'] == 1   # once per person
    assert api(client, other, 'post', path + '/like', {'active': True}).json()['like_count'] == 2
    assert api(client, other, 'post', path + '/like', {'active': False}).json()['like_count'] == 1
    first = api(client, fan, 'post', path + '/comments', {'text': 'Beautiful!'}).json()
    reply = api(client, author, 'post', path + '/comments', {'text': 'Thanks', 'parent_id': first['id']})
    assert reply.status_code == 201
    thread = client.get('/api/v1' + path + '/comments').json()
    assert thread['comment_count'] == 2 and thread['items'][0]['replies'][0]['text'] == 'Thanks'
    assert api(client, other, 'post', f"/social/comments/{first['id']}/remove", {}).status_code == 404   # not theirs
    assert api(client, author, 'post', f"/social/comments/{first['id']}/remove", {}).status_code == 200  # post author may
    assert client.post('/api/v1' + path + '/views', json={}).json() == {'id': made['id'], 'counted': True, 'view_count': 1}
    assert client.post('/api/v1' + path + '/views', json={}).json()['counted'] is False                      # once a day per viewer
    assert api(client, fan, 'post', path + '/views', {}).json()['view_count'] == 2
    assert api(client, fan, 'post', path + '/share', {}).json()['share_path'] == f"/reels/{made['id']}"
    assert api(client, fan, 'post', path + '/save', {'active': True}).json()['active']
    assert api(client, fan, 'get', '/social/me/saved').json()['items'][0]['id'] == made['id']
    shown = api(client, fan, 'get', path).json()
    assert shown['liked_by_me'] and shown['saved_by_me'] and shown['view_count'] == 2 and shown['share_count'] == 1
    # FOLLOWERS posts reach followers only
    inner = reel(client, author, visibility='FOLLOWERS').json()
    assert api(client, other, 'get', f"/social/posts/{inner['id']}").status_code == 404
    ref = reference(client, author)
    assert api(client, other, 'post', f'/social/users/{ref}/follow', {'active': True}).json()['following']
    assert api(client, other, 'get', f"/social/posts/{inner['id']}").status_code == 200
    profile = api(client, other, 'get', f'/social/users/{ref}').json()
    assert profile['followers'] == 1 and profile['followed_by_me'] and len(profile['posts']) == 2
    assert client.get(f'/api/v1/social/users/{ref}').json()['posts'][0]['id'] == made['id']   # signed out: public only


def test_report_then_admin_hides_and_restores(client):
    author, viewer, boss = person(client), person(client), person(client, 'ADMIN')
    made = reel(client, author).json()
    assert api(client, author, 'post', f"/social/posts/{made['id']}/report", {'reason': 'mine'}).json()['code'] == 'OWN_POST'
    assert api(client, viewer, 'post', f"/social/posts/{made['id']}/report", {'reason': 'Shows a stranger’s face'}).status_code == 201
    assert api(client, viewer, 'post', f"/social/posts/{made['id']}/report", {'reason': 'again'}).json()['code'] == 'ALREADY_REPORTED'
    listed = api(client, boss, 'get', '/admin/social/posts?reported=true').json()['items']
    assert listed[0]['id'] == made['id'] and listed[0]['open_reports'][0]['reason'].startswith('Shows')
    assert api(client, viewer, 'get', '/admin/social/posts').status_code == 403
    current = api(client, boss, 'get', f"/social/posts/{made['id']}").json()['version']
    hidden = api(client, boss, 'post', f"/admin/social/posts/{made['id']}/moderation", {'expected_version': current, 'action': 'HIDE', 'reason': 'Privacy'})
    assert hidden.status_code == 200 and hidden.json()['moderation_status'] == 'HIDDEN'
    assert client.get(f"/api/v1/social/posts/{made['id']}").status_code == 404 and client.get(made['media_url']).status_code == 404
    assert client.get('/api/v1/social/feed').json()['items'] == []
    back = api(client, boss, 'post', f"/admin/social/posts/{made['id']}/moderation",
               {'expected_version': hidden.json()['version'], 'action': 'RESTORE', 'reason': 'Face blurred by author'})
    assert back.json()['moderation_status'] == 'APPROVED'
    assert api(client, boss, 'get', '/admin/social/posts?reported=true').json()['items'] == []   # reports resolved


def test_author_edits_and_removes(client):
    author, other = person(client), person(client)
    made = reel(client, author).json()
    assert api(client, other, 'patch', f"/social/posts/{made['id']}", {'expected_version': made['version'], 'caption': 'x'}).status_code == 404
    edited = api(client, author, 'patch', f"/social/posts/{made['id']}", {'expected_version': made['version'], 'caption': 'Sunset at #Galle', 'visibility': 'FOLLOWERS'})
    assert edited.status_code == 200 and edited.json()['hashtags'] == ['galle'] and edited.json()['visibility'] == 'FOLLOWERS'
    assert api(client, author, 'post', f"/social/posts/{made['id']}/remove", {}).json()['moderation_status'] == 'HIDDEN'
    assert api(client, author, 'get', f"/social/posts/{made['id']}").status_code == 404


def test_only_travellers_review_a_vehicle_once(client, running):
    c = running.ctx
    with client.app.state.sessions() as db:
        trip = db.get(Trip, UUID(running.trip['id']))
        vehicle_id = str(trip.vehicle_id)
    early = post(client, None, tokens=c.passenger, post_type='REVIEW', linked_vehicle_id=vehicle_id, rating='5', caption='Great')
    assert early.status_code == 403 and early.json()['code'] == 'REVIEW_NOT_ALLOWED'   # trip not finished yet
    done = client.post(f"/api/v1/trips/{running.trip['id']}/complete", headers=bearer(c.owner),
                       json={'expected_version': running.trip['version'], 'end_odometer_km': '1300.5'})
    assert done.status_code == 200, done.text
    can = client.get('/api/v1/social/me/reviewable-vehicles', headers=bearer(c.passenger)).json()['items']
    assert can == [{'vehicle_id': vehicle_id, 'name': can[0]['name'], 'already_reviewed': False}]
    review = post(client, None, tokens=c.passenger, post_type='REVIEW', linked_vehicle_id=vehicle_id, rating='4',
                  caption='Clean van, friendly driver', files={'file': ('v.jpg', jpeg(), 'image/jpeg')})
    assert review.status_code == 201, review.text
    assert review.json()['rating'] == 4
    again = post(client, None, tokens=c.passenger, post_type='REVIEW', linked_vehicle_id=vehicle_id, rating='1', caption='Again')
    assert again.json()['code'] == 'ALREADY_REVIEWED'
    stranger = person(client)
    assert post(client, stranger, post_type='REVIEW', linked_vehicle_id=vehicle_id, rating='1', caption='Bad').json()['code'] == 'REVIEW_NOT_ALLOWED'
    summary = client.get(f'/api/v1/social/vehicles/{vehicle_id}/reviews').json()
    assert summary['average_rating'] == '4.0' and summary['rating_count'] == 1 and summary['items'][0]['rating'] == 4


def test_a_reel_can_show_only_the_posters_own_vehicle_and_the_profile_lists_vehicles(client, hire_setup):
    c = hire_setup
    stranger = person(client)
    own = post(client, None, tokens=c.owner, files={'file': ('p.jpg', jpeg(), 'image/jpeg')}, post_type='PHOTO',
               linked_vehicle_id=str(c.vehicle_id), caption='My van')
    assert own.status_code == 201, own.text
    card = own.json()['linked_vehicle']
    assert card['id'] == str(c.vehicle_id) and card['hireable'] is True and set(card) == {'id', 'name', 'seats', 'hireable'}   # no plate, phone or email
    other = post(client, stranger, files={'file': ('p.jpg', jpeg(), 'image/jpeg')}, post_type='PHOTO', linked_vehicle_id=str(c.vehicle_id), caption='Not mine')
    assert other.status_code == 422                                     # nobody can advertise another person's vehicle
    me = client.get('/api/v1/users/me', headers=bearer(c.owner)).json()
    seen = client.get(f"/api/v1/social/users/{me['public_user_reference']}")
    assert seen.status_code == 200 and [v['id'] for v in seen.json()['vehicles']] == [str(c.vehicle_id)]


def test_people_search_finds_only_people_with_a_visible_post(client):
    author, quiet = person(client), person(client)
    assert post(client, author, files={'file': ('p.jpg', jpeg(), 'image/jpeg')}, post_type='PHOTO', caption='Sunset').status_code == 201
    mine, silent = reference(client, author), reference(client, quiet)
    name = client.get(f'/api/v1/social/users/{mine}').json()['name']
    found = client.get('/api/v1/social/users', params={'q': name[:4]})
    assert found.status_code == 200, found.text
    refs = [item['reference'] for item in found.json()['items']]
    assert mine in refs and silent not in refs                         # no post, no search result
    assert set(found.json()['items'][0]) == {'reference', 'name', 'profile_image_url'}   # no email, phone or id
    assert client.get('/api/v1/social/users', params={'q': 'a'}).status_code == 422
    assert client.get('/api/v1/social/users', params={'q': 'ab', 'x': '1'}).status_code == 422
    assert client.get('/api/v1/social/users', params={'q': '%%'}).json() == {'items': []}   # wildcards are plain text
