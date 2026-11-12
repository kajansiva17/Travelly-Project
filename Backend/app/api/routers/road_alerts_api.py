"""Road alerts (PRD matrix 86-89, data dictionary table 20, owner decisions 12 Nov 2026).

    POST /road-alerts                         the assigned Driver of an active trip (a self-driving Owner is that Driver)
                                              reports police, a speed check, an accident, a roadblock or a road hazard
    POST /road-alerts/voice-classify          turns what the Driver said (en/ta/si) into an alert type; stores nothing
    GET  /road-alerts?trip_id=                live alerts within 15 km of that active trip, for its Driver, Owner and
                                              Passengers, worded in each person's language
    POST /road-alerts/{id}/votes              a nearby Driver says "still there" (CONFIRM) or "not there" (DENY)
    GET  /admin/road-alerts[?status=]         Admin moderation list
    POST /admin/road-alerts/{id}/moderation   Admin VERIFY / REJECT / REMOVE (audited)

Rules:
- Who reports: only the trip's assigned Driver, while the trip is IN_PROGRESS, BREAKDOWN or ASSISTANCE_REQUIRED.
  Driving needs the approved DRIVER role, so a self-driving Owner qualifies and an Owner-only person does not.
- The reported point must be near the trip's latest live position, when that position is recent.
- Voice: the transcript is classified with keywords; the alert is created only after the Driver confirms
  (`driver_confirmed: true`). Listeners never hear the Driver's own words. They hear a fixed sentence for the alert
  type in their own preferred language (en/ta/si), so a Tamil report reaches a Sinhala driver in Sinhala.
- Expiry per type (settings, defaults police and speed check 60 min, accident and hazard 120, roadblock 180). A
  confirmation extends it.
- Status from nearby Drivers' answers:
  - Starts UNCONFIRMED.
  - 1 confirmation → ACTIVE; 3 → VERIFIED.
  - 2 denials → REJECTED.
  - Each Driver answers once. The answer is kept on that Driver's ROAD_ALERT notification (response_code), so no
    extra table is needed.
- Nearby people (15 km from their active trip's live position) get a ROAD_ALERT notification, with `speak` text in
  their language for the speaker.
"""
import math
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from app.api.routers.api import current, require_role, touch
from app.api.routers.review_api import admin, locked_authority
from app.core.config import get_settings
from app.core.errors import ApiError
from app.dependencies.database import get_db
from app.models import User
from app.models.hire_models import Booking, Notification, Trip
from app.models.road_alert_models import RoadAlert
from app.schemas.road_alert_schemas import AlertModeration, AlertVote, RoadAlertIn, VoiceText

router = APIRouter(prefix='/api/v1', tags=['Road alerts'])
ACTIVE_TRIP = ('IN_PROGRESS', 'BREAKDOWN', 'ASSISTANCE_REQUIRED')
LIVE = ('UNCONFIRMED', 'ACTIVE', 'VERIFIED')
FRESH_POSITION = timedelta(minutes=30)
NEAR_TRIP_KM = 3
SAME_PLACE_KM = 0.3

