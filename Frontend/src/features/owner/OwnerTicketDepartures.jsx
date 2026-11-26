import { t } from '../../i18n/language.js'
import {useEffect,useMemo,useRef,useState} from 'react'
import {Link,useLocation} from 'react-router-dom'
import {api} from '../../services/api'
import {Header,ErrorNotice,Icon} from '../../components/components'
import Chip from '../../components/ui/Chip'
import InfoTip from '../../components/ui/InfoTip'
import SeatMap from '../../components/SeatMap'
import {Field,Compact,RateErrors,CashSwitch} from './OwnerRates'
import {RoutesPanel} from './OwnerRoutes'
import {FlowShell,useWizard,checkPane,usePaged,useRowCount} from '../booking/flow/FlowParts'
import {Notice,Empty,DateTimeFields,Counter} from '../ticketing/TicketParts'
import {formatDateTime} from '../../i18n/dateTime.js'
import DepartureFulfilment,{statusChip,canManage,isOver} from './DepartureFulfilment'
import EmptyState from '../../components/ui/EmptyState'
import {fieldErrors,fieldErrorMap} from '../../services/fieldErrors.js'

// "Who will drive?" choices: the Owner's own listed Drivers (GET /owners/me/drivers), never a typed user ID.
function DriverOptions({drivers,me,self=true}){
  const others=(drivers||[]).filter(d=>d.id!==me.id)
  return <>
    {self&&me.driver&&<option value="me">{t('I will drive (self-drive)')}</option>}
    {others.length>0&&<optgroup label={t('My drivers')}>{others.map(d=><option key={d.id} value={d.id} disabled={!d.eligible}>{d.display_name}{d.reference&&d.display_name!==d.reference?` · ${d.reference}`:''}{d.eligible?'':` · ${t('Not an approved Driver')}`}</option>)}</optgroup>}
  </>
}
// One aligned card under the select: icon + message on the left, the next action on the right.
function DriverInfo({choice,drivers,me,onSelf}){
  const picked=(drivers||[]).find(d=>d.id===choice)
  const none=drivers!==null&&!(drivers||[]).some(d=>d.id!==me.id)
  let icon='users',title,sub,action=null
  if(picked){icon=picked.eligible?'check':'alert';title=picked.display_name;sub=<><Chip tone={picked.eligible?'success':'danger'}>{picked.eligible?t('Approved Driver'):t('Not an approved Driver')}</Chip> <span>{t(picked.how_you_know_them)}</span></>}
  else if(choice==='me'){icon='check';title=t('You will drive this departure');sub=<><Chip tone="success">{t('Approved Driver')}</Chip> <span>{t('You are named as the Driver for this departure.')}</span></>}
  else if(none){title=t('You have no other Drivers listed yet.');sub=<span>{me.driver?t('You can drive it yourself, or assign a Driver later.'):t('Save the draft and assign a Driver later, or apply to become a Driver.')}</span>
    action=me.driver?<button type="button" className="ui-button ui-button-secondary" onClick={onSelf}>{t('Drive it myself')}</button>:<Link className="ui-button ui-button-secondary" to="/driver/onboarding">{t('Apply to drive')}</Link>}
  else{title=t('No Driver chosen yet');sub=<span>{t('Pick a Driver above. You can also leave this and assign one later, but a Driver is needed before you publish.')}</span>}
  return <div className="tk-driver-card" role="status"><span className="tk-driver-icon"><Icon name={icon} size={22} aria-hidden="true"/></span><div className="tk-driver-text"><strong>{title}</strong><p>{sub}</p></div>{action&&<div className="tk-driver-action">{action}</div>}</div>
}

// "Find a Driver by reference" (contract 03T, section 2): POST /owners/me/drivers/lookup. The Owner types the public reference
// (USR-...), never a user ID. The id in the answer is used only when eligible, as operator_driver_user_id, like a listed Driver.
function DriverFinder({onUse}){
  const [reference,setReference]=useState(''),[busy,setBusy]=useState(false),[found,setFound]=useState(null),[problem,setProblem]=useState('')
  async function find(){
    const value=reference.trim()
    if(!value||busy)return
    setBusy(true);setFound(null);setProblem('')
    try{setFound(await api('/owners/me/drivers/lookup',{method:'POST',body:JSON.stringify({driver_reference:value})}))}
    catch(error){
      const code=error.code
      if(error instanceof TypeError||code==='API_TIMEOUT')setProblem(t('We could not reach Travelly. Please try again.'))
      else if(code==='DRIVER_NOT_FOUND'||error.status===404)setProblem(t('No Driver has this reference. Check it with the Driver and try again.'))
      else if(error.status===429||code==='RATE_LIMITED')setProblem(t('Too many lookups. Please try again in a few minutes.'))
      else if(error.status===403)setProblem(t('Only an approved Owner can look up a Driver.'))
      else if(code==='VALIDATION_ERROR'||error.status===422)setProblem(t('That does not look like a Driver reference. It starts with USR- followed by 16 letters or numbers, for example USR-0123456789ABCDEF.'))
      else setProblem(error.message||t('The Driver could not be looked up. Please try again.'))
    }finally{setBusy(false)}
  }
  const eligible=found&&found.eligible&&found.id
  return <div className="tk-finder">
    <div className="tk-bar tk-finder-row">
      <div className="tk-grow"><Field label="Find a Driver by reference" optional help="Ask the Driver for the reference on their Travelly profile. It starts with USR-."><input name="driver_reference" maxLength="40" autoComplete="off" placeholder="USR-0123456789ABCDEF" value={reference} onChange={e=>{setReference(e.target.value);setFound(null);setProblem('')}} onKeyDown={e=>{if(e.key==='Enter'){e.preventDefault();find()}}}/></Field></div>
      <button type="button" className="ui-button ui-button-secondary" disabled={busy||!reference.trim()} onClick={find}>{busy?t('Please wait…'):t('Find')}</button>
    </div>
    {problem&&<p className="tk-line is-warn" role="status">{problem}</p>}
    {found&&<p className="tk-line" role="status"><Chip tone={eligible?'success':'danger'} icon={eligible?'check':'alert'}>{eligible?t('Approved Driver'):t('Not approved')}</Chip> <strong>{found.display_name}</strong> <span>{t(found.message)}</span>
      {eligible&&<button type="button" className="ui-button ui-button-primary" onClick={()=>{onUse({id:found.id,reference:found.reference,display_name:found.display_name,eligible:true,how_you_know_them:'Found by reference'});setReference('');setFound(null)}}>{t('Use this Driver')}</button>}</p>}
  </div>
}

