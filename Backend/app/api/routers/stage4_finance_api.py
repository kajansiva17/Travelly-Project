"""Stage 4 sandbox payments, Owner settlement ledger, and verified maintenance records."""
from datetime import datetime,timezone
from decimal import Decimal,ROUND_HALF_UP
from uuid import UUID
from fastapi import APIRouter,Depends
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from app.api.routers.api import current,require_role,touch
from app.core.errors import ApiError
from app.dependencies.database import get_db
from app.models.hire_models import Booking,Trip,VehicleRecord,Notification
from app.models.review_models import Vehicle
from app.models.trip_operation_models import TripFareCalculation,VehicleOperationalExpense
from app.models.stage4_models import TripPayment,OwnerSettlement,PlatformFeePolicy,VehicleMaintenanceSchedule
from app.schemas.stage4_schemas import Version,CashReceived,ProviderCallback,MaintenanceSchedule,MaintenanceRecord
from app.services.payment_provider import provider

router=APIRouter(prefix='/api/v1',tags=['Stage 4 finance and maintenance'])
ZERO=Decimal('0.00')
def now():return datetime.now(timezone.utc)
def read(row):return {k:(str(v) if isinstance(v,(UUID,Decimal)) else v.isoformat() if isinstance(v,datetime) else v) for k,v in row.__dict__.items() if not k.startswith('_') and k not in ('provider_callback_hash',)}
def trip_for(db,trip_id):
 row=db.get(Trip,trip_id)
 if not row:raise ApiError(404,'TRIP_NOT_FOUND','Trip not found.')
 booking=db.get(Booking,row.booking_id)
 if not booking:raise ApiError(404,'BOOKING_NOT_FOUND','Booking not found.')
 return row,booking
def operator(db,trip,user):
 if trip.driver_user_id!=user.id:raise ApiError(403,'DRIVER_REQUIRED','Only the assigned Driver can record this operation.')
 require_role(db,user,'DRIVER')
def owner(db,trip,user):
 if trip.operating_owner_user_id!=user.id:raise ApiError(403,'OWNER_REQUIRED','Only the vehicle Owner can confirm this record.')
 require_role(db,user,'OWNER')
def final_fare(db,trip):
 fare=db.scalar(select(TripFareCalculation).where(TripFareCalculation.trip_id==trip.id,TripFareCalculation.status=='FINALIZED').order_by(TripFareCalculation.calculation_sequence.desc()))
 if not fare:raise ApiError(409,'FINAL_FARE_REQUIRED','A finalized Stage 3 fare is required before payment.')
 return fare
def policy(db):
 row=db.scalar(select(PlatformFeePolicy).where(PlatformFeePolicy.status=='ACTIVE').order_by(PlatformFeePolicy.effective_from.desc()))
 if not row:raise ApiError(503,'FEE_POLICY_UNAVAILABLE','No active platform-fee policy is configured.')
 return row
def reimbursement(db,trip):
 return db.scalar(select(func.coalesce(func.sum(VehicleOperationalExpense.amount),0)).where(VehicleOperationalExpense.trip_id==trip.id,VehicleOperationalExpense.approval_status=='APPROVED',VehicleOperationalExpense.reimbursement_status.in_(('APPROVED','PAID')))) or ZERO
def notify(db,booking,trip,title,body):
 for uid in {booking.passenger_user_id,booking.owner_user_id,trip.driver_user_id}-{None}:
  db.add(Notification(recipient_user_id=uid,booking_id=booking.id,trip_id=trip.id,notification_type='PAYMENT',channel='IN_APP',title=title,body=body,action_required=False,action_payload={'trip_id':str(trip.id)},status='QUEUED'))
def settle(db,trip,booking,payment,status):
 fee=policy(db);amount=payment.amount;fee_amount=(amount*fee.fee_rate).quantize(Decimal('.01'),rounding=ROUND_HALF_UP);reimb=reimbursement(db,trip);payable=amount-fee_amount+reimb
 row=OwnerSettlement(trip_id=trip.id,payment_id=payment.id,owner_user_id=trip.operating_owner_user_id,gross_fare_amount=amount,platform_fee_rate=fee.fee_rate,platform_fee_amount=fee_amount,provider_fee_amount=payment.provider_fee_amount,reimbursement_amount=reimb,owner_payable_amount=payable,status=status,created_by=payment.created_by,updated_by=payment.updated_by);db.add(row);db.flush();payment.fee_policy_id=fee.id;payment.platform_fee_rate=fee.fee_rate;payment.platform_fee_amount=fee_amount;payment.owner_payable_amount=payable;touch(payment);return row
