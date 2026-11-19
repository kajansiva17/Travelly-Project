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
const blankStop=()=>({key:Math.random().toString(36).slice(2),id:null,place:null,name:'',latitude:'',longitude:'',getOn:true,getOff:true,manual:false,price:''})
const fromServer=s=>({key:s.id,id:s.id,place:{label:s.stop_name,latitude:s.latitude,longitude:s.longitude},name:s.stop_name,latitude:s.latitude,longitude:s.longitude,
  getOn:s.pickup_allowed,getOff:s.dropoff_allowed,manual:false,
  price:s.price_from_start==null?'':String(Number(s.price_from_start))})
const money=v=>`LKR ${Number(v||0).toLocaleString('en-LK',{minimumFractionDigits:0,maximumFractionDigits:2})}`
const duration=m=>m<60?`${m} min`:`${Math.floor(m/60)} h${m%60?` ${m%60} min`:''}`
const roleOf=(index,count)=>index===0?'Starting from':index===count-1?'Going to':'Stop on the way'
const roleHelp=(index,count)=>index===0?'The trip starts here. Passengers get on here.':index===count-1?'The trip ends here. Passengers get off here.':'A place the vehicle stops on the way. Tick whether passengers can get on or off here.'

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
    {priced&&<div className="tk-grid" style={{'--cols':2}}>
      {(first
        ?<Field label="Price from the start (LKR)" help="The trip starts here, so this is 0."><input disabled value="0" readOnly/></Field>
        :<Field label="Price from the start (LKR)" help={last?'This is the price for the whole trip, from the start to here.':lastPrice!==''&&stop.price!==''&&Number(lastPrice)>Number(stop.price)?`A passenger getting on here and off at ${lastName||'the last stop'} pays ${money(Number(lastPrice)-Number(stop.price))}.`:'What a passenger pays from the first stop to this stop.'}>
          <input required name="price" type="number" min="0" step="1" inputMode="decimal" value={stop.price} onChange={e=>set({price:e.target.value})}/></Field>)}
    </div>}
    <div className="tk-checks">
      {!first&&!last&&<label><input type="checkbox" checked={stop.getOn} onChange={e=>set({getOn:e.target.checked})}/> {t('Passengers can get on here')}</label>}
      {!first&&!last&&<label><input type="checkbox" checked={stop.getOff} onChange={e=>set({getOff:e.target.checked})}/> {t('Passengers can get off here')}</label>}
      <button type="button" className="tk-link" onClick={()=>set({manual:!stop.manual})}>{stop.manual?'Search for the place instead':'Can’t find it? Enter map numbers instead'}</button>
    </div>
  </div>
}

