import React,{useEffect,useMemo,useState} from 'react'
import {Link} from 'react-router-dom'
import {api,publicRead} from '../../services/api'
import {Header,ErrorNotice} from '../../components/components'
import {TravellyGlassPanel,TravellyState,TravellyStatusChip} from '../../components/TravellyVisualFoundation'
import SeatMap from '../../components/SeatMap'

const emptyDeparture={route_id:'',vehicle_id:'',departure_at:'',estimated_arrival_at:'',arrival_auto:true,stop_before:'60',fare_per_seat:'',
  fulfilment_policy:'FIXED_GUARANTEED',minimum_confirmed_seats:'',decision_deadline:'',accepted_time_window_minutes:'0',operator_driver_user_id:''}
const iso=v=>v?new Date(v).toISOString():null
const pad=n=>String(n).padStart(2,'0')
const toLocal=d=>`${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
const STOP_OPTIONS=[['30','30 minutes before departure'],['60','1 hour before departure'],['120','2 hours before departure']]
const nice=v=>v?new Date(v).toLocaleString([],{weekday:'short',day:'numeric',month:'short',hour:'numeric',minute:'2-digit'}):''

// A date picker and a time picker side by side, each with a clear label and a calendar/clock that opens on click.
function DateTimeField({label,value,onChange,hint,min}){
  const [time,setTime]=useState('')
  const date=value?value.slice(0,10):'',clock=value?value.slice(11,16):time
  const open=e=>{try{e.target.showPicker&&e.target.showPicker()}catch{}}
  const change=(d,t)=>{setTime(t);onChange(d?`${d}T${t||'08:00'}`:'')}
  return <fieldset className="dt-field"><legend>{label}</legend>
    <div className="dt-row">
      <label>Date<input required type="date" value={date} min={min} onClick={open} onChange={e=>change(e.target.value,clock)}/></label>
      <label>Time<input required type="time" value={clock} onClick={open} onChange={e=>change(date,e.target.value)}/></label>
    </div>{hint&&<small>{hint}</small>}</fieldset>
}

// Vehicle types the Owner can start from, then adjust with the + / - buttons.
const PRESETS={
  van:{label:'Van (14 seats)',left:2,right:1,rows:3,back:4,front:1,sellFront:true},
  bus22:{label:'Bus 2+2',left:2,right:2,rows:10,back:0,front:1,sellFront:false},
  bus23:{label:'Bus 2+3',left:2,right:3,rows:8,back:0,front:1,sellFront:false},
  custom:{label:'Custom',left:2,right:1,rows:4,back:0,front:1,sellFront:false},
}
// Top-down picture. Row 0: front passenger seat on the left, Driver seat on the right (Sri Lanka drives on the left).
// Seats are numbered automatically from the front, left to right; the Driver seat has no number and is never sold.
function buildSeats({left,right,rows,back,front,sellFront,off}){
  const width=left+1+right,seats=[];let n=0
  const add=(row,column,sold)=>{n+=1;seats.push({code:String(n),row,column,deck:1,type:'STANDARD',bookable:sold&&!off.has(`${row}-${column}`)})}
  if(front)add(0,0,sellFront)
  seats.push({code:'DRV',row:0,column:width-1,deck:1,type:'CREW',bookable:false})
  for(let r=1;r<=rows;r++){
    for(let c=0;c<left;c++)add(r,c,true)
    for(let c=0;c<right;c++)add(r,left+1+c,true)
  }
  if(back>0){
    const cols=back>=width?[...Array(width).keys()]:[...Array(width).keys()].filter(c=>c!==left).slice(0,back)
    cols.forEach(c=>add(rows+1,c,true))
  }
  return seats
}

function Stepper({label,value,min,max,onChange,hint}){
  return <div className="stepper"><span className="stepper-label" id={`st-${label}`}>{label}</span>
    <button type="button" className="button" aria-label={`Fewer: ${label}`} disabled={value<=min} onClick={()=>onChange(value-1)}>−</button>
    <output aria-labelledby={`st-${label}`}>{value}</output>
    <button type="button" className="button" aria-label={`More: ${label}`} disabled={value>=max} onClick={()=>onChange(value+1)}>+</button>
    {hint&&<span className="layout-help">{hint}</span>}</div>
}

export default function OwnerTicketDepartures(){
  const [vehicles,setVehicles]=useState([]),[routes,setRoutes]=useState([]),[items,setItems]=useState(null),[error,setError]=useState(null),[busy,setBusy]=useState(false)
  const [layoutVehicle,setLayoutVehicle]=useState(''),[saved,setSaved]=useState(null)
  const [preset,setPreset]=useState('van'),[left,setLeft]=useState(2),[right,setRight]=useState(1),[rowCount,setRowCount]=useState(3),[back,setBack]=useState(4),[front,setFront]=useState(1),[sellFront,setSellFront]=useState(true),[off,setOff]=useState(new Set())
  const [form,setForm]=useState(emptyDeparture),[notice,setNotice]=useState('')
  const loadDepartures=()=>api('/scheduled-trips?mine=true&limit=100').then(x=>setItems(x.items||[])).catch(setError)
  useEffect(()=>{
    api('/owners/me/vehicles').then(x=>setVehicles((x.items||[]).filter(v=>v.verification_status==='APPROVED'))).catch(setError)
    api('/owners/me/routes').then(x=>setRoutes((x.items||[]).filter(r=>r.status==='ACTIVE'))).catch(setError)
    loadDepartures()
  },[])
  const vehicle=vehicles.find(v=>v.id===layoutVehicle)
  useEffect(()=>{setSaved(null);if(!layoutVehicle)return
    api(`/vehicles/${layoutVehicle}/seat-layout`).then(setSaved).catch(e=>{if(e.status!==404)setError(e)})},[layoutVehicle])
  const seats=useMemo(()=>buildSeats({left,right,rows:rowCount,back,front,sellFront,off}),[left,right,rowCount,back,front,sellFront,off])
  const sold=seats.filter(s=>s.bookable).length
  const capacity=vehicle?.seat_capacity
  const overCapacity=capacity!=null&&sold>capacity
  const pick=key=>{const p=PRESETS[key];setPreset(key);setLeft(p.left);setRight(p.right);setRowCount(p.rows);setBack(p.back);setFront(p.front);setSellFront(p.sellFront);setOff(new Set())}
  const adjust=setter=>v=>{setter(v);setOff(new Set())}
  const width=left+1+right
  const toggle=s=>{if(s.type==='CREW')return;const key=`${s.row}-${s.column}`;const next=new Set(off);next.has(key)?next.delete(key):next.add(key);setOff(next)}

  async function saveLayout(){
    setBusy(true);setError(null);setNotice('')
    try{
      const result=await api(`/vehicles/${layoutVehicle}/seat-layout`,{method:'PUT',body:JSON.stringify({layout_version:(saved?.layout_version||0)+1,seats:seats.map(s=>({code:s.code,row:s.row,column:s.column,deck:s.deck,type:s.type,bookable:s.bookable}))})})
      setSaved(result);setNotice('Seat layout saved. Passengers will see this picture.')
    }catch(e){setError(e)}finally{setBusy(false)}
  }
  async function createDeparture(e){
    e.preventDefault();setBusy(true);setError(null);setNotice('')
    const protectedPolicy=form.fulfilment_policy!=='FIXED_GUARANTEED'
    const departure=new Date(form.departure_at),arrival=new Date(form.estimated_arrival_at)
    if(!(departure>new Date())){setBusy(false);setError({message:'Choose a departure date and time in the future.'});return}
    if(!(arrival>departure)){setBusy(false);setError({message:'The arrival must be after the departure.'});return}
    const cutoff=new Date(departure.getTime()-Number(form.stop_before)*60000)
    if(cutoff<=new Date()){setBusy(false);setError({message:'Bookings would already be closed. Choose a later departure or a shorter "Stop bookings at" time.'});return}
    const cutoffIso=cutoff.toISOString()
    try{
      await api('/scheduled-trips',{method:'POST',body:JSON.stringify({
        route_id:form.route_id,vehicle_id:form.vehicle_id,departure_at:iso(form.departure_at),estimated_arrival_at:iso(form.estimated_arrival_at),
        booking_cutoff_at:cutoffIso,fare_per_seat:String(form.fare_per_seat),fulfilment_policy:form.fulfilment_policy,
        minimum_confirmed_seats:protectedPolicy?Number(form.minimum_confirmed_seats):null,decision_deadline:protectedPolicy?iso(form.decision_deadline):null,
        accepted_time_window_minutes:Number(form.accepted_time_window_minutes||0),accepted_replacement_terms:{},
        operator_driver_user_id:form.operator_driver_user_id||null})})
      setForm(emptyDeparture);setNotice('Departure saved as a draft. Press Publish below when you are ready.');loadDepartures();window.scrollTo({top:document.body.scrollHeight,behavior:'smooth'})
    }catch(e){setError(e)}finally{setBusy(false)}
  }
  async function publish(x){
    setError(null);setNotice('')
    try{await api(`/scheduled-trips/${x.id}/publish`,{method:'POST',body:JSON.stringify({expected_version:x.version,publish_confirmed:true})});setNotice('Departure published. Passengers can now book it.');loadDepartures()}catch(e){setError(e)}
  }
  const set=k=>e=>setForm({...form,[k]:e.target.value})
  // A route with a price for each stop fixes the whole-trip price to its last stop's price.
  const chosenRoute=routes.find(r=>r.id===form.route_id)
  const routeWhole=chosenRoute?.stop_prices_enabled?chosenRoute.stops[chosenRoute.stops.length-1]?.price_from_start:null
  useEffect(()=>{if(routeWhole!=null&&form.fare_per_seat!==String(Number(routeWhole)))setForm(f=>({...f,fare_per_seat:String(Number(routeWhole))}))},[routeWhole])
  const protectedPolicy=form.fulfilment_policy!=='FIXED_GUARANTEED'

  return <><Header/><main className="role-dashboard" id="main">
    <div className="workspace-heading"><p className="section-kicker">OWNER · FLEET SERVICES</p><h1>Ticket departures</h1>
      <p>Describe each vehicle&apos;s seats once, then publish scheduled departures. Passengers see exactly the seats you define.</p></div>
    <ErrorNotice error={error}/>{notice&&<p role="status" className="success-banner">✓ {notice}</p>}

    <TravellyGlassPanel><h2>1. Vehicle seat layout</h2>
      <label htmlFor="seat-vehicle">Vehicle</label><select id="seat-vehicle" value={layoutVehicle} onChange={e=>{setLayoutVehicle(e.target.value);setOff(new Set())}}>
        <option value="">Choose an approved vehicle</option>
        {vehicles.map(v=><option key={v.id} value={v.id}>{v.label||v.reference} · {v.seat_capacity??'?'} seats</option>)}
      </select>
      {layoutVehicle&&<>
        {saved&&<><p>Current saved layout: version {saved.layout_version}, {saved.seats.filter(s=>s.bookable).length} bookable seats. Saving below replaces it with a new version.</p></>}
        <div className="layout-builder">
          <div><strong>1. Choose your vehicle type</strong>
            <div className="layout-presets" role="group" aria-label="Vehicle type">
              {Object.entries(PRESETS).map(([k,p])=><button type="button" key={k} className="button" aria-pressed={preset===k} onClick={()=>pick(k)}>{p.label}</button>)}</div></div>
          <div><strong>2. Adjust with + and −</strong>
            <div className="stepper-row">
              <Stepper label="Rows of seats" value={rowCount} min={1} max={24} onChange={adjust(setRowCount)}/>
              <Stepper label="Seats on the left" value={left} min={1} max={4} onChange={adjust(setLeft)} hint="(door side)"/>
              <Stepper label="Seats on the right" value={right} min={1} max={4} onChange={adjust(setRight)}/>
              <Stepper label="Seats in the back row" value={back} min={0} max={width} onChange={adjust(setBack)} hint={back===0?'(no back row)':''}/>
            </div>
            <div className="layout-row">
              <label><input type="checkbox" checked={front===1} onChange={e=>{setFront(e.target.checked?1:0);setOff(new Set())}}/> Seat beside the Driver</label>
              {front===1&&<label><input type="checkbox" checked={sellFront} onChange={e=>setSellFront(e.target.checked)}/> Sell the seat beside the Driver</label>}
            </div></div>
          <p className="layout-help"><strong>3.</strong> Tap a seat in the picture to mark it &ldquo;Not for sale&rdquo; (grey). Tap again to sell it. The Driver seat (steering wheel) is never sold. Seats are numbered for you.</p>
        </div>
        <SeatMap seats={seats} editable onToggle={toggle} label="New seat layout preview"/>
        <p>Bookable seats: <strong>{sold}</strong>{capacity!=null&&<> of vehicle capacity {capacity}</>} {overCapacity&&<TravellyStatusChip tone="warning">More than the vehicle capacity</TravellyStatusChip>}</p>
        <button className="button" disabled={busy||!sold||overCapacity} onClick={saveLayout}>{busy?'Saving…':'Save seat layout'}</button>
      </>}
    </TravellyGlassPanel>

    <TravellyGlassPanel><h2>2. Create a departure draft</h2>
      <form className="passenger-detail-grid" onSubmit={createDeparture}>
        <label>Route
          <select required value={form.route_id} onChange={e=>setForm({...form,route_id:e.target.value})}><option value="">Choose a route</option>{routes.map(r=><option key={r.id} value={r.id}>{r.origin_name} → {r.destination_name}</option>)}</select></label>
        {routes.length===0&&<p>You have no routes yet. <Link to="/owner/routes">Add a route</Link> first.</p>}
        <label>Vehicle
          <select required value={form.vehicle_id} onChange={set('vehicle_id')}><option value="">Choose a vehicle</option>{vehicles.map(v=><option key={v.id} value={v.id}>{v.label||v.reference}</option>)}</select></label>
        <DateTimeField label="Departure (when the vehicle leaves)" value={form.departure_at} min={toLocal(new Date()).slice(0,10)} onChange={v=>{
          const mins=chosenRoute?.estimated_duration_minutes
          setForm(f=>({...f,departure_at:v,...(f.arrival_auto&&v&&mins?{estimated_arrival_at:toLocal(new Date(new Date(v).getTime()+mins*60000))}:{})}))}}/>
        <DateTimeField label="Estimated arrival (when it reaches the end)" value={form.estimated_arrival_at} min={form.departure_at?form.departure_at.slice(0,10):undefined}
          hint={chosenRoute?.estimated_duration_minutes?'Filled in from the route duration. You can change it.':''} onChange={v=>setForm(f=>({...f,estimated_arrival_at:v,arrival_auto:false}))}/>
        <label>Stop bookings at
          <select value={form.stop_before} onChange={set('stop_before')}>{STOP_OPTIONS.map(([v,t])=><option key={v} value={v}>{t}</option>)}</select>
          <small>{form.departure_at?`Passengers can book until ${nice(new Date(new Date(form.departure_at).getTime()-Number(form.stop_before)*60000))}.`:'Passengers cannot book after this time.'}</small></label>
        <label>Price for the whole trip, per seat (LKR)
          <input required min="0" step="0.01" type="number" value={form.fare_per_seat} disabled={routeWhole!=null} onChange={set('fare_per_seat')}/>
          {routeWhole!=null&&<small> This route has a price for each stop, so the whole-trip price comes from the route. Passengers who travel part of the way pay less.</small>}</label>
        <label>Departure type
          <select value={form.fulfilment_policy} onChange={set('fulfilment_policy')}>
            <option value="FIXED_GUARANTEED">Fixed, guaranteed departure</option>
            <option value="MINIMUM_SEATS_WITH_PROTECTED_FULFILMENT">Minimum seats with protected fulfilment</option></select>
          <small>{protectedPolicy?'The departure is confirmed only when enough seats are booked.':'The departure runs on the day whatever the number of bookings.'}</small></label>
        {protectedPolicy&&<><label>Minimum confirmed seats
            <input required min="1" type="number" value={form.minimum_confirmed_seats} onChange={set('minimum_confirmed_seats')}/>
            <small>How many seats must be booked for this departure to be confirmed.</small></label>
          <DateTimeField label="Decision deadline (you decide by this time)" value={form.decision_deadline} min={toLocal(new Date()).slice(0,10)} onChange={v=>setForm(f=>({...f,decision_deadline:v}))}/></>}
        <label>Accepted time window (minutes)
          <input min="0" max="1440" type="number" value={form.accepted_time_window_minutes} onChange={set('accepted_time_window_minutes')}/>
          <small>Leave 0 if the departure time is fixed.</small></label>
        <label>Driver user ID
          <input value={form.operator_driver_user_id} onChange={set('operator_driver_user_id')}/>
          <small>Leave empty if you drive this vehicle yourself.</small></label>
        <button className="button" disabled={busy}>{busy?'Saving…':'Save draft'}</button>
      </form></TravellyGlassPanel>

    <TravellyGlassPanel><h2>3. Your departures</h2>
      {items===null?<TravellyState kind="loading" title="Loading departures"/>:items.length?items.map(x=>
        <article className="travelly-vehicle-card" key={x.id}><div>
          <h3>{x.route.origin_name} → {x.route.destination_name}</h3>
          <p>{new Date(x.departure_at).toLocaleString()} · {x.vehicle.make} {x.vehicle.model} · LKR {x.fare_per_seat} per seat{x.available_seats!=null&&` · ${x.available_seats} seats open`}</p>
          <TravellyStatusChip tone={x.status==='PUBLISHED'?'success':'warning'}>{x.status}</TravellyStatusChip></div>
          {x.status==='DRAFT'&&<button className="button" onClick={()=>publish(x)}>Publish</button>}</article>)
        :<TravellyState title="No ticket departures">Save a seat layout, then create a draft departure.</TravellyState>}
    </TravellyGlassPanel>
  </main></>
}
