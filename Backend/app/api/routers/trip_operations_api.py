"""Stage 3 operational writes. Records are private and never alter payment or settlement state."""
import hashlib,secrets
from datetime import datetime,timezone,timedelta
from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter,Depends,Request
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from app.api.routers.api import current,require_role,touch
from app.core.errors import ApiError
from app.dependencies.database import get_db
from app.models.hire_models import Trip,Booking,Notification
from app.models.trip_operation_models import TripOperationRun,TripPickupCredential,TripOperationEvent,TripOdometerReading,TripWaitingSession,TripExtraStop,VehicleOperationalExpense,TripFareCalculation,TripFareLineItem
from app.schemas.trip_operation_schemas import DutyStart,PickupVerify,WaitingStart,WaitingStop,ExtraStop,ExtraStopDecision,ExpenseCreate,ExpenseReview,DestinationArrival,ReturnGarage,Version,FareFinalize
from app.schemas.rate_schemas import RateRule

router=APIRouter(prefix='/api/v1',tags=['Trip operations'])
def now():return datetime.now(timezone.utc)
def missing():raise ApiError(404,'TRIP_NOT_FOUND','Trip not found.')
def driver_trip(db,trip_id,user):
 trip=db.get(Trip,trip_id)
 if not trip or trip.driver_user_id!=user.id:missing()
 require_role(db,user,'DRIVER')
 if trip.assignment_status!='ACCEPTED' or trip.status in ('CANCELLED','COMPLETED'):raise ApiError(409,'TRIP_NOT_ACTIVE','This assignment is not active.')
 return trip
def owner_trip(db,trip_id,user):
 trip=db.get(Trip,trip_id)
 if not trip or trip.operating_owner_user_id!=user.id:missing()
 require_role(db,user,'OWNER');return trip
def run_for(db,trip,user,create=False):
 row=db.scalar(select(TripOperationRun).where(TripOperationRun.trip_id==trip.id).with_for_update())
 if not row and create:
  row=TripOperationRun(trip_id=trip.id,current_phase='NOT_STARTED',final_fare_status='NOT_STARTED',created_by=user.id,updated_by=user.id);db.add(row);db.flush()
 return row
def event(db,trip,user,kind,phase,related=None,note=None):
 seq=(db.scalar(select(func.coalesce(func.max(TripOperationEvent.sequence_no),0)).where(TripOperationEvent.trip_id==trip.id))+1)
 db.add(TripOperationEvent(trip_id=trip.id,sequence_no=seq,event_type=kind,phase_after=phase,occurred_at=now(),recorded_by_user_id=user.id,related_entity_type=related[0] if related else None,related_entity_id=related[1] if related else None,note=note,created_by=user.id,updated_by=user.id))
def read(row):return {k:(str(v) if isinstance(v,(Decimal,UUID)) else v.isoformat() if isinstance(v,datetime) else v) for k,v in row.__dict__.items() if not k.startswith('_') and k not in ('qr_token_hash','pin_hash')}
def commit(db):db.commit()
def notice(db,booking,trip,title,body):
 for uid in {booking.passenger_user_id,booking.owner_user_id,trip.driver_user_id}-{None}:db.add(Notification(recipient_user_id=uid,booking_id=booking.id,trip_id=trip.id,notification_type='RECONFIRMATION',channel='IN_APP',title=title,body=body,action_required=False,action_payload={'trip_id':str(trip.id)},status='QUEUED'))