function RouteForm({editing,onSaved,onCancel,onList}){
  const [stops,setStops]=useState(editing?editing.stops.map(fromServer):[blankStop(),blankStop()])
  const [name,setName]=useState(editing&&editing.route_name!==`${editing.origin_name} - ${editing.destination_name}`?editing.route_name:'')
  const [distance,setDistance]=useState(editing?.estimated_distance_km?String(Number(editing.estimated_distance_km)):'')
  const [priced,setPriced]=useState(!!editing?.stop_prices_enabled)
  const [busy,setBusy]=useState(false),[error,setError]=useState(null),[sub,setSub]=useState(null),[hint,setHint]=useState('')
  const w=useWizard(3),pane0=useRef(null),pane1=useRef(null),pane2=useRef(null)
  const last=stops.length-1,start=stops[0],end=stops[last]
  const isBlank=s=>!s.name.trim()&&s.latitude===''&&s.longitude===''&&s.price===''
  const change=(i,next)=>setStops(stops.map((s,k)=>k===i?next:s))
  const addMid=()=>{setStops([...stops.slice(0,-1),blankStop(),stops[last]]);setSub(stops.length-1)}
  const removeMid=i=>{setStops(stops.filter((_,k)=>k!==i));setSub(null)}
  const doneMid=()=>{if(sub!=null&&isBlank(stops[sub]))setStops(stops.filter((_,k)=>k!==sub));setSub(null)}
  const move=(i,d)=>{const next=[...stops];[next[i],next[i+d]]=[next[i+d],next[i]];setStops(next)}
  // Empty "on the way" stops are ignored, so only a real start, a real end and any filled stops count.
  const used=stops.filter((s,i)=>i===0||i===last||!isBlank(s))
  const prices=used.map((s,i)=>i===0?0:s.price===''?null:Number(s.price))
  const missingPlace=used.some(s=>s.latitude===''||s.longitude===''||!s.name.trim())
  const missingPrice=priced&&prices.some(p=>p==null)
  const priceDown=priced&&prices.some((p,i)=>i>0&&p!=null&&prices[i-1]!=null&&p<prices[i-1])
  const noWholePrice=priced&&!missingPrice&&!(prices[prices.length-1]>0)
  const auto=start.name&&end.name?`${start.name} - ${end.name}`:''
  const problems=[missingPlace&&'Find a place and a name for the start, the end and every stop you add.',missingPrice&&'Enter a price from the start for the end point and every stop.',
    priceDown&&'A stop further along the route cannot cost less from the start than the stop before it.',noWholePrice&&'Enter the price for the whole trip at the end point.'].filter(Boolean)
  const mids=stops.map((s,i)=>[s,i]).filter(([s,i])=>i>0&&i<last&&!isBlank(s)||i===sub)
  async function save(e){
    e.preventDefault();setBusy(true);setError(null)
    const body={stop_prices_enabled:priced,route_name:name.trim()||null,estimated_distance_km:distance===''?null:String(distance),
      stops:used.map((s,i)=>({...(s.id?{id:s.id}:{}),stop_name:s.name.trim(),latitude:six(s.latitude),longitude:six(s.longitude),
        pickup_allowed:i===0?true:i===used.length-1?false:s.getOn,dropoff_allowed:i===0?false:i===used.length-1?true:s.getOff,
        ...(priced?{price_from_start:i===0?'0':String(s.price)}:{})}))}
    try{
      const saved=editing
        ?await api(`/owners/me/routes/${editing.id}`,{method:'PUT',body:JSON.stringify({...body,expected_version:editing.version})})
        :await api('/owners/me/routes',{method:'POST',body:JSON.stringify(body)})
      onSaved(saved,editing?'Route updated.':'Route saved. You can use it for Ticket departures now.')
    }catch(problem){setError(problem)}finally{setBusy(false)}
  }
  const stepNames=['Price and name','Start point','End point']
  function next(){
    setHint('')
    if(w.step===0){if(checkPane(pane0.current).valid)w.forward();return}
    if(w.step===1){
      if(!checkPane(pane1.current).valid)return
      if(start.latitude===''||start.longitude===''){setHint('Find the start place first.');return}
      w.forward()
    }
  }
  const midStop=sub!=null?stops[sub]:null
  const summary=!problems.length&&auto?`${auto}${priced&&prices[prices.length-1]>0?` · ${money(prices[prices.length-1])}`:''}${used.length>2?` · ${t('{value0} stops on the way',{value0:used.length-2})}`:''}`:''
  return <form className="flow-wizard-form" onSubmit={save} noValidate>
    <p className="tk-stepline">{t('Step {value0} of {value1}',{value0:w.step+1,value1:3})} · <strong>{t(stepNames[w.step])}</strong></p>
    <ErrorNotice error={error}/>
    <div ref={pane0} className="tk-pane" hidden={w.step!==0}>
      <SegmentedChoice legend="Ticket price" name="pricing" value={priced?'each':'one'} onChange={k=>setPriced(k==='each')}
        options={[['one','One price for the whole trip (you enter it on each departure)'],['each','Different price for each stop (passengers pay only for the part they travel)']]}/>
      {priced&&<p className="tk-line">{t('For each stop, enter the price from the first stop. Travelly works out the rest: getting on at a stop priced LKR 2,500 and off at one priced LKR 3,500 costs LKR 1,000.')}</p>}
      <div className="tk-grid">
        <Field label="Route name" optional help={auto?`Leave empty to use “${auto}”.`:'Leave empty to name it after the start and end point.'}><input name="route_name" maxLength="150" value={name} onChange={e=>setName(e.target.value)}/></Field>
        <Field label="Distance in km" optional help="Roughly how far from the start to the end."><input name="distance" type="number" min="0" step="0.1" value={distance} onChange={e=>setDistance(e.target.value)}/></Field>
      </div>
    </div>
    <div ref={pane1} className="tk-pane" hidden={w.step!==1}>
      <p className="tk-line">{t('The trip starts here. Passengers get on here.')}</p>
      <StopEditor key={start.key} priced={priced} stop={start} index={0} count={stops.length} onChange={n=>change(0,n)}/>
      {hint&&<p className="tk-line is-warn" role="alert">{t(hint)}</p>}
    </div>
    <div ref={pane2} className="tk-pane" hidden={w.step!==2}>
      {midStop==null?<>
        <p className="tk-line">{t('The trip ends here. Passengers get off here.')}</p>
        <StopEditor key={end.key} priced={priced} lastPrice={end.price} lastName={end.name} stop={end} index={last} count={stops.length} onChange={n=>change(last,n)}/>
        {summary&&<p className="tk-line tk-summary">{summary}</p>}
        <div className="tk-mids">
          <strong>{t('Stops on the way')} <span className="tk-opt">({t('Optional')})</span></strong>
          <div className="tk-midchips">{mids.map(([s,i])=><span className="tk-midchip" key={s.key}><button type="button" className="tk-midname" onClick={()=>setSub(i)} title={t('Edit')}>{s.name||t('No name yet')}{priced&&s.price!==''?` · ${money(s.price)}`:''}</button><button type="button" className="tk-midx" aria-label={t('Remove stop')} onClick={()=>removeMid(i)}>×</button></span>)}
          <button type="button" className="ui-button ui-button-secondary tk-addmid" disabled={stops.length>=50} onClick={addMid}>{t('+ Add a stop on the way')}</button></div>
        </div>
      </>:<>
        <div className="tk-subbar"><span className="tk-line">{t(roleHelp(sub,stops.length))}</span>
          <button type="button" className="ui-button ui-button-secondary" disabled={sub<2} onClick={()=>{move(sub,-1);setSub(sub-1)}}>{t('Move up')}</button>
          <button type="button" className="ui-button ui-button-secondary" disabled={sub>=last-1} onClick={()=>{move(sub,1);setSub(sub+1)}}>{t('Move down')}</button>
          <button type="button" className="ui-button ui-button-secondary" onClick={()=>removeMid(sub)}>{t('Remove stop')}</button></div>
        <StopEditor key={midStop.key} priced={priced} lastPrice={end.price} lastName={end.name} stop={midStop} index={sub} count={stops.length} onChange={n=>change(sub,n)}/>
      </>}
      {midStop==null&&problems.map(p=><p key={p} className="tk-line is-warn" role="alert">{t(p)}</p>)}
    </div>
    {w.step>0&&midStop==null&&<ol className="tk-preview" aria-label={t('Your route so far')}>{[start,...stops.slice(1,-1).filter(x=>!isBlank(x)),end].map((s,i,arr)=><li key={s.key} className={i===0||i===arr.length-1?'is-end':''}><span className="tk-dot"/><span className="tk-pname">{s.name||(i===0?t('Start point'):t('End point'))}</span>{priced&&i>0&&s.price!==''&&<span className="tk-pprice">{money(s.price)}</span>}</li>)}</ol>}
    <div className="flow-actions">
      {w.step===0?<button type="button" className="ui-button ui-button-secondary" onClick={editing?onCancel:onList}>{t('Back to routes')}</button>
        :midStop!=null?<button type="button" className="ui-button ui-button-secondary" onClick={doneMid}>{t('Back')}</button>
        :<button type="button" className="ui-button ui-button-secondary" onClick={()=>{setHint('');w.back()}}>{t('Back')}</button>}
      {w.step<2
        ?<button key="next" type="button" className="ui-button ui-button-primary" onClick={next}>{w.step===0?t('Next'):t('Next: end point')}</button>
        :midStop!=null
          ?<button key="done" type="button" className="ui-button ui-button-primary" onClick={doneMid}>{t('Done')}</button>
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

/* Routes section. Used inside the Ticket page (tab 2) and by the old /owner/routes address.
   The parent owns "mode" ('list' or 'form') so its tab bar and step bar can follow it. */
export function RoutesPanel({mode,setMode,onStep,onGoDepartures}){
  const [routes,setRoutes]=useState(null),[error,setError]=useState(null),[notice,setNotice]=useState(''),[editing,setEditing]=useState(null),[formKey,setFormKey]=useState(0)
  const load=()=>api('/owners/me/routes').then(x=>setRoutes(x.items||[])).catch(setError)
  useEffect(()=>{load()},[])
  useEffect(()=>{if(!notice)return;const timer=setTimeout(()=>setNotice(''),8000);return ()=>clearTimeout(timer)},[notice])
  function done(message){setNotice(message);setEditing(null);setFormKey(k=>k+1);setMode('list');load()}
  const all=[...(routes||[]).filter(r=>r.mine),...(routes||[]).filter(r=>!r.mine)]
  const list=usePaged(all,Math.max(2,useRowCount(76)))
  return <>
    <Notice>{notice}</Notice><ErrorNotice error={error}/>
    <div className="tk-pane" hidden={mode!=='list'}>
      {routes===null?<p role="status">{t('Loading routes…')}</p>:all.length
        ?<div className="tk-rows">{list.slice.map(r=><RouteRow key={`${r.id}-${r.version}`} route={r} setError={setError} onChanged={done} onEdit={()=>{setEditing(r);setMode('form')}}/>)}</div>
        :<Empty>{t('No routes yet. Add your first route.')}</Empty>}
      <div className="flow-actions">{onGoDepartures&&<button type="button" className="ui-button ui-button-secondary" onClick={onGoDepartures}>{t('Next: create a departure')}</button>}{all.length>list.slice.length||list.pages>1?list.pager:null}<button type="button" className="ui-button ui-button-primary" onClick={()=>setMode('form')}>{editing?t('Continue editing'):t('Add a route')}</button></div>
    </div>
    <div className="tk-pane" hidden={mode!=='form'}>
      <RouteForm key={editing?`edit-${editing.id}-${editing.version}`:`new-${formKey}`} editing={editing} onSaved={(_,message)=>done(message)} onCancel={()=>{setEditing(null);setFormKey(k=>k+1);setMode('list')}} onList={()=>setMode('list')}/>
    </div>
  </>
}

export default function OwnerRoutes(){
  const [mode,setMode]=useState('list'),[step,setStep]=useState(0)
  const tabs=[{label:'Your routes',icon:'route',active:mode==='list',onClick:()=>setMode('list')},{label:'Add a route',icon:'calendar',active:mode==='form',onClick:()=>setMode('form')}]
  return <><Header/><FlowShell heading="Ticket routes" icon="route" title={mode==='list'?'Your routes':'Add a route'}
    info={mode==='list'?'The roads your buses and vans run Ticket trips on, with seats.':'Add where the trip starts and ends, and the stops on the way if you have any. Travelly works out the arrival time at each stop from the road.'}
    tabs={tabs}>
    <Compact.Provider value={true}>
      <RoutesPanel mode={mode} setMode={setMode} onStep={setStep}/>
    </Compact.Provider>
  </FlowShell></>
}
