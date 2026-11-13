import { t } from '../../i18n/language.js'
import {useEffect,useState} from 'react'
import {api} from '../../services/api'
import Chip from '../../components/ui/Chip'
import InfoTip from '../../components/ui/InfoTip'
import {Field,RateErrors} from '../owner/OwnerRates'
import {fieldErrors} from '../../services/fieldErrors.js'

// Passenger cancels a paid ticket (Payments contract 03P, section E1).
// The server decides the refund at the moment of the request; the screen only shows an estimate before and the
// server's own refund_percent / refund afterwards.
export const money=(currency,amount)=>`${currency||'LKR'} ${Number(amount||0).toLocaleString('en-LK',{minimumFractionDigits:2,maximumFractionDigits:2})}`

// > 72 h before departure: 100%, 24 to 72 h: 50%, under 24 h: 0% (computed from itinerary.departure_at)
export function refundBand(departureAt,total,now=Date.now()){
  const hours=(new Date(departureAt).getTime()-now)/36e5
  const percent=!Number.isFinite(hours)?0:hours>72?100:hours>=24?50:0
  return {hours,percent,amount:(Math.round(Number(total||0)*percent)/100).toFixed(2)}
}

const reasons=['Plans changed','Booked by mistake','Found another option','Illness or emergency','Other']

export const REFUND_STATUS={PENDING:['info','Waiting for Admin approval'],PROCESSING:['info','Being refunded'],PAID:['success','Refunded'],FAILED:['danger','Refund declined']}

export default function TicketCancel({booking,departureAt,refresh,onDone,onClose}){
  const [phase,setPhase]=useState('review'),[reason,setReason]=useState('Plans changed'),[other,setOther]=useState(''),[busy,setBusy]=useState(false),[message,setMessage]=useState(null),[errors,setErrors]=useState({})
  const band=refundBand(departureAt||booking.itinerary?.departure_at,booking.total_amount)
  const seats=(booking.travellers||[]).map(x=>x.seat_code).join(', ')
  const finalReason=reason==='Other'?other.trim():reason
  const refundText=band.percent>0
    ?t('Estimated refund: {value0}% ({value1}) after Admin approval.',{value0:band.percent,value1:money(booking.currency,band.amount)})
    :t('Estimated refund: none. Tickets cancelled less than 24 hours before departure are not refunded.')
  async function send(){
    setBusy(true);setMessage(null);setErrors({})
    const body={reason:finalReason,expected_version:booking.version}
    try{
      const result=await api(`/bookings/${booking.id}/ticket-cancellation`,{method:'POST',body:JSON.stringify(body)})
      await onDone(result)
    }catch(error){
      const code=error.code,fields=fieldErrors(error)
      if(error instanceof TypeError||code==='API_TIMEOUT'){setMessage(t('We could not reach Travelly. Please try again.'));return}
      setPhase('review')
      if(code==='VERSION_CONFLICT'){refresh().catch(()=>{});setMessage(t('This booking changed while you were looking. It was refreshed. Check the refund below and confirm again.'))}
      else if(code==='TICKET_NOT_CANCELLABLE'){refresh().catch(()=>{});setMessage(t('This ticket cannot be cancelled. It may already be cancelled, or it is not paid yet. A held seat can be released instead.'))}
      else if(code==='DEPARTURE_STARTED')setMessage(t('This departure has already started, so the ticket can no longer be cancelled.'))
      else if(code==='BOOKING_NOT_FOUND'||error.status===404)setMessage(t('We could not find this booking.'))
      else if(code==='VALIDATION_ERROR'&&fields.length){setErrors(Object.fromEntries(fields.map(f=>[f.field==='reason'?(reason==='Other'?'other':'reason'):f.field,f.message])))}
      else setMessage(error.message||t('The ticket could not be cancelled. Please try again.'))
    }finally{setBusy(false)}
  }
  const confirm=phase==='confirm'
  return <RateErrors.Provider value={errors}><div className="tk-hold">
    <h3>{confirm?t('Cancel this ticket?'):t('Cancel ticket')}</h3>
    <p className="tk-line">{t('Booking {value0} · Seats {value1} · Paid {value2}',{value0:booking.booking_reference,value1:seats,value2:money(booking.currency,booking.total_amount)})}</p>
    <p className="tk-line"><Chip tone={band.percent>0?'info':'muted'}>{band.percent>0?t('{value0}% refund',{value0:band.percent}):t('No refund')}</Chip> <strong>{refundText}</strong> <InfoTip>{t('More than 72 hours before departure: 100%. 24 to 72 hours: 50%. Under 24 hours: no refund. Travelly works out the final amount when you confirm.')}</InfoTip></p>
    {message&&<p className="tk-line is-warn" role="status">{message}</p>}
    {confirm
      ?<><p className="tk-line is-warn">{t('Your seats will be released at once and this cannot be undone.')} {t('Reason')}: {finalReason}</p>
        <div className="tk-bar"><button type="button" className="ui-button ui-button-primary" disabled={busy} onClick={send}>{busy?t('Please wait…'):t('Yes, cancel my ticket')}</button>
          <button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={()=>setPhase('review')}>{t('Back')}</button></div></>
      :<><div className="tk-grid" style={{'--cols':reason==='Other'?2:1}}>
          <Field label="Reason"><select name="reason" value={reason} onChange={e=>setReason(e.target.value)}>{reasons.map(r=><option key={r} value={r}>{t(r)}</option>)}</select></Field>
          {reason==='Other'&&<Field label="Tell us more"><input name="other" maxLength="200" value={other} onChange={e=>setOther(e.target.value)}/></Field>}
        </div>
        <div className="tk-bar"><button type="button" className="ui-button ui-button-primary" disabled={busy||!finalReason} onClick={()=>{setMessage(null);setPhase('confirm')}}>{t('Continue')}</button>
          <button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={onClose}>{t('Keep my ticket')}</button></div></>}
  </div></RateErrors.Provider>
}

