import { t } from '../../i18n/language.js'
import React,{useEffect,useState} from 'react'
import {api} from '../../services/api'
import {Field,RateErrors} from '../owner/OwnerRates'
import Chip from '../../components/ui/Chip'
import {formatDateTime} from '../../i18n/dateTime.js'
import {money} from '../passenger/TicketCancel'
import {statusChip} from '../owner/DepartureFulfilment'
import AdminList,{Facts} from './AdminList'

// Admin: departures waiting for Travelly (contract 03F2, sections 3 and 4). Only references, amounts, status, dates and counts are shown.
const filters=[['','All'],['DECISION_REQUIRED','Decision needed'],['DISRUPTED','Disrupted']]
const POLICY={FIXED_GUARANTEED:'Fixed, guaranteed departure',MINIMUM_SEATS_WITH_PROTECTED_FULFILMENT:'Minimum seats with protected fulfilment'}

function explain(error){
  const code=error.code,fields=error.fields||[]
  if(error instanceof TypeError||code==='API_TIMEOUT')return {text:t('We could not reach Travelly. Please try again.')}
  if(code==='VERSION_CONFLICT')return {reload:true,text:t('This departure changed while you were looking. The list was refreshed, so check it and try again.')}
  if(code==='DEPARTURE_NOT_ESCALATED')return {reload:true,text:t('This departure is no longer waiting for a Travelly decision. Someone may already have resolved it. The list was refreshed.')}
  if(code==='DEPARTURE_STARTED')return {reload:true,text:t('This departure has already started, so it can no longer be closed here.')}
  if(code==='DEPARTURE_NOT_FOUND'||error.status===404)return {reload:true,text:t('This departure no longer exists. The list was refreshed.')}
  if(code==='ADMIN_REQUIRED'||error.status===403)return {text:t('Only an Admin can do this.')}
  if(code==='VALIDATION_ERROR'&&fields.length)return {fields:Object.fromEntries(fields.map(f=>[f.field,f.message])),text:t('Please check the highlighted fields.')}
  return {text:error.message||t('The departure could not be closed. Please try again.')}
}

function CannotFulfil({item,onDone,onProblem}){
  const [mode,setMode]=useState(null),[reason,setReason]=useState(''),[busy,setBusy]=useState(false),[errors,setErrors]=useState({}),[message,setMessage]=useState('')
  const text=reason.trim(),ok=text.length>=5&&text.length<=1000
  async function send(){
    setBusy(true);setMessage('');setErrors({})
    try{onDone(await api(`/admin/scheduled-trips/${item.id}/cannot-fulfil`,{method:'POST',body:JSON.stringify({expected_version:item.version,reason:text})}))}
    catch(error){const out=explain(error);if(out.reload){setMode(null);onProblem(out.text);return}setMessage(out.text);setErrors(out.fields||{});setMode('form')}
    finally{setBusy(false)}
  }
  return <RateErrors.Provider value={errors}><div className="tk-pane">
    {message&&<p className="tk-line is-warn" role="status">{message}</p>}
    {!mode&&<div className="tk-bar"><button type="button" className="ui-button ui-button-primary" onClick={()=>setMode('form')}>{t('Cannot fulfil, refund everyone')}</button></div>}
    {mode&&<div className="tk-hold">
      <Field label="Reason" help="Between 5 and 1000 characters. It is saved with the Admin decision."><input name="reason" maxLength="1000" value={reason} disabled={mode==='confirm'} onChange={e=>setReason(e.target.value)}/></Field>
      {mode==='confirm'&&<p className="tk-line is-warn"><strong>{t('Close {value0} and refund everyone in full?',{value0:item.departure_reference})}</strong> {t('{value0} seats are booked and {value1} has been paid. Every paid booking is cancelled and refunded at 100%, seats are blocked, and the passengers and the Owner are told. This cannot be undone.',{value0:item.booked_seats,value1:money(item.currency,item.paid_amount)})}</p>}
      <div className="tk-bar">{mode==='confirm'
        ?<><button type="button" className="ui-button ui-button-primary" disabled={busy} onClick={send}>{busy?t('Please wait…'):t('Yes, refund everyone')}</button><button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={()=>setMode('form')}>{t('Back')}</button></>
        :<><button type="button" className="ui-button ui-button-primary" disabled={!ok} onClick={()=>{setErrors({});setMessage('');setMode('confirm')}}>{t('Continue')}</button><button type="button" className="ui-button ui-button-secondary" onClick={()=>{setMode(null);setReason('');setErrors({})}}>{t('Not yet')}</button></>}</div></div>}
  </div></RateErrors.Provider>
}

