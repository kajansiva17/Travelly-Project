import { t } from '../../i18n/language.js'
import {useCallback,useEffect,useState} from 'react'
import {api} from '../../services/api'
import {ErrorNotice} from '../../components/components'
import Chip from '../../components/ui/Chip'
import InfoTip from '../../components/ui/InfoTip'
import TicketPayment,{newKey} from '../passenger/TicketPayment'
import {correctAmount} from '../../services/fieldErrors.js'

// Private-hire payment panel (Payments contract 03P, section D). Everything is drawn from
// GET /bookings/{id}/payment-summary; after every answer the summary is read again.
export const loadSummary=bookingId=>api(`/bookings/${bookingId}/payment-summary`)

const money=(currency,amount)=>`${currency||'LKR'} ${amount}`

// One cash confirmation. Each side sends only its own flag. A second step ("Yes, confirm") stops accidental taps.
export function CashConfirm({summary,side,onDone}){
  const [ask,setAsk]=useState(false),[busy,setBusy]=useState(false),[message,setMessage]=useState(null)
  async function send(){
    setBusy(true);setMessage(null)
    const body={booking_id:summary.booking_id,confirmed_by:side==='passenger'?'passenger':'driver'}
    try{
      try{await api('/payments/cash-receipt',{method:'POST',body:JSON.stringify(body)})}
      catch(error){
        if(error.status!==404)throw error
        const legacy={amount:summary.amount_due,currency:summary.currency||'LKR',collection_stage:'END',collector_user_id:summary.collector_user_id,passenger_confirmation:side==='passenger',collector_confirmation:side==='collector',idempotency_key:newKey()}
        await api(`/bookings/${summary.booking_id}/cash-receipts`,{method:'POST',body:JSON.stringify(legacy)})
      }
      setAsk(false);await onDone()
    }
    catch(error){
      const code=error.code
      if(error instanceof TypeError||code==='API_TIMEOUT'){setMessage(t('We could not reach Travelly. Please try again.'));return}
      setAsk(false)
      if(code==='CASH_NOT_ACCEPTED')setMessage(t('The Owner does not accept cash for this vehicle. Please pay online.'))
      else if(code==='PAYMENT_NOT_DUE')setMessage(t('Payment opens when the trip is completed.'))
      else if(code==='PAYMENT_AMOUNT_MISMATCH')setMessage(t('The amount changed. It is now {value0}.',{value0:correctAmount(error)}))
      else if(code==='PAYMENT_IN_PROGRESS')setMessage(t('An online payment is waiting. Finish or wait for it first.'))
      else if(code==='BOOKING_ALREADY_PAID')setMessage(t('This booking is already paid.'))
      else if(code==='COLLECTOR_NOT_ASSIGNED')setMessage(t('The person collecting the cash has changed. The page was refreshed, please try again.'))
      else if(code==='CONFIRMATION_NOT_YOURS')setMessage(t('You can only confirm your own side.'))
      else if(code==='BOOKING_NOT_FOUND'||error.status===404)setMessage(t('We could not find this booking.'))
      else if(code==='CASH_NOT_AVAILABLE')setMessage(t('Cash is not available for this booking.'))
      else setMessage(error.message||t('The confirmation could not be sent. Please try again.'))
      onDone().catch(()=>{})
    }finally{setBusy(false)}
  }
  const money_=money(summary.currency,summary.amount_due)
  const question=side==='collector'?t('Confirm that you received {value0} in cash from the Passenger.',{value0:money_}):t('Confirm that you handed {value0} in cash to the Driver.',{value0:money_})
  return <div className="tk-pay">
    {message&&<p className="tk-line is-warn" role="status">{message}</p>}
    {ask
      ?<div className="tk-hold"><p className="tk-line"><strong>{question}</strong> {t('Only confirm if this is true.')}</p>
        <div className="tk-bar"><button type="button" className="ui-button ui-button-primary" disabled={busy} onClick={send}>{busy?t('Please wait…'):t('Yes, confirm')}</button>
          <button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={()=>setAsk(false)}>{t('Not yet')}</button></div></div>
      :<div className="tk-bar"><button type="button" className="ui-button ui-button-primary" disabled={busy} onClick={()=>setAsk(true)}>{side==='collector'?t('Cash received'):t('I have paid cash')}</button></div>}
  </div>
}

const waitingText=(summary,isPassenger,isCollector)=>{
  const cash=summary.cash||{}
  if(cash.passenger_confirmed&&!cash.collector_confirmed)return isPassenger?t('Waiting for the driver to confirm cash received.'):t('The Passenger says they paid. Please confirm you received the cash.')
  if(cash.collector_confirmed&&!cash.passenger_confirmed)return isCollector&&!isPassenger?t('Waiting for the passenger to confirm.'):t('The Driver says the cash was received. Please confirm that you paid.')
  return t('Waiting for confirmation.')
}

