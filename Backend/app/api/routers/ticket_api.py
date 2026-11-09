import hashlib,secrets
from datetime import datetime,timedelta,timezone
from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter,Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.dependencies.database import get_db
from app.api.routers.api import current,require_role,touch
from app.core.errors import ApiError
from app.models.ticket_models import TicketDeparture,TicketSeat,TicketHold,TicketReservation
from app.models.review_models import Vehicle
from app.models import User
from app.models.hire_models import Notification
router=APIRouter(prefix='/api/v1',tags=['Ticket booking'])
def now():return datetime.now(timezone.utc)
def notify(db,recipient,title,body,reference):
 if recipient:db.add(Notification(recipient_user_id=recipient,notification_type='BOOKING_CONFIRMED',channel='IN_APP',title=title,body=body,action_required=False,action_payload={'ticket_reference':reference},status='QUEUED',created_by=recipient,updated_by=recipient))
def expire(db):
 for hold in db.scalars(select(TicketHold).where(TicketHold.status=='ACTIVE',TicketHold.expires_at<=now()).with_for_update()).all():
  hold.status='EXPIRED';touch(hold)
  for seat in db.scalars(select(TicketSeat).where(TicketSeat.departure_id==hold.departure_id,TicketSeat.seat_number.in_(hold.seat_snapshot))).all():seat.status='AVAILABLE';touch(seat)
  notify(db,hold.passenger_user_id,'Ticket seat hold expired','Your selected ticket seats are available again.','')
def departure(db,id):
 row=db.get(TicketDeparture,id)
 if not row or row.status!='PUBLISHED':raise ApiError(404,'DEPARTURE_NOT_FOUND','Scheduled departure not found.')
 return row
@router.get('/ticket-departures')
def search(route:str='',date:str='',vehicle_type:str='',air_conditioned:str='',db:Session=Depends(get_db)):
 expire(db);db.commit();rows=db.scalars(select(TicketDeparture).where(TicketDeparture.status=='PUBLISHED',TicketDeparture.departure_at>now()).order_by(TicketDeparture.departure_at).limit(100)).all();out=[]
 for d in rows:
  if route.lower() not in d.route_label.lower() or date and d.departure_at.date().isoformat()!=date or vehicle_type and d.vehicle_type!=vehicle_type or air_conditioned and str(d.air_conditioned).lower()!=air_conditioned.lower():continue
  seats=db.scalars(select(TicketSeat).where(TicketSeat.departure_id==d.id,TicketSeat.status=='AVAILABLE')).all();out.append({'id':str(d.id),'route':d.route_label,'departure_at':d.departure_at.isoformat(),'vehicle_type':d.vehicle_type,'air_conditioned':d.air_conditioned,'fare_per_seat':str(d.fare_per_seat),'available_seats':len(seats)})
 return {'items':out}
@router.get('/owners/me/ticket-departures')
def owner_departures(user=Depends(current),db:Session=Depends(get_db)):
 require_role(db,user,'OWNER');rows=db.scalars(select(TicketDeparture).where(TicketDeparture.owner_user_id==user.id).order_by(TicketDeparture.departure_at.desc())).all();return {'items':[{'id':str(x.id),'route':x.route_label,'departure_at':x.departure_at.isoformat(),'status':x.status,'vehicle_type':x.vehicle_type,'air_conditioned':x.air_conditioned,'fare_per_seat':str(x.fare_per_seat),'vehicle_id':str(x.vehicle_id),'driver_user_id':str(x.driver_user_id) if x.driver_user_id else None,'seat_count':len(db.scalars(select(TicketSeat).where(TicketSeat.departure_id==x.id)).all())} for x in rows]}
@router.post('/owners/me/ticket-departures')
def create_departure(body:dict,user=Depends(current),db:Session=Depends(get_db)):
 require_role(db,user,'OWNER');vehicle=db.get(Vehicle,UUID(body['vehicle_id'])) if body.get('vehicle_id') else None
 if not vehicle or vehicle.owner_user_id!=user.id or vehicle.verification_status!='APPROVED' or vehicle.availability_status!='ACTIVE':raise ApiError(409,'TICKET_VEHICLE_UNAVAILABLE','Use an approved active Owner vehicle.')
 seats=body.get('seat_numbers') or [];driver=UUID(body['driver_user_id']) if body.get('driver_user_id') else user.id
 assigned_driver=db.get(User,driver)
 if not assigned_driver:raise ApiError(422,'DRIVER_NOT_FOUND','Choose an eligible Driver or Owner-driver.')
 require_role(db,assigned_driver,'DRIVER')
 if not seats or len(seats)!=len(set(seats)) or body.get('vehicle_type') not in ('BUS','VAN'):raise ApiError(422,'DEPARTURE_INVALID','A Bus/Van, Driver and unique seat layout are required.')
 row=TicketDeparture(owner_user_id=user.id,vehicle_id=vehicle.id,route_label=body.get('route_label',''),departure_at=datetime.fromisoformat(body['departure_at'].replace('Z','+00:00')),vehicle_type=body['vehicle_type'],air_conditioned=bool(body.get('air_conditioned')),fare_per_seat=Decimal(str(body['fare_per_seat'])),cancellation_policy_snapshot=body.get('cancellation_policy',{}),driver_user_id=driver,status='DRAFT',created_by=user.id,updated_by=user.id);db.add(row);db.flush()
 for seat in seats:db.add(TicketSeat(departure_id=row.id,seat_number=str(seat),status='AVAILABLE',created_by=user.id,updated_by=user.id))
 db.commit();return {'id':str(row.id),'status':row.status}
