import React,{useEffect,useState} from 'react'
import {Link} from 'react-router-dom'
import {api} from '../../services/api'
import {Header,ErrorNotice} from '../../components/components'
import {TravellyGlassPanel,TravellyState,TravellyStatusChip} from '../../components/TravellyVisualFoundation'

const blankStop=()=>({stop_name:'',latitude:'',longitude:'',pickup_allowed:true,dropoff_allowed:true,scheduled_offset_minutes:'0'})
const blankRoute=()=>({route_code:'',route_name:'',origin_name:'',destination_name:'',estimated_distance_km:'',estimated_duration_minutes:'',active:true})
const num=v=>v===''||v==null?null:String(v)

export default function AdminRoutes(){
  const [form,setForm]=useState(blankRoute()),[stops,setStops]=useState([blankStop(),blankStop()]),[routes,setRoutes]=useState(null),[error,setError]=useState(null),[busy,setBusy]=useState(false),[notice,setNotice]=useState('')
  const load=()=>api('/admin/routes').then(x=>setRoutes(x.items||[])).catch(setError)
  useEffect(()=>{load()},[])
  const setStop=(i,patch)=>setStops(stops.map((s,k)=>k===i?{...s,...patch}:s))
  async function create(e){
    e.preventDefault();setBusy(true);setError(null);setNotice('')
    try{
      const created=await api('/admin/routes',{method:'POST',body:JSON.stringify({
        route_code:form.route_code.trim(),route_name:form.route_name,origin_name:form.origin_name,destination_name:form.destination_name,
        estimated_distance_km:num(form.estimated_distance_km),estimated_duration_minutes:form.estimated_duration_minutes===''?null:Number(form.estimated_duration_minutes),
        active:form.active,
        stops:stops.map(s=>({stop_name:s.stop_name,latitude:String(s.latitude),longitude:String(s.longitude),pickup_allowed:s.pickup_allowed,dropoff_allowed:s.dropoff_allowed,scheduled_offset_minutes:Number(s.scheduled_offset_minutes||0)}))})})
      setNotice(`Route ${created.route_code} saved as ${created.status}.`);setForm(blankRoute());setStops([blankStop(),blankStop()]);load()
    }catch(problem){setError(problem)}finally{setBusy(false)}
  }
  async function toggle(r){
    setError(null);setNotice('')
    try{const saved=await api(`/admin/routes/${r.id}`,{method:'PATCH',body:JSON.stringify({expected_version:r.version,status:r.status==='ACTIVE'?'INACTIVE':'ACTIVE'})})
      setNotice(saved.status==='ACTIVE'?`${saved.route_name} turned on.`:`${saved.route_name} turned off. The Owner cannot turn it back on.`);load();window.scrollTo({top:0,behavior:'smooth'})}
    catch(problem){setError(problem)}
  }
  return <><Header/><main className="role-dashboard" id="main">
    <div className="workspace-heading"><p className="section-kicker">ADMIN · SERVICES &amp; ROUTES</p><h1>Ticket routes</h1>
      <p>Owners add their own routes; you only need to turn off a wrong or abusive route. You can also add a Travelly route every Owner can use. <Link to="/admin/services-routes">Back to service catalogue</Link></p></div>
    <ErrorNotice error={error}/>{notice&&<p role="status" style={{background:'#e6f7ec',color:'#0b5d2a',border:'1px solid #7bcf9b',borderRadius:10,padding:'12px 16px',fontWeight:600}}>✓ {notice}</p>}
    <TravellyGlassPanel><h2>Create a route</h2>
      <form className="passenger-detail-grid" onSubmit={create}>
        <input required maxLength="30" placeholder="Route code (e.g. COL-KDY)" value={form.route_code} onChange={e=>setForm({...form,route_code:e.target.value})}/>
        <input required maxLength="150" placeholder="Route name" value={form.route_name} onChange={e=>setForm({...form,route_name:e.target.value})}/>
        <input required maxLength="150" placeholder="Origin" value={form.origin_name} onChange={e=>setForm({...form,origin_name:e.target.value})}/>
        <input required maxLength="150" placeholder="Destination" value={form.destination_name} onChange={e=>setForm({...form,destination_name:e.target.value})}/>
        <input min="0" step="0.001" type="number" placeholder="Distance (km, optional)" value={form.estimated_distance_km} onChange={e=>setForm({...form,estimated_distance_km:e.target.value})}/>
        <input min="0" type="number" placeholder="Duration (minutes, optional)" value={form.estimated_duration_minutes} onChange={e=>setForm({...form,estimated_duration_minutes:e.target.value})}/>
        <label><input type="checkbox" checked={form.active} onChange={e=>setForm({...form,active:e.target.checked})}/> Make the route available to Owners now</label>
        <h3>Stops, in travel order</h3>
        {stops.map((s,i)=><div className="layout-row" key={i}>
          <strong>{i+1}</strong>
          <input required maxLength="150" placeholder="Stop name" value={s.stop_name} onChange={e=>setStop(i,{stop_name:e.target.value})}/>
          <input required type="number" step="0.000001" min="-90" max="90" placeholder="Latitude" value={s.latitude} onChange={e=>setStop(i,{latitude:e.target.value})}/>
          <input required type="number" step="0.000001" min="-180" max="180" placeholder="Longitude" value={s.longitude} onChange={e=>setStop(i,{longitude:e.target.value})}/>
          <input required type="number" min="0" placeholder="Minutes from start" value={s.scheduled_offset_minutes} onChange={e=>setStop(i,{scheduled_offset_minutes:e.target.value})}/>
          <label><input type="checkbox" checked={s.pickup_allowed} onChange={e=>setStop(i,{pickup_allowed:e.target.checked})}/> Pickup</label>
          <label><input type="checkbox" checked={s.dropoff_allowed} onChange={e=>setStop(i,{dropoff_allowed:e.target.checked})}/> Drop-off</label>
          {stops.length>2&&<button type="button" className="button" onClick={()=>setStops(stops.filter((_,k)=>k!==i))}>Remove</button>}
        </div>)}
        <div><button type="button" className="button" disabled={stops.length>=50} onClick={()=>setStops([...stops,blankStop()])}>Add stop</button></div>
        <p>Minutes from start must not decrease along the route. The first stop must allow pickup and the last must allow drop-off.</p>
        <button className="button" disabled={busy}>{busy?'Saving…':'Save route'}</button>
      </form></TravellyGlassPanel>
    <TravellyGlassPanel><h2>All routes</h2>
      {routes===null?<TravellyState kind="loading" title="Loading routes"/>:routes.length?routes.map(r=>
        <article className="travelly-vehicle-card" key={`${r.id}-${r.version}`}><div><h3>{r.route_name}</h3><p>{r.origin_name} → {r.destination_name} · {r.owner_user_id?'Owner route':'Travelly route'}</p><TravellyStatusChip tone={r.status==='ACTIVE'?'success':'warning'}>{r.status==='ACTIVE'?'On':'Off'}</TravellyStatusChip></div>
          {r.status!=='DRAFT'&&<button type="button" className="button outline" onClick={()=>toggle(r)}>{r.status==='ACTIVE'?'Turn off':'Turn on'}</button>}</article>)
        :<TravellyState title="No routes yet">Create the first route above.</TravellyState>}
    </TravellyGlassPanel>
  </main></>
}
