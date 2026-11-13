import { t, getLanguage } from '../i18n/language.js'
import React,{useEffect,useState} from 'react'
import {Link,useLocation,useNavigate} from 'react-router-dom'
import {api} from '../services/api'
import {Asset,ErrorNotice,Header,Icon} from './components'
import {BookingPipeline} from './TravellyVisuals'
import {ItineraryPreview,PlatformMapPlaceholder,TravellyAiPanel,TravellyHelp,UnavailableFeature} from './ReferenceWidgets'
import VehiclePhoto from './VehiclePhoto'
import ProfileAuth from '../features/auth/ProfileAuth'
import ProfileDetails,{PROFILE_FORM_ID} from '../features/auth/ProfileDetails'
import {Chip} from './ui'
import ApplicationStatusNotices from './ApplicationStatusNotices'
import {useWorkspace} from '../context/workspaceContext'
import {accountPath,personalBookingPath,withWorkspace,workspaceMenu,workspaceRoles} from '../routes/workspaceRoutes'
import {displayTime,loadBookings,pendingBooking,tripRoute,useWorkspaceData,words} from '../hooks/workspaceData'
import {FlowShell,usePaged,useRowCount} from '../features/booking/flow/FlowParts'
import InfoTip from './ui/InfoTip'
import EmptyState from './ui/EmptyState'
import {reminderKind,reminderLink} from '../features/notifications/reminders'
import {isExpired,isRoadAlertNotice,noticeBookingId} from '../features/notifications/notices'
import TripInProgressCard from '../features/trips/TripInProgressCard'
import {useActiveTrips} from '../features/trips/tripHooks'
import CommissionBanner from '../features/settlements/CommissionBanner'
import ReelsCard,{useReelsPreview} from '../features/social/ReelsCard'

function Resource({resource,children,empty='Nothing here yet.'}){if(resource.loading)return <p className="workspace-loading" role="status"><span className="spinner"/>{t(" Loading…")}</p>;if(resource.error)return <div className="workspace-resource-error"><h3>{[401,403].includes(resource.error.status)?t('Access unavailable'):t('Unable to load this information')}</h3><ErrorNotice error={resource.error}/><button className="button outline" onClick={resource.reload}>{t("Try again")}</button></div>;if(!resource.data)return <p>{t(empty)}</p>;return children(resource.data)}
function Empty({icon='calendar',title,children,to,action}){return <div className="workspace-empty"><Icon name={icon} size={30}/><h3>{t(title)}</h3><p>{children}</p>{to&&<Link className="button outline" to={to}>{t(action)||t('Explore')}<Icon name="arrow" size={17}/></Link>}</div>}
function BookingsList({items,role,empty='No journeys to show yet.',limit=4,personal=false,operation=false}){return items.length?<div className="workspace-record-list">{items.slice(0,limit).map(b=><Link className="workspace-record" key={b.id} to={operation&&b.trip?.id?withWorkspace('/trips/'+b.trip.id+'/operation',role):personal?personalBookingPath(role,b.id):withWorkspace('/bookings/'+b.id,role)}><span className="workspace-record-icon"><Icon name="car"/></span><div><strong>{tripRoute(b)}</strong><span>{b.reference} · {displayTime(b.start_at)}</span></div><span className={'workspace-badge '+(b.status==='CONFIRMED'||b.status==='COMPLETED'?'positive':'')}>{t(words(b.status))}</span><Icon name="arrow" size={16}/></Link>)}</div>:<Empty title={empty}>{t("Your real journeys and their current status will appear here.")}</Empty>}
const sortTrips=items=>[...items].sort((a,b)=>new Date(a.start_at)-new Date(b.start_at))
const activeAssignment=b=>pendingBooking(b)&&['PENDING','ACCEPTED'].includes(b.trip?.assignment_status)&&b.trip?.status!=='CANCELLED'
const bookingScope='Latest 100 accessible booking records. Counts describe this returned set, not lifetime totals. Times are in Sri Lanka.'

