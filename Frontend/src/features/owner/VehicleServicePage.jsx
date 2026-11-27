import { t } from '../../i18n/language.js'
import React,{useEffect,useState} from 'react'
import {createPortal} from 'react-dom'
import {Link,Navigate,useSearchParams} from 'react-router-dom'
import {api,hasSession} from '../../services/api'
import {Header,ErrorNotice} from '../../components/components'
import {Compact} from './OwnerRates'
import Chip from '../../components/ui/Chip'
import {EmptyCard} from '../people/PeopleParts'
import {FlowShell} from '../booking/flow/FlowParts'
import VehicleMaintenance from './VehicleMaintenance'
import EventPackages from './EventPackages'
import RentalRates from '../rental/RentalRates'

/* One sidebar page per vehicle service (Maintenance, Event packages, Rental). The person picks a vehicle here and the same forms that were
   vehicle tabs open for it. The vehicle is kept in the address (?vehicle=...) so a reminder or a refresh returns to the same vehicle.
   Owners see their own vehicles; a Driver sees the vehicles they are the preferred Driver of (Maintenance is read-only for a Driver). */
const KINDS={
  maintenance:{heading:'Maintenance',icon:'settings',info:'Service, repair, fuel and odometer records for one vehicle. Pick the vehicle below.',Body:VehicleMaintenance},
  'event-packages':{heading:'Event packages',icon:'calendar',info:'Fixed-price Event hire packages for one vehicle. Pick the vehicle below.',Body:EventPackages},
  rental:{heading:'Rental',icon:'key',info:'Rental rates and extras for one vehicle. Pick the vehicle below.',Body:RentalRates}
}

export default function VehicleServicePage({kind,driver=false}){
  const spec=KINDS[kind],[params,setParams]=useSearchParams(),[rows,setRows]=useState(null),[error,setError]=useState(null),[slot,setSlot]=useState(null)
  useEffect(()=>{
    if(!hasSession())return
    api(driver?'/drivers/me/vehicles':'/owners/me/vehicles?page=1&page_size=50').then(d=>setRows(d.items)).catch(setError)
  },[driver])
  if(!hasSession())return <Navigate to="/login" replace/>
  const wanted=params.get('vehicle'),vehicle=rows&&(rows.find(r=>r.id===wanted)||(rows.length===1?rows[0]:null))
  const Footer=({children})=>slot?createPortal(children,slot):null
  const Body=spec.Body
  return <><Header/><FlowShell heading={t(spec.heading)} icon={spec.icon} title={vehicle?vehicle.label:t(spec.heading)} info={t(spec.info)}><Compact.Provider value={true}>
    <ErrorNotice error={error}/>
    {rows===null&&!error&&<p role="status">{t("Loading vehicles…")}</p>}
    {rows&&rows.length===0&&<EmptyCard icon="car" title={driver?t("No vehicle is assigned to you yet."):t("No vehicles in this list yet.")}>{driver?t("When an Owner assigns you a vehicle, its records show up here."):<Link to="/owner/vehicles">{t("Open My vehicles")}</Link>}</EmptyCard>}
    {rows&&rows.length>1&&<div className="bk-groups" role="tablist" aria-label={t("Vehicle")}>{rows.map(r=><Chip key={r.id} selected={vehicle?.id===r.id} onClick={()=>setParams({vehicle:r.id},{replace:true})}>{r.label}</Chip>)}</div>}
    {rows&&rows.length>1&&!vehicle&&<EmptyCard icon="car" title={t("Choose a vehicle")}/>}
    {vehicle&&<div className="flow-wizard-form"><Body key={vehicle.id} vehicle={vehicle} Footer={Footer} readOnly={driver}/></div>}
    <div className="flow-actions"><span className="footer-slot" ref={setSlot}/></div>
  </Compact.Provider></FlowShell></>
}
