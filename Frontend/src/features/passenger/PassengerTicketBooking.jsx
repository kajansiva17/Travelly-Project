import React,{useState} from 'react'
import {publicRead} from '../../services/api'
import {TravellyGlassPanel,TravellyState,TravellyStatusChip} from '../../components/TravellyVisualFoundation'
import {ErrorNotice,Header} from '../../components/components'
import SeatMap from '../../components/SeatMap'

export default function PassengerTicketBooking(){
  const [query,setQuery]=useState({origin:'',destination:'',date:'',travellers:1}),[items,setItems]=useState(null),[departure,setDeparture]=useState(null),
    [seats,setSeats]=useState([]),[selected,setSelected]=useState([]),[error,setError]=useState(null)
  async function search(e){
    e.preventDefault();setError(null);setDeparture(null);setSeats([]);setSelected([])
    const params=new URLSearchParams({min_seats:String(Math.max(1,Number(query.travellers)||1))})
    if(query.origin.trim())params.set('origin',query.origin.trim())
    if(query.destination.trim())params.set('destination',query.destination.trim())
    if(query.date)params.set('date',query.date)
    try{setItems(await publicRead(`/scheduled-trips?${params}`))}catch(e){setError(e)}
  }
  async function choose(d){
    setError(null);setSelected([])
    try{const [detail,map]=await Promise.all([publicRead(`/scheduled-trips/${d.id}`),publicRead(`/scheduled-trips/${d.id}/seats`)]);setDeparture({...detail,currency:map.currency});setSeats(map.seats)}catch(e){setError(e)}
  }
  const toggle=s=>setSelected(selected.includes(s.code)?selected.filter(x=>x!==s.code):[...selected,s.code])
  const total=seats.filter(s=>selected.includes(s.code)).reduce((sum,s)=>sum+Number(s.fare),0)
  const travellers=Math.max(1,Number(query.travellers)||1)
  const mapSeats=seats.map(s=>({...s,bookable:true}))
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
        <SeatMap seats={mapSeats} selected={selected} onToggle={toggle} label="Choose seats"/>
        <p>Selected: {selected.length?selected.join(', '):'none'}{selected.length>0&&<> · Total {departure.currency} {total.toFixed(2)}</>}</p>
        {selected.length>0&&selected.length!==travellers&&<p>You searched for {travellers} traveller{travellers>1?'s':''}; select {travellers} seat{travellers>1?'s':''}.</p>}
        <TravellyStatusChip tone="warning">Coming soon</TravellyStatusChip>
        <p>Holding seats and paying for a ticket is not available yet. Nothing has been reserved.</p>
        <button className="button" disabled>Hold selected seats</button>
      </section>}
    </TravellyGlassPanel></main></>
}
