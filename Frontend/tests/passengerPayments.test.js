import test from 'node:test'
import assert from 'node:assert/strict'
import {PAYMENT_STATUSES,paymentRow,paymentService,paymentStatusText} from '../src/features/passenger/passengerPaymentsModel.js'

test('the payment page recognises every stored booking payment status',()=>{
  assert.deepEqual([...PAYMENT_STATUSES],['PENDING','PROCESSING','PAID','CASH_AWAITING_CONFIRMATION','FAILED','REFUNDED','PARTIALLY_REFUNDED'])
  assert.equal(paymentStatusText('CASH_AWAITING_CONFIRMATION'),'Cash waiting for confirmation')
  assert.equal(paymentStatusText('PARTIALLY_REFUNDED'),'Partly refunded')
})

test('a payment row uses the booking total and latest payment date without exposing a private route',()=>{
  const booking={id:'b1',reference:'BKG-ONE',booking_type:'PRIVATE_HIRE',origin_text:'Private home',destination_text:'Private destination',total_amount:'2500.00',currency:'LKR',start_at:'2026-11-20T08:00:00Z'}
  const row=paymentRow(booking,{payment_status:'PAID',items:[{amount:'2500.00',currency:'LKR',created_at:'2026-11-17T10:00:00Z',captured_at:'2026-11-17T10:01:00Z'}]})
  assert.deepEqual(row,{id:'b1',reference:'BKG-ONE',service:'Private hire',status:'PAID',amount:'2500.00',currency:'LKR',date:'2026-11-17T10:01:00Z'})
  assert.equal(paymentService({...booking,booking_type:'TICKET_HIRE'}),'Ticket')
  assert.equal(paymentService({...booking,booking_type:'RENTAL'}),'Self-drive rental')
})

test('bookings without one of the contracted payment statuses are not payment rows',()=>{
  assert.equal(paymentRow({id:'b1'},{payment_status:null,items:[]}),null)
})