@router.get('/trips/{trip_id}/operation')
def operation(trip_id:UUID,user=Depends(current),db:Session=Depends(get_db)):
 trip=db.get(Trip,trip_id)
 if not trip or user.id not in (trip.driver_user_id,trip.operating_owner_user_id):missing()
 run=run_for(db,trip,user);events=db.scalars(select(TripOperationEvent).where(TripOperationEvent.trip_id==trip.id).order_by(TripOperationEvent.sequence_no)).all();odos=db.scalars(select(TripOdometerReading).where(TripOdometerReading.trip_id==trip.id)).all();waiting=db.scalars(select(TripWaitingSession).where(TripWaitingSession.trip_id==trip.id).order_by(TripWaitingSession.started_at)).all();stops=db.scalars(select(TripExtraStop).where(TripExtraStop.trip_id==trip.id).order_by(TripExtraStop.sequence_no)).all();expenses=db.scalars(select(VehicleOperationalExpense).where(VehicleOperationalExpense.trip_id==trip.id).order_by(VehicleOperationalExpense.recorded_at)).all();fares=db.scalars(select(TripFareCalculation).where(TripFareCalculation.trip_id==trip.id).order_by(TripFareCalculation.calculation_sequence)).all()
 return {'trip_id':str(trip.id),'trip_status':trip.status,'run':read(run) if run else None,'events':[read(x) for x in events],'odometers':[read(x) for x in odos],'waiting_sessions':[read(x) for x in waiting],'extra_stops':[read(x) for x in stops],'expenses':[read(x) for x in expenses],'fare_calculations':[read(x) for x in fares]}
@router.post('/trips/{trip_id}/operation/duty-start')
def duty_start(trip_id:UUID,body:DutyStart,user=Depends(current),db:Session=Depends(get_db)):
 trip=driver_trip(db,trip_id,user);run=run_for(db,trip,user,True)
 if run.version!=body.expected_version or run.current_phase!='NOT_STARTED':raise ApiError(409,'OPERATION_CHANGED','Reload the operation before recording duty start.')
 reading=TripOdometerReading(trip_id=trip.id,reading_type='DEPARTURE',odometer_km=body.departure_odometer_km,recorded_at=now(),recorded_by_user_id=user.id,created_by=user.id,updated_by=user.id);db.add(reading);db.flush();run.current_phase='DUTY_STARTED';run.duty_started_at=now();run.duty_started_by_user_id=user.id;run.fuel_level_percent=body.fuel_level_percent;touch(run);run.updated_by=user.id;event(db,trip,user,'DUTY_STARTED','DUTY_STARTED',('trip_odometer_readings',reading.id));commit(db);return read(run)
@router.post('/trips/{trip_id}/pickup-verifications')
def pickup_verify(trip_id:UUID,body:PickupVerify,user=Depends(current),db:Session=Depends(get_db)):
 trip=driver_trip(db,trip_id,user);run=run_for(db,trip,user);credential=db.scalar(select(TripPickupCredential).where(TripPickupCredential.trip_id==trip.id).with_for_update())
 if not run or run.version!=body.expected_version or run.current_phase not in ('DUTY_STARTED','EN_ROUTE_PICKUP'):raise ApiError(409,'OPERATION_CHANGED','Duty start is required before pickup.')
 if not credential or credential.expires_at<now() or credential.verification_status!='PENDING':raise ApiError(409,'PICKUP_VERIFICATION_UNAVAILABLE','Current pickup verification is unavailable.')
 digest=hashlib.sha256(body.credential.encode()).hexdigest();valid=digest==credential.qr_token_hash if body.method=='QR' else False
 if body.method=='PIN':from app.core.security import verify_password;valid=verify_password(body.credential,credential.pin_hash)
 if not valid:
  credential.failed_attempts+=1;touch(credential);commit(db);raise ApiError(409,'PICKUP_VERIFICATION_FAILED','The pickup credential was not accepted.')
 reading=TripOdometerReading(trip_id=trip.id,reading_type='PICKUP',odometer_km=body.pickup_odometer_km,recorded_at=now(),recorded_by_user_id=user.id,created_by=user.id,updated_by=user.id);db.add(reading);db.flush();credential.verification_status='VERIFIED';credential.verified_at=now();credential.verified_by_user_id=user.id;touch(credential);run.current_phase='PASSENGER_ONBOARD';run.passenger_started_at=now();touch(run);run.updated_by=user.id;booking=db.get(Booking,trip.booking_id);trip.status='IN_PROGRESS';touch(trip);trip.updated_by=user.id
 if booking:booking.status='IN_PROGRESS';touch(booking);booking.updated_by=user.id
 event(db,trip,user,'PICKUP_VERIFIED','PASSENGER_ONBOARD',('trip_odometer_readings',reading.id));notice(db,booking,trip,'Passenger pickup verified','The assigned Driver verified pickup and started the passenger trip.');commit(db);return read(run)
