"""Approved first fleet delivery; no calendar, ownership transfer or deletion."""
import copy
from datetime import datetime, timezone
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from starlette.datastructures import UploadFile
from starlette.concurrency import run_in_threadpool
from sqlalchemy import select, func, exists
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from pydantic import ValidationError
from app.api.routers.api import current, require_role, touch
from app.dependencies.database import get_db
from app.core.errors import ApiError
from app.models import User
from app.models.review_models import Vehicle, Document
from app.models.rate_models import ServiceType
from app.api.routers.review_api import admin, locked_authority, query_values, pagination, page_result
from app.api.routers.rate_api import owned
from app.services.private_documents import document_summary
from app.schemas.hire_schemas import Version
from app.services.hire_services import eligible_vehicle, vehicle_evidence, compatible_driver, approved
from app.schemas.vehicle_schemas import (VehicleCreate,VehiclePatch,VehicleFacts,VehicleDecision,RegistrationCorrection,
    Availability,HireLocationSettings,VehicleLocationUpdate,DriverLookup,PreferredDriver,PhotoDecision,DescriptionDecision)
from app.services.review_audit import canonical
from app.services.vehicle_rules import FACTS,MATERIAL,facts,require_complete,has_exterior,commitments,no_commitments,photo_summary,public_photos,validate_public_facts

router=APIRouter(prefix='/api/v1',tags=['Vehicle management'])


def version(row,body):
    if row.version!=body.expected_version:raise ApiError(409,'VERSION_CONFLICT','Vehicle changed. Reload before retrying.')


def summary(row):
    return {'id':str(row.id),'reference':row.public_vehicle_reference,'label':' '.join(str(x) for x in (row.make,row.model,row.registration_number) if x),
        'registration_number':str(row.registration_number),'verification_status':row.verification_status,'availability_status':row.availability_status,
        'published':row.is_published,'removed':row.archived_at is not None,'version':row.version,**facts(row),
        'preferred_driver_id':str(row.default_driver_user_id) if row.default_driver_user_id else None,
        'hire_location':{'base_label':row.base_location_label,'base_configured':row.base_latitude is not None,
            'pickup_distance_km':format(row.pickup_distance_km, '.2f') if row.pickup_distance_km is not None else None,
            'accepts_bookings':bool(row.accepts_hire_bookings),
            'current_source':row.current_location_source,
            'current_observed_at':row.current_location_observed_at.isoformat() if row.current_location_observed_at else None,
            'current_accuracy_m':str(row.current_location_accuracy_m) if row.current_location_accuracy_m is not None else None},
        'photos':[photo_summary(row.id,p) for p in row.media],
        'description_review':{k:v for k,v in row.verified_eligibility.get('description_review',{}).items() if k in ('status','approved_text','reason','reviewed_at')}}


def before(row):
    return {'version':row.version,'verification_status':row.verification_status,'state':{
        **facts(row),'registration_number':str(row.registration_number),'verification_status':row.verification_status,
        'availability_status':row.availability_status,'published':row.is_published,'removed':row.archived_at is not None,'preferred_driver_id':str(row.default_driver_user_id) if row.default_driver_user_id else None,
        'approved_by':str(row.approved_by) if row.approved_by else None,'approved_at':row.approved_at.isoformat() if row.approved_at else None,
        'odometer_updated_at':row.odometer_updated_at.isoformat() if row.odometer_updated_at else None,
        'hire_location':{'base_location_label':row.base_location_label,
            'base_latitude':str(row.base_latitude) if row.base_latitude is not None else None,
            'base_longitude':str(row.base_longitude) if row.base_longitude is not None else None,
            'pickup_distance_km':format(row.pickup_distance_km, '.2f') if row.pickup_distance_km is not None else None,
            'accepts_hire_bookings':row.accepts_hire_bookings,
            'current_latitude':str(row.current_latitude) if row.current_latitude is not None else None,
            'current_longitude':str(row.current_longitude) if row.current_longitude is not None else None,
            'current_location_source':row.current_location_source,
            'current_location_observed_at':row.current_location_observed_at.isoformat() if row.current_location_observed_at else None,
            'current_location_accuracy_m':str(row.current_location_accuracy_m) if row.current_location_accuracy_m is not None else None},
        'updated_by':str(row.updated_by) if row.updated_by else None,'updated_at':row.updated_at.isoformat() if row.updated_at else None,
        'media':copy.deepcopy(row.media),'eligibility':copy.deepcopy(row.verified_eligibility)}}


