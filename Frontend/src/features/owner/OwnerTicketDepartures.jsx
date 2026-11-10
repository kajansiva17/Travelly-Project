import React,{useEffect,useMemo,useRef,useState} from 'react'
import {Link} from 'react-router-dom'
import {api} from '../../services/api'
import {Header,ErrorNotice} from '../../components/components'
import Chip from '../../components/ui/Chip'
import SeatMap from '../../components/SeatMap'
import {Field,Compact} from './OwnerRates'
import {FlowShell,useWizard,checkPane,usePaged,useRowCount} from '../booking/flow/FlowParts'
import {Notice,Empty,DateTimeFields,Counter} from '../ticketing/TicketParts'

const emptyDeparture={route_id:'',vehicle_id:'',departure_at:'',estimated_arrival_at:'',arrival_auto:true,stop_before:'60',fare_per_seat:'',
  fulfilment_policy:'FIXED_GUARANTEED',minimum_confirmed_seats:'',decision_deadline:'',accepted_time_window_minutes:'0',operator_driver_user_id:''}
const iso=v=>v?new Date(v).toISOString():null
const pad=n=>String(n).padStart(2,'0')
const toLocal=d=>`${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
const STOP_OPTIONS=[['30','30 minutes before departure'],['60','1 hour before departure'],['120','2 hours before departure']]
const nice=v=>v?new Date(v).toLocaleString([],{weekday:'short',day:'numeric',month:'short',hour:'numeric',minute:'2-digit'}):''

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

export default function OwnerTicketDepartures(){
  const [vehicles,setVehicles]=useState([]),[routes,setRoutes]=useState([]),[items,setItems]=useState(null),[error,setError]=useState(null),[busy,setBusy]=useState(false)
  const [layoutVehicle,setLayoutVehicle]=useState(''),[saved,setSaved]=useState(null)
  const [preset,setPreset]=useState('van'),[left,setLeft]=useState(2),[right,setRight]=useState(1),[rowCount,setRowCount]=useState(3),[back,setBack]=useState(4),[front,setFront]=useState(1),[sellFront,setSellFront]=useState(true),[off,setOff]=useState(new Set())
  const [form,setForm]=useState(emptyDeparture),[notice,setNotice]=useState('')
  const [tab,setTab]=useState(0),lw=useWizard(2),dw=useWizard(3),panes=[useRef(null),useRef(null),useRef(null)]
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
  async function createDeparture(){
    setBusy(true);setError(null);setNotice('')
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
      setForm(emptyDeparture);setNotice('Departure saved as a draft. Press Publish below when you are ready.');loadDepartures();dw.setStep(0);setTab(2)
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

  const departureList=usePaged(items||[],Math.max(2,useRowCount(64)))
  // Every step is checked again when the draft is saved: the first step with a problem is shown.
  const badPane=()=>panes.findIndex(p=>p.current&&[...p.current.querySelectorAll('input,select,textarea')].some(el=>!el.disabled&&!el.checkValidity()))
  function submitDeparture(e){
    e.preventDefault()
    const bad=badPane()
    if(bad>=0){dw.setStep(bad);requestAnimationFrame(()=>checkPane(panes[bad].current));return}
    createDeparture()
  }
  const nextDeparture=()=>{if(checkPane(panes[dw.step].current).valid)dw.forward()}
  const tabs=[{label:'Seat layout',icon:'car'},{label:'New departure',icon:'calendar'},{label:'Your departures',icon:'route'}].map((x,i)=>({...x,active:tab===i,onClick:()=>setTab(i)}))
  const stepNames=tab===0?['Vehicle and type','Seats']:['Route and time','Arrival and price','Type and driver']

  return <><Header/><FlowShell heading="Ticket departures" icon="ticket" title={['Vehicle seat layout','Create a departure draft','Your departures'][tab]}
    info={['Describe each vehicle’s seats once, then publish scheduled departures. Passengers see exactly the seats you define.','Save a draft, then publish it from Your departures when you are ready.','Publish a draft when you are ready for passengers to book it.'][tab]}
    tabs={tabs} steps={tab<2?stepNames:undefined} current={tab===0?lw.step:dw.step}>
    <Compact.Provider value={true}>
    <ErrorNotice error={error}/><Notice>{notice}</Notice>

    <div className="tk-pane" hidden={tab!==0}>
      <div className="tk-pane" hidden={lw.step!==0}>
        <div className="tk-grid" style={{'--cols':2}}>
          <Field label="Vehicle" help="Only approved vehicles can have a seat layout."><select name="seat-vehicle" value={layoutVehicle} onChange={e=>{setLayoutVehicle(e.target.value);setOff(new Set())}}>
            <option value="">Choose an approved vehicle</option>
            {vehicles.map(v=><option key={v.id} value={v.id}>{v.label||v.reference} · {v.seat_capacity??'?'} seats</option>)}
          </select></Field>
        </div>
        <div className="tk-bar" role="group" aria-label="Vehicle type"><strong className="tk-line">Vehicle type</strong>
          {Object.entries(PRESETS).map(([k,p])=><Chip key={k} tone="info" selected={preset===k} onClick={()=>pick(k)}>{p.label}</Chip>)}</div>
        {saved&&<p className="tk-line">Current saved layout: version {saved.layout_version}, {saved.seats.filter(s=>s.bookable).length} bookable seats. Saving replaces it with a new version.</p>}
        {vehicles.length===0&&<Empty>You have no approved vehicles yet.</Empty>}
      </div>
      <div className="tk-split" hidden={lw.step!==1}>
        <div className="tk-side">
          <Counter label="Rows of seats" value={rowCount} min={1} max={24} onChange={adjust(setRowCount)}/>
          <Counter label="Seats on the left" hint="(door side)" value={left} min={1} max={4} onChange={adjust(setLeft)}/>
          <Counter label="Seats on the right" value={right} min={1} max={4} onChange={adjust(setRight)}/>
          <Counter label="Seats in the back row" hint={back===0?'(no back row)':''} value={back} min={0} max={width} onChange={adjust(setBack)}/>
          <div className="tk-checks">
            <label><input type="checkbox" checked={front===1} onChange={e=>{setFront(e.target.checked?1:0);setOff(new Set())}}/> Seat beside the Driver</label>
            {front===1&&<label><input type="checkbox" checked={sellFront} onChange={e=>setSellFront(e.target.checked)}/> Sell the seat beside the Driver</label>}
          </div>
          <p className="tk-line">Tap a seat in the picture to mark it “Not for sale” (grey). Tap again to sell it. The Driver seat (steering wheel) is never sold. Seats are numbered for you.</p>
          <p className="tk-line">Bookable seats: <strong>{sold}</strong>{capacity!=null&&<> of vehicle capacity {capacity}</>} {overCapacity&&<Chip tone="danger" icon="alert">More than the vehicle capacity</Chip>}</p>
        </div>
        <div className="tk-map"><SeatMap seats={seats} editable onToggle={toggle} label="New seat layout preview"/></div>
      </div>
      <div className="flow-actions">
        {lw.step>0?<button type="button" className="ui-button ui-button-secondary" onClick={lw.back}>Back</button>:<span/>}
        {lw.step===0
          ?<button type="button" className="ui-button ui-button-primary" disabled={!layoutVehicle} onClick={lw.forward}>Next</button>
          :<button type="button" className="ui-button ui-button-primary" disabled={busy||!sold||overCapacity} onClick={saveLayout}>{busy?'Saving…':'Save seat layout'}</button>}
      </div>
    </div>

    <form className="flow-wizard-form tk-pane" hidden={tab!==1} noValidate onSubmit={submitDeparture}>
      <div ref={panes[0]} className="tk-pane" hidden={dw.step!==0}>
        <div className="tk-grid" style={{'--cols':2}}>
          <Field label="Route"><select required name="route" value={form.route_id} onChange={e=>setForm({...form,route_id:e.target.value})}><option value="">Choose a route</option>{routes.map(r=><option key={r.id} value={r.id}>{r.origin_name} → {r.destination_name}</option>)}</select></Field>
          <Field label="Vehicle"><select required name="vehicle" value={form.vehicle_id} onChange={set('vehicle_id')}><option value="">Choose a vehicle</option>{vehicles.map(v=><option key={v.id} value={v.id}>{v.label||v.reference}</option>)}</select></Field>
          <DateTimeFields label="Departure" help="When the vehicle leaves." value={form.departure_at} min={toLocal(new Date()).slice(0,10)} onChange={v=>{
            const mins=chosenRoute?.estimated_duration_minutes
            setForm(f=>({...f,departure_at:v,...(f.arrival_auto&&v&&mins?{estimated_arrival_at:toLocal(new Date(new Date(v).getTime()+mins*60000))}:{})}))}}/>
        </div>
        {routes.length===0&&<p className="tk-line">You have no routes yet. <Link to="/owner/routes">Add a route</Link> first.</p>}
      </div>
      <div ref={panes[1]} className="tk-pane" hidden={dw.step!==1}>
        <div className="tk-grid" style={{'--cols':2}}>
          <DateTimeFields label="Arrival" help={chosenRoute?.estimated_duration_minutes?'When it reaches the end. Filled in from the route duration; you can change it.':'When it reaches the end.'} value={form.estimated_arrival_at} min={form.departure_at?form.departure_at.slice(0,10):undefined}
            onChange={v=>setForm(f=>({...f,estimated_arrival_at:v,arrival_auto:false}))}/>
          <Field label="Stop bookings at" help={form.departure_at?`Passengers can book until ${nice(new Date(new Date(form.departure_at).getTime()-Number(form.stop_before)*60000))}.`:'Passengers cannot book after this time.'}>
            <select name="stop_before" value={form.stop_before} onChange={set('stop_before')}>{STOP_OPTIONS.map(([v,t])=><option key={v} value={v}>{t}</option>)}</select></Field>
          <Field label="Price for the whole trip, per seat (LKR)" help={routeWhole!=null?'This route has a price for each stop, so the whole-trip price comes from the route. Passengers who travel part of the way pay less.':'What each passenger pays for the whole trip.'}>
            <input required name="fare" min="0" step="0.01" type="number" value={form.fare_per_seat} disabled={routeWhole!=null} onChange={set('fare_per_seat')}/></Field>
        </div>
      </div>
      <div ref={panes[2]} className="tk-pane" hidden={dw.step!==2}>
        <div className="tk-grid" style={{'--cols':3}}>
          <Field label="Departure type" help={protectedPolicy?'The departure is confirmed only when enough seats are booked.':'The departure runs on the day whatever the number of bookings.'}>
            <select name="policy" value={form.fulfilment_policy} onChange={set('fulfilment_policy')}>
              <option value="FIXED_GUARANTEED">Fixed, guaranteed departure</option>
              <option value="MINIMUM_SEATS_WITH_PROTECTED_FULFILMENT">Minimum seats with protected fulfilment</option></select></Field>
          <Field label="Accepted time window (minutes)" optional help="Leave 0 if the departure time is fixed."><input name="window" min="0" max="1440" type="number" value={form.accepted_time_window_minutes} onChange={set('accepted_time_window_minutes')}/></Field>
          <Field label="Driver user ID" optional help="Leave empty if you drive this vehicle yourself."><input name="driver" value={form.operator_driver_user_id} onChange={set('operator_driver_user_id')}/></Field>
          {protectedPolicy&&<>
            <Field label="Minimum confirmed seats" help="How many seats must be booked for this departure to be confirmed."><input required name="minseats" min="1" type="number" value={form.minimum_confirmed_seats} onChange={set('minimum_confirmed_seats')}/></Field>
            <DateTimeFields label="Decision deadline" help="You decide by this time." value={form.decision_deadline} min={toLocal(new Date()).slice(0,10)} onChange={v=>setForm(f=>({...f,decision_deadline:v}))}/></>}
        </div>
      </div>
      <div className="flow-actions">
        {dw.step>0?<button type="button" className="ui-button ui-button-secondary" onClick={dw.back}>Back</button>:<span/>}
        {dw.step<2
          ?<button key="next" type="button" className="ui-button ui-button-primary" onClick={nextDeparture}>Next</button>
          :<button key="save" type="submit" className="ui-button ui-button-primary" disabled={busy}>{busy?'Saving…':'Save draft'}</button>}
      </div>
    </form>

    <div className="tk-pane" hidden={tab!==2}>
      {items===null?<p role="status">Loading departures…</p>:items.length
        ?<div className="tk-rows">{departureList.slice.map(x=><article className="tk-row" key={x.id}>
          <div className="tk-row-main"><strong>{x.route.origin_name} → {x.route.destination_name}</strong>
            <span>{new Date(x.departure_at).toLocaleString()} · {x.vehicle.make} {x.vehicle.model} · LKR {x.fare_per_seat} per seat{x.available_seats!=null&&` · ${x.available_seats} seats open`}</span></div>
          <div className="tk-row-actions"><Chip tone={x.status==='PUBLISHED'?'success':'muted'}>{x.status}</Chip>
            {x.status==='DRAFT'&&<button type="button" className="ui-button ui-button-primary" onClick={()=>publish(x)}>Publish</button>}</div></article>)}</div>
        :<Empty>No ticket departures. Save a seat layout, then create a draft departure.</Empty>}
      <div className="flow-actions">{departureList.pages>1?departureList.pager:<span/>}<button type="button" className="ui-button ui-button-primary" onClick={()=>setTab(1)}>New departure</button></div>
    </div>
    </Compact.Provider>
  </FlowShell></>
}