// After cancelling: the cancelled state and the refund, from the cancel answer and then from the payment history (A4).
export function CancelledTicket({booking,result}){
  const [refund,setRefund]=useState(result?.refund||null),[loaded,setLoaded]=useState(false)
  useEffect(()=>{
    let alive=true
    api(`/bookings/${booking.id}/payments`).then(r=>{if(!alive)return;const rows=(r.items||[]).filter(x=>/REFUND$/.test(x.transaction_type||''));if(rows.length)setRefund(rows[0])}).catch(()=>{}).finally(()=>alive&&setLoaded(true))
    return ()=>{alive=false}
  },[booking.id,booking.version])
  const percent=result?.refund_percent
  const [tone,label]=REFUND_STATUS[refund?.status]||['muted','Waiting for Admin approval']
  const seats=(booking.travellers||[]).map(x=>x.seat_code).join(', ')
  return <div className="tk-hold">
    <p className="tk-line"><Chip tone="danger" icon="close">{t('Ticket cancelled')}</Chip> <strong>{t('Booking {value0}',{value0:booking.booking_reference})}</strong></p>
    <p className="tk-line">{t('Seats {value0} were released.',{value0:seats})}</p>
    {refund
      ?<><p className="tk-line"><Chip tone={tone}>{t(label)}</Chip> <strong>{t('Refund {value0}',{value0:money(refund.currency||booking.currency,refund.amount)})}</strong>{percent!=null&&<> ({percent}%)</>} {refund.payment_reference&&<span>· {refund.payment_reference}</span>}</p>
        <p className="tk-line">{refund.status==='FAILED'?t('The refund was declined. Please contact support if you have questions.'):refund.status==='PAID'?t('The money has been sent back to you.'):t('An Admin will approve the refund. We will tell you when the money goes back.')}</p></>
      :<p className="tk-line">{loaded||result?t('No refund applies to this cancellation.'):t('Loading…')}</p>}
  </div>
}
