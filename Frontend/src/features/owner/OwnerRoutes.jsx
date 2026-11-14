import { t } from '../../i18n/language.js'
import {useEffect,useRef,useState} from 'react'
import {Link} from 'react-router-dom'
import {api} from '../../services/api'
import {ErrorNotice,Header} from '../../components/components'
import Chip from '../../components/ui/Chip'
import {PlaceSearch,Field,Compact} from './OwnerRates'
import {FlowShell,SegmentedChoice,useWizard,checkPane,usePaged,useRowCount} from '../booking/flow/FlowParts'
import {Notice,Empty} from '../ticketing/TicketParts'

// Owner routes (decision 9 Nov 2026): the Owner adds the roads they run Ticket trips on. A route is usable
// as soon as it is saved; no Admin approval. Places come from location search, never typed coordinates,
// unless search is unavailable (then the Owner may paste map numbers).

const six=v=>v===''||v==null?'':String(Math.round(Number(v)*1e6)/1e6)
const shortName=label=>(label||'').split(',')[0].trim().slice(0,150)
const blankStop=()=>({key:Math.random().toString(36).slice(2),id:null,place:null,name:'',latitude:'',longitude:'',hours:'0',minutes:'0',getOn:true,getOff:true,manual:false,price:''})
const fromServer=s=>({key:s.id,id:s.id,place:{label:s.stop_name,latitude:s.latitude,longitude:s.longitude},name:s.stop_name,latitude:s.latitude,longitude:s.longitude,
  hours:String(Math.floor(s.scheduled_offset_minutes/60)),minutes:String(s.scheduled_offset_minutes%60),getOn:s.pickup_allowed,getOff:s.dropoff_allowed,manual:false,
  price:s.price_from_start==null?'':String(Number(s.price_from_start))})
const offset=s=>(Number(s.hours)||0)*60+(Number(s.minutes)||0)
const money=v=>`LKR ${Number(v||0).toLocaleString('en-LK',{minimumFractionDigits:0,maximumFractionDigits:2})}`
const duration=m=>m<60?`${m} min`:`${Math.floor(m/60)} h${m%60?` ${m%60} min`:''}`
const roleOf=(index,count)=>index===0?'Starting from':index===count-1?'Going to':'Stop on the way'

// One stop at a time: place, name, time from start, optional price, and the two get-on / get-off choices.
function StopEditor({stop,index,count,onChange,priced,lastPrice,lastName}){
  const first=index===0,last=index===count-1
  const set=patch=>onChange({...stop,...patch})
  return <div className="tk-pane">
    <div className="tk-grid" style={{'--cols':stop.manual?3:2}}>
      {stop.manual
        ?<>
          <Field label="Latitude (map number)" help="Google Maps: press and hold the place, then copy the first number."><input required name="latitude" type="number" step="0.000001" min="-90" max="90" value={stop.latitude} onChange={e=>set({latitude:e.target.value})}/></Field>
          <Field label="Longitude (map number)" help="The second number from the same place."><input required name="longitude" type="number" step="0.000001" min="-180" max="180" value={stop.longitude} onChange={e=>set({longitude:e.target.value})}/></Field>
        </>
        :<PlaceSearch key={stop.key} name="place" label="Find the place" value={stop.place} querySeed={stop.name}
           onChange={place=>set(place?{place,latitude:place.latitude,longitude:place.longitude,name:stop.name||shortName(place.label)}:{place:null,latitude:'',longitude:''})}/>}
      <Field label="Name passengers will see" help="Short and clear, e.g. Vavuniya bus stand."><input required name="name" maxLength="150" value={stop.name} onChange={e=>set({name:e.target.value})}/></Field>
    </div>
    <div className="tk-grid" style={{'--cols':priced?3:2}}>
      {first
        ?<Field label="Time from start" help="The trip starts here."><input disabled value="0 min" readOnly/></Field>
        :<>
          <Field label="Hours from start" help="About how long after leaving the first stop you reach this stop."><select name="hours" value={stop.hours} onChange={e=>set({hours:e.target.value})}>{Array.from({length:49},(_,h)=><option key={h} value={h}>{h} h</option>)}</select></Field>
          <Field label="Minutes"><select name="minutes" value={stop.minutes} onChange={e=>set({minutes:e.target.value})}>{[0,5,10,15,20,25,30,35,40,45,50,55].map(m=><option key={m} value={m}>{t('{value0} min',{value0:m})}</option>)}</select></Field>
        </>}
      {priced&&(first
        ?<Field label="Price from the start (LKR)" help="The trip starts here, so this is 0."><input disabled value="0" readOnly/></Field>
        :<Field label="Price from the start (LKR)" help={last?'This is the price for the whole trip.':lastPrice!==''&&stop.price!==''&&Number(lastPrice)>Number(stop.price)?`A passenger getting on here and off at ${lastName||'the last stop'} pays ${money(Number(lastPrice)-Number(stop.price))}.`:'What a passenger pays from the first stop to this stop.'}>
          <input required name="price" type="number" min="0" step="1" inputMode="decimal" value={stop.price} onChange={e=>set({price:e.target.value})}/></Field>)}
    </div>
    <div className="tk-checks">
      <label><input type="checkbox" checked={stop.getOn} disabled={first} onChange={e=>set({getOn:e.target.checked})}/> {t('Passengers can get on here')}</label>
      <label><input type="checkbox" checked={stop.getOff} disabled={last} onChange={e=>set({getOff:e.target.checked})}/> {t('Passengers can get off here')}</label>
      <button type="button" className="tk-link" onClick={()=>set({manual:!stop.manual})}>{stop.manual?'Search for the place instead':'Can’t find it? Enter map numbers instead'}</button>
    </div>
  </div>
}