@router.get('/trips/{trip_id}/financials')
def financials(trip_id:UUID,user=Depends(current),db:Session=Depends(get_db)):
 trip,booking=trip_for(db,trip_id)
 if user.id not in (booking.passenger_user_id,trip.driver_user_id,trip.operating_owner_user_id):raise ApiError(404,'TRIP_NOT_FOUND','Trip not found.')
 payments=db.scalars(select(TripPayment).where(TripPayment.trip_id==trip.id).order_by(TripPayment.created_at.desc())).all();settlements=db.scalars(select(OwnerSettlement).where(OwnerSettlement.trip_id==trip.id)).all();fare=db.scalar(select(TripFareCalculation).where(TripFareCalculation.trip_id==trip.id,TripFareCalculation.status=='FINALIZED').order_by(TripFareCalculation.calculation_sequence.desc()))
 return {'booking_version':booking.version,'final_fare':read(fare) if fare else None,'payments':[read(x) for x in payments],'settlements':[read(x) for x in settlements]}
@router.post('/trips/{trip_id}/payments/online-intents')
def online_intent(trip_id:UUID,body:Version,user=Depends(current),db:Session=Depends(get_db)):
 trip,booking=trip_for(db,trip_id)
 if booking.passenger_user_id!=user.id:raise ApiError(403,'PASSENGER_REQUIRED','Only the Passenger can begin payment.')
 if booking.version!=body.expected_version:raise ApiError(409,'BOOKING_CHANGED','Reload the booking before payment.')
 fare=final_fare(db,trip);intent=provider.create_intent();row=TripPayment(trip_id=trip.id,booking_id=booking.id,payer_user_id=user.id,payment_method='ONLINE',provider_code=provider.code,provider_reference=intent.provider_reference,provider_callback_hash=provider.callback_hash(intent.callback_token),amount=fare.total_amount,currency=fare.currency,status='PROCESSING',initiated_at=now(),provider_fee_amount=ZERO,created_by=user.id,updated_by=user.id);db.add(row);booking.payment_status_snapshot='PROCESSING';touch(booking);booking.updated_by=user.id;notify(db,booking,trip,'Online payment awaiting sandbox confirmation','The final fare remains unpaid until the sandbox provider callback succeeds.');db.commit();return read(row)
@router.post('/payments/{payment_id}/provider-callback')
def provider_callback(payment_id:UUID,body:ProviderCallback,db:Session=Depends(get_db)):
 payment=db.get(TripPayment,payment_id)
 if not payment or payment.payment_method!='ONLINE' or payment.status!='PROCESSING' or not provider.verify_callback(payment,body.provider_reference,body.callback_token):raise ApiError(404,'PAYMENT_NOT_FOUND','Payment callback was not accepted.')
 trip,booking=trip_for(db,payment.trip_id)
 if body.status=='FAILED':payment.status='FAILED';touch(payment);booking.payment_status_snapshot='FAILED';touch(booking);db.commit();return read(payment)
 payment.status='ONLINE_PAID';payment.provider_confirmed_at=now();payment.confirmed_at=payment.provider_confirmed_at;payment.provider_fee_amount=body.provider_fee_amount;touch(payment);payment.updated_by=payment.payer_user_id;booking.payment_status_snapshot='PAID';touch(booking);booking.updated_by=payment.payer_user_id;settle(db,trip,booking,payment,'OWNER_PAYABLE');notify(db,booking,trip,'Online payment confirmed','Sandbox provider confirmed the final fare. Owner payable and platform-fee values are ledger records only.');db.commit();return read(payment)
