import { t } from '../../i18n/language.js'
import {useEffect,useState} from 'react'
import {api} from '../../services/api'
import {Field,RateErrors} from '../owner/OwnerRates'
import Chip from '../../components/ui/Chip'
import {formatDateTime} from '../../i18n/dateTime.js'
import {money} from '../passenger/TicketCancel'
import {statusChip} from '../owner/DepartureFulfilment'
import AdminList from './AdminList'
import {Icon} from '../../components/components'
import {Thumb} from '../booking/BookingCardParts'
import {fieldErrors,fieldErrorMap} from '../../services/fieldErrors.js'
import {codeLabel} from '../../i18n/codeLabels.js'

// Admin: departures waiting for Travelly (contract 03F2, sections 3 and 4). Only references, amounts, status, dates and counts are shown.
const filters=[['','All'],['DECISION_REQUIRED','Decision needed'],['DISRUPTED','Disrupted']]
const POLICY={FIXED_GUARANTEED:'Fixed, guaranteed departure',MINIMUM_SEATS_WITH_PROTECTED_FULFILMENT:'Minimum seats with protected fulfilment'}

// The facts of a departure as small cards (wrapping text, no cut-off values).
function FactCards({entries}){
  return <div className="at-facts">{entries.map(([k,v])=><div className="at-fact" key={k}><small>{k}</small><strong>{v}</strong></div>)}</div>
}

function explain(error){
  const code=error.code,fields=fieldErrors(error)
  if(error instanceof TypeError||code==='API_TIMEOUT')return {text:t('We could not reach Travelly. Please try again.')}
  if(code==='VERSION_CONFLICT')return {reload:true,text:t('This departure changed while you were looking. The list was refreshed, so check it and try again.')}
  if(code==='DEPARTURE_NOT_ESCALATED')return {reload:true,text:t('This departure is no longer waiting for a Travelly decision. Someone may already have resolved it. The list was refreshed.')}
  if(code==='DEPARTURE_STARTED')return {reload:true,text:t('This departure has already started, so it can no longer be closed here.')}
  if(code==='NO_VEHICLE_TO_ASK')return {reload:true,text:t('None of these vehicles can be asked now. The list was refreshed.')}
  if(code==='REPLACEMENT_NOT_ALLOWED')return {reload:true,text:t('This departure can no longer be given to another vehicle. The list was refreshed.')}
  if(code==='DEPARTURE_NOT_FOUND'||error.status===404)return {reload:true,text:t('This departure no longer exists. The list was refreshed.')}
  if(code==='ADMIN_REQUIRED'||error.status===403)return {text:t('Only an Admin can do this.')}
  if(code==='VALIDATION_ERROR'&&fields.length)return {fields:fieldErrorMap(error),text:t('Please check the highlighted fields.')}
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
  return <RateErrors.Provider value={errors}><section className="bc-card at-block is-danger">
    {message&&<p className="tk-line is-warn" role="status">{message}</p>}
    {!mode&&<div className="tk-bar"><button type="button" className="ui-button ui-button-primary" onClick={()=>setMode('form')}>{t('Cannot fulfil, refund everyone')}</button></div>}
    {mode&&<div className="tk-hold">
      <Field label="Reason" help="Between 5 and 1000 characters. It is saved with the Admin decision."><input name="reason" maxLength="1000" value={reason} disabled={mode==='confirm'} onChange={e=>setReason(e.target.value)}/></Field>
      {mode==='confirm'&&<p className="tk-line is-warn"><strong>{t('Close {value0} and refund everyone in full?',{value0:item.departure_reference})}</strong> {t('{value0} seats are booked and {value1} has been paid. Every paid booking is cancelled and refunded at 100%, seats are blocked, and the passengers and the Owner are told. This cannot be undone.',{value0:item.booked_seats,value1:money(item.currency,item.paid_amount)})}</p>}
      <div className="tk-bar">{mode==='confirm'
        ?<><button type="button" className="ui-button ui-button-primary" disabled={busy} onClick={send}>{busy?t('Please wait…'):t('Yes, refund everyone')}</button><button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={()=>setMode('form')}>{t('Back')}</button></>
        :<><button type="button" className="ui-button ui-button-primary" disabled={!ok} onClick={()=>{setErrors({});setMessage('');setMode('confirm')}}>{t('Continue')}</button><button type="button" className="ui-button ui-button-secondary" onClick={()=>{setMode(null);setReason('');setErrors({})}}>{t('Not yet')}</button></>}</div></div>}
  </section></RateErrors.Provider>
}

