import React,{useEffect,useState} from 'react'
import {Link} from 'react-router-dom'
import {api} from '../../services/api'
import {ErrorNotice,Header} from '../../components/components'
import {TravellyField,TravellyGlassPanel,TravellyState,TravellyStatusChip} from '../../components/TravellyVisualFoundation'
import {PlaceSearch} from './OwnerRates'

// Owner routes (decision 9 Nov 2026): the Owner adds the roads they run Ticket trips on. A route is usable
// as soon as it is saved; no Admin approval. Places come from location search, never typed coordinates,
// unless search is unavailable (then the Owner may paste map numbers).

const six=v=>v===''||v==null?'':String(Math.round(Number(v)*1e6)/1e6)
const shortName=label=>(label||'').split(',')[0].trim().slice(0,150)
const blankStop=()=>({key:Math.random().toString(36).slice(2),id:null,place:null,name:'',latitude:'',longitude:'',hours:'0',minutes:'0',getOn:true,getOff:true,manual:false})
const fromServer=s=>({key:s.id,id:s.id,place:{label:s.stop_name,latitude:s.latitude,longitude:s.longitude},name:s.stop_name,latitude:s.latitude,longitude:s.longitude,
  hours:String(Math.floor(s.scheduled_offset_minutes/60)),minutes:String(s.scheduled_offset_minutes%60),getOn:s.pickup_allowed,getOff:s.dropoff_allowed,manual:false})
const offset=s=>(Number(s.hours)||0)*60+(Number(s.minutes)||0)
const duration=m=>m<60?`${m} min`:`${Math.floor(m/60)} h${m%60?` ${m%60} min`:''}`

function StopCard({stop,index,count,onChange,onMove,onRemove}){
  const first=index===0,last=index===count-1
  const role=first?'Starting from':last?'Going to':'Stop on the way'
  const set=patch=>onChange({...stop,...patch})
  return <fieldset className="owner-route-stop" style={{border:'1px solid rgba(15,40,80,.15)',borderRadius:14,padding:'14px 16px',marginBottom:12}}>
    <legend style={{fontWeight:700,padding:'0 6px'}}>Stop {index+1} · {role}</legend>
    {stop.manual
      ?<div className="passenger-detail-grid">
        <TravellyField label="Latitude (map number)" help="Google Maps: press and hold the place, then copy the first number."><input required type="number" step="0.000001" min="-90" max="90" value={stop.latitude} onChange={e=>set({latitude:e.target.value})}/></TravellyField>
        <TravellyField label="Longitude (map number)" help="The second number from the same place."><input required type="number" step="0.000001" min="-180" max="180" value={stop.longitude} onChange={e=>set({longitude:e.target.value})}/></TravellyField>
      </div>
      :<PlaceSearch label="Find the place" value={stop.place} querySeed={stop.name}
         onChange={place=>set(place?{place,latitude:place.latitude,longitude:place.longitude,name:stop.name||shortName(place.label)}:{place:null,latitude:'',longitude:''})}/>}
    <button type="button" className="inline-link" onClick={()=>set({manual:!stop.manual})}>{stop.manual?'Search for the place instead':'Can’t find it? Enter map numbers instead'}</button>
    <div className="passenger-detail-grid">
      <TravellyField label="Name passengers will see" help="Short and clear, e.g. Vavuniya bus stand."><input required maxLength="150" value={stop.name} onChange={e=>set({name:e.target.value})}/></TravellyField>
      {first?<TravellyField label="Time from start" help="The trip starts here."><input disabled value="0 min"/></TravellyField>
        :<TravellyField label="Time from start" help="About how long after leaving the first stop you reach this stop.">
          <span style={{display:'flex',gap:8}}>
            <select aria-label="Hours" value={stop.hours} onChange={e=>set({hours:e.target.value})}>{Array.from({length:49},(_,h)=><option key={h} value={h}>{h} h</option>)}</select>
            <select aria-label="Minutes" value={stop.minutes} onChange={e=>set({minutes:e.target.value})}>{[0,5,10,15,20,25,30,35,40,45,50,55].map(m=><option key={m} value={m}>{m} min</option>)}</select>
          </span></TravellyField>}
    </div>
    <label><input type="checkbox" checked={stop.getOn} disabled={first} onChange={e=>set({getOn:e.target.checked})}/> Passengers can get on here</label>{' '}
    <label><input type="checkbox" checked={stop.getOff} disabled={last} onChange={e=>set({getOff:e.target.checked})}/> Passengers can get off here</label>
    <div style={{display:'flex',gap:8,marginTop:8}}>
      {!first&&<button type="button" className="button outline" onClick={()=>onMove(-1)}>Move up</button>}
      {!last&&<button type="button" className="button outline" onClick={()=>onMove(1)}>Move down</button>}
      {count>2&&<button type="button" className="button outline" onClick={onRemove}>Remove stop</button>}
    </div>
  </fieldset>
}