function RouteForm({editing,onSaved,onCancel,onStep}){
  const [stops,setStops]=useState(editing?editing.stops.map(fromServer):[blankStop(),blankStop()])
  const [name,setName]=useState(editing&&editing.route_name!==`${editing.origin_name} - ${editing.destination_name}`?editing.route_name:'')
  const [distance,setDistance]=useState(editing?.estimated_distance_km?String(Number(editing.estimated_distance_km)):'')
  const [priced,setPriced]=useState(!!editing?.stop_prices_enabled)
  const [busy,setBusy]=useState(false),[error,setError]=useState(null),[current,setCurrent]=useState(0)
  const w=useWizard(3),pane0=useRef(null),pane1=useRef(null)
  useEffect(()=>{onStep(w.step)},[w.step])
  const change=(i,next)=>setStops(stops.map((s,k)=>k===i?next:s))
  const move=d=>{const i=current,next=[...stops];[next[i],next[i+d]]=[next[i+d],next[i]];setStops(next);setCurrent(i+d)}
  const add=()=>{setStops([...stops.slice(0,-1),blankStop(),stops[stops.length-1]]);setCurrent(stops.length-1)}
  const remove=()=>{setStops(stops.filter((_,k)=>k!==current));setCurrent(Math.max(0,current-1))}
  const times=stops.map((s,i)=>i===0?0:offset(s))
  const timeProblem=times.some((m,i)=>i>0&&m<times[i-1])
  const missingPlace=stops.some(s=>s.latitude===''||s.longitude===''||!s.name.trim())
  const prices=stops.map((s,i)=>i===0?0:s.price===''?null:Number(s.price))
  const missingPrice=priced&&prices.some(p=>p==null)
  const priceDown=priced&&prices.some((p,i)=>i>0&&p!=null&&prices[i-1]!=null&&p<prices[i-1])
  const noWholePrice=priced&&!missingPrice&&!(prices[prices.length-1]>0)
  const auto=stops[0].name&&stops[stops.length-1].name?`${stops[0].name} - ${stops[stops.length-1].name}`:''
  const problems=[timeProblem&&'Each stop’s time from start must be the same as or later than the stop before it.',missingPlace&&'Find a place and a name for every stop before saving.',missingPrice&&'Enter a price from the start for every stop.',
    priceDown&&'A stop further along the route cannot cost less from the start than the stop before it.',noWholePrice&&'Enter the price for the whole trip at the last stop.'].filter(Boolean)
  const stop=stops[current]
  async function save(e){
    e.preventDefault();setBusy(true);setError(null)
    const body={stop_prices_enabled:priced,route_name:name.trim()||null,estimated_distance_km:distance===''?null:String(distance),estimated_duration_minutes:times[times.length-1]||null,
      stops:stops.map((s,i)=>({...(s.id?{id:s.id}:{}),stop_name:s.name.trim(),latitude:six(s.latitude),longitude:six(s.longitude),
        pickup_allowed:i===0?true:s.getOn,dropoff_allowed:i===stops.length-1?true:s.getOff,scheduled_offset_minutes:i===0?0:offset(s),
        ...(priced?{price_from_start:i===0?'0':String(s.price)}:{})}))}
    try{
      const saved=editing
        ?await api(`/owners/me/routes/${editing.id}`,{method:'PUT',body:JSON.stringify({...body,expected_version:editing.version})})
        :await api('/owners/me/routes',{method:'POST',body:JSON.stringify(body)})
      onSaved(saved,editing?'Route updated.':'Route saved. You can use it for Ticket departures now.')
    }catch(problem){setError(problem)}finally{setBusy(false)}
  }
  const next=()=>{if(checkPane(w.step===0?pane0.current:pane1.current).valid)w.forward()}
  const review=usePaged(stops,Math.max(3,useRowCount(56)))
  return <form className="flow-wizard-form" onSubmit={save} noValidate>
    <ErrorNotice error={error}/>
    <div ref={pane0} className="tk-pane" hidden={w.step!==0}>
      <SegmentedChoice legend="Ticket price" name="pricing" value={priced?'each':'one'} onChange={k=>setPriced(k==='each')}
        options={[['one','One price for the whole trip (you enter it on each departure)'],['each','Different price for each stop (passengers pay only for the part they travel)']]}/>
      {priced&&<p className="tk-line">{t('For each stop, enter the price from the first stop. Travelly works out the rest: getting on at a stop priced LKR 2,500 and off at one priced LKR 3,500 costs LKR 1,000.')}</p>}
      <div className="tk-grid">
        <Field label="Route name" optional help={auto?`Leave empty to use “${auto}”.`:'Leave empty to name it after the first and last stop.'}><input name="route_name" maxLength="150" value={name} onChange={e=>setName(e.target.value)}/></Field>
        <Field label="Distance in km" optional help="Roughly how far from the first to the last stop."><input name="distance" type="number" min="0" step="0.1" value={distance} onChange={e=>setDistance(e.target.value)}/></Field>
      </div>
    </div>
    <div ref={pane1} className="tk-pane" hidden={w.step!==1}>
      <div className="tk-stop-nav">
        <button type="button" className="ui-button ui-button-secondary" aria-label="Previous stop" disabled={current===0} onClick={()=>setCurrent(current-1)}>‹</button>
        <strong>{t('Stop {value0} of {value1}',{value0:current+1,value1:stops.length})} · {t(roleOf(current,stops.length))}</strong>
        <button type="button" className="ui-button ui-button-secondary" aria-label="Next stop" disabled={current===stops.length-1} onClick={()=>setCurrent(current+1)}>›</button>
        <span className="tk-grow" style={{flex:1}}/>
        {current>0&&<button type="button" className="ui-button ui-button-secondary" onClick={()=>move(-1)}>{t('Move up')}</button>}
        {current<stops.length-1&&<button type="button" className="ui-button ui-button-secondary" onClick={()=>move(1)}>{t('Move down')}</button>}
        {stops.length>2&&<button type="button" className="ui-button ui-button-secondary" onClick={remove}>{t('Remove stop')}</button>}
        <button type="button" className="ui-button ui-button-secondary" disabled={stops.length>=50} onClick={add}>{t('+ Add a stop on the way')}</button>
      </div>
      <StopEditor key={stop.key} priced={priced} lastPrice={stops[stops.length-1].price} lastName={stops[stops.length-1].name} stop={stop} index={current} count={stops.length} onChange={next=>change(current,next)}/>
    </div>
    <div className="tk-pane" hidden={w.step!==2}>
      <p className="tk-line"><strong>{name.trim()||auto||t('New route')}</strong>{times[times.length-1]>0&&<> · {t('whole trip about {value0}',{value0:duration(times[times.length-1])})}</>}{priced&&!missingPrice&&!priceDown&&prices[prices.length-1]>0&&<> · {t('whole trip {value0}',{value0:money(prices[prices.length-1])})}</>}</p>
      <div className="tk-rows">{review.slice.map(s=>{const i=stops.indexOf(s);return <div className="tk-row" key={s.key}>
        <div className="tk-row-main"><strong>{i+1}. {s.name||'No name yet'}</strong><span>{roleOf(i,stops.length)} · {i===0?'0 min':duration(times[i])}{priced&&` · ${i===0?money(0):s.price===''?'no price':money(s.price)}`}</span></div>
        <div className="tk-row-actions">{i>0&&<Chip tone={s.getOn?'success':'muted'}>{s.getOn?'Get on':'No get on'}</Chip>}{i<stops.length-1&&<Chip tone={s.getOff?'success':'muted'}>{s.getOff?'Get off':'No get off'}</Chip>}
          <button type="button" className="ui-button ui-button-secondary" onClick={()=>{setCurrent(i);w.setStep(1)}}>{t('Edit')}</button></div></div>})}</div>
      {problems.map(p=><p key={p} className="tk-line is-warn" role="alert">{p}</p>)}
    </div>
    <div className="flow-actions">
      {w.step>0?<button type="button" className="ui-button ui-button-secondary" onClick={w.back}>{t('Back')}</button>:editing?<button type="button" className="ui-button ui-button-secondary" onClick={onCancel}>{t('Cancel')}</button>:<span/>}
      {w.step===2&&review.pages>1&&review.pager}
      {w.step<2
        ?<button key="next" type="button" className="ui-button ui-button-primary" onClick={next}>{t('Next')}</button>
        :<button key="save" type="submit" className="ui-button ui-button-primary" disabled={busy||problems.length>0}>{busy?'Saving…':editing?'Save changes':'Save route'}</button>}
    </div>
  </form>
}

