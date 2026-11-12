"""Travel Reels and social (PRD matrix 79-85 and 95; tables social_posts, social_interactions).

Owner decisions 13 Nov 2026:
- Anyone signed in can post a REEL (video, up to 60 s / 50 MB), a PHOTO or a REVIEW.
- Posts are public at once (no approval queue). The Admin can hide sensitive posts (HIDDEN) and show them again.
- Views are counted (view_count, the one column added to the PRD table).
- A REVIEW (1-5 stars) is only for a vehicle the person travelled in on a completed trip; one review per vehicle.

Endpoints (base /api/v1):
    POST /social/posts                         multipart: create a post (author)
    GET  /social/feed[?type=&hashtag=&author=&before=&limit=]   what this viewer may see, newest first (public read)
    GET  /social/posts/{id}                    one post
    GET  /social/posts/{id}/media[?t=]         the video/photo; a signed t= link for non-public posts
    GET  /social/posts/{id}/thumbnail[?t=]
    PATCH /social/posts/{id}                   author: caption, hashtags, location, visibility
    POST /social/posts/{id}/remove             author takes the post down (HIDDEN)
    POST /social/posts/{id}/views              count one view (once per person or address per day)
    POST /social/posts/{id}/like | /save       {"active": true|false}
    POST /social/posts/{id}/share              count a share, returns the share path
    GET  /social/posts/{id}/comments           comments with one level of replies
    POST /social/posts/{id}/comments           {"text", "parent_id"?}
    POST /social/comments/{id}/remove          the commenter, the post author or the Admin
    POST /social/posts/{id}/report             {"reason"}
    POST /social/users/{reference}/follow      {"active": true|false}
    GET  /social/users/{reference}             profile: counts and visible posts
    GET  /social/me/saved                      my saved posts
    GET  /social/me/reviewable-vehicles        vehicles I may review
    GET  /social/vehicles/{vehicle_id}/reviews average rating and reviews
    GET  /admin/social/posts[?status=&reported=]   Admin list with reports
    POST /admin/social/posts/{id}/moderation   {"expected_version", "action": "HIDE"|"RESTORE", "reason"} (audited)
"""
import json
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Literal, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile
from app.api.routers.api import current, touch
from app.api.routers.review_api import admin, locked_authority
from app.core.errors import ApiError
from app.dependencies.database import get_db
from app.models import User, UserRole
from app.models.hire_models import Booking, Route, ScheduledTrip, Trip
from app.models.review_models import Vehicle
from app.models.social_models import SocialInteraction, SocialPost
from app.services import social_media

router = APIRouter(prefix='/api/v1', tags=['Travel Reels'])
VISIBILITY = ('PUBLIC', 'FOLLOWERS', 'PRIVATE')
TAG = re.compile(r'#([\w஀-௿඀-෿]{1,50})')


def now():
    return datetime.now(timezone.utc)


def missing():
    return ApiError(404, 'POST_NOT_FOUND', 'Post not found.')


def maybe_user(request, db):
    """Feeds and posts are public reads (PRD D10); signed-in viewers also see what is shared with them."""
    if not request.headers.get('authorization'):
        return None
    return current(request, db)


def is_admin(db, user):
    return bool(user and db.scalar(select(UserRole.id).where(UserRole.user_id == user.id, UserRole.role_code == 'ADMIN',
                                                            UserRole.approval_status == 'APPROVED')))


def follows(db, viewer_id, author_id):
    return bool(db.scalar(select(SocialInteraction.id).where(
        SocialInteraction.actor_user_id == viewer_id, SocialInteraction.target_user_id == author_id,
        SocialInteraction.interaction_type == 'FOLLOW', SocialInteraction.interaction_status == 'ACTIVE')))


def visible_clause(viewer):
    shown = and_(SocialPost.moderation_status == 'APPROVED', SocialPost.published_at.is_not(None))
    if viewer is None:
        return and_(shown, SocialPost.visibility == 'PUBLIC')
    followed = select(SocialInteraction.target_user_id).where(
        SocialInteraction.actor_user_id == viewer.id, SocialInteraction.interaction_type == 'FOLLOW',
        SocialInteraction.interaction_status == 'ACTIVE')
    return and_(shown, or_(SocialPost.visibility == 'PUBLIC', SocialPost.author_user_id == viewer.id,
                           and_(SocialPost.visibility == 'FOLLOWERS', SocialPost.author_user_id.in_(followed))))


def can_see(db, post, viewer):
    if post is None:
        return False
    if post.moderation_status != 'APPROVED' or post.published_at is None:
        return False
    if post.visibility == 'PUBLIC':
        return True
    if viewer is None:
        return False
    if post.author_user_id == viewer.id:
        return True
    return post.visibility == 'FOLLOWERS' and follows(db, viewer.id, post.author_user_id)


def visible_post(db, post_id, viewer):
    post = db.get(SocialPost, post_id)
    if not can_see(db, post, viewer):
        raise missing()
    return post


def author_out(user):
    return {'reference': user.public_user_reference, 'name': user.display_name or user.full_name,
            'profile_image_url': user.profile_image_url}


