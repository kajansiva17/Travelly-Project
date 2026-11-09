import React,{useEffect,useState} from 'react'
import {api,publicRead} from '../../services/api'
import {TravellyGlassPanel,TravellyState,TravellyStatusChip} from '../../components/TravellyVisualFoundation'
import {ButtonLink,ErrorNotice,Header,useSession} from '../../components/components'
import SeatMap from '../../components/SeatMap'

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
    try{const [detail,map]=await Promise.all([publicRead(`/scheduled-trips/${d.id}`),loadSeats(d.id)]);setDeparture({...detail,currency:map.currency})}catch(e){setError(e)}
  }
  // When the timer ends, read the booking again: the server releases the seats and reports the final state.
  useEffect(()=>{
    if(left!==0||!booking)return
    api(`/bookings/${booking.id}/ticket`).then(setBooking).catch(setError)
    if(departure)loadSeats(departure.id).catch(setError)
  },[left])

  const byCode=Object.fromEntries(seats.map(s=>[s.code,s]))
  const toggle=s=>setSelected(selected.includes(s.code)?selected.filter(x=>x!==s.code):[...selected,s.code])
  const total=selected.reduce((sum,code)=>sum+Number(byCode[code]?.fare||0),0)
  const travellers=Math.max(1,Number(query.travellers)||1)
  const stopsReady=(stops.boarding==='')===(stops.dropoff==='')
  const namesReady=selected.length>0&&selected.every(code=>(names[code]||'').trim())

  async function hold(){
    setBusy(true);setError(null)
    try{
      const body={scheduled_trip_id:departure.id,idempotency_key:key,
        travellers:selected.map(code=>({seat_id:byCode[code].seat_id,full_name:names[code].trim()}))}
      if(stops.boarding){body.boarding_stop_id=stops.boarding;body.dropoff_stop_id=stops.dropoff}
      setBooking(await api('/bookings/ticket-holds',{method:'POST',body:JSON.stringify(body)}))
      await loadSeats(departure.id)
    }catch(e){
      setError(e)
      if(e.code==='SEAT_UNAVAILABLE'){setKey(newKey());const map=await loadSeats(departure.id).catch(()=>null)
        if(map)setSelected(selected.filter(code=>map.seats.find(s=>s.code===code)?.status==='AVAILABLE'))}
    }finally{setBusy(false)}
  }
  async function release(){
    setBusy(true);setError(null)
    try{await api(`/bookings/${booking.id}/seat-hold`,{method:'DELETE',body:JSON.stringify({expected_version:booking.version})})
      setBooking(await api(`/bookings/${booking.id}/ticket`));setSelected([]);setKey(newKey());await loadSeats(departure.id)}
    catch(e){setError(e)}finally{setBusy(false)}
  }
  const clock=left==null?'':`${Math.floor(left/60)}:${String(left%60).padStart(2,'0')}`

  return <><Header/><main className="passenger-booking-flow" id="main">
    <header className="passenger-booking-heading"><p>Travel &amp; Booking</p><h1>Find a scheduled ticket</h1>
      <span>Choose a departure before seeing its fare or selecting numbered seats.</span></header>
    <ErrorNotice error={error}/>
    <TravellyGlassPanel>
      <form className="passenger-detail-grid" onSubmit={search}>
        <input placeholder="From" value={query.origin} onChange={e=>setQuery({...query,origin:e.target.value})}/>
        <input placeholder="To" value={query.destination} onChange={e=>setQuery({...query,destination:e.target.value})}/>
        <input type="date" value={query.date} onChange={e=>setQuery({...query,date:e.target.value})}/>
        <input min="1" max="100" type="number" aria-label="Travellers" value={query.travellers} onChange={e=>setQuery({...query,travellers:e.target.value})}/>
        <button className="button">Search departures</button>
      </form>
      {items?.items?.length===0&&<TravellyState title="No matching departures">No published departure matches these requirements.</TravellyState>}
      {items?.items?.map(d=><article className="travelly-vehicle-card" key={d.id}><div>
        <h3>{d.route.route_name}</h3>
        <p>{new Date(d.departure_at).toLocaleString()} · {d.vehicle.make} {d.vehicle.model}{d.vehicle.air_conditioned?' · AC':''} · {d.available_seats} seats available</p></div>
        <button className="button" onClick={()=>choose(d)}>Select departure</button></article>)}

      {departure&&<section className="passenger-quote">
        <h2>Select numbered seats</h2>
        <p>{departure.route.origin_name} → {departure.route.destination_name} · {new Date(departure.departure_at).toLocaleString()} · fare per seat {departure.currency} {departure.fare_per_seat}</p>
        <div className="seat-legend"><span>□ Available</span><span>■ Selected</span><span>▨ Not for sale</span><span>▭ Held / booked</span></div>
        <SeatMap seats={seats.map(s=>({...s,bookable:true}))} selected={booking?.hold_active?[]:selected} onToggle={booking?.hold_active?undefined:toggle} label="Choose seats"/>
        {!booking?.hold_active&&<>
          <p>Selected: {selected.length?selected.join(', '):'none'}{selected.length>0&&<> · Total {departure.currency} {total.toFixed(2)}</>}</p>
          {selected.length>0&&selected.length!==travellers&&<p>You searched for {travellers} traveller{travellers>1?'s':''}; select {travellers} seat{travellers>1?'s':''}.</p>}
        </>}

        {booking?.hold_active?<TravellyGlassPanel>
          <TravellyStatusChip tone="success">Seats held</TravellyStatusChip>
          <h3>Booking {booking.booking_reference}</h3>
          <p>Seats {booking.travellers.map(t=>t.seat_code).join(', ')} · Total {booking.currency} {booking.total_amount}</p>
          <p role="timer" aria-live="off">Held for <strong>{clock}</strong>. The seats are released automatically when the timer ends.</p>
          <TravellyStatusChip tone="warning">Payment coming soon</TravellyStatusChip>
          <p>Paying for a ticket is not available yet, so this hold cannot be confirmed. Nothing has been charged.</p>
          <button className="button outline" disabled={busy} onClick={release}>{busy?'Releasing…':'Release seats'}</button>
        </TravellyGlassPanel>:<>
          {booking?.status==='CANCELLED'&&<TravellyState title={booking.cancellation_reason==='Seat hold expired.'?'Hold expired':'Hold released'}>
            Seats {booking.travellers.map(t=>t.seat_code).join(', ')} are free again. You can select seats and hold them again.</TravellyState>}
          {selected.length>0&&<div className="passenger-detail-grid">
            {selected.map((code,i)=><label key={code}>Traveller name for seat {code}{i===0?' (primary)':''}
              <input required maxLength="150" value={names[code]||''} onChange={e=>setNames({...names,[code]:e.target.value})}/></label>)}
            {departure.stops?.length>0&&<>
              <label>Boarding stop (optional)<select value={stops.boarding} onChange={e=>setStops({...stops,boarding:e.target.value})}>
                <option value="">Route start</option>{departure.stops.filter(s=>s.pickup_allowed).map(s=><option key={s.id} value={s.id}>{s.stop_name}</option>)}</select></label>
              <label>Drop-off stop (optional)<select value={stops.dropoff} onChange={e=>setStops({...stops,dropoff:e.target.value})}>
                <option value="">Route end</option>{departure.stops.filter(s=>s.dropoff_allowed).map(s=><option key={s.id} value={s.id}>{s.stop_name}</option>)}</select></label>
              {!stopsReady&&<p>Choose both a boarding stop and a drop-off stop, or neither.</p>}</>}
          </div>}
          {signedIn
            ?<button className="button" disabled={busy||!namesReady||!stopsReady} onClick={hold}>{busy?'Holding…':'Hold selected seats'}</button>
            :<ButtonLink to="/login">Sign in to hold seats</ButtonLink>}
        </>}
      </section>}
    </TravellyGlassPanel></main></>
}
