import { t } from '../../i18n/language.js'
import React,{useState} from 'react'
import {Link} from './travelRouter'
import {api} from '../../services/api'
import Chip from '../../components/ui/Chip'
import InfoTip from '../../components/ui/InfoTip'
import {Pager} from '../booking/flow/FlowParts'
import {isReplacementAction,noticeBookingId} from '../notifications/notices'

// Replacement vehicle decision (contract 03F2, section 6). Shown only while pending_change.status is PENDING.
// No answer means the passenger travels, so "Travel in the new vehicle" is a plain answer and Reject asks to confirm first.
export const isPending=booking=>booking?.pending_change?.kind==='REPLACEMENT_VEHICLE'&&booking.pending_change.status==='PENDING'&&booking.status==='CONFIRMED'
export const vehicleLine=v=>v?[`${v.make||''} ${v.model||''}`.trim(),v.vehicle_type_code,v.colour,v.air_conditioned?'AC':null,v.seat_capacity!=null?t('{value0} seats',{value0:v.seat_capacity}):null].filter(Boolean).join(' · '):''

function explain(error){
  const code=error.code
  if(error instanceof TypeError||code==='API_TIMEOUT')return {text:t('We could not reach Travelly. Please try again.')}
  if(code==='NO_PENDING_CHANGE')return {reload:true,text:t(error.message)}
  if(code==='DEPARTURE_STARTED')return {reload:true,text:t(error.message)}
  if(code==='VERSION_CONFLICT')return {reload:true,text:t('Your booking changed while you were looking. It was refreshed, so check it and answer again.')}
  if(code==='BOOKING_NOT_FOUND'||error.status===404)return {text:t('We could not find this booking.')}
  return {text:error.message||t('Your answer could not be sent. Please try again.')}
}

export default function ReplacementCard({booking,refresh,onRejected}){
  const change=booking.pending_change,[mode,setMode]=useState(null),[busy,setBusy]=useState(false),[message,setMessage]=useState('')
  const [page,setPage]=useState(0),seats=change.seats||[],size=3,pages=Math.max(1,Math.ceil(seats.length/size)),current=Math.min(page,pages-1)
  async function answer(decision){
    setBusy(true);setMessage('')
    try{
      const result=await api(`/bookings/${booking.id}/replacement-decision`,{method:'POST',body:JSON.stringify({expected_version:booking.version,decision})})
      if(decision==='REJECT')onRejected&&onRejected(result)
      await refresh()
    }catch(error){
      const out=explain(error);setMessage(out.text);setMode(null)
      if(out.reload)refresh().catch(()=>{})
    }finally{setBusy(false)}
  }
  const was=change.previous_vehicle,now=change.replacement_vehicle
  return <div className="tk-hold tk-replace" role="group" aria-label={t('Your vehicle has changed')}>
    <p className="tk-line"><Chip tone="info" icon="route">{t('Action needed')}</Chip> <strong>{t('Your vehicle has changed')}</strong> <InfoTip>{t('If you do nothing you travel in the new vehicle. If you reject it, you get a full refund.')}</InfoTip></p>
    {mode!=='reject'&&<div className="tk-replace-body">
      <dl className="tk-facts" style={{'--cols':1}}>
        <div><dt>{t('Was')}</dt><dd title={vehicleLine(was)}>{vehicleLine(was)}</dd></div>
        <div><dt>{t('Now')}</dt><dd title={vehicleLine(now)}><strong>{vehicleLine(now)}</strong></dd></div>
        {change.operator_changed&&now?.operator_name&&<div><dt>{t('New operator')}</dt><dd title={now.operator_name}><strong>{now.operator_name}</strong></dd></div>}
      </dl>
      <div className="tk-replace-seats"><strong className="tk-line">{t('Your seats')}</strong>
        {seats.slice(current*size,(current+1)*size).map(s=><span className="tk-line" key={`${s.seat_id}-${s.from_seat}`}>{s.full_name}: {s.from_seat} → <strong>{s.to_seat}</strong></span>)}
        {pages>1&&<Pager page={current} pages={pages} onPage={setPage}/>}</div>
    </div>}
    {message&&<p className="tk-line is-warn" role="status">{message}</p>}
    {mode==='reject'
      ?<><p className="tk-line is-warn"><strong>{t('Reject the new vehicle?')}</strong> {t('Your booking is cancelled, your seats go back on sale, and you get a full refund ({value0}%) after Admin approval.',{value0:change.refund_if_rejected_percent??100})}</p>
        <div className="tk-bar"><button type="button" className="ui-button ui-button-primary" disabled={busy} onClick={()=>answer('REJECT')}>{busy?t('Please wait…'):t('Yes, reject and get a full refund')}</button><button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={()=>setMode(null)}>{t('Back')}</button></div></>
      :<div className="tk-bar"><button type="button" className="ui-button ui-button-primary" disabled={busy} onClick={()=>answer('ACCEPT')}>{busy?t('Please wait…'):t('Travel in the new vehicle')}</button>
        <button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={()=>setMode('reject')}>{t('Reject and get a full refund')}</button></div>}
  </div>
}

// Dashboard: one compact row for a REPLACEMENT notification that needs an answer (notification_type and action_required, contract 03N).
// It opens that booking's change card; the notification's own text is shown, so no ticket has to be read to find the booking.
export function ReplacementRow({notes}){
  const note=(notes||[]).find(isReplacementAction)
  if(!note)return null
  return <Link className="dash-row" to={`/travel/book/tickets?booking=${noticeBookingId(note)}`}><Chip tone="info" icon="route">{t('Action needed')}</Chip>
    <div><strong>{t('Your vehicle has changed')}</strong><span>{note.body}</span></div></Link>
}