def changed_fields(old,new):
    if old==new:return None
    if isinstance(old,dict) and isinstance(new,dict):
        return {k:changed_fields(old.get(k),new.get(k)) for k in old.keys()|new.keys() if old.get(k)!=new.get(k)}
    if isinstance(old,list) and isinstance(new,list) and all(isinstance(p,dict) and 'id' in p for p in old+new):
        return changed_fields({p['id']:p for p in old},{p['id']:p for p in new})
    return {'before':old,'after':new}


def commit(db,request,user,row,old,reason=None,purpose='VEHICLE_EDIT'):
    touch(row);row.updated_by=user.id
    try:
        db.flush()
    except IntegrityError:
        db.rollback();raise ApiError(409,'REGISTRATION_ALREADY_EXISTS','This registration is already registered. Contact Admin for an ownership dispute.') from None
    evidence={'changes':changed_fields(old['state'],before(row)['state'])}
    if len(canonical(evidence))>56000:
        db.rollback();raise ApiError(422,'VEHICLE_METADATA_TOO_LARGE','The changed vehicle metadata exceeds the bounded review size. Save smaller edits separately.')
    request.app.state.audit.commit(db,actor=user.id,target={'resource':'vehicles','id':str(row.id),'owner':str(row.owner_user_id),'purpose':purpose},
        previous_status=old['verification_status'],new_status=row.verification_status,previous_version=old['version'],new_version=row.version,
        full_reason=reason,previous_decision_evidence=evidence,trace_id=request.state.trace_id)


def own_locked(db,request,user,vid,body):
    row=owned(db,request,user,vid,lock=True);version(row,body);return row


def admin_locked(db,request,user,vid,body=None):
    row=db.get(Vehicle,vid)
    if not row:raise ApiError(404,'VEHICLE_NOT_FOUND','Vehicle not found.')
    if row.owner_user_id==user.id:raise ApiError(403,'REVIEW_FORBIDDEN','Self vehicle review is not allowed.')
    locked_authority(db,request,user,row.owner_user_id)
    row=db.scalar(select(Vehicle).where(Vehicle.id==vid).with_for_update().execution_options(populate_existing=True))
    if body:version(row,body)
    return row


def route_permit(db,vehicle_id):
    # Optional permit badge only: never blocks approval, publication or booking.
    from zoneinfo import ZoneInfo
    replacement=Document.__table__.alias('replacement')
    doc=db.scalar(select(Document).where(Document.vehicle_id==vehicle_id,Document.document_type=='ROUTE_PERMIT',
        ~exists(select(replacement.c.id).where(replacement.c.superseded_document_id==Document.id))).order_by(Document.created_at.desc()).limit(1))
    if not doc:return {'uploaded':False,'current':False,'expiry_date':None}
    today=datetime.now(ZoneInfo('Asia/Colombo')).date()
    return {'uploaded':True,'current':bool(doc.expiry_date and doc.expiry_date>=today),'expiry_date':doc.expiry_date.isoformat() if doc.expiry_date else None}


def details(db,request,user,row):
    projection=request.app.state.audit.vehicle_projection(user.id,row.id)
    declaration=row.verified_eligibility.get('owner_declaration',{})
    applicable=row.verified_eligibility.get('conditional_documents',{})
    checklist=[{'type':t,'requirement':'Required'} for t in ('VEHICLE_REGISTRATION','INSURANCE','REVENUE_LICENCE')]
    checklist.append({'type':'OWNER_AUTHORISATION','requirement':'Required for your case' if declaration.get('registered_owner_case') in ('OTHER_PERSON','COMPANY') or row.verified_eligibility.get('authorisation_required') else 'Optional'})
    checklist.extend({'type':t,'requirement':'Required for your case' if applicable.get(t) else 'Optional' if applicable.get(t) is False else 'Required for your case — Admin must confirm applicability'} for t in ('EMISSION',))
    checklist.append({'type':'FITNESS','requirement':'Optional — upload it only if you have one.'})
    checklist.append({'type':'ROUTE_PERMIT','requirement':'Optional — upload only if you have one. The system checks it; Admin does not review it.'})
    owner=db.get(User,row.owner_user_id)
    replacement=Document.__table__.alias('replacement')
    from app.api.routers.hire_api import priced_for_publication
    return {**summary(row),**projection,'checklist':checklist,'has_commitments':commitments(db,row.id),
        'prices_ready':priced_for_publication(db,row),
        'reviewed_category':row.verified_eligibility.get('category'),'conditional_documents':applicable,
        'route_permit':route_permit(db,row.id),
        'authorisation_required':row.verified_eligibility.get('authorisation_required'),
        'owner_reference':owner.public_user_reference,'owner_name':owner.full_name,
        'documents':[document_summary(d) for d in db.scalars(select(Document).where(Document.vehicle_id==row.id,
            ~exists(select(replacement.c.id).where(replacement.c.superseded_document_id==Document.id))).order_by(Document.created_at.desc()).limit(100))]}


