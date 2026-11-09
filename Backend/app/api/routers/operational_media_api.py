from datetime import datetime,timezone,timedelta
from uuid import UUID
from fastapi import APIRouter,Depends,File,Form,UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.routers.api import current,require_role
from app.core.errors import ApiError
from app.dependencies.database import get_db
from app.models.hire_models import Trip,Booking,VehicleRecord
from app.models.review_models import Vehicle
from app.models.trip_operation_models import TripMedia,TripOdometerReading,VehicleOperationalExpense
from app.services.operational_media import OperationalMedia

router=APIRouter(prefix='/api/v1',tags=['Private operational media'])
KINDS={'DASHBOARD','DEPARTURE_ODOMETER','PICKUP_ODOMETER','DROPOFF_ODOMETER','RETURN_ODOMETER','EXPENSE_RECEIPT','MAINTENANCE_RECEIPT','RENTAL_INSPECTION'}
def summary(row):return {'id':str(row.id),'trip_id':str(row.trip_id) if row.trip_id else None,'media_kind':row.media_kind,'mime_type':row.mime_type,'byte_size':row.byte_size,'sha256':row.sha256,'captured_at':row.captured_at.isoformat() if row.captured_at else None,'retention_until':row.retention_until.isoformat() if row.retention_until else None,'download_url':f'/api/v1/operational-media/{row.id}/download'}
def trip_access(db,trip,user,write=False):
 if not trip:raise ApiError(404,'TRIP_NOT_FOUND','Trip not found.')
 vehicle=db.get(Vehicle,trip.vehicle_id);booking=db.get(Booking,trip.booking_id)
 if write and user.id in (trip.driver_user_id,trip.operating_owner_user_id):require_role(db,user,'DRIVER' if user.id==trip.driver_user_id else 'OWNER');return
 if not write and (user.id in (trip.driver_user_id,trip.operating_owner_user_id) or vehicle and vehicle.owner_user_id==user.id or booking and booking.passenger_user_id==user.id):return
 raise ApiError(403,'MEDIA_PERMISSION_DENIED','You are not permitted to access this operational evidence.')
@router.post('/operational-media')
def upload(trip_id:str|None=Form(None),vehicle_record_id:str|None=Form(None),media_kind:str=Form(...),odometer_reading_id:str|None=Form(None),expense_id:str|None=Form(None),captured_at:str|None=Form(None),file:UploadFile=File(...),user=Depends(current),db:Session=Depends(get_db)):
 if media_kind not in KINDS:raise ApiError(422,'MEDIA_KIND_INVALID','This evidence kind is not supported.')
 trip=db.get(Trip,UUID(trip_id)) if trip_id else None;record=db.get(VehicleRecord,UUID(vehicle_record_id)) if vehicle_record_id else None
 if bool(trip)==bool(record):raise ApiError(422,'MEDIA_PARENT_REQUIRED','Attach evidence to exactly one trip or maintenance record.')
 if record:
  vehicle=db.get(Vehicle,record.vehicle_id)
  if media_kind!='MAINTENANCE_RECEIPT' or not vehicle or vehicle.owner_user_id!=user.id:raise ApiError(403,'MEDIA_PERMISSION_DENIED','Only the Vehicle Owner may attach a maintenance receipt.')
  require_role(db,user,'OWNER')
 else:
  trip_access(db,trip,user,True)
  if media_kind=='MAINTENANCE_RECEIPT':raise ApiError(422,'MEDIA_PARENT_REQUIRED','Maintenance evidence must reference its maintenance record.')
  odometer=db.get(TripOdometerReading,UUID(odometer_reading_id)) if odometer_reading_id else None;expense=db.get(VehicleOperationalExpense,UUID(expense_id)) if expense_id else None
  if odometer and odometer.trip_id!=trip.id or expense and expense.trip_id!=trip.id:raise ApiError(422,'MEDIA_LINK_INVALID','Evidence links must belong to the selected trip.')
 try:captured=datetime.fromisoformat(captured_at.replace('Z','+00:00')) if captured_at else None
 except ValueError:raise ApiError(422,'MEDIA_CAPTURED_AT_INVALID','Use an ISO-8601 capture time.')
 store=OperationalMedia(__import__('app.core.config',fromlist=['get_settings']).get_settings());key,mime,size,digest=store.place(file)
 row=TripMedia(trip_id=trip.id if trip else None,vehicle_record_id=record.id if record else None,odometer_reading_id=odometer.id if trip and odometer else None,expense_id=expense.id if trip and expense else None,media_kind=media_kind,storage_key=key,sha256=digest,mime_type=mime,byte_size=size,captured_at=captured,retention_until=datetime.now(timezone.utc)+timedelta(days=365),uploaded_by_user_id=user.id,created_by=user.id,updated_by=user.id);db.add(row);db.commit();return summary(row)
@router.get('/operational-media/{media_id}')
def metadata(media_id:UUID,user=Depends(current),db:Session=Depends(get_db)):
 row=db.get(TripMedia,media_id)
 if not row:raise ApiError(404,'MEDIA_NOT_FOUND','Evidence was not found.')
 if row.trip_id:trip_access(db,db.get(Trip,row.trip_id),user)
 else:
  record=db.get(VehicleRecord,row.vehicle_record_id);vehicle=db.get(Vehicle,record.vehicle_id) if record else None
  if not vehicle or vehicle.owner_user_id!=user.id:raise ApiError(403,'MEDIA_PERMISSION_DENIED','You are not permitted to access this evidence.')
 return summary(row)
@router.get('/operational-media/{media_id}/download')
def download(media_id:UUID,user=Depends(current),db:Session=Depends(get_db)):
 row=metadata(media_id,user,db);entity=db.get(TripMedia,media_id);raw=OperationalMedia(__import__('app.core.config',fromlist=['get_settings']).get_settings()).open(entity)
 return Response(raw,media_type=entity.mime_type,headers={'Content-Disposition':'attachment; filename="evidence"','Cache-Control':'private, no-store'})