@router.post('/owners/me/ticket-departures/{departure_id}/publish')
def publish(departure_id:UUID,body:dict,user=Depends(current),db:Session=Depends(get_db)):
 require_role(db,user,'OWNER');row=db.get(TicketDeparture,departure_id)
 if not row or row.owner_user_id!=user.id:raise ApiError(404,'DEPARTURE_NOT_FOUND','Departure not found.')
 if not row.driver_user_id or not db.scalar(select(TicketSeat.id).where(TicketSeat.departure_id==row.id).limit(1)):raise ApiError(409,'DEPARTURE_NOT_READY','Driver and numbered seat layout are required.')
 row.status='PUBLISHED' if body.get('published') else 'DRAFT';touch(row);db.commit();return {'id':str(row.id),'status':row.status}
@router.get('/admin/ticket-audit')
def audit(user=Depends(current),db:Session=Depends(get_db)):
 require_role(db,user,'ADMIN');rows=db.scalars(select(TicketDeparture).order_by(TicketDeparture.departure_at.desc()).limit(200)).all();return {'items':[{'id':str(d.id),'route':d.route_label,'status':d.status,'departure_at':d.departure_at.isoformat(),'seat_totals':{s:len(db.scalars(select(TicketSeat).where(TicketSeat.departure_id==d.id,TicketSeat.status==s)).all()) for s in ('AVAILABLE','HELD','RESERVED','BLOCKED')},'holds':[{'expires_at':h.expires_at.isoformat(),'status':h.status} for h in db.scalars(select(TicketHold).where(TicketHold.departure_id==d.id)).all()],'reservations':[{'reference':r.reservation_reference,'payment_status':r.payment_status,'boarding_status':r.boarding_status,'cancelled_at':r.cancellation_recorded_at.isoformat() if r.cancellation_recorded_at else None} for r in db.scalars(select(TicketReservation).where(TicketReservation.departure_id==d.id)).all()]} for d in rows]}
@router.get('/ticket-departures/{departure_id}/seats')
def seats(departure_id:UUID,db:Session=Depends(get_db)):
 expire(db);db.commit();departure(db,departure_id);return {'items':[{'seat_number':s.seat_number,'status':s.status} for s in db.scalars(select(TicketSeat).where(TicketSeat.departure_id==departure_id).order_by(TicketSeat.seat_number)).all()]}
@router.post('/ticket-departures/{departure_id}/holds')
def hold(departure_id:UUID,body:dict,user=Depends(current),db:Session=Depends(get_db)):
 require_role(db,user,'PASSENGER');expire(db);d=departure(db,departure_id);numbers=body.get('seat_numbers') or []
 if not numbers or len(numbers)>20 or len(numbers)!=len(set(numbers)):raise ApiError(422,'SEAT_SELECTION_INVALID','Select unique numbered seats.')
 seats=db.scalars(select(TicketSeat).where(TicketSeat.departure_id==d.id,TicketSeat.seat_number.in_(numbers)).with_for_update()).all()
 if len(seats)!=len(numbers) or any(s.status!='AVAILABLE' for s in seats):raise ApiError(409,'SEAT_UNAVAILABLE','One or more selected seats are no longer available.')
 expiry=now()+timedelta(minutes=5);snapshot={'fare_per_seat':str(d.fare_per_seat),'total':str(d.fare_per_seat*len(numbers)),'route':d.route_label,'departure_at':d.departure_at.isoformat(),'cancellation_policy':d.cancellation_policy_snapshot};row=TicketHold(departure_id=d.id,passenger_user_id=user.id,expires_at=expiry,status='ACTIVE',seat_snapshot=numbers,quote_snapshot=snapshot,created_by=user.id,updated_by=user.id);db.add(row)
 for s in seats:s.status='HELD';touch(s)
 db.commit();return {'id':str(row.id),'expires_at':expiry.isoformat(),'quote':snapshot,'seats':numbers}