export default function HirePayment({bookingId,passengerUserId,userId,returned,asCollector=false}){
  const [summary,setSummary]=useState(null),[error,setError]=useState(null),[mode,setMode]=useState('online')
  const read=useCallback(async()=>{const next=await loadSummary(bookingId);setSummary(next);setError(null);return next},[bookingId])
  useEffect(()=>{setSummary(null);read().catch(setError)},[read])
  if(error&&!summary)return <div className="bc-card pay-card"><ErrorNotice error={error}/><div className="tk-bar"><button type="button" className="ui-button ui-button-secondary" onClick={()=>read().catch(setError)}>{t('Try again')}</button></div></div>
  if(!summary)return <p role="status">{t('Loading payment…')}</p>
  const isPassenger=!asCollector&&passengerUserId===userId,isCollector=asCollector||summary.collector_user_id===userId
  const paid=summary.payment_status==='PAID',cash=summary.cash,awaiting=summary.payment_status==='CASH_AWAITING_CONFIRMATION'
  const chip=paid?<Chip tone="success">{t('Paid')}</Chip>:awaiting?<Chip tone="info" icon="clock">{t('Cash waiting for confirmation')}</Chip>:summary.payment_status==='PENDING'?<Chip tone="info" icon="clock">{t('Payment pending')}</Chip>:summary.payment_status==='FAILED'?<Chip tone="danger" icon="alert">{t('Payment failed')}</Chip>:summary.payment_due?<Chip tone="muted">{t('Payment due')}</Chip>:<Chip tone="muted" icon="clock">{t('Not due yet')}</Chip>
  const reload=()=>read().catch(setError)
  const head=<p className="tk-line">{chip} {summary.amount_due&&!paid&&<strong>{money(summary.currency,summary.amount_due)}</strong>}</p>

  if(paid)return <div className="bc-card pay-card">{head}<p className="tk-line">{t('This booking is paid.')} {summary.latest_payment?.payment_reference&&<strong>{summary.latest_payment.payment_reference}</strong>}</p></div>
  if(!summary.payment_due&&!awaiting)return <div className="bc-card pay-card">{head}<p className="tk-line">{t('Payment opens when the trip is completed.')}</p><ErrorNotice error={error}/></div>

  // cash waiting for the other side
  if(awaiting){
    const myTurn=isPassenger?(cash?.collector_confirmed&&!cash?.passenger_confirmed):(isCollector&&cash?.passenger_confirmed&&!cash?.collector_confirmed)
    return <div className="bc-card pay-card">{head}<p className="tk-line" role="status">{waitingText(summary,isPassenger,isCollector)}</p><ErrorNotice error={error}/>
      {myTurn&&<CashConfirm summary={summary} side={isPassenger?'passenger':'collector'} onDone={reload}/>}</div>
  }

  // payment due
  if(!isPassenger){
    return <div className="bc-card pay-card">{head}<p className="tk-line">{isCollector&&summary.cash_accepted?t('Waiting for cash payment…'):isCollector?t('The Passenger pays online. Nothing is needed from you.'):t('The Passenger pays after the trip.')}</p><ErrorNotice error={error}/>
      {isCollector&&summary.cash_accepted&&<CashConfirm summary={summary} side="collector" onDone={reload}/>}</div>
  }
  // The Owner may take online only, cash only, or both (owner decision, 25 Nov 2026).
  const onlineOk=summary.online_accepted!==false,cashOk=Boolean(summary.cash_accepted),choose=onlineOk&&cashOk,payMode=!onlineOk?'cash':mode
  // hand the summary to the shared Pay flow as a booking-shaped object
  const asBooking={id:summary.booking_id,status:summary.booking_status,currency:summary.currency,total_amount:summary.amount_due,payment_status:summary.payment_status,latest_payment:summary.latest_payment,payment_provider:summary.payment_provider,payment_method:summary.payment_method,payer_details_required:summary.payer_details_required}
  return <div className="bc-card pay-card"><p className="tk-line"><strong>{t('Trip completed. Total: LKR {value0}',{value0:summary.amount_due})}</strong></p>{head}
    {choose&&<div className="tk-bar" role="group" aria-label={t('How do you want to pay?')}><strong className="tk-line">{t('How do you want to pay?')}</strong>
      <Chip tone="info" selected={mode==='online'} onClick={()=>setMode('online')}>{t('Pay online')}</Chip>
      <Chip tone="info" selected={mode==='cash'} onClick={()=>setMode('cash')}>{t('Pay in cash')}</Chip></div>}
    {payMode==='cash'&&cashOk
      ?<><p className="tk-line">{t('Pay the Driver in cash at the end of the trip. Then both of you confirm here and the booking is marked paid.')} <InfoTip>{t('The booking is paid only after you and the Driver both confirm.')}</InfoTip></p>
        <CashConfirm summary={summary} side="passenger" onDone={reload}/></>
      :<TicketPayment hire booking={asBooking} refresh={read} returned={returned}/>}
  </div>
}