def mine(db, viewer, post_ids, kind):
    if viewer is None or not post_ids:
        return set()
    return set(db.scalars(select(SocialInteraction.post_id).where(
        SocialInteraction.actor_user_id == viewer.id, SocialInteraction.post_id.in_(post_ids),
        SocialInteraction.interaction_type == kind, SocialInteraction.interaction_status == 'ACTIVE')))


def ratings(db, posts):
    ids = [p.id for p in posts if p.post_type == 'REVIEW']
    if not ids:
        return {}
    rows = db.execute(select(SocialInteraction.post_id, SocialInteraction.rating).where(
        SocialInteraction.post_id.in_(ids), SocialInteraction.interaction_type == 'RATING',
        SocialInteraction.interaction_status == 'ACTIVE')).all()
    return {post_id: rating for post_id, rating in rows}


def media_links(request, post):
    settings = request.app.state.settings
    def link(kind, stored):
        if not stored:
            return None
        if post.visibility == 'PUBLIC' and post.moderation_status == 'APPROVED':
            return stored
        return f'{stored}?t={social_media.sign(settings, post.id, kind)}'
    return link('media', post.media_url), link('thumbnail', post.thumbnail_url)


def posts_out(request, db, posts, viewer):
    authors = {u.id: u for u in db.scalars(select(User).where(User.id.in_({p.author_user_id for p in posts})))} if posts else {}
    ids = [p.id for p in posts]
    liked, saved, stars = mine(db, viewer, ids, 'LIKE'), mine(db, viewer, ids, 'SAVE'), ratings(db, posts)
    followed = set(db.scalars(select(SocialInteraction.target_user_id).where(
        SocialInteraction.actor_user_id == viewer.id, SocialInteraction.interaction_type == 'FOLLOW',
        SocialInteraction.interaction_status == 'ACTIVE'))) if viewer else set()
    out = []
    for p in posts:
        media, thumb = media_links(request, p)
        out.append({'id': str(p.id), 'version': p.version, 'post_type': p.post_type, 'author': author_out(authors[p.author_user_id]),
                    'media_url': media, 'thumbnail_url': thumb, 'caption': p.caption, 'hashtags': p.hashtags,
                    'location_name': p.location_name,
                    'latitude': None if p.latitude is None else str(p.latitude),
                    'longitude': None if p.longitude is None else str(p.longitude),
                    'linked_vehicle_id': str(p.linked_vehicle_id) if p.linked_vehicle_id else None,
                    'linked_route_id': str(p.linked_route_id) if p.linked_route_id else None,
                    'linked_scheduled_trip_id': str(p.linked_scheduled_trip_id) if p.linked_scheduled_trip_id else None,
                    'visibility': p.visibility, 'moderation_status': p.moderation_status,
                    'published_at': p.published_at.isoformat() if p.published_at else None,
                    'duration_seconds': p.duration_seconds, 'rating': stars.get(p.id),
                    'like_count': p.denormalized_like_count, 'comment_count': p.comment_count,
                    'share_count': p.share_count, 'view_count': p.view_count,
                    'liked_by_me': p.id in liked, 'saved_by_me': p.id in saved,
                    'following_author': p.author_user_id in followed, 'is_mine': bool(viewer and viewer.id == p.author_user_id)})
    return out


def bump(db, post_id, **deltas):
    """Counter caches change with SQL arithmetic (never below zero) and count as one mutation (version + 1)."""
    values = {name: func.greatest(getattr(SocialPost, name) + delta, 0) for name, delta in deltas.items()}
    db.execute(update(SocialPost).where(SocialPost.id == post_id).values(
        **values, version=SocialPost.version + 1, updated_at=func.greatest(func.now(), SocialPost.updated_at)))


# ------------------------------------------------------------------------------------------------------- create

def text_field(form, name, low, high):
    value = form.get(name)
    if value is None or value == '':
        return None
    if not isinstance(value, str) or not low <= len(value.strip()) <= high:
        raise ApiError(422, 'VALIDATION_ERROR', f'{name} must be {low}-{high} characters.')
    return value.strip()


def tags_from(caption, extra):
    found = [t.lower() for t in TAG.findall(caption or '')]
    if extra:
        try:
            more = json.loads(extra) if extra.strip().startswith('[') else extra.split(',')
        except ValueError:
            raise ApiError(422, 'VALIDATION_ERROR', 'hashtags must be a list or comma separated.') from None
        found += [str(t).strip().lstrip('#').lower() for t in more if str(t).strip()]
    unique = []
    for tag in found:
        if not re.fullmatch(r'[\w஀-௿඀-෿]{1,50}', tag):
            raise ApiError(422, 'VALIDATION_ERROR', 'A hashtag can have letters, numbers and _ only (up to 50).')
        if tag not in unique:
            unique.append(tag)
    if len(unique) > 30:
        raise ApiError(422, 'VALIDATION_ERROR', 'Use at most 30 hashtags.')
    return unique


def coordinate(form, name, limit):
    value = form.get(name)
    if value in (None, ''):
        return None
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        raise ApiError(422, 'VALIDATION_ERROR', f'Enter a valid {name}.') from None
    if not number.is_finite() or abs(number) > limit:
        raise ApiError(422, 'VALIDATION_ERROR', f'Enter a valid {name}.')
    return number.quantize(Decimal('0.000001'))