@router.post('/trips/{trip_id}/waiting-sessions')
def waiting_start(trip_id:UUID,body:WaitingStart,user=Depends(current),db:Session=Depends(get_db)):
 trip=driver_trip(db,trip_id,user);run=run_for(db,trip,user)
 if not run or run.version!=body.expected_version or run.current_phase!='PASSENGER_ONBOARD':raise ApiError(409,'OPERATION_CHANGED','Passenger trip must be active.')
 if db.scalar(select(TripWaitingSession.id).where(TripWaitingSession.trip_id==trip.id,TripWaitingSession.status=='ACTIVE')):raise ApiError(409,'WAITING_ACTIVE','Stop the current waiting timer first.')
 row=TripWaitingSession(trip_id=trip.id,started_at=now(),started_by_user_id=user.id,status='ACTIVE',note=body.note,created_by=user.id,updated_by=user.id);db.add(row);db.flush();event(db,trip,user,'WAITING_STARTED','PASSENGER_ONBOARD',('trip_waiting_sessions',row.id));commit(db);return read(row)
@router.post('/trips/{trip_id}/waiting-sessions/{session_id}/stop')
def waiting_stop(trip_id:UUID,session_id:UUID,body:WaitingStop,user=Depends(current),db:Session=Depends(get_db)):
 trip=driver_trip(db,trip_id,user);row=db.get(TripWaitingSession,session_id)
 if not row or row.trip_id!=trip.id or row.status!='ACTIVE' or row.version!=body.expected_version:raise ApiError(409,'WAITING_CHANGED','Reload the waiting timer.')
 row.status='STOPPED';row.stopped_at=now();row.stopped_by_user_id=user.id;row.note=body.note or row.note;touch(row);event(db,trip,user,'WAITING_STOPPED','PASSENGER_ONBOARD',('trip_waiting_sessions',row.id));commit(db);return read(row)
@router.post('/trips/{trip_id}/extra-stops')
def extra_stop(trip_id:UUID,body:ExtraStop,user=Depends(current),db:Session=Depends(get_db)):
 trip=driver_trip(db,trip_id,user);run=run_for(db,trip,user)
 if not run or run.version!=body.expected_version or run.current_phase!='PASSENGER_ONBOARD':raise ApiError(409,'OPERATION_CHANGED','Passenger trip must be active.')
 seq=(db.scalar(select(func.coalesce(func.max(TripExtraStop.sequence_no),0)).where(TripExtraStop.trip_id==trip.id))+1);row=TripExtraStop(trip_id=trip.id,sequence_no=seq,place_label=body.place_label,latitude=body.latitude,longitude=body.longitude,proposed_by_user_id=user.id,proposed_at=now(),approval_status='PROPOSED',created_by=user.id,updated_by=user.id);db.add(row);db.flush();event(db,trip,user,'EXTRA_STOP_PROPOSED','PASSENGER_ONBOARD',('trip_extra_stops',row.id));commit(db);return read(row)
@router.get('/trips/{trip_id}/extra-stops')
def extra_stops(trip_id:UUID,user=Depends(current),db:Session=Depends(get_db)):
 trip=db.get(Trip,trip_id);booking=db.get(Booking,trip.booking_id) if trip else None
 if not trip or not booking or user.id not in (trip.driver_user_id,trip.operating_owner_user_id,booking.passenger_user_id):missing()
 rows=db.scalars(select(TripExtraStop).where(TripExtraStop.trip_id==trip.id).order_by(TripExtraStop.sequence_no)).all()
 return {'items':[read(row) for row in rows]}
