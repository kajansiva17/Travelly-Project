import { t } from '../../i18n/language.js'
import React,{useState} from 'react'
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
export const canCommit=x=>COMMITTABLE.includes(x.status)&&beforeDeparture(x)&&(['DECISION_REQUIRED','DISRUPTED'].includes(x.status)||(x.fulfilment?.policy===MINIMUM&&!x.committed_at))
export const canReport=x=>REPORTABLE.includes(x.status)&&beforeDeparture(x)
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
  if(error.status===403)return {text:t('Only the Owner of this departure can do this.')}
  if(code==='VALIDATION_ERROR'&&fields.length)return {fields:Object.fromEntries(fields.map(f=>[f.field,f.message])),text:t('Please check the highlighted fields.')}
  return {text:error.message||(action==='commit'?t('The departure could not be committed. Please try again.'):t('The problem could not be reported. Please try again.'))}
}

export default function DepartureFulfilment({departure:x,onDone,onProblem,onBack}){
  const [mode,setMode]=useState(null),[reason,setReason]=useState(''),[busy,setBusy]=useState(false),[errors,setErrors]=useState({}),[message,setMessage]=useState('')
  const {tone,label}=statusChip(x.status)
  const text=reason.trim(),reasonOk=text.length>=5&&text.length<=1000
  async function send(action){
    setBusy(true);setMessage('');setErrors({})
    try{
      const body=action==='commit'?{expected_version:x.version}:{expected_version:x.version,reason:text}
      const result=await api(`/scheduled-trips/${x.id}/${action==='commit'?'commit':'problem'}`,{method:'POST',body:JSON.stringify(body)})
      await onDone(action,result)
    }catch(error){
      const out=explain(error,action)
      if(out.reload){onProblem(out.text);return}
      setMessage(out.text);setErrors(out.fields||{});if(out.fields)setMode('report-form')
    }finally{setBusy(false)}
  }
  const route=`${x.route?.origin_name||''} → ${x.route?.destination_name||''}`
  return <RateErrors.Provider value={errors}><div className="tk-pane">
    <p className="tk-line"><strong>{route}</strong> · {formatDateTime(x.departure_at)} <Chip tone={tone}>{label}</Chip>
      {x.committed_at&&<span> · {t('Committed')} {formatDateTime(x.committed_at)}</span>}
      {x.fulfilment?.decision_deadline&&!x.committed_at&&<span> · {t('Decide by')} {formatDateTime(x.fulfilment.decision_deadline)}</span>}</p>
    {x.status==='DECISION_REQUIRED'&&<p className="tk-line is-warn">{t('The decision deadline has passed. Commit to run this departure, or tell us you cannot run it. Nothing is cancelled or refunded until then.')}</p>}
    {x.status==='DISRUPTED'&&<p className="tk-line is-warn">{t('You reported a problem. Travelly is arranging the journey for the passengers who paid. You can still commit to run it if the problem is solved.')}</p>}
    {x.status==='CANCELLED'&&<p className="tk-line">{t('This departure is cancelled.')} {x.cancellation_reason&&<span>{x.cancellation_reason}</span>}</p>}
    {x.status==='COMMITTED'&&<p className="tk-line">{t('You committed to run this departure. Passengers can keep booking until the booking cut-off.')}</p>}
    {message&&<p className="tk-line is-warn" role="status">{message}</p>}

    {!mode&&<div className="tk-bar">
      {canCommit(x)&&<button type="button" className="ui-button ui-button-primary" disabled={busy} onClick={()=>setMode('commit')}>{t('Commit to run')}</button>}
      {canReport(x)&&<button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={()=>{setReason('');setMode('report-form')}}>{t('I can’t run this departure')}</button>}
      <InfoTip>{t('Committing tells passengers who paid that the departure will run. If you cannot run it, report it before the journey starts so Travelly can arrange the passengers’ journey.')}</InfoTip></div>}

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
