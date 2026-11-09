import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter,Depends,Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.dependencies.database import get_db
from app.api.routers.api import current,require_role,touch
from app.api.routers.review_api import admin,locked_authority
from app.core.errors import ApiError
from app.models import User
from app.models.rate_models import ServiceType,VehicleService
from app.models.review_models import Vehicle
from app.models.hire_models import Booking,Trip,Notification
from app.models.event_hire_models import EventBookingGroup,EventVehicleAllocation
from app.schemas.event_hire_schemas import EventRateConfig,EventSearch,EventRequest,Version,EventAccept,EventAssignments
from app.services.hire_services import eligible_vehicle,no_conflict,compatible_driver,digest,approved
from app.services.pricing_scope import private_hire_scope

router=APIRouter(prefix='/api/v1',tags=['Event hire'])
def event_service(db,sid,active=True):
 s=db.get(ServiceType,sid)
 if not s or s.category!='PRIVATE_HIRE' or private_hire_scope(s)!='EVENT' or (active and not s.is_active):raise ApiError(409,'EVENT_SERVICE_UNAVAILABLE','An active Admin-approved Event Hire service is required.')
 return s
def end(body):return body.event_start_at+timedelta(hours=float(body.expected_hours))
def packages(row):return row.owner_terms.get('event_packages',[]) if row and row.is_enabled else []
def safe_group(row,allocations):return {'id':str(row.id),'reference':row.event_reference,'status':row.status,'version':row.version,'event_type':row.event_type,'event_start_at':row.event_start_at.isoformat(),'vehicles_required':row.vehicles_required,'quote':row.quote_snapshot,'total_amount':str(row.total_amount) if row.total_amount is not None else None,'allocations':[{'id':str(a.id),'vehicle_id':str(a.vehicle_id),'status':a.status,'trip_id':str(a.trip_id) if a.trip_id else None} for a in allocations]}
def notice(db,row,recipient,title,body):db.add(Notification(recipient_user_id=recipient,notification_type='BOOKING_REQUEST',channel='IN_APP',title=title,body=body,action_required=True,action_payload={'event_group_id':str(row.id),'event_reference':row.event_reference},created_by=row.created_by,updated_by=row.updated_by))
def owner_options(db,body,request):
 service=event_service(db,body.service_type_id);out=[]
 for owner in db.scalars(select(User).order_by(User.id).limit(500)).all():
  fleet=[]
  for vehicle in db.scalars(select(Vehicle).where(Vehicle.owner_user_id==owner.id,Vehicle.is_published.is_(True))).all():
   row=db.scalar(select(VehicleService).where(VehicleService.vehicle_id==vehicle.id,VehicleService.service_type_id==service.id))
   try:
    eligible_vehicle(db,vehicle,public=True,at=body.event_start_at);no_conflict(db,vehicle.id,body.event_start_at,end(body))
    if packages(row):fleet.append((vehicle,row))
   except ApiError:continue
  if len(fleet)>=body.vehicles_required:
   out.append({'owner_reference':owner.public_user_reference,'vehicle_count':len(fleet),'vehicles':[{'id':str(v.id),'reference':v.public_vehicle_reference} for v,_ in fleet[:body.vehicles_required]]})
 return service,out
@router.get('/event-hire/services')
def services(db:Session=Depends(get_db)):
 return {'items':[{'id':str(s.id),'name':s.name,'code':s.code} for s in db.scalars(select(ServiceType).where(ServiceType.category=='PRIVATE_HIRE',ServiceType.is_active.is_(True))).all() if private_hire_scope(s)=='EVENT']}
