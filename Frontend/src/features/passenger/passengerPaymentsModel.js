import {codeEnglish} from '../../i18n/codeLabels.js'

export const PAYMENT_STATUSES=new Set(['PENDING','PROCESSING','PAID','CASH_AWAITING_CONFIRMATION','FAILED','REFUNDED','PARTIALLY_REFUNDED'])

export const paymentStatusText=status=>status==='CASH_AWAITING_CONFIRMATION'?'Cash waiting for confirmation':codeEnglish(status)

export function paymentService(booking){
  if(booking?.booking_type==='RENTAL')return 'Self-drive rental'
  if(booking?.booking_type==='TICKET_HIRE')return 'Ticket'
  if(booking?.booking_type==='PRIVATE_HIRE')return 'Private hire'
  return codeEnglish(booking?.booking_type)||'Booking'
}

export function paymentRow(booking,history){
  const status=history?.payment_status
  if(!PAYMENT_STATUSES.has(status))return null
  const payments=history.items||[],latest=payments.at(-1)
  return {id:booking.id,reference:booking.reference,service:paymentService(booking),status,
    amount:booking.total_amount??latest?.amount??null,currency:booking.currency||latest?.currency||'LKR',
    date:latest?.captured_at||latest?.created_at||booking.start_at||null}
}