// Replacement requests (contract 03F2, sections 9 and 10): another Owner asks me to run a departure with my vehicle.
function replacementProblem(error){
  const code=error.code,fields=fieldErrors(error)
  if(error instanceof TypeError||code==='API_TIMEOUT')return {text:t('We could not reach Travelly. Please try again.')}
  if(code==='REPLACEMENT_TOO_SMALL'){const m=/has (\d+) bookable seats; (\d+) passengers/.exec(error.message||'');return {text:m?t('This vehicle has {value0} bookable seats; {value1} passengers are booked.',{value0:m[1],value1:m[2]}):t(error.message)}}
  if(['NO_REPLACEMENT_REQUEST','REPLACEMENT_NOT_ALLOWED','VEHICLE_SCHEDULE_CONFLICT','VERSION_CONFLICT','DRIVER_NOT_ELIGIBLE'].includes(code)||error.status===404)return {keep:code==='DRIVER_NOT_ELIGIBLE',text:t(error.message)}
  if(code==='VALIDATION_ERROR'&&fields.length)return {keep:true,text:t('Please check the highlighted fields.'),fields:fieldErrorMap(error)}
  return {text:error.message||t('Your answer could not be sent. Please try again.')}
}
export function ReplacementRequests({active,drivers,me,useFound,chosenDriver,onNotice}){
  const [items,setItems]=useState(null),[error,setError]=useState(null),[open,setOpen]=useState(null),[choice,setChoice]=useState('later'),[reason,setReason]=useState(''),[confirm,setConfirm]=useState(false),[busy,setBusy]=useState(false),[message,setMessage]=useState(''),[errors,setErrors]=useState({})
  const load=()=>api('/owners/me/replacement-requests').then(r=>{setItems(r.items||[]);setError(null)}).catch(setError)
  useEffect(()=>{if(active)load()},[active])
  const list=usePaged(items||[],Math.max(2,useRowCount(64)))
  const close=()=>{setOpen(null);setChoice('later');setReason('');setConfirm(false);setMessage('');setErrors({})}
  async function send(){
    const {item,kind}=open
    setBusy(true);setMessage('');setErrors({})
    const body=kind==='accept'?{expected_version:item.version,decision:'ACCEPT',operator_driver_user_id:choice==='me'?null:chosenDriver(choice)}:{expected_version:item.version,decision:'DECLINE',reason:reason.trim()}
    try{
      await api(`/scheduled-trips/${item.id}/replacement-answer`,{method:'POST',body:JSON.stringify(body)})
      close();onNotice(kind==='accept'?t('Request accepted. The passengers move to your vehicle and can accept the change or reject it for a full refund.'):t('Request declined. The other Owner and the Admin are told.'));await load()
    }catch(problem){
      const out=replacementProblem(problem)
      setMessage(out.text);setErrors(out.fields||{})
      if(out.keep){setConfirm(false)}else{setOpen(null);setConfirm(false);setChoice('later');setReason('');load()}
    }finally{setBusy(false)}
  }
  const reasonOk=reason.trim().length>=3&&reason.trim().length<=1000
  const route=r=>`${r.route?.origin_name||''} → ${r.route?.destination_name||''}`
  if(open){
    const {item,kind}=open
    return <RateErrors.Provider value={errors}><div className="tk-pane">
      <p className="tk-line"><strong>{item.original_departure_reference} · {route(item)}</strong> · {formatDateTime(item.departure_at)} · {item.vehicle?.display_name||item.vehicle?.public_vehicle_reference} · {t('{value0} seats booked',{value0:item.booked_seats})}</p>
      {message&&<p className="tk-line is-warn" role="status">{message}</p>}
      {kind==='accept'
        ?<div className="tk-driver-split">
          <div className="tk-driver-col"><Field label="Who will drive?" help="Choose yourself (if you are an approved Driver) or one of your Drivers. An outside Driver must still accept the trip."><select name="replacement-driver" disabled={confirm} value={choice} onChange={e=>setChoice(e.target.value)}><option value="later">{t('Choose a Driver')}</option><DriverOptions drivers={drivers} me={me}/></select></Field>
            {!confirm&&<DriverFinder onUse={useFound(setChoice)}/>}</div>
          <div className="tk-driver-col"><DriverInfo choice={choice} drivers={drivers} me={me} onSelf={()=>setChoice('me')}/></div></div>
        :<Field label="Why can’t you run it?" help="Between 3 and 1000 characters. The other Owner and the Admin see this reason."><input name="reason" maxLength="1000" disabled={confirm} value={reason} onChange={e=>setReason(e.target.value)}/></Field>}
      {confirm&&<p className="tk-line is-warn"><strong>{kind==='accept'?t('Accept and run this departure?'):t('Decline this request?')}</strong> {kind==='accept'?t('{value0} seats move to your vehicle and the departure becomes committed. After the journey, the payment for these seats appears in your settlements.',{value0:item.booked_seats}):t('The other Owner and the Admin are told. The departure stays with its Owner, who can try another vehicle.')}</p>}
      <div className="flow-actions"><button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={()=>confirm?setConfirm(false):close()}>{confirm?t('Back'):t('Back to list')}</button>
        {confirm?<button type="button" className="ui-button ui-button-primary" disabled={busy} onClick={send}>{busy?t('Please wait…'):kind==='accept'?t('Yes, accept'):t('Yes, decline')}</button>
          :<button type="button" className="ui-button ui-button-primary" disabled={kind==='accept'?choice==='later':!reasonOk} onClick={()=>{setMessage('');setConfirm(true)}}>{t('Continue')}</button>}</div>
    </div></RateErrors.Provider>
  }
  return <>
    {error&&<p className="tk-line is-warn" role="status">{error.message}</p>}
    {items===null&&!error?<p role="status">{t('Loading requests…')}</p>:items&&items.length
      ?<div className="tk-rows">{list.slice.map(r=><article className="tk-row" key={r.id}>
        <div className="tk-row-main"><strong>{r.original_departure_reference} · {route(r)}</strong>
          <span>{formatDateTime(r.departure_at)} · {r.vehicle?.display_name||r.vehicle?.public_vehicle_reference} · {t('{value0} seats booked',{value0:r.booked_seats})} · {t('LKR {value0} per seat',{value0:r.fare_per_seat})}{r.requested_by?` · ${t('Asked by')} ${r.requested_by}`:''}</span></div>
        <div className="tk-row-actions">{r.answer_pending
          ?<><Chip tone="info" icon="clock">{t('Waiting for your answer')}</Chip><button type="button" className="ui-button ui-button-primary" onClick={()=>{setChoice('later');setOpen({item:r,kind:'accept'})}}>{t('Accept')}</button><button type="button" className="ui-button ui-button-secondary" onClick={()=>setOpen({item:r,kind:'decline'})}>{t('Decline')}</button></>
          :<Chip tone={statusChip(r.status).tone}>{statusChip(r.status).label}</Chip>}</div></article>)}</div>
      :items&&<EmptyState icon="route" title={t('No replacement requests')}>{t('When another Owner asks you to run a departure with your vehicle, it appears here.')}</EmptyState>}
    <div className="flow-actions">{list.pages>1?list.pager:<span/>}<span/></div>
  </>
}

