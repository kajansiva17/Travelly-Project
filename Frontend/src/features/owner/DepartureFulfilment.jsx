import { t } from '../../i18n/language.js'
import React,{useEffect,useState} from 'react'
import {api} from '../../services/api'
import Chip from '../../components/ui/Chip'
import InfoTip from '../../components/ui/InfoTip'
import {Field,RateErrors} from './OwnerRates'
import {formatDateTime} from '../../i18n/dateTime.js'

// Protected fulfilment (contract 03F2). Status values are the contract's: PUBLISHED, BOOKING_OPEN, COMMITTED,
// DECISION_REQUIRED, DISRUPTED, READY, CANCELLED. Nothing here is decided on the screen: every answer comes from the API.
export const FULFILMENT_STATUS={
  PUBLISHED:['success','Published'],BOOKING_OPEN:['success','Booking open'],COMMITTED:['success','Committed'],READY:['success','Ready'],
  DECISION_REQUIRED:['danger','Decision needed'],DISRUPTED:['danger','Disrupted'],CANCELLED:['muted','Cancelled'],DRAFT:['muted','Draft']}
export const statusChip=status=>{const [tone,label]=FULFILMENT_STATUS[status]||['muted',String(status||'').replaceAll('_',' ')];return {tone,label:t(label)}}

const MINIMUM='MINIMUM_SEATS_WITH_PROTECTED_FULFILMENT'
const COMMITTABLE=['PUBLISHED','BOOKING_OPEN','DECISION_REQUIRED','DISRUPTED']
const REPORTABLE=['PUBLISHED','BOOKING_OPEN','COMMITTED','DECISION_REQUIRED','READY']
const beforeDeparture=x=>new Date(x.departure_at).getTime()>Date.now()
// "Commit to run": minimum-seats departures until committed, and any departure waiting for Travelly (contract section 1 and Screens).
const waitingForOther=x=>x.replacement_status==='AWAITING_OTHER_OWNER'
export const canCommit=x=>COMMITTABLE.includes(x.status)&&beforeDeparture(x)&&!waitingForOther(x)&&(['DECISION_REQUIRED','DISRUPTED'].includes(x.status)||(x.fulfilment?.policy===MINIMUM&&!x.committed_at))
export const canReport=x=>REPORTABLE.includes(x.status)&&beforeDeparture(x)
// "Use another of my vehicles": only while the departure waits for Travelly, before it starts (contract section 5).
export const canReplace=x=>['DECISION_REQUIRED','DISRUPTED'].includes(x.status)&&beforeDeparture(x)&&!waitingForOther(x)
export const canManage=x=>x.status!=='DRAFT'

function explain(error,action){
  const code=error.code,fields=error.fields||[]
  if(error instanceof TypeError||code==='API_TIMEOUT')return {text:t('We could not reach Travelly. Please try again.')}
  if(code==='VERSION_CONFLICT')return {reload:true,text:t('This departure changed while you were looking. It was refreshed, so check it and try again.')}
  if(code==='DEPARTURE_NOT_FOUND'||error.status===404)return {reload:true,text:t('This departure no longer exists. The list has been refreshed.')}
  if(code==='DEPARTURE_STARTED')return {reload:true,text:t('This departure has already started, so this can no longer be done.')}
  if(code==='DEPARTURE_ALREADY_GUARANTEED')return {reload:true,text:t('This departure is already promised to passengers. Nothing more is needed from you.')}
  if(code==='DEPARTURE_NOT_COMMITTABLE')return {reload:true,text:t('This departure cannot be committed in its current state. The list has been refreshed.')}
  if(code==='DEPARTURE_NOT_REPORTABLE')return {reload:true,text:t('A problem can no longer be reported for this departure. The list has been refreshed.')}
  if(code==='REPLACEMENT_NOT_ALLOWED'||code==='REPLACEMENT_VEHICLE_UNAVAILABLE'||code==='VEHICLE_SCHEDULE_CONFLICT'||code==='REPLACEMENT_PENDING'){return {reload:code==='REPLACEMENT_NOT_ALLOWED'||code==='REPLACEMENT_PENDING',text:t(error.message)}}
  if(code==='REPLACEMENT_TOO_SMALL'){const m=/has (\d+) bookable seats; (\d+) passengers/.exec(error.message||'');return {text:m?t('This vehicle has {value0} bookable seats; {value1} passengers are booked.',{value0:m[1],value1:m[2]}):t(error.message)}}
  if(error.status===403)return {text:t('Only the Owner of this departure can do this.')}
  if(code==='VALIDATION_ERROR'&&fields.length)return {fields:Object.fromEntries(fields.map(f=>[f.field,f.message])),text:t('Please check the highlighted fields.')}
  return {text:error.message||(action==='commit'?t('The departure could not be committed. Please try again.'):t('The problem could not be reported. Please try again.'))}
}

