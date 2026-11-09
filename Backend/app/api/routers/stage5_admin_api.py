"""Stage 5 Admin oversight. Read-only workflow inspection plus explicit, non-mutating exception events."""
from datetime import datetime,timezone
from uuid import UUID
from fastapi import APIRouter,Depends,Request
from sqlalchemy import select,func,or_
from sqlalchemy.orm import Session
from app.api.routers.api import current,require_role,touch
from app.api.routers.review_api import admin
from app.core.errors import ApiError
from app.dependencies.database import get_db
from app.models.hire_models import Booking,Trip,VehicleRecord
from app.models.review_models import Vehicle
from app.models.trip_operation_models import TripFareCalculation,TripOperationEvent,TripOdometerReading,VehicleOperationalExpense
from app.models.stage4_models import TripPayment,OwnerSettlement
from app.models.stage5_models import VehicleTypeCatalog,AdminManualFulfilmentEvent
from app.schemas.stage5_schemas import VehicleTypeRequest,VehicleTypeReview,ManualFulfilmentEvent,ManualFulfilmentClose

router=APIRouter(prefix='/api/v1',tags=['Stage 5 Admin workflow'])
def now():return datetime.now(timezone.utc)
def read(row):return {k:(str(v) if isinstance(v,UUID) else v.isoformat() if isinstance(v,datetime) else v) for k,v in row.__dict__.items() if not k.startswith('_')}
def pages(request):
 p=max(1,int(request.query_params.get('page','1')));s=min(100,max(1,int(request.query_params.get('page_size','25'))));return p,s
def trip_view(db,trip):
 booking=db.get(Booking,trip.booking_id);fare=db.scalar(select(TripFareCalculation).where(TripFareCalculation.trip_id==trip.id).order_by(TripFareCalculation.calculation_sequence.desc()));payment=db.scalar(select(TripPayment).where(TripPayment.trip_id==trip.id).order_by(TripPayment.created_at.desc()));settlement=db.scalar(select(OwnerSettlement).where(OwnerSettlement.trip_id==trip.id));return {'trip_id':str(trip.id),'trip_reference':trip.trip_reference,'booking_id':str(booking.id),'booking_reference':booking.booking_reference,'booking_status':booking.status,'trip_status':trip.status,'scheduled_start_at':trip.scheduled_start_at.isoformat(),'scheduled_end_at':trip.scheduled_end_at.isoformat(),'final_fare':{'status':fare.status,'total_amount':str(fare.total_amount),'currency':fare.currency,'snapshot_hash':fare.snapshot_hash} if fare else None,'payment':{'status':payment.status,'method':payment.payment_method,'amount':str(payment.amount),'currency':payment.currency,'platform_fee_amount':str(payment.platform_fee_amount) if payment.platform_fee_amount is not None else None} if payment else None,'settlement':{'status':settlement.status,'owner_payable_amount':str(settlement.owner_payable_amount),'platform_fee_amount':str(settlement.platform_fee_amount)} if settlement else None}
@router.get('/admin/workflow/bookings')
def bookings(request:Request,user=Depends(admin),db:Session=Depends(get_db)):
 p,s=pages(request);status=request.query_params.get('status');q=request.query_params.get('q','').strip()
 query=select(Trip).join(Booking,Booking.id==Trip.booking_id)
 if status:query=query.where(or_(Trip.status==status,Booking.status==status))
 if q:query=query.where(or_(Trip.trip_reference.ilike('%'+q+'%'),Booking.booking_reference.ilike('%'+q+'%')))
 total=db.scalar(select(func.count()).select_from(query.subquery()));rows=db.scalars(query.order_by(Trip.scheduled_start_at.desc()).offset((p-1)*s).limit(s)).all();return {'items':[trip_view(db,row) for row in rows],'page':p,'page_size':s,'total':total}
@router.get('/admin/workflow/trips/{trip_id}')
def booking_detail(trip_id:UUID,user=Depends(admin),db:Session=Depends(get_db)):
 trip=db.get(Trip,trip_id)
 if not trip:raise ApiError(404,'TRIP_NOT_FOUND','Trip not found.')
 result=trip_view(db,trip);events=db.scalars(select(TripOperationEvent).where(TripOperationEvent.trip_id==trip.id).order_by(TripOperationEvent.sequence_no)).all();odos=db.scalars(select(TripOdometerReading).where(TripOdometerReading.trip_id==trip.id).order_by(TripOdometerReading.recorded_at)).all();expenses=db.scalars(select(VehicleOperationalExpense).where(VehicleOperationalExpense.trip_id==trip.id).order_by(VehicleOperationalExpense.recorded_at)).all();result.update({'timeline':[read(x) for x in events],'odometer_evidence':[{'reading_type':x.reading_type,'odometer_km':str(x.odometer_km),'recorded_at':x.recorded_at.isoformat()} for x in odos],'expense_metadata':[{'expense_type':x.expense_type,'amount':str(x.amount),'approval_status':x.approval_status,'reimbursement_status':x.reimbursement_status,'recorded_at':x.recorded_at.isoformat()} for x in expenses]});return result
