import React,{useEffect,useState} from 'react'
import {Link} from 'react-router-dom'
import {api} from '../../services/api'
import {t} from '../../i18n/language.js'
import AdminList,{Facts,factsOf} from './AdminList'

// Read-only oversight: vehicle queue, booking audit and payment audit as three tabs of the shared Admin list.
export default function AdminOversight(){
  const [vehicles,setVehicles]=useState(null),[bookings,setBookings]=useState(null),[payments,setPayments]=useState(null),[error,setError]=useState(null),[tab,setTab]=useState(0)
  useEffect(()=>{Promise.all([api('/admin/vehicles?verification_status=SUBMITTED&page=1&page_size=50'),api('/admin/workflow/bookings'),api('/admin/workflow/payments')]).then(([v,b,p])=>{setVehicles(v.items||[]);setBookings(b.items||[]);setPayments(p.items||[])}).catch(setError)},[])
  const tabs=[['Vehicle verification queue','car'],['Booking oversight','calendar'],['Payment mismatch review','wallet']].map(([label,icon],i)=>({label:t(label),icon,active:tab===i,onClick:()=>setTab(i)}))
  const common={heading:t('Verification, bookings and payments'),icon:'shield',info:t('Read-only oversight data excludes private files, contacts, media paths, QR/PIN values and payment secrets.'),tabs,error}
  const footer=<Link className="ui-button ui-button-secondary" to="/admin/manual-fulfilment">{t('Open audit events')}</Link>
  if(tab===0)return <AdminList key="v" {...common} title={t('Vehicle verification queue')} items={vehicles} empty={t('No submitted vehicles. The current verification queue is clear.')} footer={footer}
    row={v=>({key:v.id,title:v.label||v.reference,meta:`${v.verification_status} · ${v.availability_status}`,actions:<Link className="ui-button ui-button-secondary" to={`/admin/vehicles/${v.id}`}>{t('Review vehicle')}</Link>})}/>
  if(tab===1)return <AdminList key="b" {...common} title={t('Booking oversight')} items={bookings} empty={t('No booking records. No Admin booking summary was returned.')} footer={footer}
    row={b=>({key:b.trip_id||b.id,title:b.booking_reference||b.trip_reference||t('Booking record'),meta:[b.booking_status||b.status||t('Status unavailable'),b.event_package&&`${t('Package')}: ${b.event_package.name} · ${t('{value0} hours',{value0:b.event_package.hours})}`].filter(Boolean).join(' · '),status:t('Audit metadata'),tone:'info'})}
    detail={b=><Facts entries={factsOf(b)}/>}/>
  return <AdminList key="p" {...common} title={t('Payment mismatch review')} items={payments} empty={t('No payment audit records. Payment mismatch evidence is unavailable unless supplied by the audit API.')} footer={footer}
    row={p=>({key:p.payment?.id||p.trip_id,title:p.provider_reference||p.trip_reference||t('Payment record'),meta:p.payment?.status||p.status||t('Status unavailable'),status:t('Read-only'),tone:'muted'})}
    detail={p=><Facts entries={factsOf(p)}/>}/>
}