@router.post('/vehicles',status_code=201)
def create_vehicle(body:VehicleCreate,request:Request,user=Depends(current),db:Session=Depends(get_db)):
    with request.app.state.audit.coordinated():
        locked_authority(db,request,user,user.id,require_admin=False);require_role(db,user,'OWNER')
        row=Vehicle(public_vehicle_reference='VEH-'+uuid4().hex[:16].upper(),owner_user_id=user.id,
            registration_number=body.registration_number,created_by=user.id,updated_by=user.id)
        db.add(row)
        try:db.flush()
        except IntegrityError:
            db.rollback();raise ApiError(409,'REGISTRATION_ALREADY_EXISTS','This registration is already registered. Contact Admin for an ownership dispute.') from None
        request.app.state.audit.commit(db,actor=user.id,target={'resource':'vehicles','id':str(row.id),'owner':str(user.id),'purpose':'VEHICLE_CREATE',
            'registration_number':body.registration_number,'public_reference':row.public_vehicle_reference},
            previous_status=None,new_status='DRAFT',previous_version=0,new_version=1,full_reason=None,previous_decision_evidence={},trace_id=request.state.trace_id)
    return summary(row)


@router.get('/drivers/me/vehicles')
def driver_vehicles(user=Depends(current),db:Session=Depends(get_db)):
    """Vehicles this Driver is the preferred Driver of (for the Driver's Maintenance page; read-only)."""
    require_role(db,user,'DRIVER')
    rows=db.scalars(select(Vehicle).where(Vehicle.default_driver_user_id==user.id).order_by(Vehicle.created_at)).all()
    return {'items':[{'id':str(r.id),'reference':r.public_vehicle_reference,'registration_number':str(r.registration_number),
        'label':' '.join(str(x) for x in (r.make,r.model,r.registration_number) if x)} for r in rows]}


@router.get('/owners/me/vehicles/{vehicle_id}')
def own_detail(vehicle_id:UUID,request:Request,user=Depends(current),db:Session=Depends(get_db)):
    with request.app.state.audit.coordinated():return details(db,request,user,owned(db,request,user,vehicle_id))


@router.patch('/vehicles/{vehicle_id}')
def edit_vehicle(vehicle_id:UUID,body:VehiclePatch,request:Request,user=Depends(current),db:Session=Depends(get_db)):
    with request.app.state.audit.coordinated():
        row=own_locked(db,request,user,vehicle_id,body)
        if row.verification_status in ('SUBMITTED','SUSPENDED'):raise ApiError(409,'VEHICLE_EDIT_UNAVAILABLE','Submitted facts stay under review; suspended vehicles cannot self-reset. Correct requested documents separately.')
        old=before(row);values=body.model_dump(exclude_unset=True);values.pop('expected_version')
        registration=values.pop('registration_number',None)
        if registration is not None:
            registration=VehicleCreate(registration_number=registration).registration_number
            projection=request.app.state.audit.vehicle_projection(user.id,row.id)
            if projection['registration_locked'] and registration.lower()!=str(row.registration_number).lower():
                raise ApiError(409,'REGISTRATION_LOCKED','Registration cannot be changed after first submission. Request an Admin correction.')
        # VehiclePatch already turned the odometer into a Decimal; the fact validator reads it as text, like facts(row) does.
        merged={**facts(row),**{k:(str(v) if k=='current_odometer_km' and v is not None else v) for k,v in values.items()}}
        try:validated=VehicleFacts.model_validate(merged)
        except ValidationError as exc:raise ApiError(422,'VEHICLE_FACTS_INVALID','Check factual values and choose power/fuel together. Do not guess missing facts.',[{'field':str(e['loc'][-1]) if e['loc'] else 'power_type','message':e['msg']} for e in exc.errors()]) from None
        validate_public_facts(merged,registration if registration is not None else str(row.registration_number))
        changed={key for key,value in values.items() if value!=facts(row).get(key)}
        if MATERIAL & changed:
            no_commitments(db,row.id)
            declaration={**row.verified_eligibility.get('owner_declaration',{}),'registered_owner_case':validated.registered_owner_case}
            row.verified_eligibility={'owner_declaration':declaration};row.is_published=False;row.verification_status='DRAFT'
            row.availability_status='DRAFT';row.approved_by=row.approved_at=None
        elif row.verification_status=='REJECTED':row.verification_status='DRAFT';row.availability_status='DRAFT'
        for key in values:
            if key!='registered_owner_case':setattr(row,key,getattr(validated,key))
        if 'registered_owner_case' in values:
            row.verified_eligibility={**row.verified_eligibility,'owner_declaration':{'registered_owner_case':validated.registered_owner_case}}
        if 'description' in changed:
            previous=row.verified_eligibility.get('description_review',{})
            row.verified_eligibility={**row.verified_eligibility,'description_review':
                {'status':'PENDING','approved_text':previous.get('approved_text')} if validated.description else {'status':'WITHDRAWN','approved_text':None}}
        if registration is not None:row.registration_number=registration
        if 'current_odometer_km' in values:row.odometer_updated_at=datetime.now(timezone.utc) if row.current_odometer_km is not None else None
        commit(db,request,user,row,old)
    return summary(row)