function RouteRow({route,onEdit,onChanged,setError}){
  const [busy,setBusy]=useState(false)
  async function toggle(){
    setBusy(true);setError(null)
    try{const saved=await api(`/owners/me/routes/${route.id}/status`,{method:'PATCH',body:JSON.stringify({expected_version:route.version,active:route.status!=='ACTIVE'})})
      onChanged(saved.status==='ACTIVE'?'Route turned on.':'Route turned off. New departures cannot use it.')}
    catch(problem){setError(problem)}finally{setBusy(false)}
  }
  const path=route.stops.map(s=>s.stop_name+(route.stop_prices_enabled&&s.price_from_start!=null?` (${money(s.price_from_start)})`:'')).join(' → ')
  return <article className="tk-row">
    <div className="tk-row-main"><strong>{route.route_name}</strong>
      <span title={path}>{path}</span>
      <span>{route.stop_prices_enabled?t('Price for each stop'):t('One price, set on each departure')} · {t('{value0} stops',{value0:route.stops.length})}{route.estimated_duration_minutes?` · ${t('about {value0}',{value0:duration(route.estimated_duration_minutes)})}`:''}{route.estimated_distance_km?` · ${Number(route.estimated_distance_km)} km`:''}</span></div>
    <div className="tk-row-actions">
      <Chip tone={route.status==='ACTIVE'?'success':'muted'}>{route.status==='ACTIVE'?t('On'):route.deactivated_by_admin?t('Turned off by Travelly'):t('Off')}</Chip>
      {!route.mine&&<Chip tone="info">{t('Travelly route')}</Chip>}
      {route.mine&&<button type="button" className="ui-button ui-button-secondary" onClick={onEdit}>{t('Edit')}</button>}
      {route.mine&&!route.deactivated_by_admin&&<button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={toggle}>{route.status==='ACTIVE'?'Turn off':'Turn on'}</button>}
    </div>
  </article>
}