MESSAGES = {
    'POLICE_PRESENCE': {'en': 'Police ahead. Drive carefully.',
                        'ta': 'முன்னால் போலீஸ் இருக்கிறார்கள். கவனமாக ஓட்டுங்கள்.',
                        'si': 'ඉදිරියෙන් පොලිසිය සිටී. ප්‍රවේශමෙන් රිය පදවන්න.'},
    'SPEED_CHECK': {'en': 'Speed check ahead. Slow down.',
                    'ta': 'முன்னால் வேக சோதனை. வேகத்தைக் குறையுங்கள்.',
                    'si': 'ඉදිරියෙන් වේග පරීක්ෂාවක්. වේගය අඩු කරන්න.'},
    'ACCIDENT': {'en': 'Accident ahead. Slow down.',
                 'ta': 'முன்னால் விபத்து. வேகத்தைக் குறையுங்கள்.',
                 'si': 'ඉදිරියෙන් අනතුරක්. වේගය අඩු කරන්න.'},
    'ROADBLOCK': {'en': 'Road blocked ahead. Expect delays.',
                  'ta': 'முன்னால் சாலை மூடப்பட்டுள்ளது. தாமதம் ஏற்படலாம்.',
                  'si': 'ඉදිරියෙන් මාර්ගය අවහිරයි. ප්‍රමාද විය හැක.'},
    'ROAD_HAZARD': {'en': 'Road hazard ahead. Drive carefully.',
                    'ta': 'முன்னால் சாலையில் ஆபத்து. கவனமாக ஓட்டுங்கள்.',
                    'si': 'ඉදිරියෙන් මාර්ගයේ අවදානමක්. ප්‍රවේශමෙන් රිය පදවන්න.'},
}
TITLES = {'en': 'Road alert', 'ta': 'சாலை எச்சரிக்கை', 'si': 'මාර්ග අනතුරු ඇඟවීම'}
NAMES = {
    'POLICE_PRESENCE': {'en': 'Police', 'ta': 'போலீஸ்', 'si': 'පොලිසිය'},
    'SPEED_CHECK': {'en': 'Speed check', 'ta': 'வேக சோதனை', 'si': 'වේග පරීක්ෂාව'},
    'ACCIDENT': {'en': 'Accident', 'ta': 'விபத்து', 'si': 'අනතුර'},
    'ROADBLOCK': {'en': 'Roadblock', 'ta': 'சாலை மூடல்', 'si': 'මාර්ග අවහිරය'},
    'ROAD_HAZARD': {'en': 'Road hazard', 'ta': 'சாலை ஆபத்து', 'si': 'මාර්ග අවදානම'},
}
CONFIRM_PROMPT = {'en': 'Send a {name} alert?', 'ta': '{name} எச்சரிக்கை அனுப்பவா?', 'si': '{name} අනතුරු ඇඟවීමක් යවන්නද?'}
# Voice keywords per alert type (lower case; Tamil and Sinhala as spoken, plus common English loan words).
KEYWORDS = {
    'SPEED_CHECK': ['speed', 'radar', 'speed check', 'speed gun', 'வேக', 'ஸ்பீட்', 'ரேடார்', 'වේග', 'ස්පීඩ්', 'රේඩාර්'],
    'POLICE_PRESENCE': ['police', 'cop', 'cops', 'checkpoint', 'போலீஸ்', 'பொலிஸ்', 'காவல்', 'பொலீஸ்', 'පොලිස්', 'පොලීසි', 'පොලිසිය', 'පොලීසිය'],
    'ACCIDENT': ['accident', 'crash', 'collision', 'விபத்து', 'ஆக்சிடென்ட்', 'ஆக்ஸிடென்ட்', 'மோதல்', 'අනතුර', 'ඇක්සිඩන්ට්', 'හැප්පීම', 'හැප්පිලා'],
    'ROADBLOCK': ['roadblock', 'road block', 'blocked', 'closed', 'road closed', 'மூடப்பட்ட', 'மூடியிருக்கு', 'அடைப்பு', 'ரோட் பிளாக்', 'தடை',
                  'අවහිර', 'වහලා', 'වසා', 'රෝඩ් බ්ලොක්'],
    'ROAD_HAZARD': ['hazard', 'pothole', 'flood', 'tree', 'landslide', 'debris', 'oil', 'animal', 'பள்ளம்', 'வெள்ளம்', 'மரம்', 'மண்சரிவு',
                    'ஆபத்து', 'වළ', 'ගංවතුර', 'ගහ', 'ගස', 'නායයෑම', 'අවදානම'],
}


def now():
    return datetime.now(timezone.utc)


def lang(user):
    return user.preferred_language if user and user.preferred_language in ('en', 'ta', 'si') else 'en'


def km_between(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(lambda v: math.radians(float(v)), (lat1, lon1, lat2, lon2))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(min(1.0, h)))


def box(lat, lon, radius_km):
    """Bounding box for the B-tree (latitude, longitude) index; the exact distance is checked afterwards."""
    dlat = radius_km / 111.0
    dlon = radius_km / max(1e-6, 111.0 * math.cos(math.radians(float(lat))))
    return (Decimal(str(float(lat) - dlat)), Decimal(str(float(lat) + dlat)),
            Decimal(str(float(lon) - dlon)), Decimal(str(float(lon) + dlon)))