def uuid_field(form, name):
    value = form.get(name)
    if value in (None, ''):
        return None
    try:
        return UUID(str(value))
    except ValueError:
        raise ApiError(422, 'VALIDATION_ERROR', f'{name} is not a valid id.') from None


def travelled_in(db, user_id, vehicle_id):
    """A completed trip in this vehicle on one of the person's own bookings (private hire or ticket)."""
    mine_ = select(Booking.id, Booking.current_scheduled_trip_id).where(
        Booking.passenger_user_id == user_id, Booking.status != 'CANCELLED').subquery()
    return bool(db.scalar(select(Trip.id).where(
        Trip.vehicle_id == vehicle_id, Trip.status == 'COMPLETED',
        or_(Trip.booking_id.in_(select(mine_.c.id)), Trip.scheduled_trip_id.in_(select(mine_.c.current_scheduled_trip_id))))
        .limit(1)))


def reviewed(db, user_id, vehicle_id):
    return bool(db.scalar(select(SocialPost.id).where(
        SocialPost.author_user_id == user_id, SocialPost.post_type == 'REVIEW', SocialPost.linked_vehicle_id == vehicle_id,
        SocialPost.moderation_status.in_(('PENDING', 'APPROVED'))).limit(1)))


@router.post('/social/posts', status_code=201)
async def create_post(request: Request, user=Depends(current), db: Session = Depends(get_db)):
    allowed = {'post_type', 'caption', 'hashtags', 'location_name', 'latitude', 'longitude', 'linked_vehicle_id',
               'linked_route_id', 'linked_scheduled_trip_id', 'visibility', 'duration_seconds', 'rating', 'file', 'thumbnail'}
    async with request.form(max_files=2, max_fields=14, max_part_size=16384) as form:
        names = [k for k, _ in form.multi_items()]
        if len(names) != len(set(names)) or not set(names) <= allowed:
            raise ApiError(422, 'VALIDATION_ERROR', 'Unknown or repeated field.')
        return await run_in_threadpool(place_post, form, request, user, db)


def place_post(form, request, user, db):
    settings = request.app.state.settings
    request.app.state.store.rate(f'social-post:{user.id}', 20, 3600)
    kind = form.get('post_type')
    if kind not in ('REEL', 'PHOTO', 'REVIEW'):
        raise ApiError(422, 'VALIDATION_ERROR', 'post_type must be REEL, PHOTO or REVIEW.')
    visibility = form.get('visibility')
    if visibility not in VISIBILITY:
        raise ApiError(422, 'VALIDATION_ERROR', 'Choose who can see it: PUBLIC, FOLLOWERS or PRIVATE.')
    caption = text_field(form, 'caption', 1, 2200)
    location = text_field(form, 'location_name', 1, 150)
    lat, lng = coordinate(form, 'latitude', 90), coordinate(form, 'longitude', 180)
    if (lat is None) != (lng is None):
        raise ApiError(422, 'VALIDATION_ERROR', 'Send both latitude and longitude, or neither.')
    vehicle_id, route_id, departure_id = (uuid_field(form, n) for n in ('linked_vehicle_id', 'linked_route_id', 'linked_scheduled_trip_id'))
    if vehicle_id and not db.get(Vehicle, vehicle_id): raise ApiError(422, 'VALIDATION_ERROR', 'That vehicle does not exist.')
    if route_id and not db.get(Route, route_id): raise ApiError(422, 'VALIDATION_ERROR', 'That route does not exist.')
    if departure_id and not db.get(ScheduledTrip, departure_id): raise ApiError(422, 'VALIDATION_ERROR', 'That departure does not exist.')
    upload, thumb_upload = form.get('file'), form.get('thumbnail')
    if upload is not None and not isinstance(upload, UploadFile): raise ApiError(422, 'VALIDATION_ERROR', 'file must be a file.')
    if thumb_upload is not None and not isinstance(thumb_upload, UploadFile): raise ApiError(422, 'VALIDATION_ERROR', 'thumbnail must be a file.')
    duration = rating = None
    media = ext = thumb = None
    if kind == 'REEL':
        if upload is None: raise ApiError(422, 'VALIDATION_ERROR', 'A reel needs a video.')
        try:
            duration = int(form.get('duration_seconds') or '')
        except ValueError:
            raise ApiError(422, 'VALIDATION_ERROR', 'Send duration_seconds (the video length).') from None
        if not 1 <= duration <= settings.social_reel_max_seconds:
            raise ApiError(422, 'REEL_TOO_LONG', f'A reel can be at most {settings.social_reel_max_seconds} seconds.')
        media, ext = social_media.check_video(upload, settings.social_reel_max_mb)
        thumb = social_media.clean_image(thumb_upload) if thumb_upload is not None else None
    else:
        if thumb_upload is not None: raise ApiError(422, 'VALIDATION_ERROR', 'Only a reel takes a separate thumbnail.')
        if kind == 'PHOTO' and upload is None: raise ApiError(422, 'VALIDATION_ERROR', 'A photo post needs a photo.')
        if upload is not None:
            media, ext = social_media.clean_image(upload), '.jpg'
    if kind == 'REVIEW':
        try:
            rating = int(form.get('rating') or '')
        except ValueError:
            raise ApiError(422, 'VALIDATION_ERROR', 'Give 1 to 5 stars.') from None
        if not 1 <= rating <= 5: raise ApiError(422, 'VALIDATION_ERROR', 'Give 1 to 5 stars.')
        if not vehicle_id: raise ApiError(422, 'VALIDATION_ERROR', 'A review is about a vehicle: send linked_vehicle_id.')
        if not caption: raise ApiError(422, 'VALIDATION_ERROR', 'Write a few words for your review.')
        if not travelled_in(db, user.id, vehicle_id):
            raise ApiError(403, 'REVIEW_NOT_ALLOWED', 'You can review a vehicle after a completed trip in it.')
        if reviewed(db, user.id, vehicle_id):
            raise ApiError(409, 'ALREADY_REVIEWED', 'You already reviewed this vehicle. Edit your review instead.')
    elif form.get('rating'):
        raise ApiError(422, 'VALIDATION_ERROR', 'Stars belong to a review.')
    moment = now()
    post = SocialPost(author_user_id=user.id, post_type=kind, caption=caption, hashtags=tags_from(caption, form.get('hashtags')),
                      location_name=location, latitude=lat, longitude=lng, linked_vehicle_id=vehicle_id,
                      linked_route_id=route_id, linked_scheduled_trip_id=departure_id, visibility=visibility,
                      # Owner decision 13 Nov 2026: public at once; the Admin can hide it afterwards.
                      moderation_status='APPROVED', published_at=moment, duration_seconds=duration,
                      created_by=user.id, updated_by=user.id)
    db.add(post)
    db.flush()
    if media is not None:
        post.media_url = f'/api/v1/social/posts/{post.id}/media'
    if thumb is not None or (kind != 'REEL' and media is not None):
        post.thumbnail_url = f'/api/v1/social/posts/{post.id}/thumbnail'
    if rating:
        db.add(SocialInteraction(actor_user_id=user.id, post_id=post.id, interaction_type='RATING', rating=rating,
                                 created_by=user.id, updated_by=user.id))
    try:
        social_media.save(settings, post.id, media, ext, thumb if thumb is not None else (media if kind != 'REEL' else None))
        db.commit()
    except Exception:
        db.rollback()
        social_media.remove(settings, post.id)
        raise
    db.refresh(post)
    return posts_out(request, db, [post], user)[0]