@router.post('/ticket-holds/{hold_id}/sandbox-confirmation')
def confirm(hold_id:UUID,body:dict,user=Depends(current),db:Session=Depends(get_db)):
 require_role(db,user,'PASSENGER');expire(db);row=db.get(TicketHold,hold_id)
 if not row or row.passenger_user_id!=user.id or row.status!='ACTIVE' or row.expires_at<=now():raise ApiError(409,'HOLD_EXPIRED','The five-minute seat hold expired.')
 if body.get('status')!='SUCCEEDED':raise ApiError(422,'SANDBOX_CONFIRMATION_REQUIRED','Only a successful sandbox confirmation reserves seats.')
 token=secrets.token_urlsafe(24);pin=f'{secrets.randbelow(1000000):06d}';res=TicketReservation(reservation_reference='TKT-'+secrets.token_hex(8).upper(),hold_id=row.id,departure_id=row.departure_id,passenger_user_id=user.id,seat_snapshot=row.seat_snapshot,frozen_snapshot=row.quote_snapshot,payment_reference='sandbox-'+secrets.token_hex(8),payment_status='SANDBOX_CONFIRMED',boarding_qr_hash=hashlib.sha256(token.encode()).hexdigest(),boarding_pin_hash=hashlib.sha256(pin.encode()).hexdigest(),created_by=user.id,updated_by=user.id);db.add(res);row.status='CONFIRMED';touch(row)
 for seat in db.scalars(select(TicketSeat).where(TicketSeat.departure_id==row.departure_id,TicketSeat.seat_number.in_(row.seat_snapshot))).all():seat.status='RESERVED';touch(seat)
 notify(db,user.id,'Ticket reservation confirmed','Your ticket reservation is confirmed. Keep your boarding credential private.',res.reservation_reference)
 db.commit();return {'reference':res.reservation_reference,'seats':res.seat_snapshot,'boarding_qr_token':token,'boarding_pin':pin,'snapshot':res.frozen_snapshot}
@router.post('/ticket-reservations/{reference}/cancel')
def cancel(reference:str,body:dict,user=Depends(current),db:Session=Depends(get_db)):
 row=db.scalar(select(TicketReservation).where(TicketReservation.reservation_reference==reference))
 if not row or row.passenger_user_id!=user.id:raise ApiError(404,'TICKET_NOT_FOUND','Ticket reservation not found.')
 row.boarding_status='CANCELLED';row.cancellation_recorded_at=now();row.cancellation_reason=body.get('reason','');touch(row);notify(db,user.id,'Ticket cancellation recorded','Your cancellation was recorded. No refund is calculated or issued.',reference);db.commit();return {'reference':reference,'status':'CANCELLED','message':'Cancellation recorded. No refund is calculated or issued.'}
@router.post('/ticket-reservations/{reference}/boarding-verification')
def board(reference:str,body:dict,user=Depends(current),db:Session=Depends(get_db)):
 row=db.scalar(select(TicketReservation).where(TicketReservation.reservation_reference==reference));d=db.get(TicketDeparture,row.departure_id) if row else None
 require_role(db,user,'DRIVER')
 if not row or not d or user.id!=d.driver_user_id:raise ApiError(404,'TICKET_NOT_FOUND','Ticket reservation not found.')
 if row.boarding_status!='PENDING' or (body.get('qr_token') and hashlib.sha256(body['qr_token'].encode()).hexdigest()!=row.boarding_qr_hash) and (body.get('pin') and hashlib.sha256(body['pin'].encode()).hexdigest()!=row.boarding_pin_hash):raise ApiError(409,'BOARDING_CREDENTIAL_INVALID','Boarding credential is invalid.')
 row.boarding_status='BOARDED';touch(row);notify(db,row.passenger_user_id,'Ticket boarding verified','Your boarding was verified by the assigned departure driver.',reference);db.commit();return {'reference':reference,'boarding_status':'BOARDED'}

@router.get('/drivers/me/ticket-departures')
def driver_departures(user=Depends(current),db:Session=Depends(get_db)):
 require_role(db,user,'DRIVER')
 rows=db.scalars(select(TicketDeparture).where(TicketDeparture.driver_user_id==user.id,TicketDeparture.status=='PUBLISHED').order_by(TicketDeparture.departure_at)).all()
 return {'items':[{'id':str(x.id),'route':x.route_label,'departure_at':x.departure_at.isoformat(),'vehicle_type':x.vehicle_type,'air_conditioned':x.air_conditioned} for x in rows]}