@router.post('/vehicles/{vehicle_id}/submit')
def submit_vehicle(vehicle_id:UUID,body:Version,request:Request,user=Depends(current),db:Session=Depends(get_db)):
    with request.app.state.audit.coordinated():
        row=own_locked(db,request,user,vehicle_id,body)
        if row.verification_status!='DRAFT':raise ApiError(409,'INVALID_VEHICLE_TRANSITION','Only a corrected or new draft can be submitted.')
        require_complete(row)
        from app.services.hire_services import current_documents
        rows=db.scalars(select(Document).where(Document.vehicle_id==row.id).order_by(Document.created_at.desc())).all()
        newest={}
        for d in rows:
            if d.document_type not in newest:newest[d.document_type]=d
        needed={'VEHICLE_REGISTRATION','INSURANCE','REVENUE_LICENCE'}
        if facts(row)['registered_owner_case']!='SELF':needed.add('OWNER_AUTHORISATION')
        from zoneinfo import ZoneInfo
        day=datetime.now(timezone.utc).astimezone(ZoneInfo('Asia/Colombo')).date()
        if any(t not in newest or newest[t].status not in ('SUBMITTED','UNDER_REVIEW','APPROVED')
            or (newest[t].expiry_date is not None and newest[t].expiry_date<day)
            or (newest[t].issue_date is not None and newest[t].issue_date>day) for t in needed):
            raise ApiError(422,'VEHICLE_EVIDENCE_REQUIRED','Upload this vehicle’s current registration, insurance, revenue licence and case-specific authorization before submission.')
        old=before(row);row.verification_status='SUBMITTED';row.availability_status='PENDING_VERIFICATION';row.is_published=False
        commit(db,request,user,row,old,purpose='VEHICLE_SUBMISSION')
    return summary(row)


@router.patch('/vehicles/{vehicle_id}/availability')
def availability(vehicle_id:UUID,body:Availability,request:Request,user=Depends(current),db:Session=Depends(get_db)):
    with request.app.state.audit.coordinated():
        row=own_locked(db,request,user,vehicle_id,body)
        if row.availability_status in ('BOOKED','ON_TRIP','MAINTENANCE','SUSPENDED'):
            raise ApiError(409,'AVAILABILITY_WORKFLOW_CONTROLLED','This operational state is controlled by its workflow; Owner controls cannot override it.')
        if body.availability_status=='INACTIVE':no_commitments(db,row.id)
        elif row.verification_status!='APPROVED' or row.availability_status=='SUSPENDED':
            raise ApiError(409,'VEHICLE_NOT_ELIGIBLE','Only an approved eligible vehicle may be made active.')
        if body.availability_status=='ACTIVE':vehicle_evidence(db,row)
        old=before(row);row.availability_status=body.availability_status;row.is_published=False
        commit(db,request,user,row,old,purpose='VEHICLE_AVAILABILITY')
    return summary(row)


