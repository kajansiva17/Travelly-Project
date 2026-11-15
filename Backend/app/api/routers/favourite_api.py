"""Favourite vehicles: a Passenger's own bookmarks of vehicles they hire often (sidebar > Favourite vehicles).
A bookmark changes no booking, price or availability. The list shows only vehicles that can still be hired today."""
from uuid import UUID
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.api.routers.api import current
from app.core.errors import ApiError
from app.dependencies.database import get_db
from app.models import User
from app.models.hire_models import FavouriteVehicle
from app.models.review_models import Vehicle
from app.services.hire_services import eligible_vehicle

router = APIRouter(prefix='/api/v1', tags=['Favourite vehicles'])
MAX_FAVOURITES = 30


def hireable(db, vehicle):
    try:
        eligible_vehicle(db, vehicle, public=True)
        return True
    except ApiError as exc:
        if exc.status == 503:
            raise
        return False


@router.get('/me/favourite-vehicles')
def list_favourites(user=Depends(current), db: Session = Depends(get_db)):
    from app.api.routers.hire_api import safe_vehicle
    rows = db.execute(select(FavouriteVehicle, Vehicle).join(Vehicle, Vehicle.id == FavouriteVehicle.vehicle_id)
                      .where(FavouriteVehicle.user_id == user.id).order_by(FavouriteVehicle.created_at.desc())).all()
    items = []
    for fav, vehicle in rows:
        if hireable(db, vehicle):
            items.append({**safe_vehicle(vehicle, db.get(User, vehicle.owner_user_id)), 'available': True})
        else:   # kept as a bookmark, but not hireable now (for example switched off by its Owner)
            items.append({'id': str(vehicle.id), 'make': vehicle.make, 'model': vehicle.model, 'available': False, 'photos': []})
    return {'items': items, 'ids': [i['id'] for i in items]}


@router.put('/me/favourite-vehicles/{vehicle_id}')
def add_favourite(vehicle_id: UUID, user=Depends(current), db: Session = Depends(get_db)):
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle or not hireable(db, vehicle):
        raise ApiError(404, 'VEHICLE_NOT_FOUND', 'Vehicle not found.')
    if db.scalar(select(FavouriteVehicle.id).where(FavouriteVehicle.user_id == user.id, FavouriteVehicle.vehicle_id == vehicle_id)):
        return {'id': str(vehicle_id), 'favourite': True}
    if (db.scalar(select(func.count()).select_from(FavouriteVehicle).where(FavouriteVehicle.user_id == user.id)) or 0) >= MAX_FAVOURITES:
        raise ApiError(409, 'FAVOURITES_FULL', f'You can keep up to {MAX_FAVOURITES} favourite vehicles. Remove one first.')
    db.add(FavouriteVehicle(user_id=user.id, vehicle_id=vehicle_id))
    db.commit()
    return {'id': str(vehicle_id), 'favourite': True}


@router.delete('/me/favourite-vehicles/{vehicle_id}')
def remove_favourite(vehicle_id: UUID, user=Depends(current), db: Session = Depends(get_db)):
    row = db.scalar(select(FavouriteVehicle).where(FavouriteVehicle.user_id == user.id, FavouriteVehicle.vehicle_id == vehicle_id))
    if row:
        db.delete(row)
        db.commit()
    return {'id': str(vehicle_id), 'favourite': False}