@router.post('/trips/{trip_id}/payments/cash-confirmations')
def passenger_cash(trip_id:UUID,body:Version,user=Depends(current),db:Session=Depends(get_db)):
 trip,booking=trip_for(db,trip_id)
 if booking.passenger_user_id!=user.id:raise ApiError(403,'PASSENGER_REQUIRED','Only the Passenger can confirm cash payment.')
 if booking.version!=body.expected_version:raise ApiError(409,'BOOKING_CHANGED','Reload the booking before payment.')
 fare=final_fare(db,trip);row=TripPayment(trip_id=trip.id,booking_id=booking.id,payer_user_id=user.id,payment_method='CASH',amount=fare.total_amount,currency=fare.currency,status='CASH_PASSENGER_CONFIRMED',initiated_at=now(),passenger_cash_confirmed_at=now(),provider_fee_amount=ZERO,created_by=user.id,updated_by=user.id);db.add(row);booking.payment_status_snapshot='CASH_AWAITING_CONFIRMATION';touch(booking);booking.updated_by=user.id;notify(db,booking,trip,'Passenger reported cash payment','Driver confirmation is required before cash is treated as received.');db.commit();return read(row)
@router.post('/payments/{payment_id}/cash-received')
def cash_received(payment_id:UUID,body:CashReceived,user=Depends(current),db:Session=Depends(get_db)):
 row=db.get(TripPayment,payment_id)
 if not row or row.payment_method!='CASH' or row.status!='CASH_PASSENGER_CONFIRMED':raise ApiError(409,'PAYMENT_CHANGED','Reload the cash payment.')
 trip,booking=trip_for(db,row.trip_id);operator(db,trip,user)
 if row.version!=body.expected_version or body.amount!=row.amount:raise ApiError(409,'CASH_AMOUNT_MISMATCH','Cash received must equal the finalized fare.')
 row.status='CASH_HELD_BY_DRIVER';row.driver_cash_received_at=now();row.confirmed_at=row.driver_cash_received_at;row.held_by_driver_user_id=user.id;touch(row);row.updated_by=user.id;booking.payment_status_snapshot='CASH_AWAITING_CONFIRMATION';touch(booking);booking.updated_by=user.id;settle(db,trip,booking,row,'CASH_HELD_BY_DRIVER');notify(db,booking,trip,'Cash received by Driver','Cash is held by the Driver and awaits handover to the vehicle Owner.');db.commit();return read(row)
@router.post('/payments/{payment_id}/cash-handover')
def cash_handover(payment_id:UUID,body:Version,user=Depends(current),db:Session=Depends(get_db)):
 row=db.get(TripPayment,payment_id)
 if not row or row.status!='CASH_HELD_BY_DRIVER' or row.held_by_driver_user_id!=user.id or row.version!=body.expected_version:raise ApiError(409,'PAYMENT_CHANGED','Reload the cash payment.')
 trip,booking=trip_for(db,row.trip_id);operator(db,trip,user);settlement=db.scalar(select(OwnerSettlement).where(OwnerSettlement.payment_id==row.id).with_for_update());row.status='CASH_OWNER_SETTLEMENT_PENDING';row.driver_cash_handover_at=now();touch(row);row.updated_by=user.id;settlement.status='OWNER_SETTLEMENT_PENDING';settlement.driver_handover_by_user_id=user.id;settlement.driver_handover_at=row.driver_cash_handover_at;touch(settlement);settlement.updated_by=user.id;notify(db,booking,trip,'Cash handover recorded','The vehicle Owner must confirm receipt before cash settlement is complete.');db.commit();return read(row)
@router.post('/payments/{payment_id}/owner-settlement-receipt')
def owner_receipt(payment_id:UUID,body:Version,user=Depends(current),db:Session=Depends(get_db)):
 row=db.get(TripPayment,payment_id)
 if not row or row.status!='CASH_OWNER_SETTLEMENT_PENDING' or row.version!=body.expected_version:raise ApiError(409,'PAYMENT_CHANGED','Reload the settlement.')
 trip,booking=trip_for(db,row.trip_id);owner(db,trip,user);settlement=db.scalar(select(OwnerSettlement).where(OwnerSettlement.payment_id==row.id).with_for_update());row.status='SETTLED';touch(row);row.updated_by=user.id;booking.payment_status_snapshot='PAID';touch(booking);booking.updated_by=user.id;settlement.status='OWNER_PAID';settlement.owner_received_at=now();settlement.owner_received_by_user_id=user.id;touch(settlement);settlement.updated_by=user.id;notify(db,booking,trip,'Cash settlement complete','Vehicle Owner confirmed cash receipt.');db.commit();return read(row)