@router.patch('/vehicles/{vehicle_id}/hire-location')
def hire_location_settings(vehicle_id:UUID,body:HireLocationSettings,request:Request,user=Depends(current),db:Session=Depends(get_db)):
    """Owner-controlled base, pickup radius and new-booking switch. This never refreshes current-location freshness."""
    if body.base_location:request.app.state.rate_locations.verify(body.base_location)
    with request.app.state.audit.coordinated():
        row=own_locked(db,request,user,vehicle_id,body);old=before(row)
        if body.base_location:
            row.base_location_label=body.base_location.label
            row.base_latitude=body.base_location.latitude;row.base_longitude=body.base_location.longitude
        elif row.base_latitude is None:
            raise ApiError(422,'BASE_LOCATION_REQUIRED','Select the vehicle base location before accepting bookings.')
        row.pickup_distance_km=body.pickup_distance_km
        row.accepts_hire_bookings=body.accepts_hire_bookings
        commit(db,request,user,row,old,purpose='VEHICLE_HIRE_LOCATION_SETTINGS')
    return summary(row)


def location_vehicle(db,request,user,vehicle_id,body):
    """Owner, or an accepted operating Driver, may explicitly confirm this vehicle's position."""
    from app.models.hire_models import Trip
    row=db.get(Vehicle,vehicle_id)
    if not row:raise ApiError(404,'VEHICLE_NOT_FOUND','Vehicle not found.')
    if row.owner_user_id==user.id:
        require_role(db,user,'OWNER')
    else:
        require_role(db,user,'DRIVER')
        active=db.scalar(select(Trip.id).where(Trip.vehicle_id==vehicle_id,Trip.driver_user_id==user.id,
            Trip.assignment_status=='ACCEPTED',Trip.status.in_(('READY','IN_PROGRESS','BREAKDOWN','ASSISTANCE_REQUIRED'))).limit(1))
        if not active:raise ApiError(404,'VEHICLE_NOT_FOUND','Vehicle not found.')
    locked_authority(db,request,user,user.id,require_admin=False)
    row=db.scalar(select(Vehicle).where(Vehicle.id==vehicle_id).with_for_update().execution_options(populate_existing=True))
    version(row,body)
    return row


@router.patch('/vehicles/{vehicle_id}/location')
def confirm_vehicle_location(vehicle_id:UUID,body:VehicleLocationUpdate,request:Request,user=Depends(current),db:Session=Depends(get_db)):
    request.app.state.rate_locations.verify(body.location)
    with request.app.state.audit.coordinated():
        row=location_vehicle(db,request,user,vehicle_id,body);old=before(row)
        row.current_latitude=body.location.latitude;row.current_longitude=body.location.longitude
        row.current_location_source='MANUAL';row.current_location_observed_at=datetime.now(timezone.utc)
        row.current_location_accuracy_m=body.accuracy_m
        commit(db,request,user,row,old,purpose='VEHICLE_LOCATION_CONFIRMATION')
    return summary(row)


def eligible_preference(db,vehicle,sid,reference):
    """A Driver is eligible when the licence fits the vehicle for the chosen service, or (no service chosen) for at least one active private-hire service."""
    if sid:
        services=[db.get(ServiceType,sid)]
    else:
        services=list(db.scalars(select(ServiceType).where(ServiceType.category=='PRIVATE_HIRE',ServiceType.is_active.is_(True)).order_by(ServiceType.code)))
    services=[s for s in services if s and s.is_active and s.category=='PRIVATE_HIRE']
    if not services:raise ApiError(409,'SERVICE_UNAVAILABLE','No active service is available for the suitability check.')
    driver=db.scalar(select(User).where(User.public_user_reference==reference))
    if not driver:raise ApiError(404,'DRIVER_NOT_FOUND','An eligible Driver for this vehicle/service was not found.')
    failure=None
    for service in services:
        try:
            compatible_driver(db,driver,vehicle,service,datetime.now(timezone.utc));return driver
        except ApiError as error:failure=error
    raise failure


@router.post('/vehicles/{vehicle_id}/remove')
def remove_vehicle(vehicle_id:UUID,body:Version,request:Request,user=Depends(current),db:Session=Depends(get_db)):
    """Owner removes a vehicle from the fleet list. Archive only: the record, bookings, payments and history stay (PRD).
    A Draft goes at once; an approved vehicle only when no confirmed/upcoming booking, trip or scheduled trip needs it."""
    with request.app.state.audit.coordinated():
        row=own_locked(db,request,user,vehicle_id,body)
        if row.archived_at is not None:raise ApiError(409,'VEHICLE_ALREADY_REMOVED','This vehicle is already removed.')
        if row.verification_status!='DRAFT':no_commitments(db,row.id)
        old=before(row);row.archived_at=datetime.now(timezone.utc);row.is_published=False
        if row.availability_status in ('ACTIVE',):row.availability_status='INACTIVE'
        commit(db,request,user,row,old,purpose='VEHICLE_REMOVED')
    return summary(row)


