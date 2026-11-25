import { t } from '../../i18n/language.js'
import {useEffect,useState} from 'react'
import {api} from '../../services/api'
import {Field,RateErrors} from '../owner/OwnerRates'
import AdminList from './AdminList'
import {fieldErrorMap} from '../../services/fieldErrors.js'

// Admin: how many hours before a booking starts the Passenger, Owner and Driver can see each other's phone number (default 2). Book now shows it at once.
// Chat is open from confirmation until the trip ends, whatever this is set to.
function WindowForm({row,max,onSaved,onConflict}){
  const [hours,setHours]=useState(String(row.contact_hours_before)),[busy,setBusy]=useState(false),[errors,setErrors]=useState({}),[message,setMessage]=useState('')
  async function save(event){
    event.preventDefault();setBusy(true);setErrors({});setMessage('')
    try{onSaved(await api(`/admin/service-types/${row.id}/contact-window`,{method:'PATCH',body:JSON.stringify({expected_version:row.version,hours:Number(String(hours).trim())})}))}
    catch(error){
      if(error.code==='VERSION_CONFLICT'){onConflict();return}
      if(error.code==='VALIDATION_ERROR')setErrors(fieldErrorMap(error))
      else setMessage(error.message||t('The settings could not be saved. Please try again.'))
    }finally{setBusy(false)}
  }
  return <RateErrors.Provider value={errors}><form className="flow-wizard-form tk-pane" onSubmit={save} noValidate>
    <div className="tk-grid" style={{'--cols':3}}>
      <Field label="Hours before start" help="Phone numbers show from this many hours before the trip starts. 0 means only when it starts. Book now trips show them at once."><input required name="hours" type="number" min="0" max={max} step="1" inputMode="numeric" value={hours} onChange={event=>setHours(event.target.value)}/></Field>
    </div>
    <p className="tk-line">{t('Chat is open from confirmation until the trip ends. A change applies to all bookings that have not started.')}</p>
    {message&&<p className="tk-line is-warn" role="alert">{message}</p>}
    <div className="flow-actions"><span/><button type="submit" className="ui-button ui-button-primary" disabled={busy}>{busy?t('Saving…'):t('Save call time')}</button></div>
  </form></RateErrors.Provider>
}

export default function AdminContactSettings({base}){
  const [items,setItems]=useState(null),[max,setMax]=useState(168),[error,setError]=useState(null),[notice,setNotice]=useState('')
  const load=()=>api('/admin/contact-settings',{cache:'no-store'}).then(result=>{setItems(result.items||[]);setMax(result.max_hours||168)}).catch(setError)
  useEffect(()=>{load()},[])
  const saved=row=>{setItems(list=>(list||[]).map(item=>item.id===row.id?{...item,...row}:item));setNotice(t('Call time saved.'))}
  const conflict=()=>{setNotice(t('Changed by someone else — the list was reloaded. Check the values and save again.'));load()}
  return <AdminList {...base} title={t('Call & chat')} error={error||base.error} notice={notice} items={items} empty={t('No services found.')}
    row={item=>({key:item.id,title:item.name,meta:`${t('Hours before start')} ${item.contact_hours_before}`,status:item.is_active?t('ACTIVE'):t('INACTIVE'),tone:item.is_active?'success':'muted'})}
    detailTitle={item=>item.name} detailLabel="Edit"
    detail={item=><WindowForm key={`${item.id}-${item.version}`} row={item} max={max} onSaved={saved} onConflict={conflict}/>}/>
}
