import React,{useEffect,useMemo,useState} from 'react'
import {api,publicRead} from '../../services/api'
import {Header,ErrorNotice} from '../../components/components'
import {TravellyGlassPanel,TravellyState,TravellyStatusChip} from '../../components/TravellyVisualFoundation'
import SeatMap from '../../components/SeatMap'

const emptyDeparture={route_id:'',vehicle_id:'',departure_at:'',estimated_arrival_at:'',booking_cutoff_at:'',fare_per_seat:'',
  fulfilment_policy:'FIXED_GUARANTEED',minimum_confirmed_seats:'',decision_deadline:'',accepted_time_window_minutes:'0',operator_driver_user_id:''}
const iso=v=>v?new Date(v).toISOString():null

// The Owner describes the layout; nothing here assumes a vehicle type.
// Front row: optional front passenger seats on the left, the Driver seat on the right (never sold).
function buildSeats({frontSeats,sellFront,rows,off}){
  const width=Math.max(frontSeats+1,...rows.map(r=>r.count+(r.aisleAfter>0&&r.aisleAfter<r.count?1:0)))
  const seats=[]
  for(let j=0;j<frontSeats;j++){const code=`F${j+1}`;seats.push({code,row:0,column:j,deck:1,type:'STANDARD',bookable:sellFront&&!off.has(code)})}
  seats.push({code:'DRV',row:0,column:width-1,deck:1,type:'CREW',bookable:false})
  rows.forEach((r,i)=>{for(let j=1;j<=r.count;j++){const code=`${String.fromCharCode(64+i+1)}${j}`
    seats.push({code,row:i+1,column:j-1+(r.aisleAfter>0&&j>r.aisleAfter?1:0),deck:1,type:'STANDARD',bookable:!off.has(code)})}})
  return seats
}