def minutes_for(alert_type, settings):
    return getattr(settings, 'road_alert_minutes_' + alert_type.lower())


def fresh_position(trip, moment):
    if trip.current_latitude is None or trip.current_longitude is None or not trip.location_updated_at:
        return None
    if moment - trip.location_updated_at > FRESH_POSITION:
        return None
    return trip.current_latitude, trip.current_longitude


def expire_old(db, moment):
    db.execute(update(RoadAlert).where(RoadAlert.status.in_(LIVE), RoadAlert.expires_at <= moment)
               .values(status='EXPIRED', updated_at=moment, version=RoadAlert.version + 1))


def trip_people(db, trip):
    """Driver, operating Owner and Passengers of one trip (private hire or ticket departure)."""
    people = {trip.driver_user_id, trip.operating_owner_user_id}
    if trip.booking_id:
        people.add(db.scalar(select(Booking.passenger_user_id).where(Booking.id == trip.booking_id)))
    if trip.scheduled_trip_id:
        people.update(db.scalars(select(Booking.passenger_user_id).where(Booking.current_scheduled_trip_id == trip.scheduled_trip_id,
                                                                         Booking.status.in_(('CONFIRMED', 'IN_PROGRESS')))).all())
    people.discard(None)
    return people


def nearby_trips(db, lat, lon, radius_km, moment):
    s, n, w, e = box(lat, lon, radius_km)
    rows = db.scalars(select(Trip).where(Trip.status.in_(ACTIVE_TRIP), Trip.current_latitude.between(s, n),
                                         Trip.current_longitude.between(w, e), Trip.location_updated_at >= moment - FRESH_POSITION)).all()
    return [(t, km_between(lat, lon, t.current_latitude, t.current_longitude)) for t in rows
            if km_between(lat, lon, t.current_latitude, t.current_longitude) <= radius_km]


def alert_out(alert, viewer=None, distance=None, my_vote=None, can_vote=False):
    language = lang(viewer)
    return {'id': str(alert.id), 'alert_type': alert.alert_type, 'status': alert.status, 'version': alert.version,
            'latitude': format(alert.latitude, '.6f'), 'longitude': format(alert.longitude, '.6f'),
            'travel_direction_degrees': None if alert.travel_direction_degrees is None else format(alert.travel_direction_degrees, '.3f'),
            'source_input': alert.source_input, 'confirmation_count': alert.confirmation_count, 'denial_count': alert.denial_count,
            'reported_at': alert.reported_at.isoformat(), 'expires_at': alert.expires_at.isoformat(),
            'verified_at': alert.verified_at.isoformat() if alert.verified_at else None,
            'distance_km': None if distance is None else round(distance, 1),
            'language': language, 'name': NAMES[alert.alert_type][language], 'message': MESSAGES[alert.alert_type][language],
            'my_vote': my_vote, 'can_vote': can_vote}


def notify_nearby(db, alert, reporter_id, settings, moment):
    sent = 0
    seen = set()
    for trip, distance in nearby_trips(db, alert.latitude, alert.longitude, settings.road_alert_radius_km, moment):
        for person in trip_people(db, trip):
            if person == reporter_id or person in seen:
                continue
            seen.add(person)
            user = db.get(User, person)
            language = lang(user)
            db.add(Notification(recipient_user_id=person, trip_id=trip.id, notification_type='ROAD_ALERT', channel='IN_APP',
                                title=TITLES[language], body=f"{MESSAGES[alert.alert_type][language]} ({distance:.1f} km)",
                                action_required=False, status='QUEUED', expires_at=alert.expires_at,
                                action_payload={'road_alert_id': str(alert.id), 'alert_type': alert.alert_type,
                                                'latitude': format(alert.latitude, '.6f'), 'longitude': format(alert.longitude, '.6f'),
                                                'distance_km': round(distance, 1), 'language': language,
                                                'speak': MESSAGES[alert.alert_type][language]}))
            sent += 1
    return sent


