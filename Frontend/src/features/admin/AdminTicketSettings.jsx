import { t } from '../../i18n/language.js'
import {useEffect,useState} from 'react'
import {Link} from 'react-router-dom'
import {api} from '../../services/api'
import {ErrorNotice,Header} from '../../components/components'
import Chip from '../../components/ui/Chip'
import {Field,Compact} from '../owner/OwnerRates'
import {FlowShell,usePaged} from '../booking/flow/FlowParts'
import {Notice,Empty} from '../ticketing/TicketParts'

// Admin sets how long a Passenger's selected Ticket seats stay held. Stored in service_types.settings.hold_minutes.
function ServiceHold({row,onSaved,pager}){
  const [minutes,setMinutes]=useState(row.hold_minutes??''),[busy,setBusy]=useState(false),[error,setError]=useState(null),[saved,setSaved]=useState(false)
  async function save(event){
    event.preventDefault();setBusy(true);setError(null);setSaved(false)
    try{await api(`/admin/ticket-services/${row.id}/hold-settings`,{method:'PATCH',body:JSON.stringify({expected_version:row.version,hold_minutes:Number(minutes)})});setSaved(true);await onSaved()}
    catch(problem){setError(problem)}finally{setBusy(false)}
  }
  return <form className="flow-wizard-form tk-pane" onSubmit={save}>
    <div className="tk-bar"><strong className="tk-line">{row.name}</strong><span className="tk-line">{row.code}</span><Chip tone={row.is_active?'success':'muted'}>{row.is_active?'ACTIVE':'INACTIVE'}</Chip></div>
    <ErrorNotice error={error}/><Notice>{saved?'Hold time saved.':''}</Notice>
    <div className="tk-grid" style={{'--cols':2}}>
      <Field label="Seat hold time (minutes)" help="How long selected seats stay reserved for a Passenger before they are released automatically. New holds use the new time; existing holds keep theirs.">
        <input required name="minutes" type="number" min="1" max="1440" step="1" value={minutes} onChange={e=>setMinutes(e.target.value)}/>
      </Field>
    </div>
    <p className="tk-line">{row.hold_minutes?t('Current: {value0} minutes',{value0:row.hold_minutes}):t('Current: not set — Passengers cannot hold seats yet')}</p>
    <div className="flow-actions"><Link className="ui-button ui-button-secondary" to="/admin/services-routes">{t('Back to services')}</Link>{pager}
      <button className="ui-button ui-button-primary" disabled={busy||!minutes||Number(minutes)===row.hold_minutes}>{busy?'Saving…':'Save hold time'}</button></div>
  </form>
}

export default function AdminTicketSettings(){
  const [items,setItems]=useState(null),[error,setError]=useState(null)
  const load=()=>api('/admin/ticket-services').then(result=>setItems(result.items||[])).catch(setError)
  useEffect(()=>{load()},[])
  const rows=usePaged(items||[],1)
  return <><Header/><FlowShell heading="Ticket settings" icon="ticket" title="Seat hold time"
    info="Control how long Passengers can hold numbered seats while they complete a Ticket booking.">
    <Compact.Provider value={true}>
    <ErrorNotice error={error}/>
    {items===null?<p role="status">{t('Loading Ticket services…')}</p>:items.length
      ?rows.slice.map(row=><ServiceHold key={`${row.id}-${row.version}`} row={row} onSaved={load} pager={rows.pages>1?rows.pager:null}/>)
      :<><Empty>{t('No Ticket service configured. The Ticket Hire service has not been set up in this database.')}</Empty>
        <div className="flow-actions"><Link className="ui-button ui-button-secondary" to="/admin/services-routes">{t('Back to services')}</Link></div></>}
    </Compact.Provider>
  </FlowShell></>
}