@router.put('/vehicles/{vehicle_id}/event-packages')
def save_packages(vehicle_id:UUID,body:EventRateConfig,request:Request,user=Depends(current),db:Session=Depends(get_db)):
 require_role(db,user,'OWNER');vehicle=db.scalar(select(Vehicle).where(Vehicle.id==vehicle_id,Vehicle.owner_user_id==user.id).with_for_update())
 if not vehicle:raise ApiError(404,'VEHICLE_NOT_FOUND','Vehicle not found.')
 event_service(db,body.service_type_id);row=db.scalar(select(VehicleService).where(VehicleService.vehicle_id==vehicle_id,VehicleService.service_type_id==body.service_type_id).with_for_update())
 if body.expected_version!=(row.version if row else 0):raise ApiError(409,'VERSION_CONFLICT','Event package rules changed. Reload before saving.')
 if row:row.is_enabled=body.enabled;row.owner_terms={**row.owner_terms,'event_packages':[p.model_dump(mode='json') for p in body.packages]};touch(row);row.updated_by=user.id
 else:row=VehicleService(vehicle_id=vehicle_id,service_type_id=body.service_type_id,is_enabled=body.enabled,pricing_basis='OWNER_QUOTE',currency='LKR',owner_terms={'event_packages':[p.model_dump(mode='json') for p in body.packages]},created_by=user.id,updated_by=user.id);db.add(row)
 db.commit();return {'service_type_id':str(body.service_type_id),'version':row.version,'enabled':row.is_enabled,'packages':row.owner_terms['event_packages']}
@router.post('/event-hire/search')
def search(body:EventSearch,request:Request,db:Session=Depends(get_db)):
 if body.event_start_at<=datetime.now(timezone.utc):raise ApiError(422,'EVENT_IN_PAST','Choose a future event start.')
 for place in [body.venue,*body.pickup_locations]:request.app.state.rate_locations.verify(place)
 _,items=owner_options(db,body,request);return {'items':items,'message':'Only single-Owner fleets that can allocate every requested vehicle are shown. Select a fleet to reveal its combined package quote.'}
@router.post('/event-hire/owners/{owner_reference}/quote')
def quote(owner_reference:str,body:EventSearch,request:Request,db:Session=Depends(get_db)):
 _,items=owner_options(db,body,request);item=next((x for x in items if x['owner_reference']==owner_reference),None)
 if not item:raise ApiError(409,'EVENT_FLEET_UNAVAILABLE','This Owner cannot allocate every required vehicle for the event.')
 chosen=[];total=Decimal('0')
 for record in item['vehicles']:
  row=db.scalar(select(VehicleService).where(VehicleService.vehicle_id==UUID(record['id']),VehicleService.service_type_id==body.service_type_id));package=packages(row)[0];amount=Decimal(str(package['package_price']));total+=amount;chosen.append({'vehicle_id':record['id'],'rate_version':row.version,'package':package,'amount':format(amount,'.2f')})
 snapshot={'allocations':chosen,'line_items':[{'code':'EVENT_PACKAGE','label':f"{len(chosen)} event vehicle package(s)",'amount':format(total,'.2f')}],'total':format(total,'.2f'),'currency':'LKR','event':body.model_dump(mode='json')};snapshot['digest']=digest(snapshot);return snapshot
@router.post('/event-hire/groups',status_code=201)
def create_group(body:EventRequest,request:Request,user=Depends(current),db:Session=Depends(get_db)):
 require_role(db,user,'PASSENGER');owner=db.scalar(select(User).where(User.public_user_reference==body.owner_user_reference));
 if not owner:raise ApiError(404,'OWNER_NOT_FOUND','Owner fleet not found.')
 quote_data=quote(body.owner_user_reference,body,request,db)
 row=EventBookingGroup(event_reference='EVT-'+secrets.token_hex(8).upper(),passenger_user_id=user.id,owner_user_id=owner.id,service_type_id=body.service_type_id,event_type=body.event_type,venue_snapshot=body.venue.model_dump(mode='json'),pickup_snapshots=[p.model_dump(mode='json') for p in body.pickup_locations],event_start_at=body.event_start_at,expected_hours=body.expected_hours,vehicles_required=body.vehicles_required,passenger_count=body.passenger_count,request_snapshot=body.model_dump(mode='json'),quote_snapshot=quote_data,status='QUOTED',created_by=user.id,updated_by=user.id);db.add(row);db.flush()
 for i,item in enumerate(quote_data['allocations'],1):db.add(EventVehicleAllocation(event_group_id=row.id,allocation_no=i,vehicle_id=UUID(item['vehicle_id']),rate_version=item['rate_version'],package_snapshot=item['package'],allocation_amount=Decimal(item['amount']),status='QUOTED',created_by=user.id,updated_by=user.id))
 notice(db,row,owner.id,'Event Hire request','A Passenger requested a complete single-Owner Event fleet quote.');db.commit();return safe_group(row,db.scalars(select(EventVehicleAllocation).where(EventVehicleAllocation.event_group_id==row.id)).all())