def driving(db, trip_id, user):
    trip = db.get(Trip, trip_id)
    if not trip or trip.driver_user_id != user.id:
        raise ApiError(404, 'TRIP_NOT_FOUND', 'Trip not found.')
    if trip.status not in ACTIVE_TRIP:
        raise ApiError(409, 'TRIP_NOT_ACTIVE', 'Road alerts can be reported only during a trip you are driving.')
    return trip


def record_vote(db, alert, user, vote, settings, moment, trip=None):
    """One answer per Driver, kept on that Driver's ROAD_ALERT notification. Returns False if they already answered."""
    note = db.scalar(select(Notification).where(Notification.recipient_user_id == user.id, Notification.notification_type == 'ROAD_ALERT',
                                                Notification.action_payload['road_alert_id'].astext == str(alert.id))
                     .order_by(Notification.created_at).limit(1).with_for_update())
    if note and note.response_code:
        return False
    if note is None:
        language = lang(user)
        note = Notification(recipient_user_id=user.id, trip_id=trip.id if trip else None, notification_type='ROAD_ALERT',
                            channel='IN_APP', title=TITLES[language], body=MESSAGES[alert.alert_type][language],
                            action_required=False, status='QUEUED', expires_at=alert.expires_at,
                            action_payload={'road_alert_id': str(alert.id), 'alert_type': alert.alert_type, 'language': language})
        db.add(note)
    note.response_code, note.response_value, note.responded_at, note.status = vote, vote.lower(), moment, 'RESPONDED'
    if vote == 'CONFIRM':
        alert.confirmation_count += 1
        alert.expires_at = max(alert.expires_at, moment + timedelta(minutes=minutes_for(alert.alert_type, settings)))
        if alert.confirmation_count >= settings.road_alert_verified_after_confirmations:
            alert.status, alert.verified_at = 'VERIFIED', alert.verified_at or moment
        elif alert.confirmation_count >= settings.road_alert_active_after_confirmations and alert.status == 'UNCONFIRMED':
            alert.status = 'ACTIVE'
    else:
        alert.denial_count += 1
        if alert.denial_count >= settings.road_alert_removed_after_denials and alert.status != 'VERIFIED':
            alert.status = 'REJECTED'
            alert.moderation_reason = f'{alert.denial_count} nearby drivers said it is not there.'
    touch(alert); alert.updated_by = user.id
    return True


# --------------------------------------------------------------------------- report

