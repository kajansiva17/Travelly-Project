import { t } from '../../i18n/language.js'
import React,{useEffect,useState} from 'react'
import {Link} from 'react-router-dom'
import {api} from '../../services/api'
import {Header,ErrorNotice} from '../../components/components'
import Chip from '../../components/ui/Chip'
import EmptyState from '../../components/ui/EmptyState'
import {FlowShell,usePaged,useRowCount} from '../booking/flow/FlowParts'
import {useWorkspace} from '../../context/workspaceContext'
import {pendingBooking,tripRoute,words} from '../../hooks/workspaceData'
import {formatDateTime} from '../../i18n/dateTime.js'
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
      const list=r.items||[],details=new Array(list.length);let next=0
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
  const rows=all.filter(x=>tab===0?!finished(x):finished(x)),paged=usePaged(tab===1?[...rows].reverse():rows,Math.max(2,useRowCount(64)))
  const tabs=[{label:t('Trips I drive'),icon:'car'},{label:t('Driving history'),icon:'clock'}].map((x,i)=>({...x,active:tab===i,onClick:()=>setTab(i)}))
  const row=item=>{
    if(item.kind==='booking'){
      const b=item.booking,mine=b.trip?.driver_user_id===user.id
      return <article className="tk-row" key={'b'+b.id}><div className="tk-row-main"><strong>{tripRoute(b)}</strong><span>{b.reference} · {formatDateTime(b.start_at)} · {t('Private hire')}</span></div>
        <div className="tk-row-actions"><Chip tone={b.status==='IN_PROGRESS'?'success':'muted'}>{t(words(b.trip?.status||b.status))}</Chip>
          {b.trip?.id&&mine&&!finished(item)?<Link className="ui-button ui-button-primary" to={'/owner/driving/trips/'+b.trip.id}>{t('Operate trip')}</Link>
            :<Link className="ui-button ui-button-secondary" to={withWorkspace('/bookings/'+b.id,'OWNER')}>{t('Open trip')}</Link>}</div></article>
    }
    const d=item.departure,chip=statusChip(d.status)
    return <article className="tk-row" key={'d'+d.id}><div className="tk-row-main"><strong>{d.route?.origin_name} → {d.route?.destination_name}</strong><span>{d.reference||''}{d.reference?' · ':''}{formatDateTime(d.departure_at)} · {d.vehicle?.public_vehicle_reference||''} · {t('Ticket departure')}</span></div>
      <div className="tk-row-actions"><Chip tone={chip.tone}>{chip.label}</Chip></div></article>
  }
  return <><Header/><FlowShell heading={t('My driving')} title={tab===0?t('Trips I drive'):t('Driving history')} icon="watch" tabs={tabs}
    info={t('Trips you drive yourself. Open a private-hire trip to check passengers, start, share your position, report a road problem and finish.')}>
    <ErrorNotice error={error}/>
    <div className="tk-pane">
      {loading?<p role="status">{t(' Loading…')}</p>
        :rows.length?<div className="tk-rows">{paged.slice.map(row)}</div>
        :<EmptyState icon="car" title={tab===0?t('Trips you drive yourself appear here.'):t('Finished trips you drove appear here.')}/>}
      <div className="flow-actions">{paged.pages>1?paged.pager:<span/>}<span/></div>
    </div>
  </FlowShell></>
}