@router.post('/vehicles/{vehicle_id}/restore')
def restore_vehicle(vehicle_id:UUID,body:Version,request:Request,user=Depends(current),db:Session=Depends(get_db)):
    """Brings a removed vehicle back to the fleet list. It stays unpublished and inactive until the Owner turns it on again."""
    with request.app.state.audit.coordinated():
        row=own_locked(db,request,user,vehicle_id,body)
        if row.archived_at is None:raise ApiError(409,'VEHICLE_NOT_REMOVED','This vehicle is not removed.')
        old=before(row);row.archived_at=None
        commit(db,request,user,row,old,purpose='VEHICLE_RESTORED')
    return summary(row)


@router.post('/drivers/eligible-lookup')
def driver_lookup(body:DriverLookup,request:Request,user=Depends(current),db:Session=Depends(get_db)):
    row=owned(db,request,user,body.vehicle_id)
    driver=eligible_preference(db,row,body.service_type_id,body.driver_reference)
    return {'reference':driver.public_user_reference,'display_name':driver.display_name or driver.public_user_reference,'eligible':True,
        'message':'Preference only. Every actual assignment/start requires fresh suitability and Driver acceptance.'}


@router.patch('/vehicles/{vehicle_id}/preferred-driver')
def preferred_driver(vehicle_id:UUID,body:PreferredDriver,request:Request,user=Depends(current),db:Session=Depends(get_db)):
    with request.app.state.audit.coordinated():
        row=own_locked(db,request,user,vehicle_id,body);old=before(row)
        driver=eligible_preference(db,row,body.service_type_id,body.driver_reference) if body.driver_reference else None
        row.default_driver_user_id=driver.id if driver else None
        commit(db,request,user,row,old,purpose='VEHICLE_DRIVER_PREFERENCE')
    return summary(row)


@router.get('/admin/vehicles')
def admin_queue(request:Request,user=Depends(admin),db:Session=Depends(get_db)):
    p=query_values(request,{'page','page_size','verification_status'});page,size=pagination(p)
    status=p.get('verification_status','SUBMITTED')
    if status not in ('DRAFT','SUBMITTED','APPROVED','REJECTED','SUSPENDED'):raise ApiError(422,'VALIDATION_ERROR','Choose a valid vehicle review status.')
    q=select(Vehicle).where(Vehicle.owner_user_id!=user.id,Vehicle.verification_status==status)
    total=db.scalar(select(func.count()).select_from(q.subquery()))
    rows=db.scalars(q.order_by(Vehicle.updated_at,Vehicle.id).offset((page-1)*size).limit(size)).all()
    return page_result([summary(r) for r in rows],page,size,total)


@router.get('/admin/vehicles/{vehicle_id}')
def admin_detail(vehicle_id:UUID,request:Request,user=Depends(admin),db:Session=Depends(get_db)):
    with request.app.state.audit.coordinated():return details(db,request,user,admin_locked(db,request,user,vehicle_id))


def decide_vehicle(vehicle_id,body,request,user,db):
    with request.app.state.audit.coordinated():
        row=admin_locked(db,request,user,vehicle_id,body)
        if (row.verification_status,body.decision) not in (('SUBMITTED','APPROVED'),('SUBMITTED','REJECTED'),('APPROVED','APPROVED'),('APPROVED','SUSPENDED')):
            raise ApiError(409,'INVALID_VEHICLE_TRANSITION','This vehicle decision is unavailable in its current state.')
        old=before(row)
        if body.decision=='APPROVED':
            require_complete(row)
            declaration=row.verified_eligibility.get('owner_declaration',{})
            if declaration.get('registered_owner_case') in ('OTHER_PERSON','COMPANY') and not body.authorisation_required:
                raise ApiError(422,'AUTHORISATION_REQUIRED','Authorization is required for another individual’s or company’s registered vehicle.')
            content=row.verified_eligibility.get('description_review',{})
            row.verified_eligibility={'owner_declaration':declaration,'category':body.category,'conditional_documents':body.conditional_documents,
                'authorisation_required':body.authorisation_required,**({'description_review':content} if content else {})}
            vehicle_evidence(db,row)
            row.approved_by=user.id;row.approved_at=datetime.now(timezone.utc)
            if old['verification_status']=='SUBMITTED' and row.availability_status!='INACTIVE':row.availability_status='ACTIVE'
        row.verification_status=body.decision;row.is_published=False
        if body.decision=='SUSPENDED':row.availability_status='SUSPENDED'
        if body.decision=='REJECTED':row.availability_status='PENDING_VERIFICATION'
        commit(db,request,user,row,old,body.reason,purpose='VEHICLE_REVIEW')
    return summary(row)