@router.get('/vehicles/{vehicle_id}/maintenance')
def maintenance(vehicle_id:UUID,user=Depends(current),db:Session=Depends(get_db)):
 vehicle=db.get(Vehicle,vehicle_id)
 if not vehicle or vehicle.owner_user_id!=user.id:raise ApiError(404,'VEHICLE_NOT_FOUND','Vehicle not found.')
 require_role(db,user,'OWNER');schedules=db.scalars(select(VehicleMaintenanceSchedule).where(VehicleMaintenanceSchedule.vehicle_id==vehicle.id).order_by(VehicleMaintenanceSchedule.created_at.desc())).all();records=db.scalars(select(VehicleRecord).where(VehicleRecord.vehicle_id==vehicle.id,VehicleRecord.record_type.in_(('OIL_CHANGE','TYRE_CHANGE','GENERAL_SERVICE','BRAKE_SERVICE','BATTERY_SERVICE','REPAIR','ODOMETER_UPDATE'))).order_by(VehicleRecord.recorded_at.desc())).all();return {'schedules':[read(x) for x in schedules],'records':[read(x) for x in records]}
@router.post('/vehicles/{vehicle_id}/maintenance/schedules')
def schedule(vehicle_id:UUID,body:MaintenanceSchedule,user=Depends(current),db:Session=Depends(get_db)):
 vehicle=db.get(Vehicle,vehicle_id)
 if not vehicle or vehicle.owner_user_id!=user.id:raise ApiError(404,'VEHICLE_NOT_FOUND','Vehicle not found.')
 require_role(db,user,'OWNER')
 if vehicle.version!=body.expected_version:raise ApiError(409,'VEHICLE_CHANGED','Reload the vehicle before scheduling maintenance.')
 if not (body.interval_km or body.interval_days) or not (body.next_due_odometer_km is not None or body.next_due_date):raise ApiError(422,'MAINTENANCE_SCHEDULE_INVALID','Provide an interval and an initial due kilometre or date.')
 if body.maintenance_type=='CUSTOM_SERVICE' and not body.custom_label:raise ApiError(422,'MAINTENANCE_SCHEDULE_INVALID','Custom service needs a label.')
 row=VehicleMaintenanceSchedule(vehicle_id=vehicle.id,maintenance_type=body.maintenance_type,custom_label=body.custom_label,interval_km=body.interval_km,interval_days=body.interval_days,next_due_odometer_km=body.next_due_odometer_km,next_due_date=body.next_due_date,active=True,created_by=user.id,updated_by=user.id);db.add(row);db.commit();return read(row)
@router.post('/vehicles/{vehicle_id}/maintenance/records')
def maintenance_record(vehicle_id:UUID,body:MaintenanceRecord,user=Depends(current),db:Session=Depends(get_db)):
 vehicle=db.get(Vehicle,vehicle_id)
 if not vehicle or vehicle.owner_user_id!=user.id:raise ApiError(404,'VEHICLE_NOT_FOUND','Vehicle not found.')
 require_role(db,user,'OWNER')
 if vehicle.version!=body.expected_version:raise ApiError(409,'VEHICLE_CHANGED','Reload the vehicle before recording maintenance.')
 try:recorded=datetime.fromisoformat(body.recorded_at.replace('Z','+00:00'))
 except ValueError:raise ApiError(422,'MAINTENANCE_RECORD_INVALID','Use an ISO-8601 date and time.')
 row=VehicleRecord(vehicle_id=vehicle.id,recorded_by_user_id=user.id,record_type=body.record_type,recorded_at=recorded,odometer_km=body.odometer_km,amount=body.amount,currency='LKR',service_provider=body.service_provider,notes=body.notes,approval_status='OWNER_RECORDED',created_by=user.id,updated_by=user.id);db.add(row);vehicle.current_odometer_km=body.odometer_km;vehicle.odometer_updated_at=now();touch(vehicle);vehicle.updated_by=user.id;db.commit();return read(row)