@router.get('/event-hire/groups')
def groups(user=Depends(current),db:Session=Depends(get_db)):
 rows=db.scalars(select(EventBookingGroup).where((EventBookingGroup.passenger_user_id==user.id)|(EventBookingGroup.owner_user_id==user.id)).order_by(EventBookingGroup.created_at.desc()).limit(100)).all()
 return {'items':[safe_group(row,db.scalars(select(EventVehicleAllocation).where(EventVehicleAllocation.event_group_id==row.id)).all()) for row in rows]}
@router.get('/event-hire/groups/{group_id}')
def detail(group_id:UUID,user=Depends(current),db:Session=Depends(get_db)):
 row=db.get(EventBookingGroup,group_id)
 if not row or user.id not in (row.passenger_user_id,row.owner_user_id):raise ApiError(404,'EVENT_GROUP_NOT_FOUND','Event booking not found.')
 return safe_group(row,db.scalars(select(EventVehicleAllocation).where(EventVehicleAllocation.event_group_id==row.id)).all())
@router.post('/event-hire/groups/{group_id}/accept')
def accept(group_id:UUID,body:EventAccept,request:Request,user=Depends(current),db:Session=Depends(get_db)):
 row=db.get(EventBookingGroup,group_id)
 if not row or row.passenger_user_id!=user.id:raise ApiError(404,'EVENT_GROUP_NOT_FOUND','Event booking not found.')
 if row.version!=body.expected_version or row.status!='QUOTED' or row.quote_snapshot.get('digest')!=body.digest:raise ApiError(409,'QUOTE_CHANGED','Reload the Event quote before accepting.')
 row.status='PASSENGER_ACCEPTED';row.accepted_quote_digest=body.digest;row.total_amount=Decimal(row.quote_snapshot['total']);row.accepted_at=datetime.now(timezone.utc);touch(row);notice(db,row,row.owner_user_id,'Event quote accepted','Assign every quoted vehicle and Driver together to confirm this Event.');db.commit();return safe_group(row,db.scalars(select(EventVehicleAllocation).where(EventVehicleAllocation.event_group_id==row.id)).all())
