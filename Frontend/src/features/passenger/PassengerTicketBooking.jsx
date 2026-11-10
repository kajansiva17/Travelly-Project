import React,{useEffect,useState} from 'react'
import {api,publicRead} from '../../services/api'
import {ButtonLink,ErrorNotice,Header,useSession} from '../../components/components'
import Chip from '../../components/ui/Chip'
import SeatMap from '../../components/SeatMap'
import {Field,Compact} from '../owner/OwnerRates'
import {FlowShell,useWizard,usePaged,useRowCount} from '../booking/flow/FlowParts'
import {Empty} from '../ticketing/TicketParts'

const newKey=()=>(globalThis.crypto?.randomUUID?.()||`${Date.now()}-${Math.random().toString(36).slice(2)}`).replace(/[^A-Za-z0-9_-]/g,'').slice(0,40)

function useCountdown(until){
  const [left,setLeft]=useState(null)
  useEffect(()=>{
    if(!until){setLeft(null);return}
    const tick=()=>setLeft(Math.max(0,Math.floor((new Date(until)-Date.now())/1000)))
    tick();const timer=setInterval(tick,1000);return ()=>clearInterval(timer)
  },[until])
  return left
}

export default function PassengerTicketBooking(){
  const signedIn=useSession()
  const [query,setQuery]=useState({origin:'',destination:'',date:'',travellers:1}),[items,setItems]=useState(null),[departure,setDeparture]=useState(null),
    [seats,setSeats]=useState([]),[selected,setSelected]=useState([]),[error,setError]=useState(null)
  const [names,setNames]=useState({}),[stops,setStops]=useState({boarding:'',dropoff:''}),[booking,setBooking]=useState(null),[busy,setBusy]=useState(false),[key,setKey]=useState(newKey)
  const left=useCountdown(booking?.hold_active?booking.hold_expires_at:null)
  const w=useWizard(3)

  async function search(e){
    e.preventDefault();setError(null);setDeparture(null);setSeats([]);setSelected([]);setBooking(null)
    const params=new URLSearchParams({min_seats:String(Math.max(1,Number(query.travellers)||1))})
    if(query.origin.trim())params.set('origin',query.origin.trim())
    if(query.destination.trim())params.set('destination',query.destination.trim())
    if(query.date)params.set('date',query.date)
    try{setItems(await publicRead(`/scheduled-trips?${params}`))}catch(e){setError(e)}
  }
  async function loadSeats(id){const map=await publicRead(`/scheduled-trips/${id}/seats`);setSeats(map.seats);return map}
  async function choose(d){
    setError(null);setSelected([]);setBooking(null);setNames({});setStops({boarding:'',dropoff:''});setKey(newKey())
    try{const [detail,map]=await Promise.all([publicRead(`/scheduled-trips/${d.id}`),loadSeats(d.id)]);setDeparture({...detail,currency:map.currency});w.setStep(1)}catch(e){setError(e)}
  }
  // When the timer ends, read the booking again: the server releases the seats and reports the final state.
  useEffect(()=>{
    if(left!==0||!booking)return
    api(`/bookings/${booking.id}/ticket`).then(setBooking).catch(setError)
    if(departure)loadSeats(departure.id).catch(setError)
  },[left])

  const byCode=Object.fromEntries(seats.map(s=>[s.code,s]))
  // The Driver seat and seats not for sale arrive with bookable:false and no seat_id: drawn, never selectable.
  const toggle=s=>{if(s.bookable===false||!s.seat_id)return;setSelected(selected.includes(s.code)?selected.filter(x=>x!==s.code):[...selected,s.code])}
  // Each stop is optional on its own: no get-on stop = route start, no get-off stop = route end.
  const routeStops=departure?.stops||[]
  const onStop=routeStops.find(s=>s.id===stops.boarding)||routeStops[0]
  const offStop=routeStops.find(s=>s.id===stops.dropoff)||routeStops[routeStops.length-1]
  const stopsReady=!onStop||!offStop||onStop.stop_order<offStop.stop_order
  // With the Owner's price for each stop, a seat costs price(get-off) - price(get-on).
  const partFare=departure?.stop_prices_enabled&&onStop&&offStop?Number(offStop.price_from_start)-Number(onStop.price_from_start):null
  const seatFare=code=>partFare!=null?partFare:Number(byCode[code]?.fare||0)
  const total=selected.reduce((sum,code)=>sum+seatFare(code),0)
  const travellers=Math.max(1,Number(query.travellers)||1)
  const namesReady=selected.length>0&&selected.every(code=>(names[code]||'').trim())
  const fareBad=partFare!=null&&partFare<=0
  const held=booking?.hold_active

  async function hold(){
    setBusy(true);setError(null)
    try{
      const body={scheduled_trip_id:departure.id,idempotency_key:key,
        travellers:selected.map(code=>({seat_id:byCode[code].seat_id,full_name:names[code].trim()}))}
      if(stops.boarding)body.boarding_stop_id=stops.boarding
      if(stops.dropoff)body.dropoff_stop_id=stops.dropoff
      setBooking(await api('/bookings/ticket-holds',{method:'POST',body:JSON.stringify(body)}))
      await loadSeats(departure.id)
    }catch(e){
      setError(e)
      if(e.code==='SEAT_UNAVAILABLE'){setKey(newKey());const map=await loadSeats(departure.id).catch(()=>null)
        if(map){setSelected(selected.filter(code=>map.seats.find(s=>s.code===code)?.status==='AVAILABLE'));w.setStep(1)}}
    }finally{setBusy(false)}
  }
  async function release(){
    setBusy(true);setError(null)
    try{await api(`/bookings/${booking.id}/seat-hold`,{method:'DELETE',body:JSON.stringify({expected_version:booking.version})})
      setBooking(await api(`/bookings/${booking.id}/ticket`));setSelected([]);setKey(newKey());await loadSeats(departure.id)}
    catch(e){setError(e)}finally{setBusy(false)}
  }
  const clock=left==null?'':`${Math.floor(left/60)}:${String(left%60).padStart(2,'0')}`
  const results=usePaged(items?.items||[],Math.max(2,useRowCount(64)))
  const nameRows=usePaged(selected,4)
  const title=['Find a scheduled ticket','Select numbered seats','Traveller names and hold'][w.step]

  return <><Header/><FlowShell heading="Travel & Booking" icon="ticket" title={title} subtitle=""
    info="Choose a departure before seeing its fare or selecting numbered seats."
    steps={['Find a departure','Choose seats','Travellers and hold']} current={w.step} onStepSelect={i=>{if(i<w.step&&!held)w.setStep(i)}}>
    <Compact.Provider value={true}>
    <ErrorNotice error={error}/>

<<<<<<< HEAD
    <form className="flow-wizard-form tk-pane" hidden={w.step!==0} onSubmit={search}>
      <div className="tk-grid" style={{'--cols':4}}>
        <Field label="From" optional><input name="origin" value={query.origin} onChange={e=>setQuery({...query,origin:e.target.value})}/></Field>
        <Field label="To" optional><input name="destination" value={query.destination} onChange={e=>setQuery({...query,destination:e.target.value})}/></Field>
        <Field label="Date" optional><input name="date" type="date" value={query.date} onChange={e=>setQuery({...query,date:e.target.value})}/></Field>
        <Field label="Travellers"><input required name="travellers" min="1" max="100" type="number" value={query.travellers} onChange={e=>setQuery({...query,travellers:e.target.value})}/></Field>
      </div>
      {items?.items?.length===0&&<Empty>No matching departures. No published departure matches these requirements.</Empty>}
      <div className="tk-rows">{results.slice.map(d=><article className="tk-row" key={d.id}>
        <div className="tk-row-main"><strong>{d.route.route_name}</strong>
          <span>{new Date(d.departure_at).toLocaleString()} · {d.vehicle.make} {d.vehicle.model}{d.vehicle.air_conditioned?' · AC':''} · {d.available_seats} seats available</span></div>
        <div className="tk-row-actions"><button type="button" className="ui-button ui-button-secondary" onClick={()=>choose(d)}>Select departure</button></div></article>)}</div>
      <div className="flow-actions">{results.pages>1?results.pager:<span/>}<button className="ui-button ui-button-primary">Search departures</button></div>
    </form>
=======
      {departure&&<section className="passenger-quote">
        <h2>Select numbered seats</h2>
        <p>{departure.route.origin_name} → {departure.route.destination_name} · {new Date(departure.departure_at).toLocaleString()} · {departure.stop_prices_enabled
          ?<>price per seat {departure.currency} {partFare!=null?partFare.toFixed(2):departure.fare_per_seat} for {onStop?.stop_name} → {offStop?.stop_name}</>
          :<>fare per seat {departure.currency} {departure.fare_per_seat}</>}</p>
        <SeatMap seats={seats} selected={booking?.hold_active?[]:selected} onToggle={booking?.hold_active?undefined:toggle} label="Choose seats"/>
        {!booking?.hold_active&&<>
          <p>Selected: {selected.length?selected.join(', '):'none'}{selected.length>0&&<> · Total {departure.currency} {total.toFixed(2)}</>}</p>
          {selected.length>0&&selected.length!==travellers&&<p>You searched for {travellers} traveller{travellers>1?'s':''}; select {travellers} seat{travellers>1?'s':''}.</p>}
        </>}
>>>>>>> origin/claude-work

    {departure&&<div className="tk-split" hidden={w.step!==1}>
      <div className="tk-side">
        <p className="tk-line"><strong>{departure.route.origin_name} → {departure.route.destination_name}</strong> · {new Date(departure.departure_at).toLocaleString()}</p>
        <p className="tk-line">{departure.stop_prices_enabled
          ?<>Price per seat {departure.currency} {partFare!=null?partFare.toFixed(2):departure.fare_per_seat} for {onStop?.stop_name} → {offStop?.stop_name}</>
          :<>Fare per seat {departure.currency} {departure.fare_per_seat}</>}</p>
        {routeStops.length>0&&!held&&<div className="tk-grid" style={{'--cols':1}}>
          <Field label="Where will you get on?" optional><select name="boarding" value={stops.boarding} onChange={e=>{const on=routeStops.find(s=>s.id===e.target.value),off=routeStops.find(s=>s.id===stops.dropoff)
              setStops({boarding:e.target.value,dropoff:on&&off&&off.stop_order<=on.stop_order?'':stops.dropoff})}}>
            <option value="">{routeStops[0].stop_name} (start)</option>{routeStops.slice(1,-1).filter(s=>s.pickup_allowed).map(s=><option key={s.id} value={s.id}>{s.stop_name}</option>)}</select></Field>
          <Field label="Where will you get off?" optional><select name="dropoff" value={stops.dropoff} onChange={e=>setStops({...stops,dropoff:e.target.value})}>
            <option value="">{routeStops[routeStops.length-1].stop_name} (end)</option>{routeStops.slice(1,-1).filter(s=>s.dropoff_allowed&&(!onStop||s.stop_order>onStop.stop_order)).map(s=><option key={s.id} value={s.id}>{s.stop_name}</option>)}</select></Field>
        </div>}
        {!stopsReady&&<p className="tk-line is-warn" role="alert">Choose a get-off stop after the stop where you get on.</p>}
        {fareBad&&<p className="tk-line is-warn" role="alert">The Owner has no price for travel between these stops.</p>}
        {!held&&<p className="tk-line">Selected: <strong>{selected.length?selected.join(', '):'none'}</strong>{selected.length>0&&<> · Total <strong>{departure.currency} {total.toFixed(2)}</strong></>}</p>}
        {!held&&selected.length>0&&selected.length!==travellers&&<p className="tk-line">You searched for {travellers} traveller{travellers>1?'s':''}; select {travellers} seat{travellers>1?'s':''}.</p>}
        {held&&<p className="tk-line">Your seats are held. Open the next step to see the timer.</p>}
      </div>
      <div className="tk-map"><SeatMap seats={seats} selected={held?[]:selected} onToggle={held?undefined:toggle} label="Choose seats"/></div>
    </div>}

    {departure&&<div className="tk-pane" hidden={w.step!==2}>
      {held
        ?<div className="tk-hold">
          <Chip tone="success">Seats held</Chip>
          <h3>Booking {booking.booking_reference}</h3>
          <p className="tk-line">Seats {booking.travellers.map(t=>t.seat_code).join(', ')} · Total {booking.currency} {booking.total_amount}</p>
          <p className="tk-line" role="timer" aria-live="off">Held for <strong>{clock}</strong>. The seats are released automatically when the timer ends.</p>
          <p className="tk-line"><Chip tone="muted" icon="clock">Payment coming soon</Chip> Paying for a ticket is not available yet, so this hold cannot be confirmed. Nothing has been charged.</p>
        </div>
        :<>
          {booking?.status==='CANCELLED'&&<p className="tk-line is-warn" role="status"><strong>{booking.cancellation_reason==='Seat hold expired.'?'Hold expired.':'Hold released.'}</strong> Seats {booking.travellers.map(t=>t.seat_code).join(', ')} are free again. You can select seats and hold them again.</p>}
          {selected.length>0
            ?<div className="tk-grid" style={{'--cols':2}}>
              {nameRows.slice.map(code=><Field key={code} label={`Traveller name for seat ${code}${code===selected[0]?' (primary)':''}`}>
                <input required name={`name-${code}`} maxLength="150" value={names[code]||''} onChange={e=>setNames({...names,[code]:e.target.value})}/></Field>)}
            </div>
            :<Empty>Choose at least one seat first.</Empty>}
          {nameRows.pages>1&&<div className="tk-bar">{nameRows.pager}<span className="tk-line">{selected.length} travellers · names are needed for every seat</span></div>}
        </>}
      <div className="flow-actions">
        {held?<span/>:<button type="button" className="ui-button ui-button-secondary" onClick={w.back}>Back</button>}
        {held
          ?<button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={release}>{busy?'Releasing…':'Release seats'}</button>
          :signedIn
            ?<button type="button" className="ui-button ui-button-primary" disabled={busy||!namesReady||!stopsReady||fareBad} onClick={hold}>{busy?'Holding…':'Hold selected seats'}</button>
            :<ButtonLink to="/login">Sign in to hold seats</ButtonLink>}
      </div>
    </div>}

    {departure&&w.step===1&&<div className="flow-actions">
      <button type="button" className="ui-button ui-button-secondary" disabled={held} onClick={w.back}>Back</button>
      <button type="button" className="ui-button ui-button-primary" disabled={!held&&!selected.length} onClick={w.forward}>{held?'View my hold':'Next'}</button>
    </div>}
    </Compact.Provider>
  </FlowShell></>
}
