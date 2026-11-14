import {useEffect,useState} from 'react'
import {api} from '../../services/api'
import {t} from '../../i18n/language.js'
import {Field} from '../owner/OwnerRates'
import AdminList,{Facts,factsOf} from './AdminList'
import OdometerProofCard from '../odometer/OdometerProofCard'
import {isRentalBooking,rentalLabel} from '../rental/rentalLabel'
import {codeLabel} from '../../i18n/codeLabels.js'

const labels={bookings:['Booking oversight','/admin/workflow/bookings','calendar'],payments:['Payment & settlement audit','/admin/workflow/payments','wallet'],reports:['Operations reports','/admin/workflow/reports','chart'],services:['Services & vehicle types','/admin/vehicle-types','settings'],reviews:['Reviews','/admin/workflow/reports','star'],alerts:['Road alerts','/admin/workflow/reports','alert'],manual:['Manual fulfilment','/admin/manual-fulfilment-events','shield']}
const tone=status=>/CONFIRM|COMPLET|APPROV|PAID|ACTIVE|SUCCEED/i.test(status||'')?'success':/REJECT|FAIL|CANCEL|MISMATCH|ALERT/i.test(status||'')?'danger':'muted'
export default function AdminWorkflowPage({kind}){
 const [data,setData]=useState(null),[error,setError]=useState(null),[busy,setBusy]=useState(false),[summary,setSummary]=useState(''),[details,setDetails]=useState(''),[notice,setNotice]=useState(''),[tab,setTab]=useState(0)
 const [title,path,icon]=labels[kind]
 const load=()=>api(path).then(setData).catch(setError)
 useEffect(()=>{setData(null);load()},[kind])
 async function createEvent(event){event.preventDefault();setBusy(true);setError(null);try{await api('/admin/manual-fulfilment-events',{method:'POST',body:JSON.stringify({event_type:'EXCEPTION_REVIEW',summary,details})});setSummary('');setDetails('');setNotice(t('Event recorded.'));setTab(0);await load()}catch(problem){setError(problem)}finally{setBusy(false)}}
 const items=data?data.items||[]:null
 const info=t('Admin-only oversight. Views are operational summaries and do not expose private evidence or initiate financial changes.')
 const tabs=kind==='manual'?[{label:t('Events'),icon:'document',active:tab===0,onClick:()=>setTab(0)},{label:t('Record an event'),icon:'calendar',active:tab===1,onClick:()=>setTab(1)}]:undefined
 const base={heading:t(title),title:t(title),icon,info,error,notice,tabs}
 if(kind==='reports')return <AdminList {...base} custom={!data?(error?null:<p role="status">{t('Loading admin workflow...')}</p>):<div className="tk-pane"><Facts cols={4} entries={Object.entries(data).filter(([key])=>key!=='note'&&typeof data[key]!=='object').map(([key,value])=>[codeLabel(key),String(value)])}/>{data.note&&<p className="tk-line">{t(data.note)}</p>}</div>}/>
 if(kind==='manual'&&tab===1)return <AdminList {...base} title={t('Create exceptional-case event')} info={t('This records an exception only. It never changes a booking, fare, payment, or settlement.')} custom={<form className="flow-wizard-form tk-pane" onSubmit={createEvent}>
   <div className="tk-grid" style={{'--cols':1}}><Field label="Summary"><input required maxLength="300" value={summary} onChange={event=>setSummary(event.target.value)}/></Field><Field label="Details"><textarea required maxLength="5000" rows="3" value={details} onChange={event=>setDetails(event.target.value)}/></Field></div>
   <div className="flow-actions"><span/><button className="ui-button ui-button-primary" disabled={busy}>{t('Record auditable event')}</button></div></form>}/>
 return <AdminList {...base} items={items} empty={t('No records are available for this view.')}
   row={item=>{const status=item.status||item.booking_status||item.payment?.status||'';return {key:item.trip_id||item.id||item.code,title:item.booking_reference||item.trip_reference||item.code||item.display_name||item.summary||item.provider_reference||t('Record'),meta:[item.display_name&&item.display_name!==item.code?item.display_name:'',isRentalBooking(item)&&rentalLabel(item),item.event_package&&`${t('Package')}: ${item.event_package.name} · ${t('{value0} hours',{value0:item.event_package.hours})}`].filter(Boolean).join(' · '),status:status?codeLabel(status):'',tone:tone(status)}}}
   detail={item=><><Facts entries={factsOf(item)}/>{item.trip_id&&<OdometerProofCard key={item.trip_id} tripId={item.trip_id}/>}</>}
   detailTitle={item=>item.booking_reference||item.trip_reference||item.code||item.summary||t('Record')}/>
}
