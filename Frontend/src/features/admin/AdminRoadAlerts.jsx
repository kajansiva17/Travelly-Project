import { t } from '../../i18n/language.js'
import React,{useEffect,useState} from 'react'
import {api} from '../../services/api'
import {Field,RateErrors} from '../owner/OwnerRates'
import Chip from '../../components/ui/Chip'
import {formatDateTime} from '../../i18n/dateTime.js'
import AdminList,{Facts} from './AdminList'
import {fieldErrors,fieldErrorMap} from '../../services/fieldErrors.js'

// Admin: road alerts (contract 03A, section 6). Verify, Reject or Remove. Reject and Remove need a reason and a confirm step.
const TYPES={POLICE_PRESENCE:'Police',SPEED_CHECK:'Speed check',ACCIDENT:'Accident',ROADBLOCK:'Roadblock',ROAD_HAZARD:'Road hazard'}
const STATUSES={UNCONFIRMED:['muted','Unconfirmed'],ACTIVE:['info','Active'],VERIFIED:['success','Verified'],REJECTED:['danger','Rejected'],EXPIRED:['muted','Expired'],REMOVED:['danger','Removed']}
const filters=[['','All alerts'],['UNCONFIRMED','Unconfirmed'],['ACTIVE','Active'],['VERIFIED','Verified'],['REJECTED','Rejected'],['EXPIRED','Expired'],['REMOVED','Removed']]
const CLOSED=['REJECTED','EXPIRED','REMOVED']
const chip=status=>STATUSES[status]||['muted',String(status||'—').replaceAll('_',' ')]
const when=value=>value?formatDateTime(value):'—'
const reporterName=reporter=>!reporter?'—':typeof reporter==='string'?reporter:[reporter.display_name||reporter.full_name,reporter.public_user_reference||reporter.reference].filter(Boolean).join(' · ')||'—'

function explain(error){
  const code=error.code,fields=fieldErrors(error)
  if(error instanceof TypeError||code==='API_TIMEOUT')return {text:t('We could not reach Travelly. Please try again.')}
  if(code==='VERSION_CONFLICT')return {reload:true,text:t('This alert changed while you were looking. The list was refreshed, so check it and try again.')}
  if(code==='ROAD_ALERT_CLOSED')return {reload:true,text:t('This alert is already closed. The list was refreshed.')}
  if(code==='REASON_REQUIRED')return {field:'reason',text:error.message}
  if(error.status===404)return {reload:true,text:t('This alert no longer exists. The list was refreshed.')}
  if(error.status===403)return {text:t('Only an Admin can do this.')}
  if(code==='VALIDATION_ERROR'&&fields.length)return {fields:fieldErrorMap(error),text:t('Please check the highlighted fields.')}
  return {text:error.message||t('The change could not be saved. Please try again.')}
}