export default function DepartureFulfilment({departure:x,onDone,onProblem,onBack}){
  const [mode,setMode]=useState(null),[reason,setReason]=useState(''),[busy,setBusy]=useState(false),[errors,setErrors]=useState({}),[message,setMessage]=useState(''),[pick,setPick]=useState(''),[options,setOptions]=useState(null),[query,setQuery]=useState(''),[looking,setLooking]=useState(false),[lookMessage,setLookMessage]=useState('')
  const {tone,label}=statusChip(x.status)
  const text=reason.trim(),reasonOk=text.length>=5&&text.length<=1000
  async function send(action){
    setBusy(true);setMessage('');setErrors({})
    try{
      const body=action==='commit'?{expected_version:x.version}:action==='replace'?{expected_version:x.version,vehicle_id:pick}:{expected_version:x.version,reason:text}
      // Section 5 for my own vehicle, section 8 for another Owner vehicle.
      const path=action==='commit'?'commit':action==='replace'?(chosen?.own?'replacement-vehicle':'replacement-request'):'problem'
      const result=await api(`/scheduled-trips/${x.id}/${path}`,{method:'POST',body:JSON.stringify(body)})
      await onDone(action==='replace'&&!chosen?.own?'request':action,result)
    }catch(error){
      const out=explain(error,action)
      if(out.reload){onProblem(out.text);return}
      setMessage(out.text);setErrors(out.fields||{});if(out.fields)setMode('report-form');else if(action==='replace')setMode('vehicle')
    }finally{setBusy(false)}
  }
  const chosen=(options||[]).find(v=>v.vehicle_id===pick)
  // Section 7: the vehicles that fit this departure (mine first, then other Owners published ones), optionally narrowed by reference.
  async function loadOptions(reference=''){
    setLooking(true);setLookMessage('')
    try{
      const r=await api(`/scheduled-trips/${x.id}/replacement-options${reference?`?reference=${encodeURIComponent(reference)}`:''}`)
      setOptions(r.items||[]);setPick('')
      if(!(r.items||[]).length)setLookMessage(reference?t('No vehicle with this reference fits this departure.'):t('No vehicle fits this departure right now.'))
    }catch(error){const out=explain(error,'replace');if(out.reload){onProblem(out.text);return}setLookMessage(out.text);setOptions([])}
    finally{setLooking(false)}
  }
  useEffect(()=>{if(mode==='vehicle'&&options===null)loadOptions()},[mode])
  const vehicleText=v=>[`${v.make||''} ${v.model||''}`.trim(),v.vehicle_type_code,v.colour,v.air_conditioned?'AC':null,t('{value0} seats',{value0:v.seat_capacity}),t('{value0} bookable',{value0:v.bookable_seats})].filter(Boolean).join(' · ')
  const route=`${x.route?.origin_name||''} → ${x.route?.destination_name||''}`
  return <RateErrors.Provider value={errors}><div className="tk-pane">
    <p className="tk-line"><strong>{route}</strong> · {formatDateTime(x.departure_at)} <Chip tone={tone}>{label}</Chip>
      {x.committed_at&&<span> · {t('Committed')} {formatDateTime(x.committed_at)}</span>}
      {x.fulfilment?.decision_deadline&&!x.committed_at&&<span> · {t('Decide by')} {formatDateTime(x.fulfilment.decision_deadline)}</span>}</p>
    {!mode&&x.status==='DECISION_REQUIRED'&&<p className="tk-line is-warn">{t('The decision deadline has passed. Commit to run this departure, or tell us you cannot run it. Nothing is cancelled or refunded until then.')}</p>}
    {!mode&&x.status==='DISRUPTED'&&<p className="tk-line is-warn">{t('You reported a problem. Travelly is arranging the journey for the passengers who paid. You can still commit to run it if the problem is solved.')}</p>}
    {waitingForOther(x)&&<p className="tk-line" role="status"><Chip tone="info" icon="clock">{t('Waiting for the other Owner')}</Chip> {t('You asked another Owner to run this departure with their vehicle. Nothing moves until they answer.')}</p>}
    {x.status==='CANCELLED'&&<p className="tk-line">{t('This departure is cancelled.')} {x.cancellation_reason&&<span>{x.cancellation_reason}</span>}</p>}
    {x.status==='COMMITTED'&&<p className="tk-line">{t('You committed to run this departure. Passengers can keep booking until the booking cut-off.')}</p>}
    {message&&<p className="tk-line is-warn" role="status">{message}</p>}

    {!mode&&<div className="tk-bar">
      {canCommit(x)&&<button type="button" className="ui-button ui-button-primary" disabled={busy} onClick={()=>setMode('commit')}>{t('Commit to run')}</button>}
      {canReplace(x)&&<button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={()=>{setPick('');setOptions(null);setQuery('');setMode('vehicle')}}>{t('Find a replacement vehicle')}</button>}
      {canReport(x)&&<button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={()=>{setReason('');setMode('report-form')}}>{t('I can’t run this departure')}</button>}
      <InfoTip>{t('Committing tells passengers who paid that the departure will run. If you cannot run it, report it before the journey starts so Travelly can arrange the passengers’ journey.')}</InfoTip></div>}

    {(mode==='vehicle'||mode==='vehicle-confirm')&&<div className="tk-hold">
      <div className="tk-bar tk-finder-row"><div className="tk-grow"><Field label="Find a vehicle by reference" optional help="Type a vehicle reference such as VEH-… to narrow the list. Leave it empty to see every vehicle that fits."><input name="vehicle_reference" maxLength="40" autoComplete="off" placeholder="VEH-…" value={query} disabled={mode==='vehicle-confirm'} onChange={e=>setQuery(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'){e.preventDefault();loadOptions(query.trim())}}}/></Field></div>
        <button type="button" className="ui-button ui-button-secondary" disabled={looking||mode==='vehicle-confirm'} onClick={()=>loadOptions(query.trim())}>{looking?t('Please wait…'):t('Search')}</button>
        {query&&<button type="button" className="ui-button ui-button-secondary" disabled={looking||mode==='vehicle-confirm'} onClick={()=>{setQuery('');loadOptions('')}}>{t('Show all')}</button>}</div>
      {lookMessage&&<p className="tk-line is-warn" role="status">{lookMessage}</p>}
      {options===null&&!lookMessage&&<p className="tk-line" role="status">{t('Loading vehicles…')}</p>}
      {options&&options.length>0&&<Field label="Replacement vehicle"><select name="replacement" value={pick} disabled={mode==='vehicle-confirm'} onChange={e=>{setPick(e.target.value);setMessage('')}}>
        <option value="">{t('Choose a vehicle')}</option>{options.map(v=><option key={v.vehicle_id} value={v.vehicle_id}>{v.public_vehicle_reference} · {v.own?t('My vehicle'):v.owner_name} · {vehicleText(v)}</option>)}</select></Field>}
      {chosen&&mode==='vehicle'&&<p className="tk-line"><Chip tone={chosen.own?'success':'info'}>{chosen.own?t('My vehicle'):t('Another Owner')}</Chip> {vehicleText(chosen)}{!chosen.own&&chosen.owner_name?` · ${chosen.owner_name}`:''}</p>}
      {mode==='vehicle-confirm'&&chosen&&(chosen.own
        ?<p className="tk-line is-warn"><strong>{t('Use {value0} for this departure?',{value0:chosen.public_vehicle_reference})}</strong> {t('Passengers who paid move to the new vehicle automatically: the same seat when it has it, otherwise the next free seat. Open seat holds end. Each passenger can accept the change or reject it for a full refund.')}</p>
        :<p className="tk-line is-warn"><strong>{t('Ask {value0} to run this departure with {value1}?',{value0:chosen.owner_name||t('the other Owner'),value1:chosen.public_vehicle_reference})}</strong> {t('Nothing moves until they accept. While you wait you cannot commit or use your own vehicle.')}</p>)}
      <div className="tk-bar">{mode==='vehicle-confirm'
        ?<><button type="button" className="ui-button ui-button-primary" disabled={busy} onClick={()=>send('replace')}>{busy?t('Please wait…'):chosen?.own?t('Yes, use this vehicle'):t('Yes, send the request')}</button><button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={()=>setMode('vehicle')}>{t('Back')}</button></>
        :<><button type="button" className="ui-button ui-button-primary" disabled={!pick} onClick={()=>{setMessage('');setMode('vehicle-confirm')}}>{t('Continue')}</button><button type="button" className="ui-button ui-button-secondary" onClick={()=>{setMode(null);setMessage('')}}>{t('Not yet')}</button></>}</div></div>}
    {mode==='commit'&&<div className="tk-hold"><p className="tk-line"><strong>{t('Commit to run this departure?')}</strong> {t('Passengers who paid are told it will run.')}{x.status==='DECISION_REQUIRED'||x.status==='DISRUPTED'?` ${t('The Admin is told it is resolved.')}`:''}</p>
      <div className="tk-bar"><button type="button" className="ui-button ui-button-primary" disabled={busy} onClick={()=>send('commit')}>{busy?t('Please wait…'):t('Yes, commit')}</button><button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={()=>setMode(null)}>{t('Not yet')}</button></div></div>}

    {(mode==='report-form'||mode==='report')&&<div className="tk-hold">
      <Field label="Why can’t you run it?" help="Between 5 and 1000 characters. The Admin sees this reason."><input name="reason" maxLength="1000" value={reason} disabled={mode==='report'} onChange={e=>setReason(e.target.value)}/></Field>
      {mode==='report'&&<p className="tk-line is-warn"><strong>{t('Report that you cannot run this departure?')}</strong> {t('Selling stops and open seat holds end. Passengers who paid stay booked while Travelly arranges their journey, and they are told. If nobody has paid, the departure is withdrawn.')}</p>}
      <div className="tk-bar">{mode==='report'
        ?<><button type="button" className="ui-button ui-button-primary" disabled={busy} onClick={()=>send('report')}>{busy?t('Please wait…'):t('Yes, I can’t run it')}</button><button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={()=>setMode('report-form')}>{t('Back')}</button></>
        :<><button type="button" className="ui-button ui-button-primary" disabled={!reasonOk} onClick={()=>{setErrors({});setMessage('');setMode('report')}}>{t('Continue')}</button><button type="button" className="ui-button ui-button-secondary" onClick={()=>{setMode(null);setReason('');setErrors({})}}>{t('Not yet')}</button></>}</div></div>}

    <div className="flow-actions"><button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={onBack}>{t('Back to list')}</button><span/></div>
  </div></RateErrors.Provider>
}