@router.post('/trips/{trip_id}/extra-stops/{stop_id}/approve')
def approve_extra_stop(trip_id:UUID,stop_id:UUID,body:ExtraStopDecision,user=Depends(current),db:Session=Depends(get_db)):
 trip=db.get(Trip,trip_id);row=db.get(TripExtraStop,stop_id)
 if not trip or not row or row.trip_id!=trip.id or not trip.booking_id:missing()
 booking=db.get(Booking,trip.booking_id)
 if not booking or booking.passenger_user_id!=user.id:raise ApiError(403,'PASSENGER_REQUIRED','Only the Passenger can decide this extra-stop proposal.')
 if row.version!=body.expected_version or row.approval_status!='PROPOSED':raise ApiError(409,'EXTRA_STOP_CHANGED','Reload the extra stop.')
 row.approval_status='PASSENGER_APPROVED' if body.decision=='APPROVED' else 'REJECTED';row.approved_by_user_id=user.id;row.approved_at=now();row.rejection_reason=body.reason;touch(row);row.updated_by=user.id;event(db,trip,user,'EXTRA_STOP_'+body.decision,'PASSENGER_ONBOARD',('trip_extra_stops',row.id),body.reason);commit(db);return read(row)
@router.post('/trips/{trip_id}/expenses')
def expense(trip_id:UUID,body:ExpenseCreate,user=Depends(current),db:Session=Depends(get_db)):
 trip=driver_trip(db,trip_id,user)
 approval='SELF_RECORDED' if trip.operating_owner_user_id==user.id else 'SUBMITTED';reimbursement='NOT_APPLICABLE' if approval=='SELF_RECORDED' else 'NOT_REQUESTED'
 row=VehicleOperationalExpense(vehicle_id=trip.vehicle_id,trip_id=trip.id,expense_type=body.expense_type,amount=body.amount,currency='LKR',paid_by_user_id=user.id,recorded_at=body.recorded_at,odometer_km=body.odometer_km,approval_status=approval,reimbursement_status=reimbursement,note=body.note,created_by=user.id,updated_by=user.id);db.add(row);db.flush();event(db,trip,user,'EXPENSE_RECORDED',run_for(db,trip,user).current_phase,('vehicle_operational_expenses',row.id));commit(db);return read(row)
@router.patch('/trips/{trip_id}/expenses/{expense_id}/review')
def expense_review(trip_id:UUID,expense_id:UUID,body:ExpenseReview,user=Depends(current),db:Session=Depends(get_db)):
 trip=owner_trip(db,trip_id,user);row=db.get(VehicleOperationalExpense,expense_id)
 if not row or row.trip_id!=trip.id:missing()
 if row.version!=body.expected_version or row.approval_status!='SUBMITTED':raise ApiError(409,'EXPENSE_CHANGED','Reload the expense before review.')
 row.approval_status=body.decision;row.reimbursement_status=body.reimbursement_status;row.approved_by_user_id=user.id;row.approved_at=now();row.note=(row.note or '')+(' | '+body.reason if body.reason else '');touch(row);row.updated_by=user.id;event(db,trip,user,'EXPENSE_'+body.decision,run_for(db,trip,user).current_phase,('vehicle_operational_expenses',row.id),body.reason);commit(db);return read(row)
@router.post('/trips/{trip_id}/operation/destination-arrival')
def destination(trip_id:UUID,body:DestinationArrival,user=Depends(current),db:Session=Depends(get_db)):
 trip=driver_trip(db,trip_id,user);run=run_for(db,trip,user)
 if not run or run.version!=body.expected_version or run.current_phase!='PASSENGER_ONBOARD':raise ApiError(409,'OPERATION_CHANGED','Passenger trip must be active.')
 pickup=db.scalar(select(TripOdometerReading).where(TripOdometerReading.trip_id==trip.id,TripOdometerReading.reading_type=='PICKUP'))
 if not pickup or body.dropoff_odometer_km<pickup.odometer_km:raise ApiError(422,'ODOMETER_INVALID','Drop-off odometer cannot precede pickup odometer.')
 row=TripOdometerReading(trip_id=trip.id,reading_type='DROPOFF',odometer_km=body.dropoff_odometer_km,recorded_at=now(),recorded_by_user_id=user.id,created_by=user.id,updated_by=user.id);db.add(row);db.flush();run.current_phase='AT_DESTINATION';run.destination_arrived_at=now();touch(run);run.updated_by=user.id;event(db,trip,user,'DESTINATION_ARRIVED','AT_DESTINATION',('trip_odometer_readings',row.id));notice(db,db.get(Booking,trip.booking_id),trip,'Passenger reached destination','Destination arrival was recorded. Final operational review and payment remain pending.');commit(db);return {'run':read(run),'passenger_distance_km':str(body.dropoff_odometer_km-pickup.odometer_km)}