function RouteForm({editing,onSaved,onCancel}){
  const [stops,setStops]=useState(editing?editing.stops.map(fromServer):[blankStop(),blankStop()])
  const [name,setName]=useState(editing&&editing.route_name!==`${editing.origin_name} - ${editing.destination_name}`?editing.route_name:'')
  const [distance,setDistance]=useState(editing?.estimated_distance_km?String(Number(editing.estimated_distance_km)):'')
  const [busy,setBusy]=useState(false),[error,setError]=useState(null)
  const change=(i,next)=>setStops(stops.map((s,k)=>k===i?next:s))
  const move=(i,d)=>{const next=[...stops];[next[i],next[i+d]]=[next[i+d],next[i]];setStops(next)}
  const add=()=>setStops([...stops.slice(0,-1),blankStop(),stops[stops.length-1]])
  const times=stops.map((s,i)=>i===0?0:offset(s))
  const timeProblem=times.some((m,i)=>i>0&&m<times[i-1])
  const missingPlace=stops.some(s=>s.latitude===''||s.longitude==='')
  const auto=stops[0].name&&stops[stops.length-1].name?`${stops[0].name} - ${stops[stops.length-1].name}`:''
  async function save(e){
    e.preventDefault();setBusy(true);setError(null)
    const body={route_name:name.trim()||null,estimated_distance_km:distance===''?null:String(distance),estimated_duration_minutes:times[times.length-1]||null,
      stops:stops.map((s,i)=>({...(s.id?{id:s.id}:{}),stop_name:s.name.trim(),latitude:six(s.latitude),longitude:six(s.longitude),
        pickup_allowed:i===0?true:s.getOn,dropoff_allowed:i===stops.length-1?true:s.getOff,scheduled_offset_minutes:i===0?0:offset(s)}))}
    try{
      const saved=editing
        ?await api(`/owners/me/routes/${editing.id}`,{method:'PUT',body:JSON.stringify({...body,expected_version:editing.version})})
        :await api('/owners/me/routes',{method:'POST',body:JSON.stringify(body)})
      onSaved(saved,editing?'Route updated.':'Route saved. You can use it for Ticket departures now.')
    }catch(problem){setError(problem)}finally{setBusy(false)}
  }
  return <TravellyGlassPanel>
    <h2>{editing?`Edit ${editing.route_name}`:'Add a route'}</h2>
    <p>Add the stops in the order the vehicle drives. The first stop is where the trip starts, the last is where it ends.</p>
    <ErrorNotice error={error}/>
    <form onSubmit={save}>
      {stops.map((s,i)=><StopCard key={s.key} stop={s} index={i} count={stops.length} onChange={next=>change(i,next)} onMove={d=>move(i,d)} onRemove={()=>setStops(stops.filter((_,k)=>k!==i))}/>)}
      <button type="button" className="button outline" disabled={stops.length>=50} onClick={add}>+ Add a stop on the way</button>
      <div className="passenger-detail-grid" style={{marginTop:16}}>
        <TravellyField label="Route name (optional)" help={auto?`Leave empty to use “${auto}”.`:'Leave empty to name it after the first and last stop.'}><input maxLength="150" value={name} onChange={e=>setName(e.target.value)}/></TravellyField>
        <TravellyField label="Distance in km (optional)" help="Roughly how far from the first to the last stop."><input type="number" min="0" step="0.1" value={distance} onChange={e=>setDistance(e.target.value)}/></TravellyField>
      </div>
      {times[times.length-1]>0&&<p>Whole trip: about {duration(times[times.length-1])}.</p>}
      {timeProblem&&<p role="alert">Each stop’s time from start must be the same as or later than the stop before it.</p>}
      {missingPlace&&<p>Find a place for every stop before saving.</p>}
      <div style={{display:'flex',gap:8}}>
        <button className="button" disabled={busy||timeProblem||missingPlace}>{busy?'Saving…':editing?'Save changes':'Save route'}</button>
        {editing&&<button type="button" className="button outline" onClick={onCancel}>Cancel</button>}
      </div>
    </form>
  </TravellyGlassPanel>
}