@router.get('/admin/workflow/payments')
def payments(request:Request,user=Depends(admin),db:Session=Depends(get_db)):
 p,s=pages(request);status=request.query_params.get('status');query=select(TripPayment)
 if status:query=query.where(TripPayment.status==status)
 total=db.scalar(select(func.count()).select_from(query.subquery()));rows=db.scalars(query.order_by(TripPayment.created_at.desc()).offset((p-1)*s).limit(s)).all();return {'items':[read(x) for x in rows],'page':p,'page_size':s,'total':total}
@router.get('/admin/workflow/reports')
def reports(user=Depends(admin),db:Session=Depends(get_db)):
 completed=db.scalar(select(func.count(Trip.id)).where(Trip.status=='COMPLETED')) or 0;revenue=db.scalar(select(func.coalesce(func.sum(TripFareCalculation.total_amount),0)).where(TripFareCalculation.status=='FINALIZED')) or 0;expenses=db.scalar(select(func.coalesce(func.sum(VehicleOperationalExpense.amount),0))) or 0;due=db.scalar(select(func.count(VehicleRecord.id)).where(VehicleRecord.next_due_odometer_km.is_not(None))) or 0;return {'completed_trips':completed,'service_revenue_lkr':str(revenue),'operational_expenses_lkr':str(expenses),'maintenance_due_records':due,'note':'Aggregates are internal oversight values, not live payout or GPS reporting.'}
@router.get('/admin/vehicle-types')
def vehicle_types(user=Depends(admin),db:Session=Depends(get_db)):
 return {'items':[read(x) for x in db.scalars(select(VehicleTypeCatalog).order_by(VehicleTypeCatalog.display_name)).all()]}
@router.post('/vehicle-types/requests',status_code=201)
def vehicle_type_request(body:VehicleTypeRequest,user=Depends(current),db:Session=Depends(get_db)):
 require_role(db,user,'OWNER');row=VehicleTypeCatalog(code=body.code,display_name=body.display_name,status='PENDING',requested_by_user_id=user.id,created_by=user.id,updated_by=user.id);db.add(row);db.commit();return read(row)
@router.patch('/admin/vehicle-types/{type_id}/review')
def vehicle_type_review(type_id:UUID,body:VehicleTypeReview,request:Request,user=Depends(admin),db:Session=Depends(get_db)):
 row=db.get(VehicleTypeCatalog,type_id)
 if not row or row.status!='PENDING' or row.version!=body.expected_version:raise ApiError(409,'VEHICLE_TYPE_CHANGED','Reload the vehicle type before review.')
 if body.decision=='REJECTED' and not body.reason:raise ApiError(422,'REASON_REQUIRED','A rejection reason is required.')
 old=row.status;row.status=body.decision;row.reviewed_by_user_id=user.id;row.reviewed_at=now();row.review_reason=body.reason;touch(row);row.updated_by=user.id;request.app.state.audit.commit(db,actor=user.id,target={'resource':'vehicle_type_catalog','id':str(row.id)},previous_status=old,new_status=row.status,previous_version=row.version-1,new_version=row.version,full_reason=body.reason,previous_decision_evidence={'code':row.code},trace_id=request.state.trace_id);return read(row)
@router.get('/admin/manual-fulfilment-events')
def events(user=Depends(admin),db:Session=Depends(get_db)):
 return {'items':[read(x) for x in db.scalars(select(AdminManualFulfilmentEvent).order_by(AdminManualFulfilmentEvent.created_at.desc()).limit(100)).all()]}
@router.post('/admin/manual-fulfilment-events',status_code=201)
def create_event(body:ManualFulfilmentEvent,request:Request,user=Depends(admin),db:Session=Depends(get_db)):
 row=AdminManualFulfilmentEvent(**body.model_dump(),status='OPEN',created_by=user.id,updated_by=user.id);db.add(row);db.flush();request.app.state.audit.commit(db,actor=user.id,target={'resource':'admin_manual_fulfilment_events','id':str(row.id)},previous_status=None,new_status='OPEN',previous_version=0,new_version=1,full_reason=body.details,previous_decision_evidence={},trace_id=request.state.trace_id);return read(row)
@router.patch('/admin/manual-fulfilment-events/{event_id}/close')
def close_event(event_id:UUID,body:ManualFulfilmentClose,request:Request,user=Depends(admin),db:Session=Depends(get_db)):
 row=db.get(AdminManualFulfilmentEvent,event_id)
 if not row or row.status!='OPEN' or row.version!=body.expected_version:raise ApiError(409,'FULFILMENT_EVENT_CHANGED','Reload the fulfilment event.')
 row.status='CLOSED';row.closed_by_user_id=user.id;row.closed_at=now();touch(row);row.updated_by=user.id;request.app.state.audit.commit(db,actor=user.id,target={'resource':'admin_manual_fulfilment_events','id':str(row.id)},previous_status='OPEN',new_status='CLOSED',previous_version=row.version-1,new_version=row.version,full_reason=body.reason,previous_decision_evidence={'summary':row.summary},trace_id=request.state.trace_id);return read(row)