# ------------------------------------------------------------------------------------------------------- read

FEED_PARAMS = {'type', 'hashtag', 'author', 'before', 'limit'}


@router.get('/social/feed')
def feed(request: Request, db: Session = Depends(get_db)):
    viewer = maybe_user(request, db)
    params = dict(request.query_params)
    if not set(params) <= FEED_PARAMS:
        raise ApiError(422, 'VALIDATION_ERROR', 'Unknown filter.')
    query = select(SocialPost).where(visible_clause(viewer))
    if params.get('type'):
        if params['type'] not in ('REEL', 'PHOTO', 'REVIEW'): raise ApiError(422, 'VALIDATION_ERROR', 'type must be REEL, PHOTO or REVIEW.')
        query = query.where(SocialPost.post_type == params['type'])
    if params.get('hashtag'):
        query = query.where(SocialPost.hashtags.contains([params['hashtag'].lstrip('#').lower()]))
    if params.get('author'):
        author = db.scalar(select(User.id).where(User.public_user_reference == params['author']))
        query = query.where(SocialPost.author_user_id == author)
    if params.get('before'):
        try:
            before = datetime.fromisoformat(params['before'])
        except ValueError:
            raise ApiError(422, 'VALIDATION_ERROR', 'before must be a date-time from next_before.') from None
        query = query.where(SocialPost.published_at < before)
    try:
        limit = min(max(int(params.get('limit', 20)), 1), 50)
    except ValueError:
        raise ApiError(422, 'VALIDATION_ERROR', 'limit must be a number.') from None
    rows = db.scalars(query.order_by(SocialPost.published_at.desc(), SocialPost.id.desc()).limit(limit + 1)).all()
    items = posts_out(request, db, rows[:limit], viewer)
    return {'items': items, 'next_before': rows[limit - 1].published_at.isoformat() if len(rows) > limit else None}


@router.get('/social/posts/{post_id}')
def one_post(post_id: UUID, request: Request, db: Session = Depends(get_db)):
    viewer = maybe_user(request, db)
    return posts_out(request, db, [visible_post(db, post_id, viewer)], viewer)[0]