export default function OwnerTicketDepartures(){
  const [vehicles,setVehicles]=useState([]),[routes,setRoutes]=useState([]),[items,setItems]=useState(null),[error,setError]=useState(null),[busy,setBusy]=useState(false)
  const [layoutVehicle,setLayoutVehicle]=useState(''),[saved,setSaved]=useState(null)
  const [frontSeats,setFrontSeats]=useState(1),[sellFront,setSellFront]=useState(false),[rows,setRows]=useState([{count:3,aisleAfter:0}]),[off,setOff]=useState(new Set())
  const [form,setForm]=useState(emptyDeparture),[notice,setNotice]=useState('')
  const loadDepartures=()=>api('/scheduled-trips?mine=true&limit=100').then(x=>setItems(x.items||[])).catch(setError)
  useEffect(()=>{
    api('/owners/me/vehicles').then(x=>setVehicles((x.items||[]).filter(v=>v.verification_status==='APPROVED'))).catch(setError)
    publicRead('/routes?limit=100').then(x=>setRoutes(x.items||[])).catch(setError)
    loadDepartures()
  },[])
  const vehicle=vehicles.find(v=>v.id===layoutVehicle)
  useEffect(()=>{setSaved(null);if(!layoutVehicle)return
    api(`/vehicles/${layoutVehicle}/seat-layout`).then(setSaved).catch(e=>{if(e.status!==404)setError(e)})},[layoutVehicle])
  const seats=useMemo(()=>buildSeats({frontSeats,sellFront,rows,off}),[frontSeats,sellFront,rows,off])
  const sold=seats.filter(s=>s.bookable).length
  const capacity=vehicle?.seat_capacity
  const overCapacity=capacity!=null&&sold>capacity
  const setRow=(i,patch)=>setRows(rows.map((r,k)=>k===i?{...r,...patch}:r))
  const toggle=s=>{if(s.type==='CREW')return;const next=new Set(off);next.has(s.code)?next.delete(s.code):next.add(s.code);setOff(next)}

  async function saveLayout(){
    setBusy(true);setError(null);setNotice('')
    try{
      const result=await api(`/vehicles/${layoutVehicle}/seat-layout`,{method:'PUT',body:JSON.stringify({layout_version:(saved?.layout_version||0)+1,seats:seats.map(s=>({code:s.code,row:s.row,column:s.column,deck:s.deck,type:s.type,bookable:s.bookable}))})})
      setSaved(result);setNotice('Seat layout saved.')
    }catch(e){setError(e)}finally{setBusy(false)}
  }
  async function createDeparture(e){
    e.preventDefault();setBusy(true);setError(null);setNotice('')
    const protectedPolicy=form.fulfilment_policy!=='FIXED_GUARANTEED'
    try{
      await api('/scheduled-trips',{method:'POST',body:JSON.stringify({
        route_id:form.route_id,vehicle_id:form.vehicle_id,departure_at:iso(form.departure_at),estimated_arrival_at:iso(form.estimated_arrival_at),
        booking_cutoff_at:iso(form.booking_cutoff_at),fare_per_seat:String(form.fare_per_seat),fulfilment_policy:form.fulfilment_policy,
        minimum_confirmed_seats:protectedPolicy?Number(form.minimum_confirmed_seats):null,decision_deadline:protectedPolicy?iso(form.decision_deadline):null,
        accepted_time_window_minutes:Number(form.accepted_time_window_minutes||0),accepted_replacement_terms:{},
        operator_driver_user_id:form.operator_driver_user_id||null})})
      setForm(emptyDeparture);setNotice('Draft departure saved.');loadDepartures()
    }catch(e){setError(e)}finally{setBusy(false)}
  }
  async function publish(x){
    setError(null);setNotice('')
    try{await api(`/scheduled-trips/${x.id}/publish`,{method:'POST',body:JSON.stringify({expected_version:x.version,publish_confirmed:true})});setNotice('Departure published.');loadDepartures()}catch(e){setError(e)}
  }
  const set=k=>e=>setForm({...form,[k]:e.target.value})
  const protectedPolicy=form.fulfilment_policy!=='FIXED_GUARANTEED'

  return <><Header/><main className="role-dashboard" id="main">
    <div className="workspace-heading"><p className="section-kicker">OWNER · FLEET SERVICES</p><h1>Ticket departures</h1>
      <p>Describe each vehicle&apos;s seats once, then publish scheduled departures. Passengers see exactly the seats you define.</p></div>
    <ErrorNotice error={error}/>{notice&&<p role="status">{notice}</p>}

    <TravellyGlassPanel><h2>1. Vehicle seat layout</h2>
      <select value={layoutVehicle} onChange={e=>{setLayoutVehicle(e.target.value);setOff(new Set())}} aria-label="Vehicle">
        <option value="">Choose an approved vehicle</option>
        {vehicles.map(v=><option key={v.id} value={v.id}>{v.label||v.reference} · {v.seat_capacity??'?'} seats</option>)}
      </select>
      {layoutVehicle&&<>
        {saved&&<><p>Current saved layout: version {saved.layout_version}, {saved.seats.filter(s=>s.bookable).length} bookable seats. Saving below replaces it with a new version.</p>
          <SeatMap seats={saved.seats} label="Saved seat layout"/></>}
        <div className="layout-rows">
          <div className="layout-row"><label>Front passenger seats (beside the Driver) <input type="number" min="0" max="2" value={frontSeats} onChange={e=>setFrontSeats(Math.min(2,Math.max(0,Number(e.target.value)||0)))}/></label>
            <label><input type="checkbox" checked={sellFront} onChange={e=>setSellFront(e.target.checked)}/> Sell front passenger seats</label></div>
          {rows.map((r,i)=><div className="layout-row" key={i}><strong>Row {String.fromCharCode(65+i)}</strong>
            <label>Seats <input type="number" min="1" max="8" value={r.count} onChange={e=>setRow(i,{count:Math.min(8,Math.max(1,Number(e.target.value)||1))})}/></label>
            <label>Aisle after seat (0 = none) <input type="number" min="0" max={Math.max(0,r.count-1)} value={r.aisleAfter} onChange={e=>setRow(i,{aisleAfter:Math.min(Math.max(0,r.count-1),Math.max(0,Number(e.target.value)||0))})}/></label>
            {rows.length>1&&<button type="button" className="button" onClick={()=>setRows(rows.filter((_,k)=>k!==i))}>Remove row</button>}</div>)}
          <div><button type="button" className="button" disabled={rows.length>=25} onClick={()=>setRows([...rows,{count:rows.at(-1)?.count||3,aisleAfter:0}])}>Add row</button></div>
        </div>
        <p>Preview. Select a seat to switch it between sold and not sold. The Driver seat is never sold.</p>
        <SeatMap seats={seats} editable onToggle={toggle} label="New seat layout preview"/>
        <p>Bookable seats: <strong>{sold}</strong>{capacity!=null&&<> of vehicle capacity {capacity}</>} {overCapacity&&<TravellyStatusChip tone="warning">More than the vehicle capacity</TravellyStatusChip>}</p>
        <button className="button" disabled={busy||!sold||overCapacity} onClick={saveLayout}>{busy?'Saving…':'Save seat layout'}</button>
      </>}
    </TravellyGlassPanel>

    <TravellyGlassPanel><h2>2. Create a departure draft</h2>
      <form className="passenger-detail-grid" onSubmit={createDeparture}>
        <select required value={form.route_id} onChange={set('route_id')} aria-label="Route"><option value="">Choose a route</option>{routes.map(r=><option key={r.id} value={r.id}>{r.route_name} ({r.origin_name} → {r.destination_name})</option>)}</select>
        <select required value={form.vehicle_id} onChange={set('vehicle_id')} aria-label="Vehicle"><option value="">Choose a vehicle</option>{vehicles.map(v=><option key={v.id} value={v.id}>{v.label||v.reference}</option>)}</select>
        <label>Departure <input required type="datetime-local" value={form.departure_at} onChange={set('departure_at')}/></label>
        <label>Estimated arrival <input required type="datetime-local" value={form.estimated_arrival_at} onChange={set('estimated_arrival_at')}/></label>
        <label>Booking cut-off <input required type="datetime-local" value={form.booking_cutoff_at} onChange={set('booking_cutoff_at')}/></label>
        <input required min="0" step="0.01" type="number" placeholder="Fare per seat (LKR)" value={form.fare_per_seat} onChange={set('fare_per_seat')}/>
        <select value={form.fulfilment_policy} onChange={set('fulfilment_policy')} aria-label="Fulfilment policy">
          <option value="FIXED_GUARANTEED">Fixed, guaranteed departure</option>
          <option value="MINIMUM_SEATS_WITH_PROTECTED_FULFILMENT">Minimum seats with protected fulfilment</option></select>
        {protectedPolicy&&<><input required min="1" type="number" placeholder="Minimum confirmed seats" value={form.minimum_confirmed_seats} onChange={set('minimum_confirmed_seats')}/>
          <label>Decision deadline <input required type="datetime-local" value={form.decision_deadline} onChange={set('decision_deadline')}/></label></>}
        <input min="0" max="1440" type="number" placeholder="Accepted time window (minutes)" value={form.accepted_time_window_minutes} onChange={set('accepted_time_window_minutes')}/>
        <input placeholder="Driver user ID (blank if you drive)" value={form.operator_driver_user_id} onChange={set('operator_driver_user_id')}/>
        <button className="button" disabled={busy}>{busy?'Saving…':'Save draft'}</button>
      </form></TravellyGlassPanel>

    <TravellyGlassPanel><h2>3. Your departures</h2>
      {items===null?<TravellyState kind="loading" title="Loading departures"/>:items.length?items.map(x=>
        <article className="travelly-vehicle-card" key={x.id}><div>
          <h3>{x.route.route_name}</h3>
          <p>{new Date(x.departure_at).toLocaleString()} · {x.vehicle.make} {x.vehicle.model} · LKR {x.fare_per_seat} per seat{x.available_seats!=null&&` · ${x.available_seats} seats open`}</p>
          <TravellyStatusChip tone={x.status==='PUBLISHED'?'success':'warning'}>{x.status}</TravellyStatusChip></div>
          {x.status==='DRAFT'&&<button className="button" onClick={()=>publish(x)}>Publish</button>}</article>)
        :<TravellyState title="No ticket departures">Save a seat layout, then create a draft departure.</TravellyState>}
    </TravellyGlassPanel>
  </main></>
}