export default function OwnerRoutes(){
  const [routes,setRoutes]=useState(null),[error,setError]=useState(null),[notice,setNotice]=useState(''),[editing,setEditing]=useState(null),[formKey,setFormKey]=useState(0),[tab,setTab]=useState(0),[step,setStep]=useState(0)
  const load=()=>api('/owners/me/routes').then(x=>setRoutes(x.items||[])).catch(setError)
  useEffect(()=>{load()},[])
  useEffect(()=>{if(!notice)return;const timer=setTimeout(()=>setNotice(''),8000);return ()=>clearTimeout(timer)},[notice])
  function done(message){setNotice(message);setEditing(null);setFormKey(k=>k+1);setTab(0);load()}
  const all=[...(routes||[]).filter(r=>r.mine),...(routes||[]).filter(r=>!r.mine)]
  const list=usePaged(all,Math.max(2,useRowCount(76)))
  const tabs=[{label:'Your routes',icon:'route',active:tab===0,onClick:()=>setTab(0)},{label:editing?'Edit route':'Add a route',icon:'calendar',active:tab===1,onClick:()=>setTab(1)}]
  return <><Header/><FlowShell heading="My routes" icon="route" title={tab===0?'Your routes':editing?`Edit ${editing.route_name}`:'Add a route'}
    info={tab===0?'The roads you run Ticket trips on. Passengers choose where they get on and off from your stops.':'Add the stops in the order the vehicle drives. The first stop is where the trip starts, the last is where it ends.'}
    tabs={tabs} steps={tab===1?['Price and name','Stops','Review and save']:undefined} current={step} onStepSelect={undefined}>
    <Compact.Provider value={true}>
      <Notice>{notice}</Notice><ErrorNotice error={error}/>
      <div className="tk-pane" hidden={tab!==0}>
        {routes===null?<p role="status">{t('Loading routes…')}</p>:all.length
          ?<div className="tk-rows">{list.slice.map(r=><RouteRow key={`${r.id}-${r.version}`} route={r} setError={setError} onChanged={done} onEdit={()=>{setEditing(r);setTab(1)}}/>)}</div>
          :<Empty>{t('No routes yet. Add your first route.')}</Empty>}
        <div className="flow-actions"><Link className="ui-button ui-button-secondary" to="/owner/ticket-departures">{t('Go to Ticket departures')}</Link>{all.length>list.slice.length||list.pages>1?list.pager:null}<button type="button" className="ui-button ui-button-primary" onClick={()=>setTab(1)}>{editing?t('Continue editing'):t('Add a route')}</button></div>
      </div>
      <div className="tk-pane" hidden={tab!==1}>
        <RouteForm key={editing?`edit-${editing.id}-${editing.version}`:`new-${formKey}`} editing={editing} onSaved={(_,message)=>done(message)} onCancel={()=>{setEditing(null);setFormKey(k=>k+1);setTab(0)}} onStep={setStep}/>
      </div>
    </Compact.Provider>
  </FlowShell></>
}
