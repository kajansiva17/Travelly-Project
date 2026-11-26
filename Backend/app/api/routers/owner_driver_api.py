"""My drivers: the people an Owner can offer a trip to, and how they get there.

 * A Driver asks an Owner to list them, using the Owner's Travelly reference (Driver > My owners).
 * An Owner can instead invite a Driver by the Driver's Travelly reference (Owner > My drivers).
 * The other side accepts or declines. Either side can remove the link at any time (it deletes only this link).

It is not a permanent Owner-Driver relationship and gives nobody anything: every trip still needs the licence check and the Driver's own
acceptance. Only ACTIVE links appear in the "Who will drive?" choices."""
from uuid import UUID
import re
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, func, or_, String
from sqlalchemy.orm import Session
from app.api.routers.api import current, require_role
from app.core.errors import ApiError
from app.dependencies.database import get_db
from app.models import User
from app.models.hire_models import OwnerDriver, Notification, Trip
from app.models.review_models import Vehicle
from app.services.hire_services import approved

router = APIRouter(prefix='/api/v1', tags=['My drivers'])
MAX_LINKS = 50
REF = r'^USR-[0-9A-Fa-f]{16}$'


class AddDriver(BaseModel):
    driver_reference: str = Field(pattern=REF)
    nickname: str | None = Field(default=None, max_length=60)


class AskOwner(BaseModel):
    owner_reference: str = Field(pattern=REF)


def tell(db, user_id, title, body):
    db.add(Notification(recipient_user_id=user_id, notification_type='DRIVER_ASSIGNMENT', channel='IN_APP', title=title, body=body,
                        action_required=False, action_payload={'kind': 'OWNER_DRIVER_LINK'}, status='QUEUED'))


def live_state(db, driver):
    """Is the Driver sending a vehicle's position right now (online), and are they on a trip that has started."""
    from datetime import datetime, timezone
    from app.api.routers.live_vehicle_api import is_online
    now = datetime.now(timezone.utc)
    online = any(is_online(v, now) for v in db.scalars(select(Vehicle).where(Vehicle.live_online_user_id == driver.id)))
    on_trip = bool(db.scalar(select(func.count()).select_from(Trip).where(
        Trip.driver_user_id == driver.id, Trip.status.in_(('IN_PROGRESS', 'BREAKDOWN', 'ASSISTANCE_REQUIRED')))))
    return online, on_trip


def owner_row(db, row, driver):
    online, on_trip = live_state(db, driver)
    return {'id': str(row.id), 'driver_user_id': str(driver.id), 'reference': driver.public_user_reference,
            'name': driver.display_name or driver.public_user_reference, 'nickname': row.nickname, 'status': row.status,
            'initiated_by': row.initiated_by, 'is_driver': bool(approved(db, driver.id, 'DRIVER')),
            'profile_image_url': driver.profile_image_url, 'online': online, 'on_trip': on_trip,
            'added_at': row.created_at.isoformat() if row.created_at else None}


def driver_row(row, owner):
    return {'id': str(row.id), 'owner_user_id': str(owner.id), 'reference': owner.public_user_reference,
            'name': owner.display_name or owner.public_user_reference, 'status': row.status, 'initiated_by': row.initiated_by,
            'added_at': row.created_at.isoformat() if row.created_at else None}


def count_links(db, owner_id):
    return db.scalar(select(func.count()).select_from(OwnerDriver).where(OwnerDriver.owner_user_id == owner_id, OwnerDriver.status != 'DECLINED')) or 0


def get_pair(db, owner_id, driver_id):
    return db.scalar(select(OwnerDriver).where(OwnerDriver.owner_user_id == owner_id, OwnerDriver.driver_user_id == driver_id))