function RouteCard({route,onEdit,onChanged,setError}){
  const [busy,setBusy]=useState(false)
  async function toggle(){
    setBusy(true);setError(null)
    try{const saved=await api(`/owners/me/routes/${route.id}/status`,{method:'PATCH',body:JSON.stringify({expected_version:route.version,active:route.status!=='ACTIVE'})})
      onChanged(saved.status==='ACTIVE'?'Route turned on.':'Route turned off. New departures cannot use it.')}
    catch(problem){setError(problem)}finally{setBusy(false)}
  }
  return <article className="travelly-vehicle-card"><div>
    <h3>{route.route_name}</h3>
    <p>{route.stops.map(s=>s.stop_name).join(' → ')}</p>
    <p>{route.stops.length} stops{route.estimated_duration_minutes?` · about ${duration(route.estimated_duration_minutes)}`:''}{route.estimated_distance_km?` · ${Number(route.estimated_distance_km)} km`:''}</p>
    <TravellyStatusChip tone={route.status==='ACTIVE'?'success':'warning'}>{route.status==='ACTIVE'?'On':route.deactivated_by_admin?'Turned off by Travelly':'Off'}</TravellyStatusChip>
  </div>
  {route.mine&&<div style={{display:'flex',gap:8,flexWrap:'wrap'}}>
    <button type="button" className="button outline" onClick={onEdit}>Edit</button>
    {!route.deactivated_by_admin&&<button type="button" className="button outline" disabled={busy} onClick={toggle}>{route.status==='ACTIVE'?'Turn off':'Turn on'}</button>}
  </div>}
  </article>
}

export default function OwnerRoutes(){
  const [routes,setRoutes]=useState(null),[error,setError]=useState(null),[notice,setNotice]=useState(''),[editing,setEditing]=useState(null),[formKey,setFormKey]=useState(0)
  const load=()=>api('/owners/me/routes').then(x=>setRoutes(x.items||[])).catch(setError)
  useEffect(()=>{load()},[])
  useEffect(()=>{if(!notice)return;const timer=setTimeout(()=>setNotice(''),8000);return ()=>clearTimeout(timer)},[notice])
  function done(message){setNotice(message);setEditing(null);setFormKey(k=>k+1);load();window.scrollTo({top:0,behavior:'smooth'})}
  const mine=(routes||[]).filter(r=>r.mine),shared=(routes||[]).filter(r=>!r.mine)
  return <><Header/><main className="role-dashboard" id="main">
    <div className="workspace-heading"><div><p className="section-kicker">OWNER · TICKET TRIPS</p><h1>My routes</h1>
      <p>The roads you run Ticket trips on. Passengers choose where they get on and off from your stops. <Link to="/owner/ticket-departures">Go to Ticket departures</Link></p></div></div>
    {notice&&<p role="status" style={{background:'#e6f7ec',color:'#0b5d2a',border:'1px solid #7bcf9b',borderRadius:10,padding:'12px 16px',fontWeight:600}}>✓ {notice}</p>}
    <ErrorNotice error={error}/>
    <RouteForm key={editing?`edit-${editing.id}-${editing.version}`:`new-${formKey}`} editing={editing} onSaved={(_,message)=>done(message)} onCancel={()=>setEditing(null)}/>
    <TravellyGlassPanel><h2>Your routes</h2>
      {routes===null?<TravellyState kind="loading" title="Loading routes"/>:mine.length
        ?mine.map(r=><RouteCard key={`${r.id}-${r.version}`} route={r} setError={setError} onChanged={done} onEdit={()=>{setEditing(r);window.scrollTo({top:0,behavior:'smooth'})}}/>)
        :<TravellyState title="No routes yet">Add your first route above.</TravellyState>}
    </TravellyGlassPanel>
    {shared.length>0&&<TravellyGlassPanel><h2>Travelly routes you can also use</h2>
      {shared.map(r=><RouteCard key={r.id} route={r} setError={setError} onChanged={done} onEdit={()=>{}}/>)}</TravellyGlassPanel>}
  </main></>
}