@router.post('/trips/{trip_id}/operation/return-garage')
def return_garage(trip_id:UUID,body:ReturnGarage,user=Depends(current),db:Session=Depends(get_db)):
 trip=driver_trip(db,trip_id,user);run=run_for(db,trip,user)
 if not run or run.version!=body.expected_version or run.current_phase not in ('AT_DESTINATION','RETURNING'):raise ApiError(409,'OPERATION_CHANGED','Destination arrival is required first.')
 drop=db.scalar(select(TripOdometerReading).where(TripOdometerReading.trip_id==trip.id,TripOdometerReading.reading_type=='DROPOFF'))
 if not drop or body.return_odometer_km<drop.odometer_km:raise ApiError(422,'ODOMETER_INVALID','Return odometer cannot precede drop-off odometer.')
 row=TripOdometerReading(trip_id=trip.id,reading_type='RETURN',odometer_km=body.return_odometer_km,recorded_at=now(),recorded_by_user_id=user.id,created_by=user.id,updated_by=user.id);db.add(row);db.flush();run.current_phase='RETURNED';run.returned_to_garage_at=now();touch(run);run.updated_by=user.id;event(db,trip,user,'RETURNED_TO_GARAGE','RETURNED',('trip_odometer_readings',row.id));commit(db);return read(run)