# ---------------- Owner side ----------------
@router.get('/owners/me/saved-drivers')
def list_drivers(user=Depends(current), db: Session = Depends(get_db)):
    require_role(db, user, 'OWNER')
    rows = db.execute(select(OwnerDriver, User).join(User, User.id == OwnerDriver.driver_user_id)
                      .where(OwnerDriver.owner_user_id == user.id, OwnerDriver.status != 'DECLINED')
                      .order_by(OwnerDriver.created_at.desc())).all()
    return {'items': [owner_row(db, r, d) for r, d in rows], 'my_reference': user.public_user_reference, 'findable': bool(user.findable_by_drivers)}


class Findable(BaseModel):
    findable: bool


@router.put('/owners/me/findable')
def set_findable(body: Findable, user=Depends(current), db: Session = Depends(get_db)):
    """Owner switch: Drivers can find me by name or number plate (the Travelly reference always works)."""
    require_role(db, user, 'OWNER')
    user.findable_by_drivers = body.findable
    db.commit()
    return {'findable': bool(user.findable_by_drivers)}


@router.post('/owners/me/saved-drivers', status_code=201)
def invite_driver(body: AddDriver, user=Depends(current), db: Session = Depends(get_db)):
    """The Owner invites a Driver by reference. If that Driver had already asked, the link becomes active at once."""
    require_role(db, user, 'OWNER')
    driver = db.scalar(select(User).where(User.public_user_reference == body.driver_reference.upper()))
    if not driver or driver.id == user.id or not approved(db, driver.id, 'DRIVER'):
        raise ApiError(404, 'DRIVER_NOT_FOUND', 'No approved Driver has this Travelly reference.')
    nickname = (body.nickname or '').strip() or None
    row = get_pair(db, user.id, driver.id)
    if row and row.status == 'ACTIVE':
        row.nickname = nickname or row.nickname
    elif row and row.status == 'DRIVER_REQUESTED':
        row.status = 'ACTIVE'; row.nickname = nickname or row.nickname
        tell(db, driver.id, 'You were added to an Owner\'s drivers', f'{user.display_name or user.public_user_reference} accepted your request.')
    elif row:   # OWNER_INVITED again, or DECLINED earlier: ask again
        row.status = 'OWNER_INVITED'; row.initiated_by = 'OWNER'; row.nickname = nickname or row.nickname
        tell(db, driver.id, 'An Owner invited you', f'{user.display_name or user.public_user_reference} invited you to their drivers. Open My owners to accept or decline.')
    else:
        if count_links(db, user.id) >= MAX_LINKS:
            raise ApiError(409, 'DRIVERS_FULL', f'You can keep up to {MAX_LINKS} Drivers in your list. Remove one first.')
        row = OwnerDriver(owner_user_id=user.id, driver_user_id=driver.id, nickname=nickname, status='OWNER_INVITED', initiated_by='OWNER')
        db.add(row)
        tell(db, driver.id, 'An Owner invited you', f'{user.display_name or user.public_user_reference} invited you to their drivers. Open My owners to accept or decline.')
    db.commit()
    return owner_row(db, row, driver)


def owner_decision(db, user, entry_id, accept):
    require_role(db, user, 'OWNER')
    row = db.scalar(select(OwnerDriver).where(OwnerDriver.id == entry_id, OwnerDriver.owner_user_id == user.id))
    if not row or row.status != 'DRIVER_REQUESTED':
        raise ApiError(404, 'REQUEST_NOT_FOUND', 'This request is no longer waiting for you.')
    row.status = 'ACTIVE' if accept else 'DECLINED'
    tell(db, row.driver_user_id, 'Your request was ' + ('accepted' if accept else 'declined'),
         f'{user.display_name or user.public_user_reference} ' + ('added you to their drivers.' if accept else 'declined your request.'))
    db.commit()
    return {'id': str(row.id), 'status': row.status}


@router.post('/owners/me/saved-drivers/{entry_id}/accept')
def accept_request(entry_id: UUID, user=Depends(current), db: Session = Depends(get_db)):
    return owner_decision(db, user, entry_id, True)