@router.patch('/admin/vehicles/{vehicle_id}/registration')
def correct_registration(vehicle_id:UUID,body:RegistrationCorrection,request:Request,user=Depends(admin),db:Session=Depends(get_db)):
    with request.app.state.audit.coordinated():
        row=admin_locked(db,request,user,vehicle_id,body);no_commitments(db,row.id)
        if row.verification_status=='SUSPENDED':raise ApiError(409,'VEHICLE_SUSPENDED','Suspension cannot be bypassed by correcting registration.')
        old=before(row);row.registration_number=body.registration_number;row.verification_status='DRAFT';row.availability_status='DRAFT';row.is_published=False
        row.verified_eligibility={'owner_declaration':row.verified_eligibility.get('owner_declaration',{})};row.approved_by=row.approved_at=None
        commit(db,request,user,row,old,body.reason,purpose='VEHICLE_REGISTRATION_CORRECTION')
    return summary(row)


@router.patch('/admin/vehicles/{vehicle_id}/description/review')
def review_description(vehicle_id:UUID,body:DescriptionDecision,request:Request,user=Depends(admin),db:Session=Depends(get_db)):
    with request.app.state.audit.coordinated():
        row=admin_locked(db,request,user,vehicle_id,body);old=before(row)
        prior=row.verified_eligibility.get('description_review',{})
        approved_text=prior.get('approved_text')
        if body.decision=='APPROVED':
            if not row.description:raise ApiError(409,'NO_DESCRIPTION_PROPOSAL','There is no proposed description to approve.')
            approved_text=row.description
        elif body.decision=='REMOVED' or (prior.get('status')=='APPROVED' and approved_text==row.description):approved_text=None
        row.verified_eligibility={**row.verified_eligibility,'description_review':{'status':body.decision,'approved_text':approved_text,
            'reason':body.reason,'reviewed_at':datetime.now(timezone.utc).isoformat(),'reviewed_by':str(user.id)}}
        commit(db,request,user,row,old,body.reason,purpose='VEHICLE_DESCRIPTION_REVIEW')
    return summary(row)


def photo(row,pid):
    found=next((p for p in row.media if p['id']==str(pid)),None)
    if not found:raise ApiError(404,'PHOTO_NOT_FOUND','Photo not found.')
    return found


def place_photo(vid,form,request,user,db):
    if set(form)!= {'file','category','expected_version'} or form['category'] not in ('EXTERIOR','INTERIOR'):
        raise ApiError(422,'VALIDATION_ERROR','Provide one photo, its EXTERIOR/INTERIOR category and expected version.')
    import re
    if not re.fullmatch(r'[1-9][0-9]{0,9}',str(form['expected_version'])):raise ApiError(422,'VALIDATION_ERROR','Use the current vehicle version.')
    with request.app.state.audit.coordinated():
        row=own_locked(db,request,user,vid,Version(expected_version=int(form['expected_version'])))
        if len(row.media)>=12:raise ApiError(422,'PHOTO_LIMIT','This first delivery supports twelve retained photo entries per vehicle. Contact Admin for retained-media maintenance.')
        old=before(row);variants=request.app.state.vehicle_photos.place(form['file'])
        row.media=[*row.media,{'id':str(uuid4()),'category':form['category'],'status':'PENDING','variants':variants,
            'uploaded_by':str(user.id),'uploaded_at':datetime.now(timezone.utc).isoformat(),'privacy_confirmed':False,'genuine_vehicle_confirmed':False}]
        commit(db,request,user,row,old,purpose='VEHICLE_PHOTO_UPLOAD')
    return summary(row)