function CalendarPreview({vehicles,limit=2}){
 const [selected,setSelected]=useState(''),id=vehicles.some(v=>v.id===selected)?selected:vehicles[0]?.id
 const [start]=useState(()=>new Date().toISOString()),end=new Date(new Date(start).getTime()+7*86400000).toISOString()
 const calendar=useWorkspaceData(()=>id?api('/vehicles/'+id+'/calendar?'+new URLSearchParams({start_at:start,end_at:end})):Promise.resolve(null),[id,start])
 return <section className="dash-tile b-2"><header><h3><Icon name="clock" size={18}/>{t("Vehicle availability")}<InfoTip>{t("Awaiting-driver bookings remain reserved. Open the full calendar to review sources, dated blocks and their history.")}</InfoTip></h3><Link to={id?'/owner/vehicles/'+id+'/calendar':'/owner/vehicles'}>{t(id?'Open calendar':'My vehicles')}</Link></header>{id?<><label className="workspace-select">{t("Vehicle")}<select value={id} onChange={e=>setSelected(e.target.value)}>{vehicles.map(v=><option value={v.id} key={v.id}>{v.label||v.registration_number||v.reference}</option>)}</select></label><Resource resource={calendar}>{result=>result.complete?<><p className="workspace-note">{t("Next seven days · ")}{t(words(result.availability_status))} · {t(words(result.verification_status))}{t(". Checked ")}{displayTime(result.checked_at)}.</p>{result.events?.filter(e=>e.restricts).length?<div className="workspace-timeline dash-timeline">{result.events.filter(e=>e.restricts).slice(0,limit).map(e=><div key={e.source+e.id}><span className="workspace-timeline-dot"/><div><strong>{e.source==='BLOCK'?t(words(e.kind)):e.reference}</strong><span>{displayTime(e.start_at)} → {displayTime(e.end_at)}</span><small>{t(words(e.status))}</small>{e.affected_commitments?.length>0&&<p className="workspace-warning">{t("Admin support required. Affected commitments remain protected.")}</p>}</div></div>)}</div>:<p>{t("No dated restrictions in this window. Vehicle eligibility is rechecked before commitment.")}</p>}</>:<p className="workspace-warning" role="alert">{t("Availability is incomplete. Do not use this preview for new availability decisions.")}</p>}</Resource>{calendar.error&&<p className="workspace-warning">{t("Availability is incomplete. Bookings, trips, departures and blocks must all be checked.")}</p>}</>:<p className="dash-soft">{t("Add a vehicle to review its commitments and blocks.")}</p>}</section>
}
export function DashStat({icon,label,value,to,note,tone='blue'}){return <Link className={'dash-stat tone-'+tone} to={to} title={note?t(note):undefined}><span className="dash-stat-icon"><Icon name={icon} size={22}/></span><div><span>{t(label)}</span><strong>{t(value)}</strong></div></Link>}
export function Tile({icon,title,tip,to,link,className='',children}){return <section className={'dash-tile '+className}><header><h3><Icon name={icon} size={18}/>{t(title)}{tip&&<InfoTip>{tip}</InfoTip>}</h3>{to&&<Link to={to}>{t(link)}</Link>}</header><div className="dash-tile-body">{children}</div></section>}
export function Soft({children}){return <p className="dash-soft">{children}</p>}
export function DashPage({title,subtitle,stats,hero=null,children}){
 useEffect(()=>{document.title=t(title)+' | Travelly'},[title,getLanguage()])
 return <main className="dash-page" id="main"><div className="dash-hero"><h1>{title}</h1><p>{subtitle}</p></div>{hero}<div className="dash-stats">{stats}</div><div className="dash-grid">{children}</div></main>
}
function DashChart({items}){
 const groups=[['Requested',['REQUESTED']],['Awaiting driver',['AWAITING_DRIVER','OWNER_ACTION_REQUIRED']],['Confirmed',['CONFIRMED']],['On trip',['IN_PROGRESS']],['Completed',['COMPLETED']]]
 const counts=groups.map(([,s])=>items.filter(b=>s.includes(b.status)).length),max=Math.max(1,...counts)
 return <div className="dash-chart" role="img" aria-label={t("Booking status across the latest returned records")}>{groups.map(([label],i)=><div className="dash-chart-row" key={label}><span>{t(label)}</span><div className="dash-chart-track"><i style={{width:`${counts[i]/max*100}%`}}/></div><strong>{counts[i]}</strong></div>)}</div>
}
function DashVehicle({v}){
 const photo=v.photos?.find(p=>p.status!=='REMOVED'&&p.variants?.length)
 return <Link className="dash-vehicle" to={'/owner/vehicles/'+v.id}><span className="dash-vehicle-art">{photo?<VehiclePhoto photo={photo} privatePreview alt={v.label||v.reference}/>:<Icon name="car" size={24} aria-hidden="true"/>}</span><div><strong title={v.label||v.reference}>{v.label||v.reference}</strong><span className="status-chips"><span>{v.registration_number}</span><Chip tone={v.verification_status==='APPROVED'?'success':v.verification_status==='REJECTED'?'danger':'muted'}>{t(words(v.verification_status))}</Chip></span></div></Link>
}
export function DashList({items,role}){return <div className="dash-list">{items.map(b=><Link className="dash-row" key={b.id} to={withWorkspace('/bookings/'+b.id,role)}><Icon name="car" size={16}/><div><strong>{tripRoute(b)}</strong><span>{b.reference} · {displayTime(b.start_at)}</span></div><Chip tone={b.status==='CONFIRMED'||b.status==='COMPLETED'?'success':'muted'}>{t(words(b.status))}</Chip></Link>)}</div>}
export function DashLinks({items}){return <div className="dash-links">{items.map(([label,to,icon])=><Link key={label} className="dash-link" to={to} title={t(label)} aria-label={t(label)}><Icon name={icon} size={18}/><span>{t(label)}</span></Link>)}</div>}
export function useDashRows(){const [h,setH]=useState(typeof window==='undefined'?900:window.innerHeight);useEffect(()=>{const f=()=>setH(window.innerHeight);window.addEventListener('resize',f);return()=>window.removeEventListener('resize',f)},[]);return h<700?2:h<900?3:h<1200?4:6}
export const bookingsNote=(r,fn)=>r.loading?<Soft>{t(" Loading…")}</Soft>:r.error?<Soft>{t("Unable to load this information")}</Soft>:fn(r.data)
export function OwnerDashboard(){
 const {user}=useWorkspace(),trips=useActiveTrips(),reels=useReelsPreview(),settlements=useWorkspaceData(()=>api('/owners/me/settlements',{cache:'no-store'}),[user.id]),fleet=useWorkspaceData(()=>api('/owners/me/vehicles?page=1&page_size=4'),[user.id]),bookings=useWorkspaceData(()=>loadBookings(user.id,'OWNER'),[user.id]),first=(user.display_name||user.full_name).trim().split(/\s+/)[0]
 const rows=useDashRows(),list=sortTrips(bookings.data||[]).slice(0,rows-1)
 const vehicleCount=fleet.loading?'?':fleet.error?'Unavailable':fleet.data?.total??fleet.data?.items?.length??0
 return <DashPage title={t('Grow every journey, {name}.',{name:first})} subtitle={t("Your fleet moves Sri Lanka. Here's what's happening today.")} hero={<><CommissionBanner standing={settlements.data?.commission_standing} currency={settlements.data?.currency||'LKR'}/><TripInProgressCard items={trips.items}/></>}
  stats={<><DashStat icon="car" label="Your fleet" value={vehicleCount} to="/owner/vehicles" note="Registered vehicles"/><DashStat tone="red" icon="ticket" label="Open booking records" value={bookings.loading?'?':bookings.error?'Unavailable':bookings.data.filter(pendingBooking).length} note="Latest returned records" to="/owner/bookings"/><DashStat icon="calendar" label="Vehicle availability" value="Calendar" to="/owner/vehicles" note="Review dated commitments"/><DashStat tone="red" icon="wallet" label="Earnings" value={'—'} to="/owner/earnings" note="Ledger not available yet"/></>}>
  <Tile className="a-main" icon="car" title="Fleet at a glance" tip={t("Your vehicles and their current review status.")} to="/owner/vehicles" link="View fleet">
   <Resource resource={fleet}>{result=>result.items?.length?<div className="dash-vehicles">{result.items.map(v=><DashVehicle key={v.id} v={v}/>)}</div>:<Soft>{t("Add and verify a vehicle before publishing it for hire.")} <Link to="/owner/vehicles">{t("Add a vehicle")}</Link></Soft>}</Resource></Tile>
  <Tile className="a-side" icon="chart" title="Booking activity" tip={t("Status across your latest returned bookings.")+' '+t("Current records, not a revenue or historical trend forecast.")}>{bookingsNote(bookings,items=><DashChart items={items}/>)}</Tile>
  <Tile className="b-1" icon="calendar" title="Recent customer bookings" tip={t(bookingScope)} to="/owner/bookings" link="View all">{bookingsNote(bookings,()=>list.length?<DashList items={list} role="OWNER"/>:<Soft>{t("No customer bookings yet")}</Soft>)}</Tile>
  {fleet.loading?<Tile className="b-2" icon="clock" title="Vehicle availability"><Soft>{t("Loading vehicles…")}</Soft></Tile>:fleet.error?<Tile className="b-2" icon="clock" title="Vehicle availability"><Soft>{t("Availability is incomplete because your fleet could not be loaded.")}</Soft></Tile>:<CalendarPreview vehicles={fleet.data?.items||[]} limit={rows>3?3:1}/>}
  <Tile className="b-3" icon="spark" title="Quick actions"><DashLinks items={[['Add a vehicle','/owner/vehicles','car'],['Assignments & self-drive','/owner/assignments','users'],['Upload documents',accountPath('OWNER','owner'),'document'],['Review services','/owner/rates','settings']]}/></Tile>
  <ReelsCard className="c-main" state={reels}/>
  <Tile className="c-mid" icon="route" title="Travelling yourself?" tip={t("Book as a Passenger using your existing account. Your personal trips stay separate from customer bookings and assigned work.")}><DashLinks items={[["Book a ride for myself",'/owner/travel/hire','car'],['My personal trips','/owner/travel/bookings','calendar']]}/></Tile>
  <TravellyAiPanel className="dash-tile c-side"/>
 </DashPage>
}
const today=()=>new Date().toLocaleDateString('en-CA',{timeZone:'Asia/Colombo'})
export function DriverDashboard(){
 const {user}=useWorkspace(),trips=useActiveTrips(),reels=useReelsPreview(),assignments=useWorkspaceData(()=>loadBookings(user.id,'DRIVER'),[user.id]),first=(user.display_name||user.full_name).trim().split(/\s+/)[0],next=sortTrips((assignments.data||[]).filter(activeAssignment))[0]
 const rows=useDashRows(),stops=next?.itinerary?.itinerary?.stops||[],shown=stops.length>rows?[...stops.slice(0,rows-1),stops[stops.length-1]]:stops
 const count=f=>assignments.loading?'?':assignments.error?'Unavailable':f(assignments.data),first_=stops[0]?.place?.label,last_=stops[stops.length-1]?.place?.label
 const todays=b=>new Date(b.start_at).toLocaleDateString('en-CA',{timeZone:'Asia/Colombo'})===today()
 return <DashPage title={t('Ready for the road, {name}?',{name:first})} subtitle={t('Great journeys start with great drivers. Stay safe, keep moving!')} hero={<TripInProgressCard items={trips.items}/>}
  stats={<><DashStat label="Today's trips" icon="car" value={count(d=>d.filter(b=>(activeAssignment(b)||b.status==='COMPLETED')&&todays(b)).length)} to="/driver/assignments" note="Latest returned records"/><DashStat tone="green" label="Completed" icon="check" value={count(d=>d.filter(b=>b.status==='COMPLETED').length)} to="/driver/trip-history" note="Latest returned records"/><DashStat label="Upcoming" icon="calendar" value={count(d=>d.filter(b=>activeAssignment(b)&&new Date(b.start_at)>new Date()).length)} to="/driver/assignments" note="Within returned records"/><DashStat tone="red" label="Today's earnings" icon="wallet" value={'—'} to="/driver/earnings" note="Earnings ledger unavailable"/></>}>
  <Tile className="a-main" icon="pin" title="Next assignment" tip={t("Review your assigned journey before operating the trip.")}>
   {bookingsNote(assignments,()=>next?<div className="dash-assignment"><span className="dash-vehicle-art big"><Icon name="car" size={34} aria-hidden="true"/></span><div className="dash-assignment-main"><strong className="dash-route">{first_&&last_&&stops.length>1?<>{first_} → {last_}</>:tripRoute(next)}</strong><div className="dash-facts"><span><Icon name="clock" size={15}/>{displayTime(next.start_at)}</span><span><Icon name="users" size={15}/>{next.passenger_count}{t(" passengers")}</span><Chip tone="info">{t(words(next.trip.assignment_status))}</Chip></div><div className="dash-buttons"><Link className="ui-button ui-button-secondary" to={withWorkspace('/bookings/'+next.id,'DRIVER')}>{t("View trip details")}</Link>{next.trip?.assignment_status==='ACCEPTED'&&next.trip?.id&&<Link className="ui-button ui-button-primary" to={withWorkspace('/trips/'+next.trip.id+'/operation','DRIVER')}>{t("Start trip")}</Link>}</div></div></div>:<Soft>{t("No upcoming assignment")}</Soft>)}</Tile>
  <Tile className="a-side" icon="route" title="Your driving route" tip={t("Review the ordered stops in your assignment.")}>
   {stops.length?<ol className="dash-stops">{shown.map((stop,i)=><li key={i}><span className="dash-dot"/><div><strong>{t(stop.place?.label)||t('Unreported stop')}</strong><span>{stop===stops[0]?t('Pickup'):stop===stops[stops.length-1]?t('Destination'):t('Planned stop')}</span></div></li>)}</ol>:<Soft>{t("No itinerary to preview")}</Soft>}</Tile>
  <Tile className="b-1" icon="wallet" title="Today's earnings"><Soft>{t("Earnings ledger unavailable")}</Soft></Tile>
  <Tile className="b-2" icon="users" title="Passenger details" tip={t("Passenger contact, ratings and live locations are not supplied by this API.")}>
   {next?<div className="dash-facts col"><span><Icon name="pin" size={15}/>{t("Pickup")}: {first_||'—'}</span><span><Icon name="pin" size={15}/>{t("Destination")}: {last_||'—'}</span><span><Icon name="users" size={15}/>{next.passenger_count}{t(" passengers")}</span></div>:<Soft>{t("Select an assigned trip to review its details.")}</Soft>}</Tile>
  <Tile className="b-3" icon="alert" title="Road alerts"><Soft>{t("Road alerts appear on your live trip map while you drive.")}</Soft></Tile>
  <Tile className="c-main" icon="car" title="Need a ride after your shift?" tip={t("Book as a Passenger using your existing account. Your personal trips stay separate from customer bookings and assigned work.")}><DashLinks items={[["Book a ride for myself",'/driver/travel/hire','car'],['My personal trips','/driver/travel/bookings','calendar']]}/></Tile>
  <ReelsCard className="c-mid" state={reels}/>
  <TravellyAiPanel className="dash-tile c-side"/>
 </DashPage>
}