function FindReplacement({item,onSent,onProblem}){
  const [list,setList]=useState(null),[picked,setPicked]=useState([]),[mode,setMode]=useState(null),[busy,setBusy]=useState(false),[message,setMessage]=useState('')
  useEffect(()=>{let live=true;api(`/admin/scheduled-trips/${item.id}/replacement-candidates`).then(r=>{if(live)setList(r.items||[])}).catch(error=>{if(live){setList([]);setMessage(explain(error).text)}});return ()=>{live=false}},[item.id,item.version])
  const open=(list||[]).filter(v=>!v.already_asked)
  const sending=mode==='selected'?open.filter(v=>picked.includes(v.vehicle_id)):open
  const toggle=id=>setPicked(p=>p.includes(id)?p.filter(x=>x!==id):[...p,id])
  async function send(){
    setBusy(true);setMessage('')
    try{
      const body=mode==='all'?{expected_version:item.version,send_to_all:true}:{expected_version:item.version,vehicle_ids:sending.map(v=>v.vehicle_id)}
      const done=await api(`/admin/scheduled-trips/${item.id}/replacement-requests`,{method:'POST',body:JSON.stringify(body)})
      onSent(t('{value0} request(s) sent. The first Owner to accept runs the departure.',{value0:done.asked}))
    }catch(error){const out=explain(error);if(out.reload){setMode(null);onProblem(out.text);return}setMessage(out.text);setMode(null)}
    finally{setBusy(false)}
  }
  return <section className="bc-card at-block">
    <h3 className="at-title">{t('Ask other Owners to run this departure')}</h3>
    <p className="tk-line">{t('Vehicles that can take everyone who paid. The nearest to the pickup point come first.')}</p>
    {item.pending_offers>0&&<p className="tk-line" role="status"><Chip tone="info" icon="clock">{t('Waiting')}</Chip> {t('{value0} request(s) are waiting for an answer. The first Owner to accept runs the departure.',{value0:item.pending_offers})}</p>}
    {message&&<p className="tk-line is-warn" role="status">{message}</p>}
    {list===null&&<p className="tk-line" role="status">{t('Loading vehicles…')}</p>}
    {list&&list.length===0&&<><p className="tk-line">{t('No other vehicle is free for this departure right now.')}</p><p className="tk-line">{t('A vehicle is listed when it is approved and active, seats everyone who booked, is air-conditioned if the booked one is, and is free at that time. Other Owners\' vehicles must also be published.')}</p></>}
    {list&&list.length>0&&<div className="at-cands">{list.map(v=>{const on=v.already_asked||picked.includes(v.vehicle_id),name=v.display_name||[v.make,v.model].filter(Boolean).join(' ')||v.public_vehicle_reference;return <label key={v.vehicle_id} className={'bc-card at-cand'+(on?' is-on':'')+(v.already_asked?' is-off':'')}>
      <input type="checkbox" className="at-check" name={`candidate-${v.vehicle_id}`} disabled={v.already_asked||Boolean(mode)} checked={on} onChange={()=>toggle(v.vehicle_id)}/>
      <Thumb src={v.profile_image_url} icon="car" size={64}/>
      <div className="bc-body">
        <strong className="bc-name">{name}</strong>
        <span className="bc-sub">{v.public_vehicle_reference}</span>
        <span className="at-tags"><Chip tone="muted">{codeLabel(v.vehicle_type_code)}</Chip><Chip tone="muted">{t('{value0} bookable seats',{value0:v.bookable_seats})}</Chip>{v.air_conditioned&&<Chip tone="info">{t('Air-conditioned')}</Chip>}</span>
        <span className="bc-line dv-who"><Thumb src={v.owner_image_url} icon="user" name={v.owner_name||''} round size={22}/>{v.owner_name||'—'}</span>
        <span className="bc-line"><Icon name="pin" size={15}/>{v.distance_km==null?t('Location unknown'):t('{value0} km from pickup',{value0:v.distance_km})}</span>
      </div>
      <div className="bc-side">{v.same_owner&&<Chip tone="muted">{t('Same Owner')}</Chip>}{v.already_asked&&<Chip tone="info">{t('Asked')}</Chip>}</div></label>})}</div>}
    {!mode&&open.length>0&&<div className="tk-bar">
      <button type="button" className="ui-button ui-button-primary" disabled={!picked.some(id=>open.some(v=>v.vehicle_id===id))} onClick={()=>{setMessage('');setMode('selected')}}>{t('Ask selected ({value0})',{value0:open.filter(v=>picked.includes(v.vehicle_id)).length})}</button>
      <button type="button" className="ui-button ui-button-secondary" onClick={()=>{setMessage('');setMode('all')}}>{t('Ask all listed ({value0})',{value0:open.length})}</button></div>}
    {mode&&<div className="tk-hold"><p className="tk-line is-warn"><strong>{t('Ask {value0} Owner(s) to run {value1}?',{value0:sending.length,value1:item.departure_reference})}</strong> {t('The first Owner to accept takes the passengers. The other requests are withdrawn.')}</p>
      <div className="tk-bar"><button type="button" className="ui-button ui-button-primary" disabled={busy} onClick={send}>{busy?t('Please wait…'):t('Yes, send the requests')}</button><button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={()=>setMode(null)}>{t('Back')}</button></div></div>}
  </section>
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
        <div className="at-cols"><div className="at-left">
        <FactCards entries={[
          [t('Route'),x.route?.route_name||'—'],[t('Departs'),formatDateTime(x.departure_at)],[t('Owner'),x.owner?`${x.owner.display_name||''} · ${x.owner.public_user_reference||''}`:'—'],
          [t('Vehicle'),x.vehicle?`${x.vehicle.public_vehicle_reference||''} · ${codeLabel(x.vehicle.vehicle_type_code)} · ${t('{value0} seats',{value0:x.vehicle.seat_capacity})}`:'—'],
          [t('Departure type'),t(POLICY[x.fulfilment_policy]||'—')],
          [t('Seats'),`${x.booked_seats} ${t('booked')} · ${x.held_seats} ${t('held')} · ${money(x.currency,x.paid_amount)}`],
          ...(x.minimum_confirmed_seats?[[t('Minimum seats'),String(x.minimum_confirmed_seats)]]:[]),
          ...(x.decision_deadline?[[t('Decision deadline'),formatDateTime(x.decision_deadline)]]:[]),
          [t('Replacement'),x.replacement_status?codeLabel(x.replacement_status):'—']]}/>
        {result
          ?<section className="bc-card at-block">
            <p className="tk-line"><Chip tone="success">{t('Closed')}</Chip> <strong>{t('{value0} refunds created, {value1} in total.',{value0:(result.refunds||[]).length,value1:money(x.currency,refundTotal(result))})}</strong></p>
            <p className="tk-line">{(result.refunds||[]).some(r=>r.status==='PROCESSING')?t('PayHere refunds wait in Processing. Complete them in the Refunds tab after refunding in the PayHere portal.'):t('Sandbox refunds are already paid. You can follow every refund in the Refunds tab.')}</p>
            <div className="tk-bar"><button type="button" className="ui-button ui-button-primary" onClick={onOpenRefunds}>{t('Open Refunds')}</button></div>
          </section>
          :<CannotFulfil key={`${x.id}-${x.version}`} item={x} onDone={r=>done(x,r)} onProblem={problem}/>}
        </div>{!result&&<div className="at-right"><FindReplacement key={`find-${x.id}-${x.version}`} item={x} onSent={problem} onProblem={problem}/></div>}</div>
      </>}}/>
}
