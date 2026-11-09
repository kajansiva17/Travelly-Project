import React,{useEffect,useState} from 'react'
import {Link,useLocation} from 'react-router-dom'
import {api} from '../../services/api'
import {ErrorNotice,Icon} from '../../components/components'
import {t} from '../../i18n/language.js'

const labels={bookings:['Booking oversight','/admin/workflow/bookings'],payments:['Payment & settlement audit','/admin/workflow/payments'],reports:['Operations reports','/admin/workflow/reports'],services:['Services & vehicle types','/admin/vehicle-types'],reviews:['Reviews','/admin/workflow/reports'],alerts:['Road alerts','/admin/workflow/reports'],manual:['Manual fulfilment','/admin/manual-fulfilment-events']}
export default function AdminWorkflowPage({kind}){
 const [data,setData]=useState(null),[error,setError]=useState(null),[busy,setBusy]=useState(false),[summary,setSummary]=useState(''),[details,setDetails]=useState('')
 const [title,path]=labels[kind]
 const load=()=>api(path).then(setData).catch(setError)
 useEffect(()=>{load()},[kind])
 async function createEvent(event){event.preventDefault();setBusy(true);setError(null);try{await api('/admin/manual-fulfilment-events',{method:'POST',body:JSON.stringify({event_type:'EXCEPTION_REVIEW',summary,details})});setSummary('');setDetails('');await load()}catch(problem){setError(problem)}finally{setBusy(false)}}
 const items=data?.items||[]
 return <main id="main" className="role-dashboard admin-workflow-page"><div className="workspace-heading"><div><h1>{t(title)}</h1><p>{t('Admin-only oversight. Views are operational summaries and do not expose private evidence or initiate financial changes.')}</p></div></div><ErrorNotice error={error}/>{!data?<p role="status">{t('Loading admin workflow...')}</p>:kind==='reports'?<section className="workspace-card admin-report-grid">{Object.entries(data).filter(([key])=>key!=='note').map(([key,value])=><div key={key}><strong>{String(value)}</strong><span>{t(key.replaceAll('_',' '))}</span></div>)}<p>{t(data.note)}</p></section>:kind==='manual'?<><section className="workspace-card"><h2>{t('Create exceptional-case event')}</h2><form onSubmit={createEvent}><label>{t('Summary')}<input required maxLength="300" value={summary} onChange={event=>setSummary(event.target.value)}/></label><label>{t('Details')}<textarea required maxLength="5000" value={details} onChange={event=>setDetails(event.target.value)}/></label><button className="button" disabled={busy}>{t('Record auditable event')}</button></form><p className="workspace-note">{t('This records an exception only. It never changes a booking, fare, payment, or settlement.')}</p></section><Records items={items}/></>:kind==='services'?<Records items={items}/>:<Records items={items}/>}</main>
}
function Records({items}){return <section className="workspace-card"><h2>{t('Records')}</h2>{items.length?<div className="workspace-record-list">{items.map(item=><article className="workspace-record" key={item.trip_id||item.id||item.code}><Icon name="document"/><div><strong>{item.booking_reference||item.trip_reference||item.code||item.display_name||item.summary||item.provider_reference||t('Record')}</strong><span>{item.status||item.booking_status||item.payment?.status||item.display_name||''}</span></div></article>)}</div>:<p>{t('No records are available for this view.')}</p>}</section>}
