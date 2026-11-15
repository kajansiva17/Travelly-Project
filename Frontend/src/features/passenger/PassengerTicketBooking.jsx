import { t } from '../../i18n/language.js'
import {useEffect,useState} from 'react'
import {api,publicRead} from '../../services/api'
import {Header,useSession} from '../../components/components'
import Chip from '../../components/ui/Chip'
import SeatMap from '../../components/SeatMap'
import {Field,Compact} from '../owner/OwnerRates'
import {FlowShell,useWizard,usePaged,useRowCount} from '../booking/flow/FlowParts'
import {Empty} from '../ticketing/TicketParts'
import {useLocation,useNavigate} from 'react-router-dom'
import TicketPayment from './TicketPayment'
import {formatDateTime} from '../../i18n/dateTime.js'
import TicketCancel,{CancelledTicket} from './TicketCancel'
import FulfilmentNotice from './FulfilmentNotice'
import ReplacementCard,{isPending,vehicleLine} from './ReplacementCard'
import NotAvailableNotice from '../../components/NotAvailableNotice'

/* A guest can search, pick a departure and seats and type names; sign-in is asked at "hold seats". The choice waits in session storage across the sign-in and is checked again against the live seat map. */
const PENDING='travelly.ticket.pending.v1'
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
  const signedIn=useSession(),navigate=useNavigate()
  const [query,setQuery]=useState({origin:'',destination:'',date:'',travellers:1}),[items,setItems]=useState(null),[departure,setDeparture]=useState(null),
    [seats,setSeats]=useState([]),[selected,setSelected]=useState([]),[error,setError]=useState(null)
  const [names,setNames]=useState({}),[stops,setStops]=useState({boarding:'',dropoff:''}),[booking,setBooking]=useState(null),[busy,setBusy]=useState(false),[key,setKey]=useState(newKey),[cancelOpen,setCancelOpen]=useState(false),[cancelResult,setCancelResult]=useState(null)
  const left=useCountdown(booking?.hold_active?booking.hold_expires_at:null)
  const w=useWizard(3)
  // PayHere sends the passenger back to ?booking=<id>&payment=returned|cancelled. That is not proof of payment:
  // the booking is read again and the screen is drawn from payment_status only.
  const params=new URLSearchParams(useLocation().search),bookingParam=params.get('booking'),returned=params.get('payment')
  useEffect(()=>{
    if(!bookingParam||!signedIn)return
    ;(async()=>{try{
      const ticket=await api(`/bookings/${bookingParam}/ticket`);setBooking(ticket)
      const [detail,map]=await Promise.all([publicRead(`/scheduled-trips/${ticket.scheduled_trip_id}`),loadSeats(ticket.scheduled_trip_id)])
      setDeparture({...detail,currency:map.currency});w.setStep(2)
    }catch(e){setError(e)}})()
  },[bookingParam,signedIn])

  // Back from sign-in: the same departure and seats come back (seats taken meanwhile are dropped) and the person only presses Hold.
  useEffect(()=>{
    if(!signedIn||bookingParam)return
    let saved=null
    try{saved=JSON.parse(sessionStorage.getItem(PENDING)||'null');sessionStorage.removeItem(PENDING)}catch{/* Without storage the person simply chooses again. */}
    if(!saved?.departureId)return
    ;(async()=>{try{
      const [detail,map]=await Promise.all([publicRead(`/scheduled-trips/${saved.departureId}`),loadSeats(saved.departureId)])
      const free=(saved.selected||[]).filter(code=>map.seats.find(s=>s.code===code)?.status==='AVAILABLE')
      setDeparture({...detail,currency:map.currency});if(saved.query)setQuery(saved.query)
      setSelected(free);setNames(saved.names||{});setStops(saved.stops||{boarding:'',dropoff:''});w.setStep(free.length?2:1)
    }catch(e){setError(e)}})()
  },[signedIn])
  function signInToHold(){
    try{sessionStorage.setItem(PENDING,JSON.stringify({departureId:departure.id,selected,names,stops,query}))}catch{/* Storage can be unavailable. */}
    navigate('/login',{state:{returnTo:'/travel/book/tickets'}})
  }

  async function find(q){
    setError(null);setDeparture(null);setSeats([]);setSelected([]);setBooking(null)
    const params=new URLSearchParams({min_seats:String(Math.max(1,Number(q.travellers)||1))})
    if(q.origin.trim())params.set('origin',q.origin.trim())
    if(q.destination.trim())params.set('destination',q.destination.trim())
    if(q.date)params.set('date',q.date)
    try{setItems(await publicRead(`/scheduled-trips?${params}`))}catch(e){setError(e)}
  }
  function search(e){e.preventDefault();return find(query)}
  // Travelly AI (contract 03AI) opens this page with origin, destination, date and travellers in the address: the same search runs once, then everything stays manual.
  useEffect(()=>{
    if(bookingParam)return
    const origin=params.get('origin')||'',destination=params.get('destination')||'',date=params.get('date')||'',travellers=params.get('travellers')
    if(!(origin||destination||date||travellers))return
    const q={origin,destination,date,travellers:Math.max(1,Number(travellers)||1)}
    setQuery(q);find(q)
  },[])
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
  const at=stop=>{const ms=Date.parse(departure?.departure_at)+(Number(stop?.scheduled_offset_minutes)||0)*60000;return Number.isFinite(ms)?' · '+t('about {value0}',{value0:new Date(ms).toLocaleTimeString('en-GB',{hour:'2-digit',minute:'2-digit',timeZone:'Asia/Colombo'})}):''}   // arrival time at a stop: departure plus the time Travelly worked out from the road
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
  const held=booking?.hold_active,cancelled=booking?.status==='CANCELLED'
  // A cancelled booking that was paid keeps its own screen (cancelled state and refund); a released hold goes back to seat choice.
  const cancelledPaid=cancelled&&Boolean(cancelResult||['PAID','PARTIALLY_REFUNDED','REFUNDED'].includes(booking.payment_status)||booking.latest_payment?.status==='PAID')
  const confirmed=!cancelled&&(booking?.status==='CONFIRMED'||booking?.payment_status==='PAID'),locked=held||confirmed||cancelledPaid
  const refresh=async()=>{const ticket=await api(`/bookings/${booking.id}/ticket`);setBooking(ticket);if(departure)loadSeats(departure.id).catch(()=>{});return ticket}
  const chooseAgain=()=>{setBooking(null);setSelected([]);w.setStep(1);if(departure)loadSeats(departure.id).catch(setError)}
  const cancelDone=async result=>{setCancelResult(result);setCancelOpen(false);await refresh()}
  const bookMore=()=>{setCancelOpen(false);setCancelResult(null);setBooking(null);setDeparture(null);setSelected([]);setSeats([]);setNames({});w.setStep(0)}

  async function hold(){
    setBusy(true);setError(null)
    try{
      const body={scheduled_trip_id:departure.id,idempotency_key:key,
        travellers:selected.map(code=>({seat_id:byCode[code].seat_id,full_name:names[code].trim()}))}
      if(stops.boarding)body.boarding_stop_id=stops.boarding
      if(stops.dropoff)body.dropoff_stop_id=stops.dropoff
      const created=await api('/bookings/ticket-holds',{method:'POST',body:JSON.stringify(body)})
      setBooking(await api(`/bookings/${created.id}/ticket`))   // the ticket read carries payment_provider, payment_method and payer_details_required
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
    steps={['Find a departure','Choose seats','Travellers and hold']} current={w.step} onStepSelect={i=>{if(i<w.step&&!locked)w.setStep(i)}}>
    <Compact.Provider value={true}>
    <NotAvailableNotice error={error} action={<button type="button" className="ui-button ui-button-secondary" onClick={()=>{setError(null);setSelected([]);setKey(newKey());w.setStep(0)}}>{t('Search again')}</button>}/>

    <form className="flow-wizard-form tk-pane" hidden={w.step!==0} onSubmit={search}>
      <div className="tk-grid" style={{'--cols':4}}>
        <Field label="From" optional><input name="origin" value={query.origin} onChange={e=>setQuery({...query,origin:e.target.value})}/></Field>
        <Field label="To" optional><input name="destination" value={query.destination} onChange={e=>setQuery({...query,destination:e.target.value})}/></Field>
        <Field label="Date" optional><input name="date" type="date" value={query.date} onChange={e=>setQuery({...query,date:e.target.value})}/></Field>
        <Field label="Travellers"><input required name="travellers" min="1" max="100" type="number" value={query.travellers} onChange={e=>setQuery({...query,travellers:e.target.value})}/></Field>
      </div>
      {items?.items?.length===0&&<Empty>{t('No matching departures. No published departure matches these requirements.')}</Empty>}
      <div className="tk-rows">{results.slice.map(d=><article className="tk-row" key={d.id}>
        <div className="tk-row-main"><strong>{d.route?.route_name}</strong>
          <span>{formatDateTime(d.departure_at)} · {d.vehicle?.make} {d.vehicle?.model}{d.vehicle?.air_conditioned?' · AC':''} · {t('{value0} seats available',{value0:d.available_seats})}</span></div>
        <div className="tk-row-actions"><button type="button" className="ui-button ui-button-secondary" onClick={()=>choose(d)}>{t('Select departure')}</button></div></article>)}</div>
      <div className="flow-actions">{results.pages>1?results.pager:<span/>}<button className="ui-button ui-button-primary">{t('Search departures')}</button></div>
    </form>

    {departure&&<div className="tk-split" hidden={w.step!==1}>
      <div className="tk-side">
        <p className="tk-line"><strong>{departure.route.origin_name} → {departure.route.destination_name}</strong> · {formatDateTime(departure.departure_at)}</p>
        <p className="tk-line">{departure.stop_prices_enabled
          ?<>{t('Price per seat {value0} {value1} for {value2} → {value3}',{value0:departure.currency,value1:partFare!=null?partFare.toFixed(2):departure.fare_per_seat,value2:onStop?.stop_name,value3:offStop?.stop_name})}</>
          :<>{t('Fare per seat {value0} {value1}',{value0:departure.currency,value1:departure.fare_per_seat})}</>}</p>
        {routeStops.length>0&&!held&&<div className="tk-grid" style={{'--cols':1}}>
          <Field label="Where will you get on?" optional><select name="boarding" value={stops.boarding} onChange={e=>{const on=routeStops.find(s=>s.id===e.target.value),off=routeStops.find(s=>s.id===stops.dropoff)
              setStops({boarding:e.target.value,dropoff:on&&off&&off.stop_order<=on.stop_order?'':stops.dropoff})}}>
            <option value="">{routeStops[0].stop_name} {t('(start)')}{at(routeStops[0])}</option>{routeStops.slice(1,-1).filter(s=>s.pickup_allowed).map(s=><option key={s.id} value={s.id}>{s.stop_name}{at(s)}</option>)}</select></Field>
          <Field label="Where will you get off?" optional><select name="dropoff" value={stops.dropoff} onChange={e=>setStops({...stops,dropoff:e.target.value})}>
            <option value="">{routeStops[routeStops.length-1].stop_name} {t('(end)')}{at(routeStops[routeStops.length-1])}</option>{routeStops.slice(1,-1).filter(s=>s.dropoff_allowed&&(!onStop||s.stop_order>onStop.stop_order)).map(s=><option key={s.id} value={s.id}>{s.stop_name}{at(s)}</option>)}</select></Field>
        </div>}
        {!stopsReady&&<p className="tk-line is-warn" role="alert">{t('Choose a get-off stop after the stop where you get on.')}</p>}
        {fareBad&&<p className="tk-line is-warn" role="alert">{t('The Owner has no price for travel between these stops.')}</p>}
        {!held&&<p className="tk-line">{t('Selected:')} <strong>{selected.length?selected.join(', '):t('none')}</strong>{selected.length>0&&<> · {t('Total')} <strong>{departure.currency} {total.toFixed(2)}</strong></>}</p>}
        {!held&&selected.length>0&&selected.length!==travellers&&<p className="tk-line">{t(travellers>1?'You searched for {value0} travellers; select {value0} seats.':'You searched for {value0} traveller; select {value0} seat.',{value0:travellers})}</p>}
        {held&&<p className="tk-line">{t('Your seats are held. Open the next step to see the timer.')}</p>}
      </div>
      <div className="tk-map"><SeatMap seats={seats} selected={locked?[]:selected} onToggle={locked?undefined:toggle} label="Choose seats"/></div>
    </div>}

    {departure&&<div className="tk-pane" hidden={w.step!==2}>
      {locked
        ?cancelledPaid?<><FulfilmentNotice bookingId={booking.id} version={booking.version}/><CancelledTicket booking={booking} result={cancelResult}/></>
        :confirmed&&cancelOpen?<TicketCancel booking={booking} departureAt={booking.itinerary?.departure_at||departure.departure_at} refresh={refresh} onDone={cancelDone} onClose={()=>setCancelOpen(false)}/>
        :<div className="tk-hold">
          {held&&<Chip tone="success">{t('Seats held')}</Chip>}
          <h3>{t('Booking {value0}',{value0:booking.booking_reference})}</h3>
          <p className="tk-line">{t('Seats {value0} · Total {value1} {value2}',{value0:booking.travellers.map(x=>x.seat_code).join(', '),value1:booking.currency,value2:booking.total_amount})}</p>
          {held&&<p className="tk-line" role="timer" aria-live="off">{t('Held for')} <strong>{clock}</strong>. {t('The seats are released automatically when the timer ends.')}</p>}
          {confirmed&&isPending(booking)&&<ReplacementCard booking={booking} refresh={refresh} onRejected={result=>setCancelResult({refund_percent:100,refund:result.refund?{...result.refund,currency:booking.currency}:null})}/>}
          {confirmed&&!isPending(booking)&&booking.pending_change?.kind==='REPLACEMENT_VEHICLE'&&booking.pending_change.status==='ACCEPTED'&&<p className="tk-line"><Chip tone="success">{t('Vehicle change accepted')}</Chip> {vehicleLine(booking.pending_change.replacement_vehicle)}</p>}
          {confirmed&&!isPending(booking)&&<FulfilmentNotice bookingId={booking.id} version={booking.version}/>}
          {!(confirmed&&isPending(booking))&&<TicketPayment booking={booking} refresh={refresh} returned={returned} onChooseSeats={chooseAgain}/>}
        </div>
        :<>
          {booking?.status==='CANCELLED'&&<p className="tk-line is-warn" role="status"><strong>{booking.cancellation_reason==='Seat hold expired.'?t('Hold expired.'):t('Hold released.')}</strong> {t('Seats {value0} are free again. You can select seats and hold them again.',{value0:booking.travellers.map(x=>x.seat_code).join(', ')})}</p>}
          {selected.length>0
            ?<div className="tk-grid" style={{'--cols':2}}>
              {nameRows.slice.map(code=><Field key={code} label={`Traveller name for seat ${code}${code===selected[0]?' (primary)':''}`}>
                <input required name={`name-${code}`} maxLength="150" value={names[code]||''} onChange={e=>setNames({...names,[code]:e.target.value})}/></Field>)}
            </div>
            :<Empty>{t('Choose at least one seat first.')}</Empty>}
          {nameRows.pages>1&&<div className="tk-bar">{nameRows.pager}<span className="tk-line">{t('{value0} travellers · names are needed for every seat',{value0:selected.length})}</span></div>}
        </>}
      <div className="flow-actions">
        {confirmed&&!cancelOpen?<button type="button" className="ui-button ui-button-secondary" onClick={()=>setCancelOpen(true)}>{t('Cancel ticket')}</button>:locked?<span/>:<button type="button" className="ui-button ui-button-secondary" onClick={w.back}>{t('Back')}</button>}
        {cancelOpen?<span/>:held
          ?<button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={release}>{busy?'Releasing…':'Release seats'}</button>
          :confirmed||cancelledPaid?<button type="button" className="ui-button ui-button-primary" onClick={bookMore}>{t('Find another departure')}</button>
          :signedIn
            ?<button type="button" className="ui-button ui-button-primary" disabled={busy||!namesReady||!stopsReady||fareBad} onClick={hold}>{busy?'Holding…':'Hold selected seats'}</button>
            :<button type="button" className="ui-button ui-button-primary" disabled={!namesReady||!stopsReady||fareBad} onClick={signInToHold}>{t('Sign in to hold seats')}</button>}
      </div>
    </div>}

    {departure&&w.step===1&&<div className="flow-actions">
      <button type="button" className="ui-button ui-button-secondary" disabled={locked} onClick={w.back}>{t('Back')}</button>
      <button type="button" className="ui-button ui-button-primary" disabled={!locked&&!selected.length} onClick={w.forward}>{locked?'View my booking':'Next'}</button>
    </div>}
    </Compact.Provider>
  </FlowShell></>
}