@router.post('/trips/{trip_id}/fare-calculations/preview')
def fare_preview(trip_id:UUID,body:Version,user=Depends(current),db:Session=Depends(get_db)):
 trip=driver_trip(db,trip_id,user);run=run_for(db,trip,user)
 if not run or run.version!=body.expected_version or run.current_phase!='RETURNED':raise ApiError(409,'OPERATION_CHANGED','Return-to-garage odometer is required before calculating the final fare.')
 booking=db.get(Booking,trip.booking_id);pickup=db.scalar(select(TripOdometerReading).where(TripOdometerReading.trip_id==trip.id,TripOdometerReading.reading_type=='PICKUP'));drop=db.scalar(select(TripOdometerReading).where(TripOdometerReading.trip_id==trip.id,TripOdometerReading.reading_type=='DROPOFF'))
 if not booking or not pickup or not drop or not booking.price_snapshot.get('current'):raise ApiError(409,'FARE_INPUT_UNAVAILABLE','Frozen booking rate and pickup/drop-off odometers are required.')
 sequence=(db.scalar(select(func.coalesce(func.max(TripFareCalculation.calculation_sequence),0)).where(TripFareCalculation.trip_id==trip.id))+1);distance=drop.odometer_km-pickup.odometer_km;waiting=sum((Decimal((x.stopped_at-x.started_at).total_seconds())/Decimal(60) for x in db.scalars(select(TripWaitingSession).where(TripWaitingSession.trip_id==trip.id,TripWaitingSession.status=='STOPPED')).all()),Decimal(0));base=Decimal(str(booking.price_snapshot['current']['calculation']['total']));snapshot=booking.price_snapshot['current'];rule=RateRule.model_validate(snapshot['rule']);usage=snapshot.get('measurement',{}).get('usage',{});planned_distance=Decimal(str(usage.get('distance_km','0')));planned_waiting=Decimal(str(usage.get('waiting_minutes','0')));extras=[]
 def add(kind,label,quantity,rate):
  if rate is not None and quantity>0:extras.append((kind,label,quantity,Decimal(str(rate)),quantity*Decimal(str(rate))))
 if rule.method!='FIXED_ROUTE':add('EXTRA_KM','Operational distance beyond the frozen itinerary',max(Decimal(0),distance-planned_distance),rule.extra_km_rate)
 add('WAITING','Verified waiting beyond the frozen itinerary and free allowance',max(Decimal(0),waiting-rule.free_wait_minutes)-max(Decimal(0),planned_waiting-rule.free_wait_minutes),rule.waiting_hour_rate/Decimal(60))
 if rule.method=='DAY_HIRE' and run.passenger_started_at and run.destination_arrived_at:
  actual_hours=Decimal(str((run.destination_arrived_at-run.passenger_started_at).total_seconds()/3600));planned_hours=sum((Decimal(str(x)) for x in usage.get('service_hours',[])),Decimal(0));overflow=max(Decimal(0),actual_hours-planned_hours);extra_days=int(overflow//Decimal(24));add('EXTRA_DAY','Additional operational day beyond the frozen service windows',Decimal(extra_days),rule.day_charge);overtime=overflow-Decimal(extra_days*24)
  if overtime>0 and rule.extra_hour_rate is not None:extras.append(('OVERTIME','Operational hours beyond the frozen service windows',overtime,Decimal(str(rule.extra_hour_rate)),min(overtime*Decimal(str(rule.extra_hour_rate)),Decimal(str(rule.day_charge)))))
 total=base+sum((x[4] for x in extras),Decimal(0));digest=hashlib.sha256(str(snapshot).encode()).hexdigest();fare=TripFareCalculation(trip_id=trip.id,calculation_sequence=sequence,source_booking_version=booking.version,frozen_rate_snapshot=snapshot,pickup_odometer_reading_id=pickup.id,dropoff_odometer_reading_id=drop.id,passenger_distance_km=distance,waiting_minutes=int(waiting),status='DRAFT',total_amount=total,currency='LKR',calculated_at=now(),snapshot_hash=digest,created_by=user.id,updated_by=user.id);db.add(fare);db.flush();db.add(TripFareLineItem(fare_calculation_id=fare.id,line_no=1,line_type='BASE_PACKAGE',description='Frozen booking rate',amount=base,created_by=user.id,updated_by=user.id))
 for index,(kind,label,quantity,rate,amount) in enumerate(extras,2):db.add(TripFareLineItem(fare_calculation_id=fare.id,line_no=index,line_type=kind,description=label,quantity=quantity,unit_rate=rate,amount=amount,created_by=user.id,updated_by=user.id))
 run.current_phase='FARE_CALCULATED';run.final_fare_status='DRAFT';touch(run);event(db,trip,user,'FARE_PREVIEWED','FARE_CALCULATED',('trip_fare_calculations',fare.id));commit(db);return read(fare)
@router.post('/trips/{trip_id}/fare-calculations/{calculation_id}/finalize')
def fare_finalize(trip_id:UUID,calculation_id:UUID,body:FareFinalize,user=Depends(current),db:Session=Depends(get_db)):
 trip=owner_trip(db,trip_id,user);fare=db.get(TripFareCalculation,calculation_id);run=run_for(db,trip,user)
 if not fare or fare.trip_id!=trip.id or str(calculation_id)!=body.calculation_id or fare.version!=body.expected_version or fare.status!='DRAFT':raise ApiError(409,'FARE_CHANGED','Reload the fare calculation before finalizing.')
 fare.status='FINALIZED';fare.finalized_at=now();fare.finalized_by_user_id=user.id;touch(fare);fare.updated_by=user.id;run.final_fare_status='FINALIZED';touch(run);booking=db.get(Booking,trip.booking_id);trip.status='COMPLETED';touch(trip);trip.updated_by=user.id
 if booking:booking.status='COMPLETED';touch(booking);booking.updated_by=user.id;notice(db,booking,trip,'Trip completed','The final fare was finalized. Passenger payment can now be recorded.');event(db,trip,user,'FARE_FINALIZED',run.current_phase,('trip_fare_calculations',fare.id));commit(db);return read(fare)
