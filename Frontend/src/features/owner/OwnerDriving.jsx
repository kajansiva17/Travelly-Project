import { t } from '../../i18n/language.js'
import {useEffect,useState} from 'react'
import {Link} from 'react-router-dom'
import {api} from '../../services/api'
import {Header,ErrorNotice,Icon} from '../../components/components'
import Chip from '../../components/ui/Chip'
import EmptyState from '../../components/ui/EmptyState'
import {FlowShell} from '../booking/flow/FlowParts'
import {Thumb} from '../booking/BookingCardParts'
import {useWorkspace} from '../../context/workspaceContext'
import {displayTime,pendingBooking,tripRoute,words} from '../../hooks/workspaceData'
import {withWorkspace} from '../../routes/workspaceRoutes'
import {statusChip} from './DepartureFulfilment'

/* My driving (contract 03W): only for an approved Owner who is also an approved Driver.
   Trips I drive myself = GET /bookings?as=driver (private hire) + GET /scheduled-trips?driving=true (ticket departures).
   Operating a private-hire trip (passenger QR/PIN check, start, live position, road problem, finish) reuses the Driver trip page. */
const DRIVING_STATUSES=['COMPLETED','CANCELLED','REJECTED']
const finished=item=>item.kind==='departure'?item.status==='CANCELLED'||new Date(item.at)<new Date(Date.now()-86400000):DRIVING_STATUSES.includes(item.status)
export default function OwnerDriving(){
  const {user}=useWorkspace(),[tab,setTab]=useState(0),[bookings,setBookings]=useState(null),[departures,setDepartures]=useState(null),[error,setError]=useState(null)
  useEffect(()=>{
    let alive=true
    api('/bookings?as=driver').then(async r=>{
      const vehicles=r.vehicles||{},passengers=r.passengers||{}
      const list=(r.items||[]).map(b=>({...b,vehicle:vehicles[b.vehicle_id]||null,passenger:passengers[b.passenger_user_id]||null})),details=new Array(list.length);let next=0
      // The list says which bookings I drive; the trip id for each open one comes from its own record.
      await Promise.all(Array.from({length:Math.min(4,list.length)},async()=>{while(next<list.length){const i=next++;details[i]=pendingBooking(list[i])?await api('/bookings/'+list[i].id).catch(()=>list[i]):list[i]}}))
      if(alive)setBookings(details)
    }).catch(e=>{if(alive){setError(e);setBookings([])}})
    api('/scheduled-trips?driving=true&limit=100').then(r=>{if(alive)setDepartures(r.items||[])}).catch(e=>{if(alive){setError(e);setDepartures([])}})
    return()=>{alive=false}
  },[])
  const loading=bookings===null||departures===null
  const all=loading?[]:[
    ...bookings.map(b=>({kind:'booking',id:b.id,at:b.start_at,status:b.status,booking:b})),
    ...departures.map(d=>({kind:'departure',id:d.id,at:d.departure_at,status:d.status,departure:d}))
  ].sort((a,b)=>new Date(a.at)-new Date(b.at))
  const rows=all.filter(x=>tab===0?!finished(x):finished(x)),ordered=tab===1?[...rows].reverse():rows
  const tabs=[{label:t('Trips I drive'),icon:'car'},{label:t('Driving history'),icon:'clock'}].map((x,i)=>({...x,active:tab===i,onClick:()=>setTab(i)}))
  // Where each trip stands, in plain words: running now, ready to operate, a request waiting, or confirmed.
  const stageOf=item=>{
    if(item.kind==='departure')return {key:'departure',tone:'info'}
    const b=item.booking,mine=b.trip?.driver_user_id===user.id
    if(b.status==='IN_PROGRESS'||b.trip?.status==='IN_PROGRESS')return {key:'running',tone:'success',mine}
    if(b.trip?.id&&mine&&b.status==='CONFIRMED')return {key:'operate',tone:'success',mine}
    if(['REQUESTED','OWNER_ACTION_REQUIRED','AWAITING_DRIVER'].includes(b.status))return {key:'waiting',tone:'warning',mine}
    return {key:'confirmed',tone:'info',mine}
  }
  const GROUPS=[
    {key:'running',title:t('On the road now'),chip:t('On the road'),hint:t('The trip is running. Open it to continue.')},
    {key:'operate',title:t('Ready to operate'),chip:t('Ready to operate'),hint:t('Check the Passenger, start, share your position and finish here.')},
    {key:'waiting',title:t('Requests waiting for confirmation'),chip:t('Request'),hint:t('This request is not confirmed yet.')},
    {key:'confirmed',title:t('Confirmed trips'),chip:t('Confirmed'),hint:t('This trip is confirmed.')},
    {key:'departure',title:t('Ticket departures'),chip:t('Ticket departure'),hint:''}]
  const row=item=>{
    const stage=stageOf(item),group=GROUPS.find(g=>g.key===stage.key),history=tab===1
    if(item.kind==='booking'){
      const b=item.booking,v=b.vehicle||{},p=b.passenger,canOperate=b.trip?.id&&stage.mine&&!finished(item)
      return <article className="bc-card dv-card" key={'b'+b.id}>
        <Thumb src={v.profile_image_url} icon="car" size={72}/>
        <div className="bc-body">
          <strong className="bc-name">{tripRoute(b)}</strong>
          <span className="bc-sub">{b.reference}{v.name?' · '+v.name:''}{v.registration?' · '+v.registration:''}</span>
          {p&&<span className="bc-line dv-who"><Thumb src={p.profile_image_url} icon="user" name={p.name} round size={22}/>{p.name}{b.passenger_count?' · '+t('{value0} passengers',{value0:b.passenger_count}):''}</span>}
          <span className="bc-line"><Icon name="clock" size={15}/>{displayTime(b.start_at)}</span>
          {!history&&group.hint&&<span className="dv-hint">{group.hint}</span>}
        </div>
        <div className="bc-side"><Chip tone={history?'muted':stage.tone}>{history?t(words(b.trip?.status||b.status)):group.chip}</Chip>
          {canOperate?<Link className="ui-button ui-button-primary" to={'/owner/driving/trips/'+b.trip.id}>{t('Operate trip')}</Link>
            :<Link className="ui-button ui-button-secondary" to={withWorkspace('/bookings/'+b.id,'OWNER')}>{t('Open trip')}</Link>}</div></article>
    }
    const d=item.departure,chip=statusChip(d.status),v=d.vehicle||{}
    return <article className="bc-card dv-card" key={'d'+d.id}>
      <Thumb src={v.profile_image_url||v.photo_url} icon="car" size={72}/>
      <div className="bc-body">
        <strong className="bc-name">{d.route?.origin_name} → {d.route?.destination_name}</strong>
        <span className="bc-sub">{d.reference||''}{d.reference&&(v.display_name||v.public_vehicle_reference)?' · ':''}{v.display_name||v.public_vehicle_reference||''}</span>
        <span className="bc-line"><Icon name="clock" size={15}/>{displayTime(d.departure_at)}</span>
        <span className="dv-hint">{t('Ticket departure')}</span></div>
      <div className="bc-side"><Chip tone={chip.tone}>{chip.label}</Chip></div></article>
  }
  const sections=tab===1?[{key:'all',items:ordered}]:GROUPS.map(g=>({...g,items:ordered.filter(x=>stageOf(x).key===g.key)})).filter(g=>g.items.length)
  return <><Header/><FlowShell heading={t('My driving')} title={tab===0?t('Trips I drive'):t('Driving history')} icon="watch" tabs={tabs}
    info={t('Trips you drive yourself. Open a private-hire trip to check passengers, start, share your position, report a road problem and finish.')}>
    <ErrorNotice error={error}/>
    <div className="flow-wizard-form dv-pane">
      {loading?<p role="status">{t(' Loading…')}</p>
        :rows.length?<div className="bk-list dv-list">{sections.map(g=><section className="dv-section" key={g.key}>{g.title&&<h3 className="dv-head">{g.title}<span className="dv-count">{g.items.length}</span></h3>}{g.items.map(row)}</section>)}</div>
        :<EmptyState icon="car" title={tab===0?t('Trips you drive yourself appear here.'):t('Finished trips you drove appear here.')}/>}
    </div>
  </FlowShell></>
}