def serve(request, db, post_id, kind):
    settings = request.app.state.settings
    post = db.get(SocialPost, post_id)
    if post is None:
        raise missing()
    token = request.query_params.get('t')
    if set(request.query_params) - {'t'}:
        raise ApiError(422, 'VALIDATION_ERROR', 'Unknown parameter.')
    open_ = post.visibility == 'PUBLIC' and post.moderation_status == 'APPROVED'
    if not open_ and not (token and social_media.signed(settings, post.id, kind, token)):
        raise missing()
    path = social_media.media_file(settings, post.id) if kind == 'media' else social_media.thumb_file(settings, post.id)
    if path is None:
        raise ApiError(404, 'MEDIA_NOT_FOUND', 'This post has no such file.')
    media_type = {'.mp4': 'video/mp4', '.mov': 'video/quicktime', '.webm': 'video/webm'}.get(path.suffix, 'image/jpeg')
    cache = 'public, max-age=3600' if open_ else 'private, no-store'
    return FileResponse(path, media_type=media_type, headers={'Cache-Control': cache, 'X-Content-Type-Options': 'nosniff'})


@router.get('/social/posts/{post_id}/media')
def post_media(post_id: UUID, request: Request, db: Session = Depends(get_db)):
    return serve(request, db, post_id, 'media')


@router.get('/social/posts/{post_id}/thumbnail')
def post_thumbnail(post_id: UUID, request: Request, db: Session = Depends(get_db)):
    return serve(request, db, post_id, 'thumbnail')


# ------------------------------------------------------------------------------------------------------- author

