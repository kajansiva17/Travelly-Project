"""Passenger saved places (sidebar > Saved Places): up to MAX_PLACES named places such as Home or Work. The person searches and selects a real
location once (the server checks its proof); afterwards it is one tap when booking. The list gives each place a fresh proof so it can be used
as a pickup or destination straight away. Nothing about a booking, price or vehicle changes."""
from uuid import UUID
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.api.routers.api import current
from app.core.errors import ApiError
from app.dependencies.database import get_db
from app.models.ride_models import ride_requests_table
from app.models.saved_place_models import SavedPlace
from app.schemas.rate_schemas import Place

router = APIRouter(prefix='/api/v1', tags=['Saved places'])
MAX_PLACES = 10


class NewPlace(BaseModel):
    name: str = Field(min_length=1, max_length=30)
    place: Place


def out(request, row):
    return {'id': str(row.id), 'name': row.name, 'place': request.app.state.rate_locations.signed(row.place_label, row.latitude, row.longitude)}


@router.get('/me/saved-places')
def list_places(request: Request, user=Depends(current), db: Session = Depends(get_db)):
    rows = db.scalars(select(SavedPlace).where(SavedPlace.user_id == user.id).order_by(SavedPlace.created_at)).all()
    return {'items': [out(request, row) for row in rows], 'limit': MAX_PLACES}


@router.get('/me/saved-places/suggestions')
def suggest_places(request: Request, user=Depends(current), db: Session = Depends(get_db)):
    """Places this Passenger recently went to by Book now and has not saved yet; one tap saves one (the Passenger names it)."""
    saved = {row.place_label for row in db.scalars(select(SavedPlace).where(SavedPlace.user_id == user.id)).all()}
    rows = db.execute(select(ride_requests_table.c.destination).where(ride_requests_table.c.passenger_user_id == user.id)
                      .order_by(ride_requests_table.c.created_at.desc()).limit(60)).all()
    items, seen = [], set()
    for (destination,) in rows:
        try:
            label = str(destination['label'])[:200]
            latitude, longitude = float(destination['latitude']), float(destination['longitude'])
        except (KeyError, TypeError, ValueError):
            continue
        if not label or label in saved or label in seen:
            continue
        seen.add(label)
        items.append(request.app.state.rate_locations.signed(label, latitude, longitude))
        if len(items) == 5:
            break
    return {'items': items}


@router.post('/me/saved-places', status_code=201)
def add_place(body: NewPlace, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    name = body.name.strip()
    if not name:
        raise ApiError(422, 'VALIDATION_ERROR', 'Give the place a name.', [{'field': 'name', 'message': 'Give the place a name.'}])
    request.app.state.rate_locations.verify(body.place)
    if (db.scalar(select(func.count()).select_from(SavedPlace).where(SavedPlace.user_id == user.id)) or 0) >= MAX_PLACES:
        raise ApiError(409, 'SAVED_PLACES_FULL', f'You can keep up to {MAX_PLACES} saved places. Remove one first.')
    row = SavedPlace(user_id=user.id, name=name, place_label=body.place.label, latitude=body.place.latitude, longitude=body.place.longitude)
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ApiError(409, 'SAVED_PLACE_EXISTS', 'You already have a place with this name.', [{'field': 'name', 'message': 'You already have a place with this name.'}]) from None
    return out(request, row)


@router.delete('/me/saved-places/{place_id}')
def remove_place(place_id: UUID, user=Depends(current), db: Session = Depends(get_db)):
    row = db.get(SavedPlace, place_id)
    if not row or row.user_id != user.id:
        raise ApiError(404, 'PLACE_NOT_FOUND', 'This saved place was not found.')
    db.delete(row)
    db.commit()
    return {'id': str(place_id), 'removed': True}