@router.post('/owners/me/saved-drivers/{entry_id}/decline')
def decline_request(entry_id: UUID, user=Depends(current), db: Session = Depends(get_db)):
    return owner_decision(db, user, entry_id, False)


@router.delete('/owners/me/saved-drivers/{entry_id}')
def remove_driver(entry_id: UUID, user=Depends(current), db: Session = Depends(get_db)):
    require_role(db, user, 'OWNER')
    row = db.scalar(select(OwnerDriver).where(OwnerDriver.id == entry_id, OwnerDriver.owner_user_id == user.id))
    if row:
        db.delete(row)
        db.commit()
    return {'id': str(entry_id), 'removed': True}


# ---------------- Driver side ----------------
@router.get('/drivers/me/owner-links')
def my_owners(user=Depends(current), db: Session = Depends(get_db)):
    require_role(db, user, 'DRIVER')
    rows = db.execute(select(OwnerDriver, User).join(User, User.id == OwnerDriver.owner_user_id)
                      .where(OwnerDriver.driver_user_id == user.id).order_by(OwnerDriver.created_at.desc())).all()
    return {'items': [driver_row(r, o) for r, o in rows], 'my_reference': user.public_user_reference}


@router.post('/drivers/me/owner-links', status_code=201)
def ask_owner(body: AskOwner, user=Depends(current), db: Session = Depends(get_db)):
    """The Driver asks an Owner (by the Owner's Travelly reference) to list them. If that Owner had already invited them, it becomes active."""
    require_role(db, user, 'DRIVER')
    owner = db.scalar(select(User).where(User.public_user_reference == body.owner_reference.upper()))
    if not owner or owner.id == user.id or not approved(db, owner.id, 'OWNER'):
        raise ApiError(404, 'OWNER_NOT_FOUND', 'No approved Owner has this Travelly reference.')
    row = get_pair(db, owner.id, user.id)
    name = user.display_name or user.public_user_reference
    if row and row.status in ('ACTIVE', 'DRIVER_REQUESTED'):
        pass
    elif row and row.status == 'OWNER_INVITED':
        row.status = 'ACTIVE'
        tell(db, owner.id, 'A Driver joined your drivers', f'{name} accepted your invitation.')
    elif row:   # DECLINED earlier: ask again
        row.status = 'DRIVER_REQUESTED'; row.initiated_by = 'DRIVER'
        tell(db, owner.id, 'A Driver asked to join your drivers', f'{name} sent you a request. Open My drivers to accept or decline.')
    else:
        if count_links(db, owner.id) >= MAX_LINKS:
            raise ApiError(409, 'OWNER_LIST_FULL', 'This Owner cannot take more requests right now.')
        row = OwnerDriver(owner_user_id=owner.id, driver_user_id=user.id, status='DRIVER_REQUESTED', initiated_by='DRIVER')
        db.add(row)
        tell(db, owner.id, 'A Driver asked to join your drivers', f'{name} sent you a request. Open My drivers to accept or decline.')
    db.commit()
    return driver_row(row, owner)


def driver_decision(db, user, entry_id, accept):
    require_role(db, user, 'DRIVER')
    row = db.scalar(select(OwnerDriver).where(OwnerDriver.id == entry_id, OwnerDriver.driver_user_id == user.id))
    if not row or row.status != 'OWNER_INVITED':
        raise ApiError(404, 'INVITATION_NOT_FOUND', 'This invitation is no longer waiting for you.')
    row.status = 'ACTIVE' if accept else 'DECLINED'
    name = user.display_name or user.public_user_reference
    tell(db, row.owner_user_id, 'Your invitation was ' + ('accepted' if accept else 'declined'), f'{name} ' + ('joined your drivers.' if accept else 'declined your invitation.'))
    db.commit()
    return {'id': str(row.id), 'status': row.status}


@router.post('/drivers/me/owner-links/{entry_id}/accept')
def accept_invitation(entry_id: UUID, user=Depends(current), db: Session = Depends(get_db)):
    return driver_decision(db, user, entry_id, True)