/* Its own sidebar entry (contract 03W): the same Replacement requests component, with its own Driver list. */
export function OwnerReplacementRequests(){
  const [drivers,setDrivers]=useState(null),[me,setMe]=useState({id:'',driver:false}),[notice,setNotice]=useState('')
  useEffect(()=>{
    Promise.all([api('/users/me'),api('/users/me/roles')]).then(([user,roles])=>setMe({id:user.id,driver:(user.approved_roles||[]).includes('DRIVER')&&(roles.items||[]).some(r=>r.role_code==='DRIVER'&&r.approval_status==='APPROVED')})).catch(()=>{})
    api('/owners/me/drivers').then(x=>setDrivers(x.items||[])).catch(()=>setDrivers([]))
  },[])
  const useFound=choose=>driver=>{setDrivers(list=>(list||[]).some(d=>d.id===driver.id)?list:[...(list||[]),driver]);choose(driver.id)}
  const chosenDriver=choice=>choice==='me'?(me.driver?me.id:null):choice==='later'?null:choice
  return <><Header/><FlowShell heading={t('Replacement requests')} title={t('Requests from other Owners')} icon="clock" info={t('When another Owner asks you to run a departure with your vehicle, it appears here.')}>
    <Notice>{notice}</Notice>
    <Compact.Provider value={true}><ReplacementRequests active drivers={drivers} me={me} useFound={useFound} chosenDriver={chosenDriver} onNotice={setNotice}/></Compact.Provider>
  </FlowShell></>
}

const emptyDeparture={route_id:'',vehicle_id:'',departure_at:'',estimated_arrival_at:'',arrival_auto:true,stop_before:'60',fare_per_seat:'',
  fulfilment_policy:'FIXED_GUARANTEED',minimum_confirmed_seats:'',decision_deadline:'',accepted_time_window_minutes:'0',driver_choice:'later'}