@router.post('/event-hire/groups/{group_id}/assignments')
def assign(group_id:UUID,body:EventAssignments,request:Request,user=Depends(current),db:Session=Depends(get_db)):
 require_role(db,user,'OWNER');row=db.get(EventBookingGroup,group_id)
 if not row or row.owner_user_id!=user.id:raise ApiError(404,'EVENT_GROUP_NOT_FOUND','Event booking not found.')
 allocations=db.scalars(select(EventVehicleAllocation).where(EventVehicleAllocation.event_group_id==row.id).with_for_update()).all()
 if row.version!=body.expected_version or row.status!='OWNER_ACCEPTED' or len(body.allocations)!=len(allocations):raise ApiError(409,'EVENT_ASSIGNMENT_REQUIRED','Owner acceptance and assignment of every quoted allocation are required together.')
 service=event_service(db,row.service_type_id);assigned={str(x['allocation_id']):x.get('driver_reference') for x in body.allocations}
 if set(assigned)!={str(a.id) for a in allocations}:raise ApiError(422,'EVENT_ALLOCATION_MISMATCH','Every quoted allocation must be assigned exactly once.')
 for allocation in allocations:
  vehicle=db.get(Vehicle,allocation.vehicle_id);driver=db.scalar(select(User).where(User.public_user_reference==assigned[str(allocation.id)]))
  if not driver or vehicle.owner_user_id!=user.id:raise ApiError(409,'EVENT_DRIVER_UNAVAILABLE','Every allocation needs an eligible Driver for this Owner fleet.')
  eligible_vehicle(db,vehicle,at=row.event_start_at);compatible_driver(db,driver,vehicle,service,row.event_start_at);no_conflict(db,vehicle.id,row.event_start_at,row.event_start_at+timedelta(hours=float(row.expected_hours)),driver_id=driver.id)
 for allocation in allocations:
  vehicle=db.get(Vehicle,allocation.vehicle_id);driver=db.scalar(select(User).where(User.public_user_reference==assigned[str(allocation.id)]));booking=Booking(booking_reference='EVB-'+secrets.token_hex(8).upper(),passenger_user_id=row.passenger_user_id,booking_type='PRIVATE_HIRE',service_type_id=row.service_type_id,requested_owner_user_id=user.id,owner_user_id=user.id,vehicle_id=vehicle.id,origin_text=row.venue_snapshot['label'],destination_text=row.venue_snapshot['label'],start_at=row.event_start_at,end_at=row.event_start_at+timedelta(hours=float(row.expected_hours)),passenger_count=row.passenger_count,large_luggage_count=0,small_luggage_count=0,status='CONFIRMED',assurance_type='STANDARD_HIRE',currency='LKR',itinerary_snapshot={'event_group_id':str(row.id),'event':row.request_snapshot},price_snapshot={'current':allocation.package_snapshot},accepted_quote_digest=row.accepted_quote_digest,total_amount=allocation.allocation_amount,quoted_amount=allocation.allocation_amount,vehicle_committed=True,created_by=user.id,updated_by=user.id);db.add(booking);db.flush();trip=Trip(trip_reference='ETR-'+secrets.token_hex(8).upper(),booking_id=booking.id,vehicle_id=vehicle.id,operating_owner_user_id=user.id,driver_user_id=driver.id,assignment_type='EXTERNAL_DRIVER',assignment_status='ACCEPTED',status='READY',scheduled_start_at=booking.start_at,scheduled_end_at=booking.end_at,created_by=user.id,updated_by=user.id);db.add(trip);db.flush();allocation.driver_user_id=driver.id;allocation.booking_id=booking.id;allocation.trip_id=trip.id;allocation.status='CONFIRMED';touch(allocation)
 row.status='CONFIRMED';row.owner_accepted_at=row.confirmed_at=datetime.now(timezone.utc);touch(row);notice(db,row,row.passenger_user_id,'Event Hire confirmed','Every requested vehicle allocation and Driver has been confirmed.');[notice(db,row,a.driver_user_id,'Event Driver assignment','You have an assigned Event vehicle allocation.') for a in allocations];db.commit();return safe_group(row,allocations)
@router.post('/event-hire/groups/{group_id}/owner-acceptance')
def owner_accept(group_id:UUID,body:Version,user=Depends(current),db:Session=Depends(get_db)):
 require_role(db,user,'OWNER');row=db.get(EventBookingGroup,group_id)
 if not row or row.owner_user_id!=user.id:raise ApiError(404,'EVENT_GROUP_NOT_FOUND','Event booking not found.')
 if row.version!=body.expected_version or row.status!='PASSENGER_ACCEPTED':raise ApiError(409,'EVENT_ACCEPTANCE_CHANGED','Reload the Passenger-accepted Event request.')
 row.status='OWNER_ACCEPTED';row.owner_accepted_at=datetime.now(timezone.utc);touch(row);notice(db,row,row.passenger_user_id,'Owner accepted Event request','The Owner is assigning every vehicle allocation.');db.commit();return safe_group(row,db.scalars(select(EventVehicleAllocation).where(EventVehicleAllocation.event_group_id==row.id)).all())