@router.post('/road-alerts/voice-classify')
def voice_classify(body: VoiceText, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    require_role(db, user, 'DRIVER')
    request.app.state.store.rate(f'road-alert-voice:{user.id}', 30, 600)
    text_ = ' ' + body.transcript.lower() + ' '
    scores = {kind: sum(len(word) for word in words if word in text_) for kind, words in KEYWORDS.items()}
    ranked = sorted(((score, kind) for kind, score in scores.items() if score), reverse=True)
    if not ranked:
        return {'alert_type': None, 'confidence': 0, 'candidates': [], 'confirm_prompt': None,
                'message': 'Not understood. Choose the alert with a button.'}
    total = sum(score for score, _ in ranked)
    best = ranked[0][1]
    confidence = round(ranked[0][0] / total, 4)
    return {'alert_type': best, 'confidence': confidence,
            'candidates': [{'alert_type': kind, 'name': NAMES[kind][body.language]} for _, kind in ranked],
            'confirm_prompt': CONFIRM_PROMPT[body.language].format(name=NAMES[best][body.language]), 'message': None}


@router.post('/road-alerts', status_code=201)
def report(body: RoadAlertIn, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    require_role(db, user, 'DRIVER')
    if body.source_input == 'VOICE' and not body.driver_confirmed:
        raise ApiError(422, 'DRIVER_CONFIRMATION_REQUIRED', 'Confirm the alert type that was understood before it is sent.')
    settings, moment = get_settings(), now()
    request.app.state.store.rate(f'road-alert:{user.id}', 10, 600)
    trip = driving(db, body.trip_id, user)
    position = fresh_position(trip, moment)
    if position and km_between(body.latitude, body.longitude, *position) > NEAR_TRIP_KM:
        raise ApiError(422, 'ALERT_TOO_FAR', 'An alert must be reported where your trip is now.',
                       [{'field': 'latitude', 'message': 'Too far from the trip position.'}])
    expire_old(db, moment)
    s, n, w, e = box(body.latitude, body.longitude, SAME_PLACE_KM)
    same = [a for a in db.scalars(select(RoadAlert).where(RoadAlert.alert_type == body.alert_type, RoadAlert.status.in_(LIVE),
                                                          RoadAlert.latitude.between(s, n), RoadAlert.longitude.between(w, e))
                                  .order_by(RoadAlert.reported_at).with_for_update())
            if km_between(body.latitude, body.longitude, a.latitude, a.longitude) <= SAME_PLACE_KM]
    if same:
        # The same thing at the same place is already up: a second report is a confirmation, never a duplicate.
        alert = same[0]
        counted = alert.reporter_user_id != user.id and record_vote(db, alert, user, 'CONFIRM', settings, moment, trip)
        db.commit()
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=200, content={**alert_out(alert, user), 'merged': True, 'counted_as_confirmation': bool(counted)})
    alert = RoadAlert(reporter_user_id=user.id, trip_id=trip.id, alert_type=body.alert_type, latitude=body.latitude,
                      longitude=body.longitude, travel_direction_degrees=body.travel_direction_degrees, description=body.description,
                      source_input=body.source_input, status='UNCONFIRMED',
                      confidence_score=body.confidence_score if body.source_input == 'VOICE' else None,
                      reported_at=moment, expires_at=moment + timedelta(minutes=minutes_for(body.alert_type, settings)),
                      created_by=user.id, updated_by=user.id)
    db.add(alert)
    db.flush()
    notified = notify_nearby(db, alert, user.id, settings, moment)
    db.commit()
    return {**alert_out(alert, user), 'merged': False, 'notified': notified}


# --------------------------------------------------------------------------- read and answer

@router.get('/road-alerts')
def nearby(request: Request, user=Depends(current), db: Session = Depends(get_db)):
    try:
        trip_id = UUID(request.query_params.get('trip_id', ''))
    except ValueError:
        raise ApiError(422, 'VALIDATION_ERROR', 'trip_id is required.', [{'field': 'trip_id', 'message': 'Required.'}]) from None
    trip = db.get(Trip, trip_id)
    if not trip or user.id not in trip_people(db, trip):
        raise ApiError(404, 'TRIP_NOT_FOUND', 'Trip not found.')
    settings, moment = get_settings(), now()
    expire_old(db, moment)
    db.commit()
    position = fresh_position(trip, moment) if trip.status in ACTIVE_TRIP else None
    if not position:
        return {'trip_id': str(trip.id), 'radius_km': settings.road_alert_radius_km, 'items': [],
                'note': 'Road alerts appear while the trip is running and sharing its position.'}
    s, n, w, e = box(position[0], position[1], settings.road_alert_radius_km)
    rows = db.scalars(select(RoadAlert).where(RoadAlert.status.in_(LIVE), RoadAlert.expires_at > moment,
                                              RoadAlert.latitude.between(s, n), RoadAlert.longitude.between(w, e))).all()
    votes = {n.action_payload.get('road_alert_id'): n.response_code for n in db.scalars(select(Notification).where(
        Notification.recipient_user_id == user.id, Notification.notification_type == 'ROAD_ALERT', Notification.response_code.is_not(None)))}
    items = []
    for alert in rows:
        distance = km_between(position[0], position[1], alert.latitude, alert.longitude)
        if distance > settings.road_alert_radius_km:
            continue
        mine = votes.get(str(alert.id))
        can = trip.driver_user_id == user.id and alert.reporter_user_id != user.id and mine is None
        items.append(alert_out(alert, user, distance, mine, can))
    items.sort(key=lambda i: i['distance_km'])
    return {'trip_id': str(trip.id), 'radius_km': settings.road_alert_radius_km, 'items': items, 'note': None}


@router.post('/road-alerts/{alert_id}/votes')
def vote(alert_id: UUID, body: AlertVote, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    require_role(db, user, 'DRIVER')
    settings, moment = get_settings(), now()
    request.app.state.store.rate(f'road-alert-vote:{user.id}', 60, 600)
    alert = db.scalar(select(RoadAlert).where(RoadAlert.id == alert_id).with_for_update())
    if not alert:
        raise ApiError(404, 'ROAD_ALERT_NOT_FOUND', 'Road alert not found.')
    if alert.status not in LIVE or alert.expires_at <= moment:
        raise ApiError(409, 'ROAD_ALERT_CLOSED', 'This alert is no longer shown.')
    if alert.reporter_user_id == user.id:
        raise ApiError(409, 'OWN_ROAD_ALERT', 'You reported this alert.')
    trip = next((t for t, _ in nearby_trips(db, alert.latitude, alert.longitude, settings.road_alert_radius_km, moment)
                 if t.driver_user_id == user.id), None)
    if not trip:
        raise ApiError(409, 'NOT_NEAR_ROAD_ALERT', 'Only Drivers on a trip near this alert can answer.')
    if not record_vote(db, alert, user, body.vote, settings, moment, trip):
        raise ApiError(409, 'ALREADY_ANSWERED', 'You already answered this alert.')
    db.commit()
    return alert_out(alert, user, km_between(trip.current_latitude, trip.current_longitude, alert.latitude, alert.longitude), body.vote, False)


# --------------------------------------------------------------------------- Admin

@router.get('/admin/road-alerts')
def admin_list(request: Request, user=Depends(admin), db: Session = Depends(get_db)):
    moment = now()
    expire_old(db, moment)
    db.commit()
    status = request.query_params.get('status')
    query = select(RoadAlert).order_by(RoadAlert.reported_at.desc()).limit(200)
    if status:
        query = query.where(RoadAlert.status == status.upper())
    items = []
    for alert in db.scalars(query):
        reporter = db.get(User, alert.reporter_user_id)
        items.append({**alert_out(alert, user), 'description': alert.description, 'confidence_score':
                      None if alert.confidence_score is None else format(alert.confidence_score, '.4f'),
                      'reporter': {'public_user_reference': reporter.public_user_reference,
                                   'display_name': reporter.display_name or reporter.full_name} if reporter else None,
                      'trip_id': str(alert.trip_id) if alert.trip_id else None, 'moderation_reason': alert.moderation_reason})
    return {'items': items}


@router.post('/admin/road-alerts/{alert_id}/moderation')
def moderate(alert_id: UUID, body: AlertModeration, request: Request, user=Depends(admin), db: Session = Depends(get_db)):
    if body.action in ('REJECT', 'REMOVE') and not body.reason:
        raise ApiError(422, 'REASON_REQUIRED', 'Give the reason.', [{'field': 'reason', 'message': 'Required.'}])
    with request.app.state.audit.coordinated():
        locked_authority(db, request, user, user.id)
        alert = db.scalar(select(RoadAlert).where(RoadAlert.id == alert_id).with_for_update().execution_options(populate_existing=True))
        if not alert:
            raise ApiError(404, 'ROAD_ALERT_NOT_FOUND', 'Road alert not found.')
        if alert.version != body.expected_version:
            raise ApiError(409, 'VERSION_CONFLICT', 'The alert changed. Reload before deciding.')
        if alert.status in ('REJECTED', 'REMOVED'):
            raise ApiError(409, 'ROAD_ALERT_CLOSED', 'This alert was already taken down.')
        before_version, before_status, moment = alert.version, alert.status, now()
        if body.action == 'VERIFY':
            if alert.status == 'EXPIRED' or alert.expires_at <= moment:
                raise ApiError(409, 'ROAD_ALERT_CLOSED', 'An expired alert cannot be verified.')
            alert.status, alert.verified_at = 'VERIFIED', alert.verified_at or moment
        else:
            alert.status = 'REJECTED' if body.action == 'REJECT' else 'REMOVED'
        alert.moderated_by_user_id, alert.moderation_reason = user.id, body.reason or alert.moderation_reason
        touch(alert); alert.updated_by = user.id
        request.app.state.audit.commit(db, actor=user.id, target={'resource': 'road_alerts', 'id': str(alert.id)},
                                       previous_status=before_status, new_status=alert.status, previous_version=before_version,
                                       new_version=alert.version, full_reason=body.reason or 'Verified by Admin.',
                                       previous_decision_evidence=None, trace_id=request.state.trace_id)
    return alert_out(alert, user)
