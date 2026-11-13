import { t } from '../../i18n/language.js'
import React,{useCallback,useEffect,useRef,useState} from 'react'
import {api,publicRead} from '../../services/api'
import Chip from '../../components/ui/Chip'
import {Checkbox} from '../../components/ui'
import {Field,RateErrors} from './OwnerRates'
import {money} from '../passenger/TicketCancel'
import {fieldErrorMap,fieldErrorText} from '../../services/fieldErrors.js'
import {PACKAGE_LIMITS,canSave,checkPackage,newPackageId,readEvent,toBody} from './eventPackageModel'

/* Vehicle → Event packages (contract 03EV): this vehicle with its Driver for a fixed number of hours at a fixed price.
   GET /vehicles/{id}/services gives the saved packages (event_packages on the Event service row); PUT /vehicles/{id}/event-packages
   replaces the whole list (1 to 20). Add, edit and remove happen on the list first; Save packages sends it. */
const MESSAGES={name:'Enter a name (up to 120 characters).',hours:'More than 0 and at most 24 hours.',price:'Above 0, with at most two decimals.',notes:'Up to 500 characters.'}

export default function EventPackages({vehicle,Footer}){
  const [event,setEvent]=useState(null),[saved,setSaved]=useState(null),[packages,setPackages]=useState([]),[enabled,setEnabled]=useState(true),[editing,setEditing]=useState(null),[removing,setRemoving]=useState(null)
  const [busy,setBusy]=useState(false),[message,setMessage]=useState({text:'',warn:false}),[errors,setErrors]=useState({}),[loadError,setLoadError]=useState(''),sending=useRef(false)
  const load=useCallback(async(keepMessage=false)=>{
    try{
      const [types,own]=await Promise.all([publicRead('/service-types'),api(`/vehicles/${vehicle.id}/services`,{cache:'no-store'})])
      const service=(types.items||[]).find(s=>s.pricing_scope==='EVENT')
      setEvent(service||false)
      if(service){const current=readEvent(own.items,service.id);setSaved(current);setPackages(current.packages);setEnabled(current.enabled)}
      setLoadError('');if(!keepMessage)setMessage({text:'',warn:false})
    }catch(error){setLoadError(fieldErrorText(error))}
  },[vehicle.id])
  useEffect(()=>{load()},[load])
  const dirty=saved&&(JSON.stringify(packages)!==JSON.stringify(saved.packages)||enabled!==saved.enabled)
  const draftErrors=editing?checkPackage(editing):{}

  function commit(){
    if(Object.keys(draftErrors).length){setErrors(Object.fromEntries(Object.entries(draftErrors).map(([k,v])=>[k,t(MESSAGES[k])])));return}
    const item={...editing,name:editing.name.trim(),notes:editing.notes||''}
    setPackages(list=>list.some(p=>p.id===item.id)?list.map(p=>p.id===item.id?item:p):[...list,item]);setEditing(null);setErrors({})
  }
  async function save(){
    if(sending.current)return
    sending.current=true;setBusy(true);setMessage({text:'',warn:false});setErrors({})
    try{
      const result=await api(`/vehicles/${vehicle.id}/event-packages`,{method:'PUT',body:JSON.stringify(toBody({serviceTypeId:event.id,version:saved.version,enabled,packages}))})
      setMessage({text:result?.message||t('Event packages saved.'),warn:false});await load(true)
    }catch(error){
      setMessage({text:fieldErrorText(error),warn:true});setErrors(fieldErrorMap(error))
      if(error.code==='VERSION_CONFLICT')await load(true)   // the newest packages come back; the server message says to reload before editing again
    }finally{sending.current=false;setBusy(false)}
  }
  if(loadError)return <p className="tk-line is-warn" role="alert">{loadError} <button type="button" className="inline-link" onClick={()=>load()}>{t('Try again')}</button></p>
  if(event===null)return <p role="status">{t('Loading…')}</p>
  if(event===false)return <p className="tk-line" role="status">{t('Event hire is not active yet.')}</p>

  return <RateErrors.Provider value={errors}><div className="ep-pane">
    {message.text&&<p className={'tk-line'+(message.warn?' is-warn':'')} role={message.warn?'alert':'status'}>{message.text}</p>}
    {editing
      ?<div className="ep-editor">
        <div className="tk-grid" style={{'--cols':2}}>
          <Field label="Package name"><input name="name" maxLength={PACKAGE_LIMITS.name} value={editing.name} onChange={e=>setEditing(c=>({...c,name:e.target.value}))}/></Field>
          <Field label="Hours" help="More than 0 and at most 24 hours."><input name="hours" inputMode="decimal" value={editing.hours} onChange={e=>setEditing(c=>({...c,hours:e.target.value}))}/></Field>
          <Field label="Price (LKR)" help="The fixed price: vehicle and Driver."><input name="price" inputMode="decimal" value={editing.price} onChange={e=>setEditing(c=>({...c,price:e.target.value}))}/></Field>
          <Field label="Notes" optional><input name="notes" maxLength={PACKAGE_LIMITS.notes} value={editing.notes} onChange={e=>setEditing(c=>({...c,notes:e.target.value}))}/></Field></div>
        <div className="tk-bar"><button type="button" className="ui-button ui-button-secondary" onClick={()=>{setEditing(null);setErrors({})}}>{t('Cancel')}</button>
          <button type="button" className="ui-button ui-button-primary" onClick={commit}>{t('Done')}</button></div></div>
      :<>
        <div className="tk-bar"><Checkbox checked={enabled} onChange={e=>setEnabled(e.target.checked)}>{t('Enabled')}</Checkbox>
          <Chip tone="info">{t('{value0} of {value1} packages',{value0:packages.length,value1:PACKAGE_LIMITS.max})}</Chip>
          <button type="button" className="ui-button ui-button-secondary" disabled={packages.length>=PACKAGE_LIMITS.max} onClick={()=>{setMessage({text:'',warn:false});setEditing({id:newPackageId(),name:'',hours:'',price:'',notes:''})}}>{t('Add a package')}</button></div>
        {!packages.length&&<p className="tk-line" role="status">{t('No packages yet.')}</p>}
        <div className="ep-list">{packages.map(p=>removing===p.id
          ?<article className="tk-row tk-hold" key={p.id}><div className="tk-row-main"><strong>{t('Remove {value0}?',{value0:p.name})}</strong></div>
            <div className="tk-row-actions"><button type="button" className="ui-button ui-button-primary" onClick={()=>{setPackages(list=>list.filter(x=>x.id!==p.id));setRemoving(null)}}>{t('Yes, remove')}</button><button type="button" className="ui-button ui-button-secondary" onClick={()=>setRemoving(null)}>{t('Back')}</button></div></article>
          :<article className="tk-row" key={p.id}><div className="tk-row-main"><strong>{p.name}</strong><span>{t('{value0} hours',{value0:p.hours})} · {money('LKR',p.price)}{p.notes?` · ${p.notes}`:''}</span></div>
            <div className="tk-row-actions"><button type="button" className="ui-button ui-button-secondary" onClick={()=>{setMessage({text:'',warn:false});setEditing({...p})}}>{t('Edit')}</button><button type="button" className="ui-button ui-button-secondary" onClick={()=>setRemoving(p.id)}>{t('Remove')}</button></div></article>)}</div>
      </>}
    <Footer>{!editing&&<button type="button" className="ui-button ui-button-primary" disabled={busy||!dirty||!canSave(packages)} onClick={save}>{busy?t('Saving…'):t('Save packages')}</button>}</Footer>
  </div></RateErrors.Provider>
}