function Moderate({item,onDone,onProblem}){
  const [mode,setMode]=useState(null),[reason,setReason]=useState(''),[busy,setBusy]=useState(false),[errors,setErrors]=useState({}),[message,setMessage]=useState('')
  async function send(action,why){
    setBusy(true);setMessage('');setErrors({})
    try{onDone(await api(`/admin/road-alerts/${item.id}/moderation`,{method:'POST',body:JSON.stringify({expected_version:item.version,action,...(why?{reason:why}:{})})}),action)}
    catch(error){const out=explain(error);if(out.reload){setMode(null);onProblem(out.text);return}setMessage(out.field?'':out.text);setErrors(out.fields||(out.field?{reason:out.text}:{}))}
    finally{setBusy(false)}
  }
  if(CLOSED.includes(item.status))return <p className="tk-line">{t('This alert is closed.')}{item.moderation_reason&&<> {t('Reason')}: <strong>{item.moderation_reason}</strong></>}</p>
  const asking=mode==='REJECT'||mode==='REMOVE',text=reason.trim()
  return <RateErrors.Provider value={errors}><div className="tk-pane">
    {message&&<p className="tk-line is-warn" role="status">{message}</p>}
    {!mode&&<div className="tk-bar">
      <button type="button" className="ui-button ui-button-primary" disabled={busy||item.status==='VERIFIED'} onClick={()=>send('VERIFY')}>{busy?t('Please wait…'):t('Verify')}</button>
      <button type="button" className="ui-button ui-button-secondary" onClick={()=>setMode('REJECT')}>{t('Reject')}</button>
      <button type="button" className="ui-button ui-button-secondary" onClick={()=>setMode('REMOVE')}>{t('Remove')}</button></div>}
    {asking&&<div className="tk-hold">
      <Field label="Reason" help="Say why. It is saved with the Admin decision."><input name="reason" maxLength="500" value={reason} disabled={mode.startsWith('CONFIRM')} onChange={e=>setReason(e.target.value)}/></Field>
      <div className="tk-bar"><button type="button" className="ui-button ui-button-primary" disabled={!text} onClick={()=>{setErrors({});setMessage('');setMode('CONFIRM_'+mode)}}>{t('Continue')}</button><button type="button" className="ui-button ui-button-secondary" onClick={()=>{setMode(null);setReason('');setErrors({})}}>{t('Not yet')}</button></div></div>}
    {mode&&mode.startsWith('CONFIRM_')&&<div className="tk-hold">
      <p className="tk-line is-warn"><strong>{mode==='CONFIRM_REMOVE'?t('Remove this alert?'):t('Reject this alert?')}</strong> {mode==='CONFIRM_REMOVE'?t('Drivers nearby stop seeing it. The reason is saved.'):t('It is closed as not there. The reason is saved.')} <em>{text}</em></p>
      <div className="tk-bar"><button type="button" className="ui-button ui-button-primary" disabled={busy} onClick={()=>send(mode.slice(8),text)}>{busy?t('Please wait…'):mode==='CONFIRM_REMOVE'?t('Yes, remove'):t('Yes, reject')}</button><button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={()=>setMode(mode.slice(8))}>{t('Back')}</button></div></div>}
  </div></RateErrors.Provider>
}

export default function AdminRoadAlerts(){
  const [items,setItems]=useState(null),[error,setError]=useState(null),[notice,setNotice]=useState(''),[filter,setFilter]=useState('')
  const load=()=>api('/admin/road-alerts'+(filter?'?status='+filter:'')).then(result=>{setItems(result.items||[]);setError(null)}).catch(setError)
  useEffect(()=>{setItems(null);load()},[filter])
  const done=(saved,action)=>{setItems(list=>(list||[]).map(x=>x.id===saved.id?{...x,...saved}:x));setNotice(action==='VERIFY'?t('Alert verified.'):action==='REJECT'?t('Alert rejected.'):t('Alert removed.'));load()}
  const problem=text=>{setNotice(text);load()}
  return <AdminList heading={t('Road alerts')} icon="alert" title={t('Road alerts')} notice={notice} error={error} items={items} empty={t('No road alerts match this filter.')}
    filters={<Field label="Show"><select name="alert-filter" value={filter} onChange={e=>setFilter(e.target.value)}>{filters.map(([value,label])=><option key={value} value={value}>{t(label)}</option>)}</select></Field>} filterCols={4}
    row={x=>{const [tone,label]=chip(x.status);return {key:x.id,title:`${t(TYPES[x.alert_type]||String(x.alert_type||'').replaceAll('_',' '))} · ${when(x.reported_at)}`,meta:`${reporterName(x.reporter)} · ${t('{value0} confirmed, {value1} denied',{value0:x.confirmation_count??0,value1:x.denial_count??0})}`,status:t(label),tone}}}
    detailTitle={x=>t(TYPES[x.alert_type]||'Road alert')}
    detail={x=><>
      <Facts cols={3} entries={[
        [t('Status'),t(chip(x.status)[1])],[t('Reported'),when(x.reported_at)],[t('Expires'),when(x.expires_at)],
        [t('Reported by'),reporterName(x.reporter)],[t('How'),x.source_input==='VOICE'?t('Voice'):t('Button')],[t('Confidence'),x.confidence_score!=null?String(x.confidence_score):'—'],
        [t('Place'),`${x.latitude}, ${x.longitude}`],[t('Confirmed'),String(x.confirmation_count??0)],[t('Denied'),String(x.denial_count??0)],
        ...(x.description?[[t('What was heard'),x.description]]:[]),...(x.moderation_reason?[[t('Reason'),x.moderation_reason]]:[])]}/>
      <Moderate key={`${x.id}-${x.version}-${x.status}`} item={x} onDone={done} onProblem={problem}/>
    </>}/>
}