export function AdminDashboard(){
 const {user}=useWorkspace(),roles=useWorkspaceData(()=>api('/admin/role-requests?status=PENDING&page=1&page_size=4'),[]),vehicles=useWorkspaceData(()=>api('/admin/vehicles?verification_status=SUBMITTED&page=1&page_size=4'),[]),first=(user.display_name||user.full_name).trim().split(/\s+/)[0],hour=Number(new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Colombo',hour:'numeric',hourCycle:'h23'}).format(new Date())),greeting=hour<12?'Good morning':hour<17?'Good afternoon':'Good evening'
 const rows=useDashRows(),limit=rows>3?2:1,count=r=>r.loading?'?':r.error?'Unavailable':r.data?.total??r.data?.items?.length??0
 const apps=(roles.data?.items||[]).slice(0,limit),subs=(vehicles.data?.items||[]).slice(0,limit)
 return <DashPage title={`${t(greeting)}, ${first}`} subtitle={t("Welcome to your Travelly Command Centre. Here's what's happening with your platform today.")}
  stats={<><DashStat icon="users" label="Pending role applications" value={count(roles)} to="/admin/applications"/><DashStat tone="red" icon="car" label="Submitted vehicles" value={count(vehicles)} to="/admin/vehicles"/><DashStat icon="calendar" label="Global trips today" value={'—'} to="/admin/bookings" note="Summary unavailable"/><DashStat tone="red" icon="wallet" label="Revenue today (LKR)" value={'—'} to="/admin/payments" note="Summary unavailable"/></>}>
  <Tile className="a-main" icon="users" title="Pending verifications" to="/admin/applications" link="View all">
   {roles.loading||vehicles.loading?<Soft>{t(" Loading…")}</Soft>:roles.error||vehicles.error?<Soft>{t("Unable to load this information")}</Soft>:apps.length||subs.length
    ?<div className="dash-list">{apps.map(r=><Link className="dash-row" key={r.id} to={'/admin/applications/'+r.id}><Icon name="document" size={16}/><div><strong>{t(words(r.role_code))}{t(" application")}</strong><span>{r.applicant?.full_name} · {displayTime(r.requested_at)}</span></div><Chip tone="muted">{t("Pending review")}</Chip></Link>)}
     {subs.map(v=><Link className="dash-row" key={v.id} to={'/admin/vehicles/'+v.id}><Icon name="car" size={16}/><div><strong>{v.label||v.reference}</strong><span>{t("Vehicle submission")}</span></div><Chip tone="muted">{t(words(v.verification_status))}</Chip></Link>)}</div>
    :<Soft>{t("The current review queue is clear. Your own applications are excluded by the review API.")}</Soft>}</Tile>
  <Tile className="a-side" icon="pin" title="Live Trip Map" tip={t("Live location service is not connected.")}><Soft>{t("Live location service is not connected.")}</Soft></Tile>
  <Tile className="b-1" icon="chart" title="Booking Trend" tip={t("Bookings across the platform.")}><Soft>{t("Booking trend data is not available from the current API.")}</Soft></Tile>
  <Tile className="b-2" icon="shield" title="Safety Alerts" to="/admin/road-alerts" link="View all"><Soft>{t("A live safety-alert feed is not available yet.")} <Link to="/admin/manual-fulfilment">{t("Vehicle support notices")}</Link></Soft></Tile>
  <Tile className="b-3" icon="spark" title="Quick actions"><DashLinks items={[['Review role applications','/admin/applications','users'],['Approve vehicles','/admin/vehicles','car'],['Review documents','/admin/documents','document'],['Payments review','/admin/payments','wallet'],['Road alerts','/admin/road-alerts','alert'],['Reports','/admin/reports','chart']]}/></Tile>
  <Tile className="c-main" icon="calendar" title="Recent bookings" to="/admin/bookings" link="View all"><Soft>{t("Global booking summary unavailable")}. {t("A global booking list is not available to this Admin API.")}</Soft></Tile>
 </DashPage>
}

function OwnerOperationActions({booking,onChanged}){
 const {user}=useWorkspace(),[driver,setDriver]=useState(''),[match,setMatch]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState(null)
 const canSelfDrive=user.approved_roles?.includes('DRIVER')&&booking.accepted_quote_digest&&['REQUESTED','OWNER_ACTION_REQUIRED'].includes(booking.status)
 const canAssign=booking.accepted_quote_digest&&['REQUESTED','OWNER_ACTION_REQUIRED'].includes(booking.status)
 async function request(path,body){setBusy(true);setError(null);try{await api(path,{method:'POST',body:JSON.stringify(body)});onChanged()}catch(problem){setError(problem)}finally{setBusy(false)}}
 async function checkDriver(){
  setBusy(true);setError(null);setMatch(null)
  try{setMatch(await api('/drivers/eligible-lookup',{method:'POST',body:JSON.stringify({vehicle_id:booking.vehicle_id,service_type_id:booking.service_type_id,driver_reference:driver})}))}catch(problem){setError(problem)}finally{setBusy(false)}
 }
 if(!canSelfDrive&&!canAssign)return <Link className="button outline" to={withWorkspace('/bookings/'+booking.id,'OWNER')}>{t('Open booking')}<Icon name="arrow" size={16}/></Link>
 return <div className="owner-operation-actions">
  {error&&<ErrorNotice error={error}/>}
  {canSelfDrive&&<button className="button" disabled={busy} onClick={()=>request('/bookings/'+booking.id+'/self-drive',{expected_version:booking.version})}>{t("I'll drive myself")}</button>}
  {canAssign&&<div className="owner-driver-assignment"><label>{t('Verified Driver reference')}<input value={driver} onChange={event=>{setDriver(event.target.value);setMatch(null)}} placeholder="USR-…" pattern="USR-[0-9A-F]{16}"/></label><div><button className="button outline" disabled={busy||!/^USR-[0-9A-F]{16}$/.test(driver)} onClick={checkDriver}>{t('Check eligible Driver')}</button>{match&&<button className="button" disabled={busy} onClick={()=>request('/bookings/'+booking.id+'/driver-assignments',{expected_version:booking.version,driver_reference:driver})}>{t('Assign verified Driver')}</button>}</div>{match&&<p className="workspace-note" role="status">{match.display_name} · {match.reference}{t(' is currently eligible. Assignment rechecks availability before committing.')}</p>}</div>}
  <Link className="button outline" to={withWorkspace('/bookings/'+booking.id,'OWNER')}>{t('Review booking')}<Icon name="arrow" size={16}/></Link>
 </div>
}
export function OwnerOperations(){
 const {user}=useWorkspace(),[tab,setTab]=useState(0),[openId,setOpenId]=useState(null)
 const operations=useWorkspaceData(async()=>{
  const listed=await api('/bookings'),items=listed.items||[],details=new Array(items.length);let next=0
  await Promise.all(Array.from({length:Math.min(4,items.length)},async()=>{while(next<items.length){const index=next++;details[index]=await api('/bookings/'+items[index].id)}}))
  return details.filter(Boolean).filter(booking=>booking.owner_user_id===user.id||booking.trip?.driver_user_id===user.id)
 },[user.id])
 const fleet=useWorkspaceData(()=>api('/owners/me/vehicles?page=1&page_size=100'),[user.id])
 const vehicles=new Map((fleet.data?.items||[]).map(vehicle=>[vehicle.id,vehicle]))
 const items=operations.data||[]
 const driving=items.filter(booking=>booking.trip?.driver_user_id===user.id)
 const awaiting=items.filter(booking=>booking.owner_user_id===user.id&&booking.accepted_quote_digest&&['REQUESTED','OWNER_ACTION_REQUIRED'].includes(booking.status))
 const live=items.filter(booking=>booking.owner_user_id===user.id&&booking.trip&&['READY','IN_PROGRESS'].includes(booking.trip.status))
 const lists=[driving,awaiting,live]
 const paged=usePaged(lists[tab]||[],Math.max(2,useRowCount(tab===1?88:68)))
 const names=['My Driving','Driver Assignments','Live Fleet Trips','Vehicle Expenses']
 const emptyText=[['No driving assignments yet','When you drive a journey yourself, or another Owner assigns you as the Driver, it will show up here.','car'],['No decisions waiting','When a Passenger accepts a price that needs your approval, it will show up here.','users'],['No live fleet trips right now','Trips that are confirmed or on the road will show up here.','route']][tab]
 const selected=awaiting.find(booking=>booking.id===openId)
 const tabs=names.map((name,index)=>({label:t(name),icon:['car','users','route','wallet'][index],active:tab===index,onClick:()=>{setTab(index);setOpenId(null)}}))
 const tripRow=booking=>{
  const ownerDrive=booking.trip?.driver_user_id===user.id&&booking.owner_user_id===user.id,assignedDrive=booking.trip?.driver_user_id===user.id&&!ownerDrive
  const vehicle=vehicles.get(booking.vehicle_id),vehicleLabel=vehicle?.label||(booking.owner_user_id===user.id?t('Your assigned vehicle'):t('Assigned vehicle'))
  return <article className="tk-row" key={booking.id}><div className="tk-row-main"><strong>{tripRoute(booking)}</strong><span>{booking.reference} · {displayTime(booking.start_at)} · {vehicleLabel} · {ownerDrive?t('You are driving'):assignedDrive?t('You are assigned to drive'):t('Assigned Driver')}</span></div>
   <div className="tk-row-actions"><Chip tone={booking.status==='IN_PROGRESS'?'success':'muted'}>{t(words(booking.trip?.status||booking.status))}</Chip>
    <Link className="ui-button ui-button-secondary" to={booking.trip?.driver_user_id===user.id?withWorkspace('/trips/'+booking.trip.id+'/operation','OWNER'):withWorkspace('/bookings/'+booking.id,'OWNER')}>{t(booking.trip?.driver_user_id===user.id?'Operate trip':'Open trip')}</Link></div></article>
 }
 return <><Header/><FlowShell heading={t('Operations')} title={t(names[tab])} icon="watch" tabs={tabs} info={t('Run your journeys from your Owner workspace.')+' '+t('Drive a trip yourself or assign a verified Driver without leaving this page.')}>
  <ErrorNotice error={operations.error}/>
  {tab===3?<div className="tk-pane"><EmptyState icon="wallet" title={t('Vehicle expense tracking is coming soon')}>{t('Soon you will be able to record fuel, repairs and other vehicle costs here.')}</EmptyState></div>
  :operations.loading?<p role="status">{t(" Loading…")}</p>
  :<div className="tk-pane">
    {lists[tab].length?<div className="tk-rows">{paged.slice.map(booking=>tab===1
      ?<article className="tk-row" key={booking.id}><div className="tk-row-main"><strong>{tripRoute(booking)}</strong><span>{booking.reference} · {displayTime(booking.start_at)}</span></div><div className="tk-row-actions"><Chip tone="muted">{t(words(booking.status))}</Chip><button type="button" className="ui-button ui-button-secondary" onClick={()=>setOpenId(openId===booking.id?null:booking.id)}>{t(openId===booking.id?'Hide':'Assign')}</button></div></article>
      :tripRow(booking))}</div>
     :<EmptyState icon={emptyText[2]} title={t(emptyText[0])} action={tab===2?<Link className="ui-button ui-button-secondary" to={withWorkspace('/owner/vehicles','OWNER')}>{t('Open my vehicles')}</Link>:null}>{t(emptyText[1])}</EmptyState>}
    {selected&&<div className="tk-hold"><p className="tk-line">{t('Confirm who will drive only after the Passenger has accepted the price. Travelly checks the Driver’s documents, the vehicle match and any clashing trips.')}</p><OwnerOperationActions booking={selected} onChanged={operations.reload}/></div>}
    <div className="flow-actions"><span/>{paged.pages>1?paged.pager:null}</div>
   </div>}
 </FlowShell></>
}

export function WorkspaceBookings({kind='bookings',personal=false}){
 const {user,role}=useWorkspace(),resource=useWorkspaceData(()=>loadBookings(user.id,personal?'PASSENGER':role),[user.id,role,personal]),notifications=useWorkspaceData(()=>api('/notifications'),[user.id,role]),title=personal?'My trips':role==='PASSENGER'?'My Trips':kind==='history'?'Trip history':kind==='operate'?'Operate Trip':kind==='assignments'?(role==='OWNER'?'Driver assignments':'Assignments'):role==='OWNER'?'Bookings for my vehicles':'Bookings'
 const [tab,setTab]=React.useState(0),rows=useRowCount(62)
 const visible=resource.data?(kind==='history'?resource.data.filter(b=>b.status==='COMPLETED'):kind==='operate'||kind==='assignments'?sortTrips(resource.data.filter(role==='DRIVER'?activeAssignment:pendingBooking)):resource.data):[]
 // Notices are matched by notification_type and action_payload (contract 03N): reminders, road alerts (kept in the list, greyed once expired) and booking notices.
 const everything=notifications.data?.items||[]
 const reminders=!personal&&['OWNER','DRIVER'].includes(role)?everything.filter(n=>reminderKind(n)):[]
 const roadAlerts=everything.filter(isRoadAlertNotice)
 const noteItems=[...reminders,...roadAlerts,...everything.filter(n=>noticeBookingId(n)&&((!personal&&role!=='PASSENGER')||resource.data?.some(b=>b.id===noticeBookingId(n))))]
 const trips=usePaged(visible,rows),notes=usePaged(noteItems,rows)
 return <FlowShell heading={t(title)} title={tab===0?t(kind==='operate'?'Select an assigned trip':title):t('Trip notifications')} icon={tab===0?'calendar':'bell'} info={<>{t(bookingScope)} {t("Open a booking to review its itinerary and the actions currently permitted for your account. Assignment acceptance and trip-start validation use the existing trip workflow.")}</>} tabs={[{label:t(kind==='operate'?'Select an assigned trip':title),active:tab===0,onClick:()=>setTab(0),icon:'calendar'},{label:t('Trip notifications'),active:tab===1,onClick:()=>setTab(1),icon:'bell'}]}><div className="flow-wizard-form" hidden={tab!==0}><Resource resource={resource}>{()=><BookingsList items={trips.slice} role={role} personal={personal} operation={kind==='operate'} limit={100}/>}</Resource><div className="flow-actions">{role==='OWNER'&&!personal&&kind==='bookings'?<Link className="ui-button ui-button-secondary" to="/owner/operations">{t('Assign Drivers and live trips')}</Link>:<span/>}{visible.length>rows&&trips.pager}</div></div><div className="flow-wizard-form" hidden={tab!==1}><Resource resource={notifications}>{()=>noteItems.length?<div className="workspace-record-list">{notes.slice.map(n=>{
   const road=isRoadAlertNotice(n),expired=isExpired(n),icon=reminderKind(n)||road?'alert':'calendar'
   const link=reminderKind(n)?reminderLink(n,role):road?(n.trip_id&&role==='DRIVER'?'/driver/trips/'+n.trip_id+'/live':n.trip_id&&role==='OWNER'?'/owner/driving/trips/'+n.trip_id:null):personal?personalBookingPath(role,noticeBookingId(n)):withWorkspace('/bookings/'+noticeBookingId(n),role)
   const body=<><Icon name={icon}/><div><strong>{t(n.title)}{road&&expired&&<> · {t('Expired')}</>}</strong><span>{n.body}</span></div>{link&&<Icon name="arrow" size={16}/>}</>
   return link?<Link className={'workspace-record'+(expired?' is-expired':'')} key={n.id} to={link}>{body}</Link>:<div className={'workspace-record'+(expired?' is-expired':'')} key={n.id}>{body}</div>})}</div>:<Empty title="No trip notifications">{t("Updates for your journeys will appear here.")}</Empty>}</Resource><div className="flow-actions"><span/>{noteItems.length>rows&&notes.pager}</div></div></FlowShell>
}

export function WorkspaceSettings(){const {user,role}=useWorkspace(),[tab,setTab]=React.useState(0),[form,setForm]=React.useState({busy:false,changed:false,message:''});return <FlowShell heading={t(role==='ADMIN'?'Account settings':'Settings')} title={tab===0?t('Account security'):t('Profile details')} icon="settings" info={tab===0?t("Your sign-in methods and email verification. Phone verification is separate."):t("Update your name and mobile number. Your email address is changed through account recovery.")} tabs={[{label:t('Account security'),active:tab===0,onClick:()=>setTab(0),icon:'shield'},{label:t('Profile details'),active:tab===1,onClick:()=>setTab(1),icon:'user'}]}>
 <div className="flow-wizard-form" hidden={tab!==0}><ProfileAuth user={user}/><div className="flow-actions"><span/>{role!=='ADMIN'&&<Link className="ui-button ui-button-secondary" to={accountPath(role)}>{t("Open profile")}</Link>}</div></div>
 <div className="flow-wizard-form" hidden={tab!==1}><ProfileDetails user={user} onState={setForm}/><div className="flow-actions"><span className="status-chips">{form.message&&<Chip tone="success">{t(form.message)}</Chip>}</span><button type="submit" form={PROFILE_FORM_ID} className="ui-button ui-button-primary" disabled={form.busy||!form.changed}>{form.busy?t('Saving…'):t('Save Changes')}</button></div></div></FlowShell>}
const moduleNotes={
 'Ticket Booking':'Scheduled ticket search and seat checkout are not available yet. Private vehicle hire is available through Search & Hire.',
 'AI Trip Planner':'AI trip planning is not available yet. You can build and price a private-hire itinerary in trip search.',
 'Track Trip':'Live location tracking is not available yet. Open My Bookings to review the current status of your journeys.',
 'Saved':'Personal saved places are not available yet. Explore destinations and vehicle hire without creating a saved-place record.',
 'Availability':'A Driver availability schedule and online-status control are not available yet. Assignment and trip-start checks continue in the existing booking workflow.',
 'Payments':'A global payment workspace is not available yet. Payment and refund actions have not been added.',
 'Support':'A support-ticket service is not available yet. You can review your journeys and account details through the existing workflows.'
}
export function WorkspacePlaceholder(){const {role}=useWorkspace(),{pathname}=useLocation(),item=workspaceMenu(role).find(i=>i.path.split('?')[0]===pathname),title=item?.label||'Page unavailable';return <FlowShell heading={t(title)} title={t('Not available yet')} icon={item?.icon||'help'}><div className="flow-wizard-form"><Empty icon={item?.icon||'help'} title={title} to={workspaceRoles[role].home} action="Back to dashboard">{t(moduleNotes[title])||t("{value0} is not implemented for this workspace yet. No sample records or operational controls are shown.", {value0: title})}</Empty>{['OWNER','DRIVER'].includes(role)&&<p className="flow-note"><Link to={role==='OWNER'?'/owner/bookings':'/driver/assignments'}>{t("Review existing ")}{role==='OWNER'?t('bookings'):t('assignments')}</Link>{t(" for currently supported actions.")}</p>}</div></FlowShell>}
