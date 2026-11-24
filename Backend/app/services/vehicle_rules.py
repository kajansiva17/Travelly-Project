from datetime import datetime, timezone
import re
from sqlalchemy import select
from app.models.hire_models import Booking, Trip, ScheduledTrip
from app.core.errors import ApiError
from app.schemas.vehicle_schemas import VehicleFacts

FACTS = tuple(VehicleFacts.model_fields)
MATERIAL = {'vehicle_type_code','make','model','manufacture_year','power_type','engine_fuel_type',
            'seat_capacity','large_luggage_capacity','small_luggage_capacity','registered_owner_case'}


def facts(row):
    return {**{n: (str(getattr(row,n)) if n == 'current_odometer_km' and getattr(row,n) is not None else getattr(row,n)) for n in FACTS if n != 'registered_owner_case'},
        'registered_owner_case': row.verified_eligibility.get('owner_declaration',{}).get('registered_owner_case')}


def require_complete(row):
    data = facts(row)
    try:VehicleFacts.model_validate(data)
    except ValueError:raise ApiError(422,'VEHICLE_FACTS_INVALID','Check the vehicle’s type, factual values and power/fuel before submission.') from None
    validate_public_facts(data,str(row.registration_number))
    missing = [n for n in ('vehicle_type_code','make','model','manufacture_year','colour','power_type','seat_capacity',
        'large_luggage_capacity','small_luggage_capacity','registered_owner_case') if data[n] is None]
    if row.seat_capacity == 0: missing.append('seat_capacity')
    if missing: raise ApiError(422,'VEHICLE_INCOMPLETE','Complete the real vehicle facts before submission.',
        [{'field':n,'message':'Required before submission; use actual usable Passenger seats excluding Driver/crew.' if n=='seat_capacity' else 'Required before submission.'} for n in missing])


def validate_public_facts(data,registration):
    # Obvious private identifiers are not valid make/model/colour facts.
    # Free-text descriptions use the separately approved Admin content review.
    plate=''.join(re.findall('[a-z0-9]',registration.lower()))
    for name in ('make','model','display_name','colour','transmission_type'):
        value=data.get(name) or ''
        normalized=''.join(re.findall('[a-z0-9]',value.lower()))
        if re.search(r'\S+@\S+\.[A-Za-z]{2,}',value) or re.search(r'(?:\+?[0-9][\s().-]*){7,}',value) or (len(plate)>=4 and plate in normalized):
            raise ApiError(422,'PRIVATE_INFO_IN_VEHICLE_FACTS','Use factual vehicle specifications without plates, contacts or coordinates.',
                [{'field':name,'message':'Keep registration plates and contact details out of public vehicle facts.'}])


def has_exterior(row):
    return any(p.get('category')=='EXTERIOR' and p.get('status')=='APPROVED' and p.get('privacy_confirmed') is True
        and p.get('genuine_vehicle_confirmed') is True and p.get('variants') for p in row.media)


def commitments(db, vid):
    return bool(db.scalar(select(Booking.id).where(Booking.vehicle_id==vid,Booking.vehicle_committed.is_(True),
        Booking.status.notin_(('CANCELLED','REJECTED','COMPLETED'))).limit(1))
        or db.scalar(select(ScheduledTrip.id).where(ScheduledTrip.current_vehicle_id==vid,
            ScheduledTrip.status.notin_(('DRAFT','CANCELLED','COMPLETED'))).limit(1))
        or db.scalar(select(Trip.id).where(Trip.vehicle_id==vid,Trip.assignment_status=='ACCEPTED',
            Trip.status.notin_(('CANCELLED','COMPLETED'))).limit(1)))


def no_commitments(db, vid):
    if commitments(db,vid): raise ApiError(409,'VEHICLE_COMMITMENTS_REQUIRE_RESOLUTION','Resolve outstanding vehicle commitments before this material change or retirement. No booking was cancelled.')


def photo_summary(vid, photo):
    return {'id':photo['id'],'category':photo['category'],'status':photo['status'],
        'reason':photo.get('reason'),'reviewed_at':photo.get('reviewed_at'),
        'variants':[{'width':v['width'],'height':v['height'],'url':f"/api/v1/vehicles/{vid}/photos/{photo['id']}/{size}"} for size,v in photo.get('variants',{}).items()]}


def public_photos(row):
    # Approved exterior photos come before interior ones.
    shown=[{'id':p['id'],'category':p['category'],'variants':photo_summary(row.id,p)['variants']}
        for p in row.media if p.get('status')=='APPROVED' and p.get('privacy_confirmed') is True and p.get('genuine_vehicle_confirmed') is True]
    return sorted(shown,key=lambda p:p['category']!='EXTERIOR')
