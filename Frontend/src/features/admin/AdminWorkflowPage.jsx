import {useEffect,useState} from 'react'
import {api} from '../../services/api'
import {t} from '../../i18n/language.js'
import {Field} from '../owner/OwnerRates'
import AdminList,{Facts,factsOf} from './AdminList'
import OdometerProofCard from '../odometer/OdometerProofCard'
import {isRentalBooking,rentalLabel} from '../rental/rentalLabel'
import {codeLabel} from '../../i18n/codeLabels.js'
import {formatDateTime} from '../../i18n/dateTime.js'

const labels={bookings:['Booking oversight','/admin/workflow/bookings','calendar'],payments:['Payment & settlement audit','/admin/workflow/payments','wallet'],reports:['Operations reports','/admin/workflow/reports','chart'],services:['Services & vehicle types','/admin/vehicle-types','settings'],reviews:['Reviews','/admin/workflow/reports','star'],alerts:['Road alerts','/admin/workflow/reports','alert'],manual:['Manual fulfilment','/admin/manual-fulfilment-events','shield']}
const tone=status=>/CONFIRM|COMPLET|APPROV|PAID|ACTIVE|SUCCEED/i.test(status||'')?'success':/REJECT|FAIL|CANCEL|MISMATCH|ALERT/i.test(status||'')?'danger':'muted'
export default function AdminWorkflowPage({kind}){
 const [data,setData]=useState(null),[error,setError]=useState(null),[busy,setBusy]=useState(false),[summary,setSummary]=useState(''),[details,setDetails]=useState(''),[notice,setNotice]=useState(''),[tab,setTab]=useState(0),[reference,setReference]=useState(''),[editing,setEditing]=useState(null),[confirmId,setConfirmId]=useState(null)
 const [title,path,icon]=labels[kind]
 const load=()=>api(path).then(setData).catch(setError)
 useEffect(()=>{setData(null);load()},[kind])
 const clearForm=()=>{setSummary('');setDetails('');setReference('');setEditing(null)}
 const startEdit=n=>{setEditing(n);setSummary(n.summary);setDetails(n.details);setReference(n.link?n.link.reference:'');setNotice('');setError(null);setConfirmId(null);setTab(1)}
 async function saveNote(event){event.preventDefault();setBusy(true);setError(null);try{const body=JSON.stringify({summary,details,reference:reference.trim()||null});if(editing)await api(`/admin/manual-fulfilment-events/${editing.id}`,{method:'PATCH',body});else await api('/admin/manual-fulfilment-events',{method:'POST',body});clearForm();setNotice(t('Note saved.'));setTab(0);await load()}catch(problem){setError(problem)}finally{setBusy(false)}}
 async function removeNote(n){setBusy(true);setError(null);try{await api(`/admin/manual-fulfilment-events/${n.id}`,{method:'DELETE'});setConfirmId(null);setNotice(t('Note deleted.'));await load()}catch(problem){setError(problem)}finally{setBusy(false)}}
 const noteFacts=n=>[[t('Written by'),n.created_by_name],[t('Date'),formatDateTime(n.created_at)],n.updated_at&&[t('Edited'),formatDateTime(n.updated_at)+(n.updated_by_name?' · '+n.updated_by_name:'')],n.link&&[t('About'),n.link.type==='BOOKING'?t('Booking'):t('Departure')],n.link&&[t('Reference'),n.link.reference],n.link&&[t('Status'),codeLabel(n.link.status)],n.link&&n.link.route&&[t('Route'),n.link.route],n.link&&n.link.when&&[t('When'),formatDateTime(n.link.when)],n.link&&n.link.amount&&[t('Amount'),n.link.amount]].filter(Boolean)
 const items=data?data.items||[]:null
 const info=t('Admin-only oversight. Views are operational summaries and do not expose private evidence or initiate financial changes.')
 const tabs=kind==='manual'?[{label:t('Notes'),icon:'document',active:tab===0,onClick:()=>{setConfirmId(null);setTab(0)}},{label:t('Write a note'),icon:'calendar',active:tab===1,onClick:()=>{clearForm();setTab(1)}}]:undefined
 const base={heading:t(title),title:t(title),icon,info,error,notice,tabs}
 if(kind==='reports')return <AdminList {...base} custom={!data?(error?null:<p role="status">{t('Loading admin workflow...')}</p>):<div className="tk-pane"><Facts cols={4} entries={Object.entries(data).filter(([key])=>key!=='note'&&typeof data[key]!=='object').map(([key,value])=>[codeLabel(key),String(value)])}/>{data.note&&<p className="tk-line">{t(data.note)}</p>}</div>}/>
 if(kind==='manual'&&tab===1)return <AdminList {...base} title={editing?t('Edit note'):t('Write a note')} info={t('Write a note for yourself about an exceptional case. A note never changes a booking, fare, payment or settlement.')} custom={<form className="flow-wizard-form tk-pane" onSubmit={saveNote}>
   <div className="tk-grid" style={{'--cols':1}}><Field label="Summary"><input required maxLength="300" value={summary} onChange={event=>setSummary(event.target.value)}/></Field><Field label="Details"><textarea required maxLength="5000" rows="3" value={details} onChange={event=>setDetails(event.target.value)}/></Field><Field label="Booking or departure reference" optional help="Optional. The reference of the booking or departure this note is about, such as TKT-… or DEP-…. Leave it empty if the note is not about one."><input name="note_reference" maxLength="40" autoComplete="off" placeholder="TKT-… / DEP-…" value={reference} onChange={event=>setReference(event.target.value)}/></Field></div>
   <div className="flow-actions"><button type="button" className="ui-button ui-button-secondary" onClick={()=>{clearForm();setTab(0)}}>{t('Cancel')}</button><button className="ui-button ui-button-primary" disabled={busy}>{editing?t('Save changes'):t('Save note')}</button></div></form>}/>
 if(kind==='manual')return <AdminList {...base} items={items} empty={t('No notes yet.')}
   row={n=>({key:n.id,title:n.summary,meta:[formatDateTime(n.created_at),n.created_by_name,n.updated_at?t('Edited'):'',n.link?`${n.link.reference} · ${codeLabel(n.link.status)}`:''].filter(Boolean).join(' · '),
     actions:confirmId===n.id?<><span className="tk-line">{t('Delete this note?')}</span><button type="button" className="ui-button ui-button-primary" disabled={busy} onClick={()=>removeNote(n)}>{t('Yes, delete')}</button><button type="button" className="ui-button ui-button-secondary" onClick={()=>setConfirmId(null)}>{t('Keep it')}</button></>:<><button type="button" className="ui-button ui-button-secondary" onClick={()=>startEdit(n)}>{t('Edit')}</button><button type="button" className="ui-button ui-button-secondary" onClick={()=>setConfirmId(n.id)}>{t('Delete')}</button></>})}
   detail={n=><><p className="tk-line" style={{whiteSpace:'pre-wrap'}}>{n.details}</p><Facts entries={noteFacts(n)}/></>}
   detailTitle={n=>n.summary}/>
 return <AdminList {...base} items={items} empty={t('No records are available for this view.')}
   row={item=>{const status=item.status||item.booking_status||item.payment?.status||'';return {key:item.trip_id||item.id||item.code,title:item.booking_reference||item.trip_reference||item.code||item.display_name||item.summary||item.provider_reference||t('Record'),meta:[item.display_name&&item.display_name!==item.code?item.display_name:'',isRentalBooking(item)&&rentalLabel(item),item.event_package&&`${t('Package')}: ${item.event_package.name} · ${t('{value0} hours',{value0:item.event_package.hours})}`].filter(Boolean).join(' · '),status:status?codeLabel(status):'',tone:tone(status)}}}
   detail={item=><><Facts entries={factsOf(item)}/>{item.trip_id&&<OdometerProofCard key={item.trip_id} tripId={item.trip_id}/>}</>}
   detailTitle={item=>item.booking_reference||item.trip_reference||item.code||item.summary||t('Record')}/>
}
