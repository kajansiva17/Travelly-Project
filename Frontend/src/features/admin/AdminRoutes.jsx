import { t } from '../../i18n/language.js'
import React,{useEffect,useRef,useState} from 'react'
import {Link} from 'react-router-dom'
import {api} from '../../services/api'
import {Header,ErrorNotice} from '../../components/components'
import Chip from '../../components/ui/Chip'
import {Field,Compact} from '../owner/OwnerRates'
import {FlowShell,useWizard,checkPane,usePaged,useRowCount} from '../booking/flow/FlowParts'
import {Notice,Empty} from '../ticketing/TicketParts'

const blankStop=()=>({stop_name:'',latitude:'',longitude:'',pickup_allowed:true,dropoff_allowed:true,scheduled_offset_minutes:'0'})
const blankRoute=()=>({route_code:'',route_name:'',origin_name:'',destination_name:'',estimated_distance_km:'',estimated_duration_minutes:'',active:true})
const num=v=>v===''||v==null?null:String(v)

export default function AdminRoutes(){
  const [form,setForm]=useState(blankRoute()),[stops,setStops]=useState([blankStop(),blankStop()]),[routes,setRoutes]=useState(null),[error,setError]=useState(null),[busy,setBusy]=useState(false),[notice,setNotice]=useState('')
  const [tab,setTab]=useState(0),[current,setCurrent]=useState(0),w=useWizard(2),pane0=useRef(null)
  const load=()=>api('/admin/routes').then(x=>setRoutes(x.items||[])).catch(setError)
  useEffect(()=>{load()},[])
  const setStop=(i,patch)=>setStops(stops.map((s,k)=>k===i?{...s,...patch}:s))
  const stopBad=stops.some(s=>!s.stop_name.trim()||s.latitude===''||s.longitude===''||s.scheduled_offset_minutes==='')
  async function create(e){
    e.preventDefault();setBusy(true);setError(null);setNotice('')
    try{
      const created=await api('/admin/routes',{method:'POST',body:JSON.stringify({
        route_code:form.route_code.trim(),route_name:form.route_name,origin_name:form.origin_name,destination_name:form.destination_name,
        estimated_distance_km:num(form.estimated_distance_km),estimated_duration_minutes:form.estimated_duration_minutes===''?null:Number(form.estimated_duration_minutes),
        active:form.active,
        stops:stops.map(s=>({stop_name:s.stop_name,latitude:String(s.latitude),longitude:String(s.longitude),pickup_allowed:s.pickup_allowed,dropoff_allowed:s.dropoff_allowed,scheduled_offset_minutes:Number(s.scheduled_offset_minutes||0)}))})})
      setNotice(`Route ${created.route_code} saved as ${created.status}.`);setForm(blankRoute());setStops([blankStop(),blankStop()]);setCurrent(0);w.setStep(0);setTab(1);load()
    }catch(problem){setError(problem)}finally{setBusy(false)}
  }
  async function toggle(r){
    setError(null);setNotice('')
    try{const saved=await api(`/admin/routes/${r.id}`,{method:'PATCH',body:JSON.stringify({expected_version:r.version,status:r.status==='ACTIVE'?'INACTIVE':'ACTIVE'})})
      setNotice(saved.status==='ACTIVE'?`${saved.route_name} turned on.`:`${saved.route_name} turned off. The Owner cannot turn it back on.`);load()}
    catch(problem){setError(problem)}
  }
  const list=usePaged(routes||[],Math.max(2,useRowCount(64)))
  const stop=stops[current]
  const tabs=[{label:'Create a route',icon:'route'},{label:'All routes',icon:'calendar'}].map((x,i)=>({...x,active:tab===i,onClick:()=>setTab(i)}))
  const set=k=>e=>setForm({...form,[k]:e.target.value})
  const remove=()=>{setStops(stops.filter((_,k)=>k!==current));setCurrent(Math.max(0,current-1))}
  return <><Header/><FlowShell heading="Ticket routes" icon="route" title={tab===0?'Create a route':'All routes'}
    info={tab===0?'Owners add their own routes; you only need to turn off a wrong or abusive route. You can also add a Travelly route every Owner can use. Minutes from start must not decrease along the route. The first stop must allow pickup and the last must allow drop-off.':'Owners add their own routes; you only need to turn off a wrong or abusive route.'}
    tabs={tabs} steps={tab===0?['Route details','Stops']:undefined} current={w.step}>
    <Compact.Provider value={true}>
    <ErrorNotice error={error}/><Notice>{notice}</Notice>
    <form className="flow-wizard-form tk-pane" hidden={tab!==0} noValidate onSubmit={create}>
      <div ref={pane0} className="tk-pane" hidden={w.step!==0}>
        <div className="tk-grid" style={{'--cols':3}}>
          <Field label="Route code" help="For example COL-KDY."><input required name="code" maxLength="30" value={form.route_code} onChange={set('route_code')}/></Field>
          <Field label="Route name"><input required name="name" maxLength="150" value={form.route_name} onChange={set('route_name')}/></Field>
          <Field label="Origin"><input required name="origin" maxLength="150" value={form.origin_name} onChange={set('origin_name')}/></Field>
          <Field label="Destination"><input required name="destination" maxLength="150" value={form.destination_name} onChange={set('destination_name')}/></Field>
          <Field label="Distance (km)" optional><input name="distance" min="0" step="0.001" type="number" value={form.estimated_distance_km} onChange={set('estimated_distance_km')}/></Field>
          <Field label="Duration (minutes)" optional><input name="duration" min="0" type="number" value={form.estimated_duration_minutes} onChange={set('estimated_duration_minutes')}/></Field>
        </div>
        <div className="tk-checks"><label><input type="checkbox" checked={form.active} onChange={e=>setForm({...form,active:e.target.checked})}/> {t('Make the route available to Owners now')}</label></div>
      </div>
      <div className="tk-pane" hidden={w.step!==1}>
        <div className="tk-stop-nav">
          <button type="button" className="ui-button ui-button-secondary" aria-label="Previous stop" disabled={current===0} onClick={()=>setCurrent(current-1)}>‹</button>
          <strong>{t('Stop {value0} of {value1}',{value0:current+1,value1:stops.length})}</strong>
          <button type="button" className="ui-button ui-button-secondary" aria-label="Next stop" disabled={current===stops.length-1} onClick={()=>setCurrent(current+1)}>›</button>
          <span style={{flex:1}}/>
          {stops.length>2&&<button type="button" className="ui-button ui-button-secondary" onClick={remove}>{t('Remove stop')}</button>}
          <button type="button" className="ui-button ui-button-secondary" disabled={stops.length>=50} onClick={()=>{setStops([...stops,blankStop()]);setCurrent(stops.length)}}>{t('Add stop')}</button>
        </div>
        <div className="tk-grid" style={{'--cols':2}} key={current}>
          <Field label="Stop name"><input required name="stop_name" maxLength="150" value={stop.stop_name} onChange={e=>setStop(current,{stop_name:e.target.value})}/></Field>
          <Field label="Minutes from start"><input required name="offset" type="number" min="0" value={stop.scheduled_offset_minutes} onChange={e=>setStop(current,{scheduled_offset_minutes:e.target.value})}/></Field>
          <Field label="Latitude"><input required name="lat" type="number" step="0.000001" min="-90" max="90" value={stop.latitude} onChange={e=>setStop(current,{latitude:e.target.value})}/></Field>
          <Field label="Longitude"><input required name="lng" type="number" step="0.000001" min="-180" max="180" value={stop.longitude} onChange={e=>setStop(current,{longitude:e.target.value})}/></Field>
        </div>
        <div className="tk-checks">
          <label><input type="checkbox" checked={stop.pickup_allowed} onChange={e=>setStop(current,{pickup_allowed:e.target.checked})}/> {t('Pickup')}</label>
          <label><input type="checkbox" checked={stop.dropoff_allowed} onChange={e=>setStop(current,{dropoff_allowed:e.target.checked})}/> {t('Drop-off')}</label>
        </div>
        {stopBad&&<p className="tk-line is-warn">{t('Every stop needs a name, latitude, longitude and minutes from start before saving.')}</p>}
      </div>
      <div className="flow-actions">
        {w.step>0?<button type="button" className="ui-button ui-button-secondary" onClick={w.back}>{t('Back')}</button>:<span/>}
        {w.step===0
          ?<button key="next" type="button" className="ui-button ui-button-primary" onClick={()=>{if(checkPane(pane0.current).valid)w.forward()}}>{t('Next')}</button>
          :<button key="save" type="submit" className="ui-button ui-button-primary" disabled={busy||stopBad}>{busy?'Saving…':'Save route'}</button>}
      </div>
    </form>

    <div className="tk-pane" hidden={tab!==1}>
      {routes===null?<p role="status">{t('Loading routes…')}</p>:routes.length
        ?<div className="tk-rows">{list.slice.map(r=><article className="tk-row" key={`${r.id}-${r.version}`}>
          <div className="tk-row-main"><strong>{r.route_name}</strong><span>{r.origin_name} → {r.destination_name} · {r.owner_user_id?'Owner route':'Travelly route'}</span></div>
          <div className="tk-row-actions"><Chip tone={r.status==='ACTIVE'?'success':'muted'}>{r.status==='ACTIVE'?'On':'Off'}</Chip>
            {r.status!=='DRAFT'&&<button type="button" className="ui-button ui-button-secondary" onClick={()=>toggle(r)}>{r.status==='ACTIVE'?'Turn off':'Turn on'}</button>}</div></article>)}</div>
        :<Empty>{t('No routes yet. Create the first route.')}</Empty>}
      <div className="flow-actions"><Link className="ui-button ui-button-secondary" to="/admin/services-routes">{t('Back to service catalogue')}</Link>{list.pages>1?list.pager:null}<button type="button" className="ui-button ui-button-primary" onClick={()=>setTab(0)}>{t('Create a route')}</button></div>
    </div>
    </Compact.Provider>
  </FlowShell></>
}