@router.post('/vehicles/{vehicle_id}/photos',status_code=201)
async def upload_photo(vehicle_id:UUID,request:Request,user=Depends(current),db:Session=Depends(get_db)):
    async with request.form(max_files=1,max_fields=3,max_part_size=8192) as form:
        pairs=list(form.multi_items())
        if len({k for k,v in pairs})!=len(pairs) or not isinstance(form.get('file'),UploadFile):raise ApiError(422,'VALIDATION_ERROR','Provide one JPEG or PNG photo.')
        return await run_in_threadpool(place_photo,vehicle_id,form,request,user,db)


@router.get('/vehicles/{vehicle_id}/photos/{photo_id}/{width}')
def read_photo(vehicle_id:UUID,photo_id:UUID,width:int,request:Request,db:Session=Depends(get_db)):
    if width not in (480,960,1600):raise ApiError(404,'PHOTO_NOT_FOUND','Photo not found.')
    row=db.get(Vehicle,vehicle_id)
    if not row:raise ApiError(404,'PHOTO_NOT_FOUND','Photo not found.')
    p=photo(row,photo_id);private=False
    if request.headers.get('Authorization'):
        user=current(request,db)
        private=(row.owner_user_id==user.id and approved(db,user.id,'OWNER')) or (row.owner_user_id!=user.id and approved(db,user.id,'ADMIN'))
    if not private:
        try:eligible_vehicle(db,row,public=True)
        except ApiError as exc:
            if exc.status==503:raise
            raise ApiError(404,'PHOTO_NOT_FOUND','Photo not found.') from None
        if p['status']!='APPROVED' or not p.get('privacy_confirmed') or not p.get('genuine_vehicle_confirmed'):
            raise ApiError(404,'PHOTO_NOT_FOUND','Photo not found.')
    data=request.app.state.vehicle_photos.open(p['variants'][str(width)])
    return Response(data,media_type='image/jpeg',headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})


@router.patch('/vehicles/{vehicle_id}/photos/{photo_id}')
def remove_photo(vehicle_id:UUID,photo_id:UUID,body:Version,request:Request,user=Depends(current),db:Session=Depends(get_db)):
    with request.app.state.audit.coordinated():
        row=own_locked(db,request,user,vehicle_id,body);photo(row,photo_id);old=before(row)
        row.media=[{**p,'status':'REMOVED'} if p['id']==str(photo_id) else p for p in row.media]
        if not has_exterior(row):row.is_published=False
        commit(db,request,user,row,old,purpose='VEHICLE_PHOTO_REMOVE')
    return summary(row)


@router.patch('/admin/vehicles/{vehicle_id}/photos/{photo_id}/review')
def review_photo(vehicle_id:UUID,photo_id:UUID,body:PhotoDecision,request:Request,user=Depends(admin),db:Session=Depends(get_db)):
    with request.app.state.audit.coordinated():
        row=admin_locked(db,request,user,vehicle_id,body);p=photo(row,photo_id);old=before(row)
        if (p['status'],body.decision) not in (('PENDING','APPROVED'),('PENDING','REJECTED'),('APPROVED','REMOVED')):
            raise ApiError(409,'INVALID_PHOTO_TRANSITION','Upload a new corrected photo or remove the approved photo.')
        if body.decision=='APPROVED':
            for v in p['variants'].values():request.app.state.vehicle_photos.open(v)
        replacement={**p,'status':body.decision,'reason':body.reason,'privacy_confirmed':body.privacy_confirmed,
            'genuine_vehicle_confirmed':body.genuine_vehicle_confirmed,'reviewed_by':str(user.id),'reviewed_at':datetime.now(timezone.utc).isoformat()}
        row.media=[replacement if item['id']==str(photo_id) else item for item in row.media]
        if not has_exterior(row):row.is_published=False
        commit(db,request,user,row,old,body.reason,purpose='VEHICLE_PHOTO_REVIEW')
    return summary(row)


@router.get('/vehicles/{vehicle_id}')
def public_detail(vehicle_id:UUID,db:Session=Depends(get_db)):
    row=db.get(Vehicle,vehicle_id)
    if not row:raise ApiError(404,'VEHICLE_NOT_FOUND','Vehicle not found.')
    try:eligible_vehicle(db,row,public=True)
    except ApiError as exc:
        if exc.status==503:raise
        raise ApiError(404,'VEHICLE_NOT_FOUND','Vehicle not found.') from None
    from app.api.routers.hire_api import safe_vehicle
    return safe_vehicle(row,db.get(User,row.owner_user_id))