class PostEdit(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    expected_version: int = Field(ge=1)
    caption: Optional[str] = Field(default=None, min_length=1, max_length=2200)
    hashtags: Optional[list[str]] = Field(default=None, max_length=30)
    location_name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    visibility: Optional[Literal['PUBLIC', 'FOLLOWERS', 'PRIVATE']] = None
    rating: Optional[int] = Field(default=None, ge=1, le=5)


def own_locked(db, post_id, user, expected=None):
    post = db.scalar(select(SocialPost).where(SocialPost.id == post_id).with_for_update().execution_options(populate_existing=True))
    if not post or post.author_user_id != user.id or post.moderation_status not in ('APPROVED', 'PENDING'):
        raise missing()
    if expected is not None and post.version != expected:
        raise ApiError(409, 'VERSION_CONFLICT', 'The post changed. Reload before saving.')
    return post


@router.patch('/social/posts/{post_id}')
def edit_post(post_id: UUID, body: PostEdit, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    post = own_locked(db, post_id, user, body.expected_version)
    fields = body.model_fields_set - {'expected_version'}
    if not fields:
        raise ApiError(422, 'VALIDATION_ERROR', 'Nothing to change.')
    if 'caption' in fields:
        post.caption = body.caption
        post.hashtags = tags_from(body.caption, json.dumps(body.hashtags) if body.hashtags is not None else None)
    elif 'hashtags' in fields:
        post.hashtags = tags_from(post.caption, json.dumps(body.hashtags or []))
    if 'location_name' in fields: post.location_name = body.location_name
    if 'visibility' in fields: post.visibility = body.visibility
    if 'rating' in fields:
        if post.post_type != 'REVIEW' or body.rating is None: raise ApiError(422, 'VALIDATION_ERROR', 'Stars belong to a review.')
        star = db.scalar(select(SocialInteraction).where(SocialInteraction.post_id == post.id, SocialInteraction.actor_user_id == user.id,
                                                        SocialInteraction.interaction_type == 'RATING', SocialInteraction.interaction_status == 'ACTIVE'))
        star.rating = body.rating; touch(star); star.updated_by = user.id
    touch(post); post.updated_by = user.id
    db.commit()
    return posts_out(request, db, [post], user)[0]


@router.post('/social/posts/{post_id}/remove')
def remove_post(post_id: UUID, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    post = own_locked(db, post_id, user)
    post.moderation_status = 'HIDDEN'
    touch(post); post.updated_by = user.id
    db.commit()
    return {'id': str(post.id), 'moderation_status': post.moderation_status}


# ------------------------------------------------------------------------------------------------------- interactions

class Toggle(BaseModel):
    model_config = ConfigDict(extra='forbid')
    active: bool


def toggle(request, db, user, post_id, kind, active):
    post = visible_post(db, post_id, user)
    request.app.state.store.rate(f'social-toggle:{user.id}', 300, 600)
    row = db.scalar(select(SocialInteraction).where(
        SocialInteraction.actor_user_id == user.id, SocialInteraction.post_id == post.id,
        SocialInteraction.interaction_type == kind, SocialInteraction.interaction_status == 'ACTIVE').with_for_update())
    changed = False
    if active and row is None:
        db.add(SocialInteraction(actor_user_id=user.id, post_id=post.id, interaction_type=kind, created_by=user.id, updated_by=user.id))
        changed = True
    elif not active and row is not None:
        row.interaction_status = 'REMOVED'; touch(row); row.updated_by = user.id
        changed = True
    if changed and kind == 'LIKE':
        bump(db, post.id, denormalized_like_count=1 if active else -1)
    try:
        db.commit()
    except IntegrityError:   # the same tap arrived twice at once: the first one counted
        db.rollback()
    db.refresh(post)
    return {'id': str(post.id), 'active': active, 'like_count': post.denormalized_like_count}


@router.post('/social/posts/{post_id}/like')
def like(post_id: UUID, body: Toggle, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    return toggle(request, db, user, post_id, 'LIKE', body.active)


@router.post('/social/posts/{post_id}/save')
def save_post(post_id: UUID, body: Toggle, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    return toggle(request, db, user, post_id, 'SAVE', body.active)


@router.post('/social/posts/{post_id}/views')
def count_view(post_id: UUID, request: Request, db: Session = Depends(get_db)):
    viewer = maybe_user(request, db)
    post = visible_post(db, post_id, viewer)
    store = request.app.state.store
    who = f'user:{viewer.id}' if viewer else 'ip:' + (request.client.host if request.client else 'unknown')
    counted = bool(store.client.set(store.key(f'social-view:{post.id}:{who}'), '1', nx=True, ex=86400))
    if counted:
        bump(db, post.id, view_count=1)
        db.commit()
        db.refresh(post)
    return {'id': str(post.id), 'counted': counted, 'view_count': post.view_count}


@router.post('/social/posts/{post_id}/share')
def share(post_id: UUID, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    post = visible_post(db, post_id, user)
    request.app.state.store.rate(f'social-share:{user.id}', 60, 600)
    db.add(SocialInteraction(actor_user_id=user.id, post_id=post.id, interaction_type='SHARE', created_by=user.id, updated_by=user.id))
    bump(db, post.id, share_count=1)
    db.commit()
    db.refresh(post)
    return {'id': str(post.id), 'share_count': post.share_count, 'share_path': f'/reels/{post.id}'}


class CommentIn(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    text: str = Field(min_length=1, max_length=1000)
    parent_id: Optional[UUID] = None


def comment_out(row, author, viewer, post, admin_viewer):
    removable = bool(viewer and (viewer.id in (row.actor_user_id, post.author_user_id) or admin_viewer))
    return {'id': str(row.id), 'author': author_out(author), 'text': row.comment_text, 'created_at': row.created_at.isoformat(),
            'can_remove': removable, 'replies': []}


@router.get('/social/posts/{post_id}/comments')
def comments(post_id: UUID, request: Request, db: Session = Depends(get_db)):
    viewer = maybe_user(request, db)
    post = visible_post(db, post_id, viewer)
    rows = db.scalars(select(SocialInteraction).where(SocialInteraction.post_id == post.id, SocialInteraction.interaction_type == 'COMMENT',
                                                      SocialInteraction.interaction_status == 'ACTIVE')
                      .order_by(SocialInteraction.created_at, SocialInteraction.id).limit(500)).all()
    people = {u.id: u for u in db.scalars(select(User).where(User.id.in_({r.actor_user_id for r in rows})))} if rows else {}
    staff = is_admin(db, viewer)
    top, by_id = [], {}
    for row in rows:
        item = comment_out(row, people[row.actor_user_id], viewer, post, staff)
        by_id[row.id] = item
        if row.parent_interaction_id and row.parent_interaction_id in by_id:
            by_id[row.parent_interaction_id]['replies'].append(item)
        elif not row.parent_interaction_id:
            top.append(item)
    return {'items': top, 'comment_count': post.comment_count}


@router.post('/social/posts/{post_id}/comments', status_code=201)
def add_comment(post_id: UUID, body: CommentIn, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    post = visible_post(db, post_id, user)
    request.app.state.store.rate(f'social-comment:{user.id}', 30, 600)
    if body.parent_id:
        parent = db.get(SocialInteraction, body.parent_id)
        if not parent or parent.post_id != post.id or parent.interaction_type != 'COMMENT' or parent.interaction_status != 'ACTIVE':
            raise ApiError(422, 'VALIDATION_ERROR', 'Reply to a comment on this post.')
        if parent.parent_interaction_id:
            body.parent_id = parent.parent_interaction_id   # one level of replies: answer the same thread
    row = SocialInteraction(actor_user_id=user.id, post_id=post.id, interaction_type='COMMENT', comment_text=body.text,
                            parent_interaction_id=body.parent_id, created_by=user.id, updated_by=user.id)
    db.add(row)
    bump(db, post.id, comment_count=1)
    db.commit()
    db.refresh(row)
    return comment_out(row, user, user, post, False)


@router.post('/social/comments/{comment_id}/remove')
def remove_comment(comment_id: UUID, user=Depends(current), db: Session = Depends(get_db)):
    row = db.scalar(select(SocialInteraction).where(SocialInteraction.id == comment_id).with_for_update())
    if not row or row.interaction_type != 'COMMENT' or row.interaction_status != 'ACTIVE':
        raise ApiError(404, 'COMMENT_NOT_FOUND', 'Comment not found.')
    post = db.get(SocialPost, row.post_id)
    if user.id not in (row.actor_user_id, post.author_user_id) and not is_admin(db, user):
        raise ApiError(404, 'COMMENT_NOT_FOUND', 'Comment not found.')
    row.interaction_status = 'REMOVED'; touch(row); row.updated_by = user.id
    bump(db, post.id, comment_count=-1)
    db.commit()
    return {'id': str(row.id), 'status': 'REMOVED'}


class ReportIn(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    reason: str = Field(min_length=3, max_length=500)


@router.post('/social/posts/{post_id}/report', status_code=201)
def report(post_id: UUID, body: ReportIn, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    post = visible_post(db, post_id, user)
    request.app.state.store.rate(f'social-report:{user.id}', 20, 3600)
    if post.author_user_id == user.id:
        raise ApiError(409, 'OWN_POST', 'You cannot report your own post.')
    if db.scalar(select(SocialInteraction.id).where(SocialInteraction.actor_user_id == user.id, SocialInteraction.post_id == post.id,
                                                    SocialInteraction.interaction_type == 'REPORT', SocialInteraction.interaction_status == 'UNDER_REVIEW')):
        raise ApiError(409, 'ALREADY_REPORTED', 'You already reported this post. The Admin will look at it.')
    db.add(SocialInteraction(actor_user_id=user.id, post_id=post.id, interaction_type='REPORT', report_reason=body.reason,
                             interaction_status='UNDER_REVIEW', created_by=user.id, updated_by=user.id))
    db.commit()
    return {'id': str(post.id), 'reported': True}


# ------------------------------------------------------------------------------------------------------- people

def person(db, reference):
    found = db.scalar(select(User).where(User.public_user_reference == reference))
    if not found or found.account_status not in ('ACTIVE', 'PENDING_VERIFICATION'):
        raise ApiError(404, 'USER_NOT_FOUND', 'Person not found.')
    return found


@router.post('/social/users/{reference}/follow')
def follow(reference: str, body: Toggle, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    target = person(db, reference)
    if target.id == user.id:
        raise ApiError(409, 'OWN_ACCOUNT', 'You cannot follow yourself.')
    request.app.state.store.rate(f'social-follow:{user.id}', 100, 600)
    row = db.scalar(select(SocialInteraction).where(SocialInteraction.actor_user_id == user.id, SocialInteraction.target_user_id == target.id,
                                                    SocialInteraction.interaction_type == 'FOLLOW', SocialInteraction.interaction_status == 'ACTIVE').with_for_update())
    if body.active and row is None:
        db.add(SocialInteraction(actor_user_id=user.id, target_user_id=target.id, interaction_type='FOLLOW', created_by=user.id, updated_by=user.id))
    elif not body.active and row is not None:
        row.interaction_status = 'REMOVED'; touch(row); row.updated_by = user.id
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
    return {'reference': reference, 'following': body.active}


def count_follow(db, column, user_id):
    return db.scalar(select(func.count()).select_from(SocialInteraction).where(
        column == user_id, SocialInteraction.interaction_type == 'FOLLOW', SocialInteraction.interaction_status == 'ACTIVE'))


@router.get('/social/users/{reference}')
def profile(reference: str, request: Request, db: Session = Depends(get_db)):
    viewer = maybe_user(request, db)
    target = person(db, reference)
    posts = db.scalars(select(SocialPost).where(visible_clause(viewer), SocialPost.author_user_id == target.id)
                       .order_by(SocialPost.published_at.desc()).limit(60)).all()
    return {**author_out(target), 'followers': count_follow(db, SocialInteraction.target_user_id, target.id),
            'following': count_follow(db, SocialInteraction.actor_user_id, target.id),
            'post_count': db.scalar(select(func.count()).select_from(SocialPost).where(
                SocialPost.author_user_id == target.id, SocialPost.moderation_status == 'APPROVED')),
            'followed_by_me': bool(viewer and follows(db, viewer.id, target.id)), 'is_me': bool(viewer and viewer.id == target.id),
            'posts': posts_out(request, db, posts, viewer)}


@router.get('/social/me/saved')
def saved(request: Request, user=Depends(current), db: Session = Depends(get_db)):
    ids = select(SocialInteraction.post_id).where(SocialInteraction.actor_user_id == user.id, SocialInteraction.interaction_type == 'SAVE',
                                                  SocialInteraction.interaction_status == 'ACTIVE')
    posts = db.scalars(select(SocialPost).where(SocialPost.id.in_(ids), visible_clause(user)).order_by(SocialPost.published_at.desc()).limit(200)).all()
    return {'items': posts_out(request, db, posts, user)}


@router.get('/social/me/reviewable-vehicles')
def reviewable(user=Depends(current), db: Session = Depends(get_db)):
    mine_ = select(Booking.id, Booking.current_scheduled_trip_id).where(Booking.passenger_user_id == user.id, Booking.status != 'CANCELLED').subquery()
    vehicle_ids = db.scalars(select(Trip.vehicle_id).where(Trip.status == 'COMPLETED', or_(
        Trip.booking_id.in_(select(mine_.c.id)), Trip.scheduled_trip_id.in_(select(mine_.c.current_scheduled_trip_id)))).distinct()).all()
    items = []
    for vehicle_id in vehicle_ids:
        vehicle = db.get(Vehicle, vehicle_id)
        items.append({'vehicle_id': str(vehicle_id), 'name': ' '.join(filter(None, [getattr(vehicle, 'make', None), getattr(vehicle, 'model', None)])) or None,
                      'already_reviewed': reviewed(db, user.id, vehicle_id)})
    return {'items': items}


@router.get('/social/vehicles/{vehicle_id}/reviews')
def vehicle_reviews(vehicle_id: UUID, request: Request, db: Session = Depends(get_db)):
    viewer = maybe_user(request, db)
    posts = db.scalars(select(SocialPost).where(visible_clause(viewer), SocialPost.post_type == 'REVIEW', SocialPost.linked_vehicle_id == vehicle_id)
                       .order_by(SocialPost.published_at.desc()).limit(100)).all()
    stars = db.execute(select(func.avg(SocialInteraction.rating), func.count()).select_from(SocialInteraction)
                       .join(SocialPost, SocialPost.id == SocialInteraction.post_id)
                       .where(SocialPost.linked_vehicle_id == vehicle_id, SocialPost.post_type == 'REVIEW', SocialPost.moderation_status == 'APPROVED',
                              SocialPost.visibility == 'PUBLIC', SocialInteraction.interaction_type == 'RATING',
                              SocialInteraction.interaction_status == 'ACTIVE')).one()
    average = None if stars[0] is None else str(Decimal(stars[0]).quantize(Decimal('0.1')))
    return {'vehicle_id': str(vehicle_id), 'average_rating': average, 'rating_count': stars[1], 'items': posts_out(request, db, posts, viewer)}


# ------------------------------------------------------------------------------------------------------- Admin

@router.get('/admin/social/posts')
def admin_posts(request: Request, user=Depends(admin), db: Session = Depends(get_db)):
    params = dict(request.query_params)
    if not set(params) <= {'status', 'reported'}:
        raise ApiError(422, 'VALIDATION_ERROR', 'Unknown filter.')
    query = select(SocialPost)
    if params.get('status'):
        if params['status'].upper() not in ('APPROVED', 'HIDDEN', 'PENDING', 'REJECTED'): raise ApiError(422, 'VALIDATION_ERROR', 'Unknown status.')
        query = query.where(SocialPost.moderation_status == params['status'].upper())
    reports = select(SocialInteraction.post_id).where(SocialInteraction.interaction_type == 'REPORT', SocialInteraction.interaction_status == 'UNDER_REVIEW')
    if params.get('reported') in ('true', '1'):
        query = query.where(SocialPost.id.in_(reports))
    rows = db.scalars(query.order_by(SocialPost.created_at.desc()).limit(200)).all()
    items = posts_out(request, db, rows, user)
    open_reports = {}
    if rows:
        for post_id, reason, created in db.execute(select(SocialInteraction.post_id, SocialInteraction.report_reason, SocialInteraction.created_at).where(
                SocialInteraction.post_id.in_([r.id for r in rows]), SocialInteraction.interaction_type == 'REPORT',
                SocialInteraction.interaction_status == 'UNDER_REVIEW').order_by(SocialInteraction.created_at)):
            open_reports.setdefault(str(post_id), []).append({'reason': reason, 'reported_at': created.isoformat()})
    for item in items:
        media, thumb = (f"/api/v1/social/posts/{item['id']}/{k}?t={social_media.sign(request.app.state.settings, item['id'], k)}"
                        for k in ('media', 'thumbnail'))
        item['media_url'] = media if item['media_url'] else None
        item['thumbnail_url'] = thumb if item['thumbnail_url'] else None
        item['open_reports'] = open_reports.get(item['id'], [])
    return {'items': items}


class Moderation(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    expected_version: int = Field(ge=1)
    action: Literal['HIDE', 'RESTORE']
    reason: Optional[str] = Field(default=None, min_length=1, max_length=2000)


@router.post('/admin/social/posts/{post_id}/moderation')
def moderate(post_id: UUID, body: Moderation, request: Request, user=Depends(admin), db: Session = Depends(get_db)):
    if not body.reason:
        raise ApiError(422, 'REASON_REQUIRED', 'Give the reason.', [{'field': 'reason', 'message': 'Required.'}])
    with request.app.state.audit.coordinated():
        locked_authority(db, request, user, user.id)
        post = db.scalar(select(SocialPost).where(SocialPost.id == post_id).with_for_update().execution_options(populate_existing=True))
        if not post:
            raise missing()
        if post.version != body.expected_version:
            raise ApiError(409, 'VERSION_CONFLICT', 'The post changed. Reload before deciding.')
        target = 'HIDDEN' if body.action == 'HIDE' else 'APPROVED'
        if post.moderation_status == target:
            raise ApiError(409, 'NO_CHANGE', 'The post is already ' + target.lower() + '.')
        before_status, before_version = post.moderation_status, post.version
        post.moderation_status = target
        if target == 'APPROVED' and post.published_at is None:
            post.published_at = now()
        touch(post); post.updated_by = user.id
        for open_report in db.scalars(select(SocialInteraction).where(SocialInteraction.post_id == post.id, SocialInteraction.interaction_type == 'REPORT',
                                                                      SocialInteraction.interaction_status == 'UNDER_REVIEW')):
            open_report.interaction_status = 'RESOLVED'; touch(open_report); open_report.updated_by = user.id
        request.app.state.audit.commit(db, actor=user.id, target={'resource': 'social_posts', 'id': str(post.id)},
                                       previous_status=before_status, new_status=target, previous_version=before_version,
                                       new_version=post.version, full_reason=body.reason, previous_decision_evidence=None,
                                       trace_id=request.state.trace_id)
    return {'id': str(post.id), 'moderation_status': post.moderation_status, 'version': post.version}