@router.post('/drivers/me/owner-links/{entry_id}/decline')
def decline_invitation(entry_id: UUID, user=Depends(current), db: Session = Depends(get_db)):
    return driver_decision(db, user, entry_id, False)


@router.delete('/drivers/me/owner-links/{entry_id}')
def leave_owner(entry_id: UUID, user=Depends(current), db: Session = Depends(get_db)):
    """The Driver cancels a request, leaves an Owner's list or removes an invitation. Deletes only this link."""
    require_role(db, user, 'DRIVER')
    row = db.scalar(select(OwnerDriver).where(OwnerDriver.id == entry_id, OwnerDriver.driver_user_id == user.id))
    if row:
        db.delete(row)
        db.commit()
    return {'id': str(entry_id), 'removed': True}


# ---------------- Driver finds an Owner (like finding a friend) ----------------
def plate_key(text):
    return re.sub(r'[\s\-]+', '', text or '').upper()


def owner_card(db, owner, links, vehicles):
    link = links.get(owner.id)
    return {'reference': owner.public_user_reference, 'name': owner.display_name or owner.full_name,
            'vehicles': vehicles, 'link_status': link.status if link else None, 'link_id': str(link.id) if link else None}


@router.get('/drivers/me/owner-search')
def search_owners(q: str, request: Request, user=Depends(current), db: Session = Depends(get_db)):
    """A Driver looks for an Owner by name (3+ letters), by the exact full number plate of one of their vehicles, or by Travelly reference.
    Only approved Owners who allow it are found. The card shows the name and vehicle kinds only: never a phone, email or the plate."""
    require_role(db, user, 'DRIVER')
    request.app.state.store.rate(f'owner-search:{user.id}', 40, 600)
    text = (q or '').strip()[:60]
    if len(text) < 3:
        raise ApiError(422, 'VALIDATION_ERROR', 'Type at least 3 letters of the name, the full number plate or the Travelly reference.')
    found = {}
    if re.fullmatch(REF, text):                    # Travelly reference: always works, even when the Owner hides from search
        owner = db.scalar(select(User).where(User.public_user_reference == text.upper()))
        if owner:
            found[owner.id] = owner
    else:
        key = plate_key(text)
        plate = func.upper(func.replace(func.replace(func.replace(Vehicle.registration_number.cast(String), ' ', ''), '-', ''), '.', ''))
        if len(key) >= 4 and re.search(r'\d', key):  # exact full number plate only
            for owner in db.scalars(select(User).join(Vehicle, Vehicle.owner_user_id == User.id)
                                    .where(plate == key, Vehicle.archived_at.is_(None), User.findable_by_drivers.is_(True)).limit(5)):
                found[owner.id] = owner
        like = '%' + text.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
        for owner in db.scalars(select(User).where(User.findable_by_drivers.is_(True), or_(User.display_name.ilike(like, escape='\\'), User.full_name.ilike(like, escape='\\')))
                                .order_by(User.full_name).limit(30)):
            found.setdefault(owner.id, owner)
    owners = [o for o in found.values() if o.id != user.id and approved(db, o.id, 'OWNER')][:10]
    links = {l.owner_user_id: l for l in db.scalars(select(OwnerDriver).where(OwnerDriver.driver_user_id == user.id, OwnerDriver.owner_user_id.in_([o.id for o in owners] or [None])))}
    items = []
    for owner in owners:
        kinds = []
        for make, model in db.execute(select(Vehicle.make, Vehicle.model).where(Vehicle.owner_user_id == owner.id, Vehicle.archived_at.is_(None),
                                                                                   Vehicle.verification_status == 'APPROVED').limit(20)):
            label = ' '.join(x for x in (make, model) if x)
            if label and label not in kinds:
                kinds.append(label)
        items.append(owner_card(db, owner, links, kinds[:3]))
    return {'items': items}