export default function AdminAttention({base,onOpenRefunds}){
  const [items,setItems]=useState(null),[error,setError]=useState(null),[notice,setNotice]=useState(''),[filter,setFilter]=useState(''),[results,setResults]=useState({})
  const load=()=>api('/admin/departures/attention').then(r=>{setItems(r.items||[]);setError(null)}).catch(setError)
  useEffect(()=>{load()},[])
  const shown=items&&items.filter(x=>!filter||x.status===filter)
  const problem=text=>{setNotice(text);load()}
  const done=(item,result)=>{setResults(r=>({...r,[item.id]:result}));setNotice(t('Departure closed. Every paid booking is being refunded.'));load()}
  const refundTotal=result=>(result.refunds||[]).reduce((sum,r)=>sum+Number(r.amount||0),0)
  return <AdminList {...base} title={t('Departures needing attention')} notice={notice} error={error||base.error} items={shown} empty={t('No departures need attention. Nothing is waiting for a Travelly decision.')}
    filters={<Field label="Show"><select name="attention-filter" value={filter} onChange={e=>setFilter(e.target.value)}>{filters.map(([v,l])=><option key={v} value={v}>{t(l)}</option>)}</select></Field>} filterCols={4}
    row={x=>{const c=statusChip(x.status);return {key:x.id,title:`${x.departure_reference} · ${x.route?.origin_name||''} → ${x.route?.destination_name||''}`,meta:`${formatDateTime(x.departure_at)} · ${t('{value0} seats booked',{value0:x.booked_seats})} · ${t('Paid')} ${money(x.currency,x.paid_amount)}`,status:c.label,tone:c.tone}}}
    detailTitle={x=>x.departure_reference}
    detail={x=>{
      const result=results[x.id]
      return <>
        <Facts cols={3} entries={[
          [t('Route'),x.route?.route_name||'—'],[t('Departs'),formatDateTime(x.departure_at)],[t('Owner'),x.owner?`${x.owner.display_name||''} · ${x.owner.public_user_reference||''}`:'—'],
          [t('Vehicle'),x.vehicle?`${x.vehicle.public_vehicle_reference||''} · ${x.vehicle.vehicle_type_code||''} · ${t('{value0} seats',{value0:x.vehicle.seat_capacity})}`:'—'],
          [t('Departure type'),t(POLICY[x.fulfilment_policy]||'—')],
          [t('Seats'),`${x.booked_seats} ${t('booked')} · ${x.held_seats} ${t('held')} · ${money(x.currency,x.paid_amount)}`],
          ...(x.minimum_confirmed_seats?[[t('Minimum seats'),String(x.minimum_confirmed_seats)]]:[]),
          ...(x.decision_deadline?[[t('Decision deadline'),formatDateTime(x.decision_deadline)]]:[]),
          [t('Replacement'),String(x.replacement_status||'—').replaceAll('_',' ')]]}/>
        {result
          ?<div className="tk-pane">
            <p className="tk-line"><Chip tone="success">{t('Closed')}</Chip> <strong>{t('{value0} refunds created, {value1} in total.',{value0:(result.refunds||[]).length,value1:money(x.currency,refundTotal(result))})}</strong></p>
            <p className="tk-line">{(result.refunds||[]).some(r=>r.status==='PROCESSING')?t('PayHere refunds wait in Processing. Complete them in the Refunds tab after refunding in the PayHere portal.'):t('Sandbox refunds are already paid. You can follow every refund in the Refunds tab.')}</p>
            <div className="tk-bar"><button type="button" className="ui-button ui-button-primary" onClick={onOpenRefunds}>{t('Open Refunds')}</button></div>
          </div>
          :<CannotFulfil key={`${x.id}-${x.version}`} item={x} onDone={r=>done(x,r)} onProblem={problem}/>}
      </>}}/>
}