const iso=v=>v?new Date(v).toISOString():null
const pad=n=>String(n).padStart(2,'0')
const toLocal=d=>`${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
const STOP_OPTIONS=[['30','30 minutes before departure'],['60','1 hour before departure'],['120','2 hours before departure']]
const nice=formatDateTime

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
// The seats a passenger can book, as one comparable text: used to tell whether a departure still matches the vehicle's saved layout.
const signature=seats=>(seats||[]).filter(s=>s.bookable).map(s=>`${s.deck||1}-${s.row}-${s.column}-${s.code}`).sort().join('|')

export default function OwnerTicketDepartures(){
  const [vehicles,setVehicles]=useState([]),[vehiclesLoaded,setVehiclesLoaded]=useState(false),[routes,setRoutes]=useState([]),[items,setItems]=useState(null),[error,setError]=useState(null),[busy,setBusy]=useState(false)
  const [layoutVehicle,setLayoutVehicle]=useState(''),[saved,setSaved]=useState(null),[loaded,setLoaded]=useState(null)
  const [preset,setPreset]=useState('van'),[left,setLeft]=useState(2),[right,setRight]=useState(1),[rowCount,setRowCount]=useState(3),[back,setBack]=useState(4),[front,setFront]=useState(1),[sellFront,setSellFront]=useState(true),[off,setOff]=useState(new Set())
  const [drivers,setDrivers]=useState(null),[assigning,setAssigning]=useState(null),[retiming,setRetiming]=useState(null),[managing,setManaging]=useState(null),[newStart,setNewStart]=useState(''),[repeatMode,setRepeatMode]=useState(false),[history,setHistory]=useState(false),[draftSeats,setDraftSeats]=useState({}),[driverPick,setPickDriver]=useState('later'),[form,setForm]=useState(emptyDeparture),[notice,setNotice]=useState(''),[me,setMe]=useState({id:'',driver:false})
  const location=useLocation(),[tab,setTab]=useState(()=>({routes:3,departure:1,departures:2})[new URLSearchParams(location.search).get('tab')]??0),[routeMode,setRouteMode]=useState('list'),[routeStep,setRouteStep]=useState(0),lw=useWizard(2),dw=useWizard(3),panes=[useRef(null),useRef(null),useRef(null)]
  const [tripLayout,setTripLayout]=useState({}),[vehicleLayout,setVehicleLayout]=useState({})
  // How Passengers may pay for seats on this vehicle (online only, cash on the bus only, or both): saved at once, next to the price.
  const [ticketService,setTicketService]=useState(''),[ticketTerms,setTicketTerms]=useState(null)
  useEffect(()=>{api('/owners/me/ticket-service').then(r=>{if(r&&r.id)setTicketService(r.id)}).catch(()=>{})},[])
  useEffect(()=>{
    setTicketTerms(null)
    if(!form.vehicle_id||!ticketService)return undefined
    let alive=true
    api(`/vehicles/${form.vehicle_id}/services`).then(r=>{if(alive)setTicketTerms((r.items||[]).find(x=>x.service_type_id===ticketService)||{service_type_id:ticketService,version:1,payment_mode:'ONLINE_ONLY'})}).catch(()=>{})
    return ()=>{alive=false}
  },[form.vehicle_id,ticketService])
  const loadDepartures=(h=history)=>api('/scheduled-trips?mine=true&limit=100'+(h?'&archived=true':'')).then(x=>setItems(x.items||[])).catch(setError)
  useEffect(()=>{
    api('/owners/me/vehicles').then(x=>setVehicles((x.items||[]).filter(v=>v.verification_status==='APPROVED'))).catch(setError).finally(()=>setVehiclesLoaded(true))
    api('/owners/me/routes').then(x=>setRoutes((x.items||[]).filter(r=>r.status==='ACTIVE'))).catch(setError)
    // The Owner may drive only when they hold an approved Driver role (the same check the Account page uses).
    Promise.all([api('/users/me'),api('/users/me/roles')]).then(([user,roles])=>setMe({id:user.id,driver:(user.approved_roles||[]).includes('DRIVER')&&(roles.items||[]).some(r=>r.role_code==='DRIVER'&&r.approval_status==='APPROVED')})).catch(()=>{})
    api('/owners/me/drivers').then(x=>setDrivers(x.items||[])).catch(()=>setDrivers([]))
    loadDepartures()
  },[])
  useEffect(()=>{if(tab===1)api('/owners/me/routes').then(x=>setRoutes((x.items||[]).filter(r=>r.status==='ACTIVE'))).catch(()=>{})},[tab])
  const vehicle=vehicles.find(v=>v.id===layoutVehicle)
  // Choosing a vehicle shows the layout already saved for it; the Owner edits from there.
  useEffect(()=>{setSaved(null);setLoaded(null);if(!layoutVehicle)return
    api(`/vehicles/${layoutVehicle}/seat-layout`).then(result=>{setSaved(result);setLoaded(result.seats.map(s=>({...s})))}).catch(e=>{if(e.status!==404)setError(e)})},[layoutVehicle])
  const built=useMemo(()=>buildSeats({left,right,rows:rowCount,back,front,sellFront,off}),[left,right,rowCount,back,front,sellFront,off])
  const seats=loaded||built
  const sold=seats.filter(s=>s.bookable).length
  const capacity=vehicle?.seat_capacity
  const overCapacity=capacity!=null&&sold>capacity
  const pick=key=>{const p=PRESETS[key];setLoaded(null);setPreset(key);setLeft(p.left);setRight(p.right);setRowCount(p.rows);setBack(p.back);setFront(p.front);setSellFront(p.sellFront);setOff(new Set())}
  const adjust=setter=>v=>{setLoaded(null);setter(v);setOff(new Set())}
  const width=left+1+right
  const toggle=s=>{
    if(s.type==='CREW')return
    if(loaded){setLoaded(loaded.map(x=>x.deck===s.deck&&x.row===s.row&&x.column===s.column?{...x,bookable:!x.bookable}:x));return}
    const key=`${s.row}-${s.column}`;const next=new Set(off);next.has(key)?next.delete(key):next.add(key);setOff(next)
  }

  async function saveLayout(){
    setBusy(true);setError(null);setNotice('')
    try{
      const result=await api(`/vehicles/${layoutVehicle}/seat-layout`,{method:'PUT',body:JSON.stringify({layout_version:(saved?.layout_version||0)+1,seats:seats.map(s=>({code:s.code,row:s.row,column:s.column,deck:s.deck,type:s.type,bookable:s.bookable}))})})
      setSaved(result);setLoaded(result.seats.map(s=>({...s})));setVehicleLayout(v=>({...v,[layoutVehicle]:signature(result.seats)}));setNotice(t('Seat layout saved. Passengers will see this picture.'))
    }catch(e){setError(e)}finally{setBusy(false)}
  }
  async function createDeparture(){
    setBusy(true);setError(null);setNotice('')
    const protectedPolicy=form.fulfilment_policy!=='FIXED_GUARANTEED'
    const departure=new Date(form.departure_at),arrival=new Date(form.estimated_arrival_at)
    if(!(departure>new Date())){setBusy(false);setError({message:t('Choose a departure date and time in the future.')});return}
    if(!(arrival>departure)){setBusy(false);setError({message:t('The arrival must be after the departure.')});return}
    const cutoff=new Date(departure.getTime()-Number(form.stop_before)*60000)
    if(cutoff<=new Date()){setBusy(false);setError({message:t('Bookings would already be closed. Choose a later departure or a shorter "Stop bookings at" time.')});return}
    const cutoffIso=cutoff.toISOString()
    try{
      await api('/scheduled-trips',{method:'POST',body:JSON.stringify({
        route_id:form.route_id,vehicle_id:form.vehicle_id,departure_at:iso(form.departure_at),estimated_arrival_at:iso(form.estimated_arrival_at),
        booking_cutoff_at:cutoffIso,fare_per_seat:String(form.fare_per_seat),fulfilment_policy:form.fulfilment_policy,
        minimum_confirmed_seats:protectedPolicy?Number(form.minimum_confirmed_seats):null,decision_deadline:protectedPolicy?iso(form.decision_deadline):null,
        accepted_time_window_minutes:Number(form.accepted_time_window_minutes||0),accepted_replacement_terms:{},
        operator_driver_user_id:chosenDriver(form.driver_choice)})})
      setForm(emptyDeparture);setNotice(t('Departure saved as a draft. Press Publish below when you are ready.'));loadDepartures();dw.setStep(0);setTab(2)
    }catch(e){setError(e.code==='DRIVER_NOT_ELIGIBLE'?{message:t('That person is not an approved Driver. Choose another Driver or drive it yourself.')}:e)}finally{setBusy(false)}
  }
  // A Driver found by reference joins the list like a listed Driver and becomes the choice.
  const useFound=choose=>driver=>{setDrivers(list=>(list||[]).some(d=>d.id===driver.id)?list:[...(list||[]),driver]);choose(driver.id)}
  const chosenDriver=choice=>choice==='me'?(me.driver?me.id:null):choice==='later'?null:choice
  const driverName=x=>!x.operator_driver_user_id?null:x.operator_driver_user_id===me.id?t('You (self-drive)'):(drivers||[]).find(d=>d.id===x.operator_driver_user_id)?.display_name||t('Driver assigned')
  async function assign(){
    const trip=assigning,driver=chosenDriver(driverPick)
    if(!driver){setError({message:t('Choose a Driver first.')});return}
    setBusy(true);setError(null);setNotice('')
    try{await api(`/scheduled-trips/${trip.id}`,{method:'PATCH',body:JSON.stringify({expected_version:trip.version,operator_driver_user_id:driver})});setNotice(t('Driver assigned. You can publish this departure now.'));setAssigning(null);setPickDriver('later');loadDepartures()}
    catch(e){
      if(e.code==='VERSION_CONFLICT'){setAssigning(null);loadDepartures();setError({message:t('This departure changed while you were choosing. It has been refreshed, so choose the Driver again.')})}
      else if(e.code==='DRIVER_NOT_ELIGIBLE')setError({message:t('That person is not an approved Driver. Choose another Driver or drive it yourself.')})
      else if(e.code==='DEPARTURE_NOT_FOUND'||e.status===404){setAssigning(null);loadDepartures();setError({message:t('This departure no longer exists. The list has been refreshed.')})}
      else if(e.code==='DEPARTURE_NOT_DRAFT'){setAssigning(null);loadDepartures();setError({message:t('Only a draft departure can change its Driver. The list has been refreshed.')})}
      else setError(e)
    }finally{setBusy(false)}
  }
  async function publish(x){
    setError(null);setNotice('')
    try{await api(`/scheduled-trips/${x.id}/publish`,{method:'POST',body:JSON.stringify({expected_version:x.version,publish_confirmed:true})});setNotice(t('Departure published. Passengers can now book it.'));loadDepartures()}
    catch(e){
      const text=String(e.message||'')
      if(e.code==='REPLACEMENT_REQUEST_DRAFT')setError({message:t(e.message)})
      else if(/cut-off has already passed/i.test(text))setError({message:t('The booking cut-off has passed. Choose a later departure time.')})
      else if(/departure must be in the future/i.test(text))setError({message:t('The departure time has passed. Choose a later departure time.')})
      else setError(e)
    }
  }
  const passedKind=x=>{if(x.status!=='DRAFT')return null;const now=Date.now();return new Date(x.departure_at).getTime()<=now?'departure':x.booking_cutoff_at&&new Date(x.booking_cutoff_at).getTime()<=now?'cutoff':null}
  // Move a draft to a later time: arrival and booking cut-off move by the same amount (PATCH /scheduled-trips/{id}, draft only).
  async function repeat(){
    const trip=retiming,start=new Date(newStart)
    if(!(start>new Date())){setError({message:t('Choose a departure date and time in the future.')});return}
    setBusy(true);setError(null);setNotice('')
    try{await api(`/scheduled-trips/${trip.id}/repeat`,{method:'POST',body:JSON.stringify({departure_at:start.toISOString()})});setNotice(t('Next trip saved as a draft. Publish it when you are ready. The finished trip moved to History.'));setRetiming(null);setRepeatMode(false);loadDepartures()}
    catch(e){setError(e.code==='ROUTE_NOT_AVAILABLE'?{message:t('This route is switched off. Open Routes, switch it on, then try again.')}:e)}finally{setBusy(false)}
  }
  async function archive(x){
    setBusy(true);setError(null);setNotice('')
    try{await api(`/scheduled-trips/${x.id}/archive`,{method:'POST',body:'{}'});setNotice(t('Removed from your list. It is kept in History.'));loadDepartures()}
    catch(e){setError(e)}finally{setBusy(false)}
  }
  async function retime(){
    const trip=retiming,start=new Date(newStart)
    if(!(start>new Date())){setError({message:t('Choose a departure date and time in the future.')});return}
    const shift=start.getTime()-new Date(trip.departure_at).getTime()
    const cutoff=new Date(new Date(trip.booking_cutoff_at).getTime()+shift)
    if(cutoff<=new Date()){setError({message:t('The booking cut-off would still be in the past. Choose a later departure time.')});return}
    setBusy(true);setError(null);setNotice('')
    try{await api(`/scheduled-trips/${trip.id}`,{method:'PATCH',body:JSON.stringify({expected_version:trip.version,departure_at:start.toISOString(),estimated_arrival_at:new Date(new Date(trip.estimated_arrival_at).getTime()+shift).toISOString(),booking_cutoff_at:cutoff.toISOString()})});setNotice(t('Departure time changed. You can publish this departure now.'));setRetiming(null);loadDepartures()}
    catch(e){
      if(e.code==='VERSION_CONFLICT'){setRetiming(null);loadDepartures();setError({message:t('This departure changed while you were editing. It has been refreshed, so choose the time again.')})}
      else if(e.code==='ROUTE_NOT_AVAILABLE'){setError({message:t('This route is switched off. Open Routes, switch it on, then try again.')})}
      else if(e.code==='DEPARTURE_NOT_DRAFT'){setRetiming(null);loadDepartures();setError({message:t('Only a draft departure can change its time. The list has been refreshed.')})}
      else if(e.code==='DEPARTURE_NOT_FOUND'||e.status===404){setRetiming(null);loadDepartures();setError({message:t('This departure no longer exists. The list has been refreshed.')})}
      else setError(e)
    }finally{setBusy(false)}
  }
  const set=k=>e=>setForm({...form,[k]:e.target.value})
  // A route with a price for each stop fixes the whole-trip price to its last stop's price.
  const chosenRoute=routes.find(r=>r.id===form.route_id)
  const routeWhole=chosenRoute?.stop_prices_enabled?chosenRoute.stops[chosenRoute.stops.length-1]?.price_from_start:null
  useEffect(()=>{if(routeWhole!=null&&form.fare_per_seat!==String(Number(routeWhole)))setForm(f=>({...f,fare_per_seat:String(Number(routeWhole))}))},[routeWhole])
  const protectedPolicy=form.fulfilment_policy!=='FIXED_GUARANTEED'

  const departureList=usePaged(items||[],Math.max(2,useRowCount(64)))
  // A published departure keeps the seats it was published with. For the departures on screen, compare them with the vehicle's current saved layout.
  const visibleKey=tab===2?departureList.slice.filter(x=>x.status!=='DRAFT').map(x=>`${x.id}:${x.vehicle_id}`).join(','):''
  useEffect(()=>{
    visibleKey.split(',').filter(Boolean).forEach(pair=>{
      const [id,vehicleId]=pair.split(':')
      if(tripLayout[id]===undefined){setTripLayout(c=>({...c,[id]:null}));api(`/scheduled-trips/${id}/seats`).then(r=>setTripLayout(c=>({...c,[id]:signature(r.seats)}))).catch(()=>{})}
      if(vehicleId&&vehicleLayout[vehicleId]===undefined){setVehicleLayout(c=>({...c,[vehicleId]:null}));api(`/vehicles/${vehicleId}/seat-layout`).then(r=>setVehicleLayout(c=>({...c,[vehicleId]:signature(r.seats)}))).catch(()=>{})}
    })
  },[visibleKey])
  // A draft has no seat rows yet (they are created on publish), so its list entry carries available_seats 0 which is not a real count.
  // Show the bookable seats of the vehicle's saved layout instead, or a neutral line when that is not known.
  const draftKey=tab===2?departureList.slice.filter(x=>x.status==='DRAFT'&&x.vehicle_id).map(x=>x.vehicle_id).join(','):''
  useEffect(()=>{
    draftKey.split(',').filter(Boolean).forEach(id=>{
      if(draftSeats[id]!==undefined)return
      setDraftSeats(c=>({...c,[id]:null}))
      api(`/vehicles/${id}/seat-layout`).then(r=>setDraftSeats(c=>({...c,[id]:(r.seats||[]).filter(x=>x.bookable).length}))).catch(()=>{})
    })
  },[draftKey])
  const seatsText=x=>x.status==='DRAFT'?(draftSeats[x.vehicle_id]>0?t('{value0} seats when published',{value0:draftSeats[x.vehicle_id]}):t('Seats are created when you publish')):x.available_seats!=null?t('{value0} seats open',{value0:x.available_seats}):''
  const isOlder=x=>x.status!=='DRAFT'&&tripLayout[x.id]&&vehicleLayout[x.vehicle_id]&&tripLayout[x.id]!==vehicleLayout[x.vehicle_id]
  // Every step is checked again when the draft is saved: the first step with a problem is shown.
  const badPane=()=>panes.findIndex(p=>p.current&&[...p.current.querySelectorAll('input,select,textarea')].some(el=>!el.disabled&&!el.checkValidity()))
  function submitDeparture(e){
    e.preventDefault()
    const bad=badPane()
    if(bad>=0){dw.setStep(bad);requestAnimationFrame(()=>checkPane(panes[bad].current));return}
    createDeparture()
  }
  const nextDeparture=()=>{if(checkPane(panes[dw.step].current).valid)dw.forward()}
  const tabs=[[0,'1 · '+t('Seat layout'),'car'],[3,'2 · '+t('Routes'),'route'],[1,'3 · '+t('New departure'),'calendar'],[2,'4 · '+t('Your departures'),'ticket']].map(([id,label,icon])=>({label,icon,active:tab===id,onClick:()=>{setTab(id);if(id===3)setRouteMode('list')}}))
  const stepNames=tab===0?[t('Vehicle and type'),t('Seats')]:[t('Route and time'),t('Arrival and price'),t('Type and driver')]

  return <><Header/><FlowShell heading={t('Ticket')} icon="ticket" title={[t('Vehicle seat layout'),t('Create a departure draft'),t('Your departures'),routeMode==='form'?t('Add a route'):t('Your routes')][tab]}
    info={[t('Describe each vehicle’s seats once, then publish scheduled departures. Passengers see exactly the seats you define.'),t('Save a draft, then publish it from Your departures when you are ready.'),t('Publish a draft when you are ready for passengers to book it.'),t('The roads your buses and vans run Ticket trips on, with seats.')][tab]}
    tabs={tabs} steps={tab===3?undefined:tab<2?stepNames:undefined} current={tab===3?routeStep:tab===0?lw.step:dw.step}>
    <Compact.Provider value={true}>
    <ErrorNotice error={error}/><Notice>{notice}</Notice>

    <div className="tk-pane" hidden={tab!==3}>{tab===3&&<RoutesPanel mode={routeMode} setMode={setRouteMode} onStep={setRouteStep} onGoDepartures={()=>setTab(1)}/>}</div>
    <div className="tk-pane" hidden={tab!==0}>
      <div className="tk-pane" hidden={lw.step!==0}>
        <div className="tk-grid" style={{'--cols':2}}>
          <Field label="Vehicle" help="Only approved vehicles can have a seat layout."><select name="seat-vehicle" value={layoutVehicle} onChange={e=>setLayoutVehicle(e.target.value)}>
            <option value="">{t('Choose an approved vehicle')}</option>
            {vehicles.map(v=><option key={v.id} value={v.id}>{v.label||v.reference} · {t('{value0} seats',{value0:v.seat_capacity??'?'})}</option>)}
          </select></Field>
        </div>
        <div className="tk-bar" role="group" aria-label={t('Vehicle type')}><strong className="tk-line">{t('Vehicle type')}</strong>
          {Object.entries(PRESETS).map(([k,p])=><Chip key={k} tone="info" selected={!loaded&&preset===k} onClick={()=>pick(k)}>{t(p.label)}</Chip>)}</div>
        {saved&&<p className="tk-line">{loaded?t('Showing the saved layout: version {value0}, {value1} bookable seats. Saving replaces it with a new version.',{value0:saved.layout_version,value1:signature(saved.seats).split('|').filter(Boolean).length}):t('Starting a new layout. Saving replaces version {value0} with a new version.',{value0:saved.layout_version})}</p>}
        {layoutVehicle&&!saved&&<p className="tk-line">{t('This vehicle has no saved seat layout yet. Choose a vehicle type to start.')}</p>}
        {vehiclesLoaded&&!error&&vehicles.length===0&&<Empty>{t('You have no approved vehicles yet.')}</Empty>}
      </div>
      <div className="tk-split" hidden={lw.step!==1}>
        <div className="tk-side">
          {loaded
            ?<>
              <p className="tk-line">{t('This is the layout saved for this vehicle. Passengers see exactly this picture.')}</p>
              <div className="tk-bar"><button type="button" className="ui-button ui-button-secondary" onClick={()=>setLoaded(null)}>{t('Start a new layout')}</button></div>
            </>
            :<>
              <Counter label={t('Rows of seats')} value={rowCount} min={1} max={24} onChange={adjust(setRowCount)}/>
              <Counter label={t('Seats on the left')} hint={t('(door side)')} value={left} min={1} max={4} onChange={adjust(setLeft)}/>
              <Counter label={t('Seats on the right')} value={right} min={1} max={4} onChange={adjust(setRight)}/>
              <Counter label={t('Seats in the back row')} hint={back===0?t('(no back row)'):''} value={back} min={0} max={width} onChange={adjust(setBack)}/>
              <div className="tk-checks">
                <label><input type="checkbox" checked={front===1} onChange={e=>{setFront(e.target.checked?1:0);setOff(new Set())}}/> {t('Seat beside the Driver')}</label>
                {front===1&&<label><input type="checkbox" checked={sellFront} onChange={e=>setSellFront(e.target.checked)}/> {t('Sell the seat beside the Driver')}</label>}
              </div>
            </>}
          <p className="tk-line">{t('Tap a seat in the picture to mark it “Not for sale” (grey). Tap again to sell it. The Driver seat (steering wheel) is never sold. Seats are numbered for you.')}</p>
          <p className="tk-line">{t('Bookable seats:')} <strong>{sold}</strong>{capacity!=null&&<> {t('of vehicle capacity {value0}',{value0:capacity})}</>} {overCapacity&&<Chip tone="danger" icon="alert">{t('More than the vehicle capacity')}</Chip>}</p>
        </div>
        <div className="tk-map"><SeatMap seats={seats} editable onToggle={toggle} label={t('New seat layout preview')}/></div>
      </div>
      <div className="flow-actions">
        {lw.step>0?<button type="button" className="ui-button ui-button-secondary" onClick={lw.back}>{t('Back')}</button>:<span/>}
        {lw.step===0
          ?<button type="button" className="ui-button ui-button-primary" disabled={!layoutVehicle} onClick={lw.forward}>{t('Next')}</button>
          :<button type="button" className="ui-button ui-button-primary" disabled={busy||!sold||overCapacity} onClick={saveLayout}>{busy?t('Saving…'):t('Save seat layout')}</button>}
      </div>
    </div>

    <form className="flow-wizard-form tk-pane" hidden={tab!==1} noValidate onSubmit={submitDeparture}>
      <div ref={panes[0]} className="tk-pane" hidden={dw.step!==0}>
        <div className="tk-grid" style={{'--cols':2}}>
          <Field label="Route"><select required name="route" value={form.route_id} onChange={e=>setForm({...form,route_id:e.target.value})}><option value="">{t('Choose a route')}</option>{routes.map(r=><option key={r.id} value={r.id}>{r.origin_name} → {r.destination_name}</option>)}</select></Field>
          <Field label="Vehicle"><select required name="vehicle" value={form.vehicle_id} onChange={set('vehicle_id')}><option value="">{t('Choose a vehicle')}</option>{vehicles.map(v=><option key={v.id} value={v.id}>{v.label||v.reference}</option>)}</select></Field>
          <DateTimeFields dateLabel="Departure date" timeLabel="Departure time" help="When the vehicle leaves." value={form.departure_at} min={toLocal(new Date()).slice(0,10)} onChange={v=>{
            const mins=chosenRoute?.estimated_duration_minutes
            setForm(f=>({...f,departure_at:v,...(f.arrival_auto&&v&&mins?{estimated_arrival_at:toLocal(new Date(new Date(v).getTime()+mins*60000))}:{})}))}}/>
        </div>
        {routes.length===0&&<p className="tk-line">{t('You have no routes yet.')} <button type="button" className="inline-link" onClick={()=>setTab(3)}>{t('Add a route')}</button> {t('first.')}</p>}
      </div>
      <div ref={panes[1]} className="tk-pane" hidden={dw.step!==1}>
        <div className="tk-grid" style={{'--cols':2}}>
          <DateTimeFields dateLabel="Arrival date" timeLabel="Arrival time" help={chosenRoute?.estimated_duration_minutes?'When it reaches the end. Filled in from the route duration; you can change it.':'When it reaches the end.'} value={form.estimated_arrival_at} min={form.departure_at?form.departure_at.slice(0,10):undefined}
            onChange={v=>setForm(f=>({...f,estimated_arrival_at:v,arrival_auto:false}))}/>
          <Field label="Stop bookings at" help={form.departure_at?t('Passengers can book until {value0}.',{value0:nice(new Date(new Date(form.departure_at).getTime()-Number(form.stop_before)*60000))}):'Passengers cannot book after this time.'}>
            <select name="stop_before" value={form.stop_before} onChange={set('stop_before')}>{STOP_OPTIONS.map(([v,label])=><option key={v} value={v}>{t(label)}</option>)}</select></Field>
          <Field label="Price for the whole trip, per seat (LKR)" help={routeWhole!=null?'This route has a price for each stop, so the whole-trip price comes from the route. Passengers who travel part of the way pay less.':'What each passenger pays for the whole trip.'}>
            <input required name="fare" min="0" step="0.01" type="number" value={form.fare_per_seat} disabled={routeWhole!=null} onChange={set('fare_per_seat')}/></Field>
        </div>
        {form.vehicle_id&&ticketService&&<CashSwitch vehicle={form.vehicle_id} service={ticketService} saved={ticketTerms} onSaved={setTicketTerms} allowNew/>}
      </div>
      <div ref={panes[2]} className="tk-pane" hidden={dw.step!==2}>
        <div className="tk-driver-split">
        <div className="tk-grid" style={{'--cols':2}}>
          <Field label="Departure type" help={protectedPolicy?'The departure is confirmed only when enough seats are booked.':'The departure runs on the day whatever the number of bookings.'}>
            <select name="policy" value={form.fulfilment_policy} onChange={set('fulfilment_policy')}>
              <option value="FIXED_GUARANTEED">{t('Fixed, guaranteed departure')}</option>
              <option value="MINIMUM_SEATS_WITH_PROTECTED_FULFILMENT">{t('Minimum seats with protected fulfilment')}</option></select></Field>
          <Field label="Time window (min)" optional help="How many minutes the departure time may move. Leave 0 if the departure time is fixed."><input name="window" min="0" max="1440" type="number" value={form.accepted_time_window_minutes} onChange={set('accepted_time_window_minutes')}/></Field>
          {protectedPolicy&&<>
            <Field label="Minimum confirmed seats" help="How many seats must be booked for this departure to be confirmed."><input required name="minseats" min="1" type="number" value={form.minimum_confirmed_seats} onChange={set('minimum_confirmed_seats')}/></Field>
            <DateTimeFields dateLabel="Decision deadline date" timeLabel="Decision deadline time" help="You decide by this time." value={form.decision_deadline} min={toLocal(new Date()).slice(0,10)} onChange={v=>setForm(f=>({...f,decision_deadline:v}))}/></>}
        </div>
        <div className="tk-driver-col">
          <Field label="Who will drive?" help="Choose yourself (if you are an approved Driver) or one of your Drivers. You can also assign a Driver later, but one is needed before you publish.">
            <select name="driver" value={form.driver_choice} onChange={set('driver_choice')}>
              <option value="later">{t('Assign later')}</option>
              <DriverOptions drivers={drivers} me={me}/></select></Field>
          <DriverFinder onUse={useFound(id=>setForm(f=>({...f,driver_choice:id})))}/>
          <DriverInfo choice={form.driver_choice} drivers={drivers} me={me} onSelf={()=>setForm(f=>({...f,driver_choice:'me'}))}/>
        </div>
        </div>
      </div>
      <div className="flow-actions">
        {dw.step>0?<button type="button" className="ui-button ui-button-secondary" onClick={dw.back}>{t('Back')}</button>:<span/>}
        {dw.step<2
          ?<button key="next" type="button" className="ui-button ui-button-primary" onClick={nextDeparture}>{t('Next')}</button>
          :<button key="save" type="submit" className="ui-button ui-button-primary" disabled={busy}>{busy?t('Saving…'):t('Save draft')}</button>}
      </div>
    </form>

    <div className="tk-pane" hidden={tab!==2}>
      {managing?<DepartureFulfilment key={`${managing.id}-${managing.version}`} departure={items?.find(i=>i.id===managing.id)||managing} onBack={()=>setManaging(null)}
        onProblem={text=>{setManaging(null);setNotice('');setError({message:text});loadDepartures()}}
        onDone={async(action,result)=>{setManaging(null);setError(null);setNotice(action==='commit'?t('Departure committed. Passengers who paid are told it will run.'):action==='replace'?t('Replacement vehicle set. {value0} seats moved. Passengers who paid can accept the change or reject it for a full refund.',{value0:result?.moved_seats??0}):action==='request'?t('Request sent. Waiting for the other Owner to answer.'):result?.status==='CANCELLED'?t('Departure withdrawn. Nobody had paid for it.'):t('Reported. Selling has stopped and Travelly will arrange the journey for passengers who paid.'));await loadDepartures()}}/>
      :retiming?<>
        <p className="tk-line"><strong>{retiming.route?.origin_name} → {retiming.route?.destination_name}</strong> · {repeatMode?t('Last trip'):t('Now')}: {nice(retiming.departure_at)}</p>
        <div className="tk-grid" style={{'--cols':2}}>
          <DateTimeFields dateLabel="New departure date" timeLabel="New departure time" help={repeatMode?'Same route, vehicle, price and rules. Arrival and the booking cut-off move by the same amount.':'Arrival and the booking cut-off move by the same amount.'} value={newStart} min={toLocal(new Date()).slice(0,10)} onChange={setNewStart}/>
        </div>
        <div className="flow-actions"><button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={()=>{setRetiming(null);setRepeatMode(false)}}>{t('Back to list')}</button>
          <button type="button" className="ui-button ui-button-primary" disabled={busy||!newStart} onClick={repeatMode?repeat:retime}>{busy?t('Saving…'):repeatMode?t('Create next trip'):t('Save new time')}</button></div>
      </>:assigning?<>
        <p className="tk-line"><strong>{assigning.route?.origin_name} → {assigning.route?.destination_name}</strong> · {nice(assigning.departure_at)}</p>
        <div className="tk-grid" style={{'--cols':2}}>
          <Field label="Driver" help="Only people you have worked with are listed. A Driver must be approved by Travelly."><select name="assign-driver" value={driverPick} onChange={e=>setPickDriver(e.target.value)}>
            <option value="later">{t('Choose a Driver')}</option><DriverOptions drivers={drivers} me={me}/></select></Field>
        </div>
        <DriverFinder onUse={useFound(setPickDriver)}/>
        <DriverInfo choice={driverPick} drivers={drivers} me={me} onSelf={()=>setPickDriver('me')}/>
        <div className="flow-actions"><button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={()=>{setAssigning(null);setPickDriver('later')}}>{t('Back to list')}</button>
          <button type="button" className="ui-button ui-button-primary" disabled={busy||driverPick==='later'} onClick={assign}>{busy?t('Saving…'):t('Assign driver')}</button></div>
      </>:<>
      {!history&&items?.some(x=>isOver(x)&&x.status!=='CANCELLED')&&<p className="tk-line tk-finished"><Icon name="check" size={16} aria-hidden="true"/> {t('A trip has finished. Is the next trip on the same route? Press Repeat for next trip and choose the new date and time, or remove it from your list.')}</p>}
      {items===null?<p role="status">{t('Loading departures…')}</p>:items.length
        ?<div className="tk-rows">{departureList.slice.map(x=><article className="tk-row" key={x.id}>
          <div className="tk-row-main"><strong>{x.route?.origin_name} → {x.route?.destination_name}</strong>
            <span>{nice(x.departure_at)} · {x.vehicle?.display_name||`${x.vehicle?.make} ${x.vehicle?.model}`} · {t('LKR {value0} per seat',{value0:x.fare_per_seat})}{seatsText(x)&&` · ${seatsText(x)}`}{x.status==='DRAFT'&&(driverName(x)?` · ${t('Driver')}: ${driverName(x)}`:` · ${t('No Driver yet')}`)}</span></div>
          <div className="tk-row-actions">
            {isOlder(x)&&<><Chip tone="danger" icon="alert">{t('Older seat layout')}</Chip><InfoTip>{t('This departure uses an older seat layout than the one now saved for its vehicle. Passengers see the layout it was published with.')}</InfoTip></>}
            <Chip tone={statusChip(x.status).tone}>{statusChip(x.status).label}</Chip>
            {isOver(x)&&<>{!['COMPLETED','CANCELLED'].includes(x.status)&&<Chip tone="muted" icon="alert">{t('Departure time has passed')}</Chip>}{x.status==='COMPLETED'&&<InfoTip>{t('This trip is finished. Repeat it for the next trip on the same route, or remove it from your list. It stays saved in History.')}</InfoTip>}
              <button type="button" className="ui-button ui-button-primary" onClick={()=>{setError(null);setNotice('');setNewStart('');setRepeatMode(true);setRetiming(x)}}>{t('Repeat for next trip')}</button>
              {!x.archived_at&&<button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={()=>archive(x)}>{t('Remove from list')}</button>}</>}
            {canManage(x)&&<button type="button" className="ui-button ui-button-secondary" onClick={()=>{setError(null);setNotice('');setManaging(x)}}>{t('Manage')}</button>}
            {x.status==='DRAFT'&&!x.operator_driver_user_id&&<button type="button" className="ui-button ui-button-secondary" onClick={()=>{setError(null);setNotice('');setPickDriver('later');setAssigning(x)}}>{t('Assign driver')}</button>}
            {passedKind(x)&&<><Chip tone="danger" icon="alert">{passedKind(x)==='departure'?t('Departure time has passed'):t('Booking cut-off has passed')}</Chip><InfoTip>{t('Create a new departure with a later time, or use Edit time to move this draft.')}</InfoTip>
              <button type="button" className="ui-button ui-button-secondary" onClick={()=>{setError(null);setNotice('');setNewStart('');setRetiming(x)}}>{t('Edit time')}</button></>}
            {x.status==='DRAFT'&&!x.archived_at&&<button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={()=>archive(x)}>{t('Remove from list')}</button>}
            {x.status==='DRAFT'&&<span title={passedKind(x)?t('The time has passed. Edit the time or create a new departure with a later time.'):undefined}><button type="button" className="ui-button ui-button-primary" disabled={Boolean(passedKind(x))} onClick={()=>publish(x)}>{t('Publish')}</button></span>}</div></article>)}</div>
        :<Empty>{history?t('No departures in History yet.'):t('No ticket departures. Save a seat layout, then create a draft departure.')}</Empty>}
      <div className="flow-actions">{departureList.pages>1?departureList.pager:<span/>}<span className="tk-foot-btns"><button type="button" className="ui-button ui-button-secondary" onClick={()=>{const h=!history;setHistory(h);setItems(null);loadDepartures(h)}}>{history?t('Back to departures'):t('History')}</button><button type="button" className="ui-button ui-button-primary" onClick={()=>setTab(1)}>{t('New departure')}</button></span></div>
      </>}
    </div>
    </Compact.Provider>
  </FlowShell></>
}
