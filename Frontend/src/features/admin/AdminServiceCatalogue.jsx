import {useEffect,useState} from 'react'
import {Link} from 'react-router-dom'
import {api} from '../../services/api'
import {t} from '../../i18n/language.js'
import {Field} from '../owner/OwnerRates'
import AdminList,{Facts} from './AdminList'
import AdminPaymentSettings from './AdminPaymentSettings'
import AdminRefunds from './AdminRefunds'
import AdminAttention from './AdminAttention'
import {codeEnglish} from '../../i18n/codeLabels.js'

const scopes=[['AIRPORT','Airport Hire'],['LOCAL','Local Hire'],['LONG_DISTANCE','Long Distance'],['EVENT','Event Hire']]
const tone={ACTIVE:'success',INACTIVE:'muted',DRAFT:'info',NEEDS_REVIEW:'danger'}
const codeFor=scope=>scope+'_HIRE'
const plain=value=>codeEnglish(value)

export default function AdminServiceCatalogue(){
 const [items,setItems]=useState(null),[error,setError]=useState(null),[busy,setBusy]=useState(''),[form,setForm]=useState({scope:'AIRPORT',name:'Airport Hire',status:'DRAFT'}),[tab,setTab]=useState(0)
 const load=()=>api('/admin/service-types').then(result=>setItems(result.items||[])).catch(setError)
 useEffect(()=>{load()},[])
 async function create(event){event.preventDefault();setBusy('create');setError(null);try{const row=await api('/admin/service-types',{method:'POST',body:JSON.stringify({code:codeFor(form.scope),name:form.name,default_pricing_basis:'DISTANCE',is_active:false,pricing_scope:form.scope})});await api(`/admin/service-types/${row.id}/catalogue`,{method:'PATCH',body:JSON.stringify({expected_version:row.version,pricing_scope:form.scope,status:form.status})});await load();setTab(0)}catch(problem){setError(problem)}finally{setBusy('')}}
 async function save(row,status,pricing_scope=row.pricing_scope){setBusy(row.id);setError(null);try{await api(`/admin/service-types/${row.id}/catalogue`,{method:'PATCH',body:JSON.stringify({expected_version:row.version,pricing_scope,status})});await load()}catch(problem){setError(problem)}finally{setBusy('')}}
 const tabs=[{label:t('Services'),icon:'settings',active:tab===0,onClick:()=>setTab(0)},{label:t('Create supported service'),icon:'calendar',active:tab===1,onClick:()=>setTab(1)},{label:t('Payments'),icon:'wallet',active:tab===2,onClick:()=>setTab(2)},{label:t('Refunds'),icon:'wallet',active:tab===3,onClick:()=>setTab(3)},{label:t('Needs attention'),icon:'alert',active:tab===4,onClick:()=>setTab(4)}]
 const ticket=<><Link className="ui-button ui-button-secondary" to="/admin/services-routes/routes">{t('Routes & stops')}</Link><Link className="ui-button ui-button-secondary" to="/admin/services-routes/ticket-settings">{t('Seat hold time')}</Link></>
 const base={heading:t('Private-hire service readiness'),icon:'settings',tabs,error,
   info:t('Create and control only Airport Hire, Local Hire, and Long Distance. Deactivation preserves referenced service records.')+' '+t('Scheduled seat tickets use Admin-approved routes. Owners publish departures and set the fare; Passengers hold numbered seats for the time set here.')}
 if(tab===2)return <AdminPaymentSettings base={base}/>
 if(tab===3)return <AdminRefunds base={base}/>
 if(tab===4)return <AdminAttention base={base} onOpenRefunds={()=>setTab(3)}/>
 if(tab===1)return <AdminList {...base} title={t('Create supported service')} custom={<form className="flow-wizard-form tk-pane" onSubmit={create}>
   <div className="tk-grid" style={{'--cols':3}}>
    <Field label="Service scope"><select value={form.scope} onChange={event=>{const scope=event.target.value;setForm({...form,scope,name:scopes.find(item=>item[0]===scope)[1]})}}>{scopes.map(([value,label])=><option value={value} key={value}>{t(label)}</option>)}</select></Field>
    <Field label="Service name"><input required maxLength="100" value={form.name} onChange={event=>setForm({...form,name:event.target.value})}/></Field>
    <Field label="Initial status"><select value={form.status} onChange={event=>setForm({...form,status:event.target.value})}>{['DRAFT','ACTIVE','INACTIVE','NEEDS_REVIEW'].map(status=><option key={status} value={status}>{t(plain(status))}</option>)}</select></Field>
   </div>
   <div className="flow-actions"><span/><button className="ui-button ui-button-primary" disabled={busy==='create'}>{busy==='create'?t('Creating…'):t('Create service')}</button></div></form>}/>
 return <AdminList {...base} title={t('Services')} items={items} empty={t('No supported services configured. Create Airport Hire, Local Hire, or Long Distance. Existing referenced services are never deleted here.')} footer={ticket}
  row={row=>({key:row.id,title:row.name,meta:`${plain(row.pricing_scope)} · ${row.code||''} · ${t('Ready vehicles')} ${row.ready_vehicle_count??0}`,status:t(plain(row.status)),tone:tone[row.status]})}
  detailTitle={row=>row.name}
  detail={row=><>
   <Facts entries={[[t('Ready vehicles'),String(row.ready_vehicle_count??0)],[t('Ready Owners'),String(row.ready_owner_count??0)],[t('Rate basis'),plain(row.default_pricing_basis)||'—']]}/>
   <p className="tk-line">{(row.ready_vehicles||[]).length?(row.ready_vehicles||[]).slice(0,6).map(item=>`${item.vehicle_reference} · ${item.owner_reference}`).join('  |  '):t('No approved, published vehicle has an active complete rate rule for this service.')}</p>
   <div className="tk-bar"><div style={{minWidth:200}}><Field label="Classification"><select value={row.pricing_scope||''} disabled={busy===row.id} onChange={event=>save(row,row.status,event.target.value)}>{scopes.map(([value,label])=><option key={value} value={value}>{t(label)}</option>)}</select></Field></div>
    {['DRAFT','ACTIVE','INACTIVE','NEEDS_REVIEW'].map(status=><button type="button" key={status} className={'ui-button '+(status==='ACTIVE'?'ui-button-primary':'ui-button-secondary')} disabled={busy===row.id||row.status===status} onClick={()=>save(row,status)}>{t(plain(status))}</button>)}</div>
  </>}/>
}
