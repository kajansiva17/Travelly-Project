import { t } from '../../i18n/language.js'
import React,{useEffect,useRef,useState} from 'react'
import {useNavigate} from 'react-router-dom'
import {api,hasSession,publicRead,publicRequest} from '../../services/api'
import {PlaceSearch,Field,Compact} from '../owner/OwnerRates'
import {ErrorNotice} from '../../components/components'
import {Chip} from '../../components/ui'
import {FlowShell,checkPane,usePaged,useRowCount} from '../booking/flow/FlowParts'
import {Empty} from '../ticketing/TicketParts'
const iso=(date,time)=>`${date}T${time||'00:00'}:00+05:30`
// Event hire: one Owner fleet must fulfil every vehicle. Two short form screens, then the results on their own tab.
export default function PassengerEventHire(){
  const navigate=useNavigate(),[services,setServices]=useState([]),[form,setForm]=useState({event_type:'',date:'',time:'',expected_hours:'',vehicles_required:'',passenger_count:'',venue:null,pickup:null}),[matches,setMatches]=useState(null),[quote,setQuote]=useState(null),[group,setGroup]=useState(null),[error,setError]=useState(null),[busy,setBusy]=useState(false),[tab,setTab]=useState(0)
  const pane0=useRef(null),pane1=useRef(null)
  useEffect(()=>{publicRead('/event-hire/services').then(x=>setServices(x.items||[])).catch(setError)},[])
  const body=()=>({service_type_id:services[0]?.id,event_type:form.event_type,venue:form.venue,pickup_locations:[form.pickup],event_start_at:iso(form.date,form.time),expected_hours:Number(form.expected_hours),vehicles_required:Number(form.vehicles_required),passenger_count:Number(form.passenger_count),accessibility_required:false})
  async function match(event){event.preventDefault();if(!checkPane(pane0.current).valid){setTab(0);return}if(!checkPane(pane1.current).valid){setTab(1);return}setBusy(true);setError(null);try{setMatches((await publicRequest('/event-hire/search',body())).items);setTab(2)}catch(e){setError(e)}finally{setBusy(false)}}
  async function getQuote(owner){setBusy(true);setError(null);try{setQuote(await publicRequest(`/event-hire/owners/${owner.owner_reference}/quote`,body()))}catch(e){setError(e)}finally{setBusy(false)}}
  async function request(){if(!hasSession()){navigate('/login');return}setBusy(true);try{setGroup(await api('/event-hire/groups',{method:'POST',body:JSON.stringify({...body(),owner_user_reference:quote.allocations?.[0]&&matches.find(x=>x.vehicles.some(v=>v.id===quote.allocations[0].vehicle_id))?.owner_reference,idempotency_key:crypto.randomUUID()})}))}catch(e){setError(e)}finally{setBusy(false)}}
  async function accept(){setBusy(true);try{setGroup(await api(`/event-hire/groups/${group.id}/accept`,{method:'POST',body:JSON.stringify({expected_version:group.version,digest:group.quote.digest})}))}catch(e){setError(e)}finally{setBusy(false)}}
  const set=name=>e=>setForm({...form,[name]:e.target.value})
  const results=Boolean(matches||quote||group)
  const rows=usePaged(matches||[],Math.max(2,useRowCount(70)))
  const tabs=[{label:t('Event'),icon:'calendar',active:tab===0,onClick:()=>setTab(0)},{label:t('Date & vehicles'),icon:'car',active:tab===1,onClick:()=>setTab(1)},...(results?[{label:t('Results'),icon:'check',active:tab===2,onClick:()=>setTab(2)}]:[])]
  return <FlowShell title={t('Event Hire')} info={t('One Owner fleet must fulfil every vehicle allocation. Partial fulfilment is never confirmed.')} icon="calendar" tabs={tabs}>
    <Compact.Provider value={true}>
    <ErrorNotice error={error}/>
    {!services.length?<Empty>{t('Event Hire unavailable. An Admin must activate the Event Hire service before it can be requested.')}</Empty>:<>
      <form className="flow-wizard-form" noValidate onSubmit={match}>
        <div ref={pane0} className="tk-pane" hidden={tab!==0}><div className="tk-grid" style={{'--cols':3}}>
          <Field label="Event type"><input required name="event_type" value={form.event_type} onChange={set('event_type')}/></Field>
          <PlaceSearch name="venue" label="Venue" value={form.venue} onChange={venue=>setForm({...form,venue})}/>
          <PlaceSearch name="pickup" label="Primary pickup location" value={form.pickup} onChange={pickup=>setForm({...form,pickup})}/>
        </div></div>
        <div ref={pane1} className="tk-pane" hidden={tab!==1}><div className="tk-grid" style={{'--cols':3}}>
          <Field label="Event date"><input required name="date" type="date" value={form.date} onChange={set('date')}/></Field>
          <Field label="Event start time"><input required name="time" type="time" value={form.time} onChange={set('time')}/></Field>
          <Field label="Expected hours"><input required name="expected_hours" type="number" min="1" max="24" value={form.expected_hours} onChange={set('expected_hours')}/></Field>
          <Field label="Vehicles required"><input required name="vehicles_required" type="number" min="1" max="20" value={form.vehicles_required} onChange={set('vehicles_required')}/></Field>
          <Field label="Total passengers"><input required name="passenger_count" type="number" min="1" value={form.passenger_count} onChange={set('passenger_count')}/></Field>
        </div></div>
        {tab<2&&<div className="flow-actions">
          {tab===0?<button type="button" className="ui-button ui-button-secondary" onClick={()=>navigate('/travel/book/service')}>{t('Back')}</button>:<button type="button" className="ui-button ui-button-secondary" onClick={()=>setTab(0)}>{t('Back')}</button>}
          {tab===0?<button key="next" type="button" className="ui-button ui-button-primary" disabled={!form.venue||!form.pickup} onClick={()=>{if(checkPane(pane0.current).valid)setTab(1)}}>{t('Next')}</button>
            :<button key="find" type="submit" className="ui-button ui-button-primary" disabled={busy||!form.venue||!form.pickup}>{t('Find one-fleet matches')}</button>}
        </div>}
      </form>
      {tab===2&&<div className="tk-pane">
        {matches&&<><div className="tk-rows">{rows.slice.map(item=><article className="tk-row" key={item.owner_reference}><div className="tk-row-main"><strong>{item.owner_reference}</strong><span>{t('{value0} currently eligible vehicles · all allocations remain with this Owner.',{value0:item.vehicle_count})}</span></div><div className="tk-row-actions"><button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={()=>getQuote(item)}>{t('View combined quote')}</button></div></article>)}</div>
          {!matches.length&&<Empty>{t('No complete fleet match. No single Owner can allocate all required vehicles at this time.')}</Empty>}</>}
        {quote&&<div className="tk-hold"><h3>{t('Combined Event quote')}</h3><p className="tk-line">{(quote.line_items||[]).map(row=>`${row.label}: LKR ${row.amount}`).join(' · ')}</p><p className="tk-line"><strong>{t('Total: LKR {value0}',{value0:quote.total})}</strong> · {t('Venue parking and tolls follow each frozen vehicle package; separately payable actual costs are excluded from this total.')}</p></div>}
        {group&&<p className="tk-line"><Chip tone="info">{String(group.status||'').replaceAll('_',' ')}</Chip> {group.reference} {group.status==='PASSENGER_ACCEPTED'&&t('Waiting for the Owner to assign every allocation. The event confirms only as a complete group.')}</p>}
        <div className="flow-actions"><button type="button" className="ui-button ui-button-secondary" onClick={()=>setTab(1)}>{t('Back')}</button>{rows.pages>1?rows.pager:null}
          {group?.status==='QUOTED'?<button type="button" className="ui-button ui-button-primary" disabled={busy} onClick={accept}>{t('Accept combined quote')}</button>:quote&&!group?<button type="button" className="ui-button ui-button-primary" disabled={busy} onClick={request}>{t('Send Event request')}</button>:<span/>}</div>
      </div>}
    </>}
    </Compact.Provider>
  </FlowShell>
}
