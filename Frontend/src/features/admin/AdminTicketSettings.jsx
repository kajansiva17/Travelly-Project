import React,{useEffect,useState} from 'react'
import {Link} from 'react-router-dom'
import {api} from '../../services/api'
import {ErrorNotice,Header} from '../../components/components'
import {TravellyField,TravellyGlassPanel,TravellyState,TravellyStatusChip} from '../../components/TravellyVisualFoundation'

// Admin sets how long a Passenger's selected Ticket seats stay held. Stored in service_types.settings.hold_minutes.
function ServiceHold({row,onSaved}){
  const [minutes,setMinutes]=useState(row.hold_minutes??''),[busy,setBusy]=useState(false),[error,setError]=useState(null),[saved,setSaved]=useState(false)
  async function save(event){
    event.preventDefault();setBusy(true);setError(null);setSaved(false)
    try{await api(`/admin/ticket-services/${row.id}/hold-settings`,{method:'PATCH',body:JSON.stringify({expected_version:row.version,hold_minutes:Number(minutes)})});setSaved(true);await onSaved()}
    catch(problem){setError(problem)}finally{setBusy(false)}
  }
  return <TravellyGlassPanel>
    <header className="workspace-heading"><div><p className="section-kicker">{row.code}</p><h2>{row.name}</h2></div>
      <TravellyStatusChip tone={row.is_active?'success':'warning'}>{row.is_active?'ACTIVE':'INACTIVE'}</TravellyStatusChip></header>
    <ErrorNotice error={error}/>{saved&&<p role="status">Hold time saved.</p>}
    <form onSubmit={save}>
      <TravellyField label="Seat hold time (minutes)" help="How long selected seats stay reserved for a Passenger before they are released automatically. New holds use the new time; existing holds keep theirs.">
        <input required type="number" min="1" max="1440" step="1" value={minutes} onChange={e=>setMinutes(e.target.value)}/>
      </TravellyField>
      <p>Current: {row.hold_minutes?`${row.hold_minutes} minutes`:'not set — Passengers cannot hold seats yet'}</p>
      <button className="button" disabled={busy||!minutes||Number(minutes)===row.hold_minutes}>{busy?'Saving…':'Save hold time'}</button>
    </form>
  </TravellyGlassPanel>
}

export default function AdminTicketSettings(){
  const [items,setItems]=useState(null),[error,setError]=useState(null)
  const load=()=>api('/admin/ticket-services').then(result=>setItems(result.items||[])).catch(setError)
  useEffect(()=>{load()},[])
  return <><Header/><main className="role-dashboard" id="main">
    <div className="workspace-heading"><div><p className="section-kicker">ADMIN · SERVICES &amp; ROUTES</p><h1>Ticket settings</h1>
      <p>Control how long Passengers can hold numbered seats while they complete a Ticket booking.</p></div></div>
    <ErrorNotice error={error}/>
    {items===null?<TravellyState kind="loading" title="Loading Ticket services"/>:items.length
      ?items.map(row=><ServiceHold key={`${row.id}-${row.version}`} row={row} onSaved={load}/>)
      :<TravellyState title="No Ticket service configured">The Ticket Hire service has not been set up in this database.</TravellyState>}
    <Link className="button outline" to="/admin/services-routes">Back to services</Link>
  </main></>
}
