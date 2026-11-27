import { t } from '../../i18n/language.js'
import {useCallback,useEffect,useRef,useState} from 'react'
import {api} from '../../services/api'
import Chip from '../../components/ui/Chip'
import {Icon} from '../../components/components'
import InfoTip from '../../components/ui/InfoTip'
import {Field,RateErrors} from './OwnerRates'
import {Pager} from '../booking/flow/FlowParts'
import {DateTimeFields,Empty} from '../ticketing/TicketParts'
import {formatDateTime,formatDate} from '../../i18n/dateTime.js'
import {fieldErrors,fieldErrorMap} from '../../services/fieldErrors.js'
import {codeEnglish} from '../../i18n/codeLabels.js'

// Vehicle Maintenance tab (Vehicle records contract 03M): summary of tasks, records list, and a two-step "Add record" form.
// The type picker comes from allowed_record_types; the fields of each type follow the contract table.
const TYPE_LABELS={OIL_CHANGE:'Oil change',OIL_FILTER_CHANGE:'Oil filter change',TYRE_CHANGE:'Tyre change',TYRE_ROTATION:'Tyre rotation',WHEEL_ALIGNMENT:'Wheel alignment',WHEEL_BALANCING:'Wheel balancing',GENERAL_SERVICE:'General service',BRAKE_SERVICE:'Brake service',BATTERY_SERVICE:'Battery service',REPAIR:'Repair',FUEL_PURCHASE:'Fuel purchase',EV_CHARGING:'EV charging',ODOMETER_UPDATE:'Odometer reading',PERSONAL_EXTRA_USE:'Personal or off-platform use'}
const typeLabel=type=>t(TYPE_LABELS[type]||codeEnglish(type))
const SERVICE_TYPES=['OIL_CHANGE','OIL_FILTER_CHANGE','TYRE_CHANGE','TYRE_ROTATION','WHEEL_ALIGNMENT','WHEEL_BALANCING','GENERAL_SERVICE','BRAKE_SERVICE','BATTERY_SERVICE']
// Extra fields per type (contract table). "step1" fields are asked with the date, the rest in step 2.
const FIELD_SPEC=type=>{
  if(SERVICE_TYPES.includes(type))return {step1:['odometer_km'],step2:['amount','next_due_odometer_km','genuine_calendar_due_date','service_provider','notes'],required:[]}
  if(type==='REPAIR')return {step1:['odometer_km'],step2:['amount','service_provider','notes'],required:[]}
  if(type==='FUEL_PURCHASE')return {step1:['odometer_km'],step2:['quantity','amount','fuel_grade_product','service_provider','notes'],required:['fuel_grade_product','quantity','amount']}
  if(type==='EV_CHARGING')return {step1:['odometer_km'],step2:['amount','charging_kwh','service_provider','notes'],required:['amount']}
  if(type==='ODOMETER_UPDATE')return {step1:['odometer_km'],step2:['notes'],required:['odometer_km']}
  if(type==='PERSONAL_EXTRA_USE')return {step1:['start_odometer_km','end_odometer_km'],step2:['notes'],required:['start_odometer_km','end_odometer_km']}
  return {step1:['odometer_km'],step2:['amount','service_provider','notes'],required:[]}
}
const FIELD_LABEL={odometer_km:'Odometer (km)',start_odometer_km:'Start odometer (km)',end_odometer_km:'End odometer (km)',amount:'Amount (LKR)',quantity:'Fuel (litres)',fuel_grade_product:'Fuel grade or product',charging_kwh:'Charged (kWh)',next_due_odometer_km:'Next due at (km)',genuine_calendar_due_date:'Next due date',service_provider:'Service provider',notes:'Notes'}
const FIELD_HELP={odometer_km:'The odometer reading when this was done.',next_due_odometer_km:'Must be above the odometer reading.',genuine_calendar_due_date:'Only if the manufacturer or the garage gave a date. Must be after the record date.',fuel_grade_product:'For example Octane 92 or Auto Diesel.'}
const DECIMALS={odometer_km:1,start_odometer_km:1,end_odometer_km:1,next_due_odometer_km:1,amount:2,quantity:3,charging_kwh:3}
const kmText=value=>value==null||value===''?'—':`${Number(value).toLocaleString('en-LK',{maximumFractionDigits:1})} km`
const moneyText=(currency,value)=>`${currency||'LKR'} ${Number(value||0).toLocaleString('en-LK',{minimumFractionDigits:2,maximumFractionDigits:2})}`
const dateOnly=formatDate
const pad=n=>String(n).padStart(2,'0')
const toLocal=d=>`${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
const nowLocal=()=>toLocal(new Date(Date.now()-60000))

const STATUS={OVERDUE:['danger','Overdue','alert'],DUE:['danger','Due today','alert'],UPCOMING:['success','OK'],NO_LIMIT_SET:['muted','No limit set'],NOT_RECORDED:['muted','Not recorded']}

// Rows that fit the card under the tab bar and the sub-tabs without scrolling (measured at 1280x585, 1366x768, 1920x1080, 2560x1440).
function useRows(){
  const [height,setHeight]=useState(typeof window==='undefined'?900:window.innerHeight)
  useEffect(()=>{const on=()=>setHeight(window.innerHeight);window.addEventListener('resize',on);return ()=>window.removeEventListener('resize',on)},[])
  return Math.max(2,Math.floor(height*0.0121-3))
}
function usePage(items,size){
  const [page,setPage]=useState(0),pages=Math.max(1,Math.ceil((items||[]).length/size)),current=Math.min(page,pages-1)
  return {slice:(items||[]).slice(current*size,(current+1)*size),pager:<Pager page={current} pages={pages} onPage={setPage}/>,pages,setPage}
}

// Messages for each odometer_status the API answers with after a save.
function statusMessage(result,current){
  const reading=kmText(result.odometer_km)
  switch(result.odometer_status){
    case 'APPLIED':return {tone:'ok',text:t('Saved. The vehicle odometer is now {value0}.',{value0:reading})}
    case 'UNCHANGED':return {tone:'ok',text:t('Saved. The odometer already showed this reading.')}
    case 'HISTORICAL':return {tone:'ok',text:t('Saved as an older entry. The vehicle keeps its newer reading.')}
    case 'NEEDS_REVIEW':return {tone:'warn',text:t('Saved, but this reading is lower than the vehicle’s current {value0}. The odometer was not changed and the record is flagged for review. If you changed the meter or mistyped, add a new record with the correct reading.',{value0:kmText(current)})}
    case 'NO_READING':return {tone:'ok',text:t('Saved. This record has no odometer reading, so the odometer did not change.')}
    default:return {tone:'ok',text:t('Record saved.')}
  }
}

// One explanation per error code of the contract; returns {text, fields?, step?, duplicate?}
function explain(error){
  const code=error.code,fields=fieldErrors(error)
  if(error instanceof TypeError||code==='API_TIMEOUT')return {text:t('We could not reach Travelly. Please try again.')}
  if(code==='POSSIBLE_DUPLICATE')return {duplicate:true,text:t('A record like this was already saved today (same type, amount and reading). Save it again only if it is a different one.')}
  if(code==='RECORD_NOT_COMPATIBLE')return {step:0,text:t('This type of record does not fit this vehicle’s power or fuel type. Choose another type.')}
  if(code==='FIELD_NOT_APPLICABLE')return {fields:fieldErrorMap(error),text:t('One of the fields does not apply to this type of record. Remove it and save again.')}
  if(code==='VALIDATION_ERROR'&&fields.length)return {fields:fieldErrorMap(error),text:t('Please check the highlighted fields.')}
  if(code==='VEHICLE_NOT_FOUND'||error.status===404)return {text:t('We could not find this vehicle. Go back to Your vehicles and open it again.')}
  if(error.status===403)return {text:t('Only the Owner of this vehicle can add records.')}
  return {text:error.message||t('The record could not be saved. Please try again.')}
}

function AddRecord({data,startType,onSaved,onCancel,Footer}){
  const allowed=data.allowed_record_types||[]
  const [step,setStep]=useState(0),[type,setType]=useState(allowed.includes(startType)?startType:allowed[0]||''),[when,setWhen]=useState(nowLocal),[values,setValues]=useState({}),[busy,setBusy]=useState(false),[errors,setErrors]=useState({}),[message,setMessage]=useState(''),[duplicate,setDuplicate]=useState(false)
  const retry=useRef(null)
  const spec=FIELD_SPEC(type),set=name=>e=>{setValues(v=>({...v,[name]:e.target.value}));setErrors(x=>({...x,[name]:undefined}))}
  const clean=name=>String(values[name]??'').trim()
  const input=name=><Field key={name} label={FIELD_LABEL[name]} optional={!spec.required.includes(name)} help={FIELD_HELP[name]}>
    {DECIMALS[name]?<input name={name} type="number" min="0" step={DECIMALS[name]===1?'0.1':DECIMALS[name]===2?'0.01':'0.001'} inputMode="decimal" value={values[name]??''} onChange={set(name)}/>
      :name==='genuine_calendar_due_date'?<input name={name} type="date" min={when.slice(0,10)} value={values[name]??''} onChange={set(name)}/>
      :name==='notes'?<input name={name} maxLength="500" value={values[name]??''} onChange={set(name)}/>
      :<input name={name} maxLength="120" value={values[name]??''} onChange={set(name)}/>}</Field>
  // Client checks that mirror the contract; the API still has the final word.
  function check(which){
    const bad={}
    const num=name=>Number(clean(name))
    const names=which===0?spec.step1:spec.step2
    if(which===0){
      const stamp=new Date(when)
      if(!when||Number.isNaN(stamp.getTime()))bad.recorded_at=t('Choose the date and time.')
      else if(stamp>new Date())bad.recorded_at=t('The time cannot be in the future.')
    }
    names.forEach(name=>{
      const value=clean(name)
      if(!value){if(spec.required.includes(name))bad[name]=t('This is needed for this type of record.');return}
      if(DECIMALS[name]){const n=Number(value);if(!Number.isFinite(n)||n<0)bad[name]=t('Enter a number, zero or more.');else{const places=(value.split('.')[1]||'').length;if(places>DECIMALS[name])bad[name]=t('Use at most {value0} decimal places.',{value0:DECIMALS[name]})}}
    })
    if(which===0&&type==='PERSONAL_EXTRA_USE'&&!bad.start_odometer_km&&!bad.end_odometer_km&&num('end_odometer_km')<num('start_odometer_km'))bad.end_odometer_km=t('The end reading must not be below the start reading.')
    if(which===1){
      if(clean('next_due_odometer_km')&&!bad.next_due_odometer_km&&clean('odometer_km')&&num('next_due_odometer_km')<=num('odometer_km'))bad.next_due_odometer_km=t('Must be above the odometer reading.')
      if(clean('genuine_calendar_due_date')&&clean('genuine_calendar_due_date')<=when.slice(0,10))bad.genuine_calendar_due_date=t('Must be after the record date.')
    }
    setErrors(bad);return Object.keys(bad).length===0
  }
  const body=confirmDuplicate=>{
    const out={record_type:type,recorded_at:new Date(when).toISOString()}
    ;[...spec.step1,...spec.step2].forEach(name=>{const v=clean(name);if(v)out[name]=v})
    if(confirmDuplicate)out.confirm_duplicate=true
    return out
  }
  async function save(confirmDuplicate=false){
    setBusy(true);setMessage('');setErrors({});setDuplicate(false)
    try{const result=await api(`/vehicles/${data.vehicle_id}/records`,{method:'POST',body:JSON.stringify(body(confirmDuplicate))});await onSaved(result)}
    catch(error){
      const out=explain(error)
      setMessage(out.text);if(out.duplicate)setDuplicate(true)
      if(out.fields){setErrors(out.fields);const first=Object.keys(out.fields)[0];setStep(['recorded_at','record_type',...FIELD_SPEC(type).step1].includes(first)?0:1)}
      else if(out.step!=null)setStep(out.step)
    }finally{setBusy(false)}
  }
  const next=()=>{if(check(0))setStep(1)}
  const review=()=>{if(check(1))setStep(2)}
  const recap=[[t('Type'),typeLabel(type)],[t('When'),formatDateTime(when)],...[...spec.step1,...spec.step2].filter(n=>clean(n)).map(n=>[t(FIELD_LABEL[n]),DECIMALS[n]&&n!=='amount'&&n!=='quantity'&&n!=='charging_kwh'?kmText(clean(n)):n==='amount'?moneyText('LKR',clean(n)):n==='genuine_calendar_due_date'?dateOnly(clean(n)):clean(n)])]
  return <RateErrors.Provider value={errors}><div className="tk-pane">
    {message&&<p className="tk-line is-warn" role="status">{message}</p>}
    {step===0&&<div className="tk-grid" style={{'--cols':3}}>
      <Field label="Type of record"><select name="record_type" value={type} onChange={e=>{setType(e.target.value);setErrors({});setMessage('')}}>{allowed.map(x=><option key={x} value={x}>{typeLabel(x)}</option>)}</select></Field>
      <DateTimeFields dateLabel="Date" timeLabel="Time" value={when} min="" onChange={v=>{setWhen(v);setErrors(x=>({...x,recorded_at:undefined}))}}/>
      {errors.recorded_at&&<p className="tk-line is-warn" style={{gridColumn:'1 / -1'}} role="status">{errors.recorded_at}</p>}
      {spec.step1.map(input)}
    </div>}
    {step===1&&<><p className="tk-line"><Chip tone="info">{typeLabel(type)}</Chip> {formatDateTime(when)}{type==='FUEL_PURCHASE'&&data.engine_fuel_type?<> · {t('Fuel type')}: {data.engine_fuel_type}</>:null}</p>
      <div className="tk-grid" style={{'--cols':spec.step2.length>4?3:2}}>{spec.step2.map(input)}</div></>}
    {step===2&&<><p className="tk-line"><strong>{t('Check the record, then save it. Records cannot be edited or deleted afterwards; a correction is a new record.')}</strong></p>
      <dl className="tk-facts" style={{'--cols':3}}>{recap.slice(0,9).map(([k,v])=><div key={k}><dt>{k}</dt><dd title={v}>{v}</dd></div>)}</dl></>}
    {duplicate&&<div className="tk-bar"><button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={()=>save(true)}>{t('Save it anyway')}</button></div>}
    <Footer>
      <button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={()=>step===0?onCancel():setStep(step-1)}>{step===0?t('Cancel'):t('Back')}</button>
      {step===0&&<button type="button" className="ui-button ui-button-primary" disabled={busy||!type} onClick={next}>{t('Next')}</button>}
      {step===1&&<button type="button" className="ui-button ui-button-primary" disabled={busy} onClick={review}>{t('Review')}</button>}
      {step===2&&<button type="button" className="ui-button ui-button-primary" disabled={busy} onClick={()=>save(false)}>{busy?t('Saving…'):t('Save record')}</button>}
    </Footer>
  </div></RateErrors.Provider>
}

export default function VehicleMaintenance({vehicle,Footer}){
  const [view,setView]=useState('summary'),[records,setRecords]=useState(null),[summary,setSummary]=useState(null),[error,setError]=useState(null),[sumError,setSumError]=useState(null),[filter,setFilter]=useState(''),[result,setResult]=useState(null),[startType,setStartType]=useState('')
  const load=useCallback(async()=>{
    setError(null);setSumError(null)
    await Promise.all([api(`/vehicles/${vehicle.id}/records`).then(setRecords).catch(setError),api(`/vehicles/${vehicle.id}/maintenance-summary`).then(setSummary).catch(setSumError)])
  },[vehicle.id])
  useEffect(()=>{load()},[load])
  const rows=useRows()
  const list=(records?.items||[]).filter(x=>!filter||x.record_type===filter)
  const recordPage=usePage(list,rows),taskPage=usePage(summary?.items||[],rows)
  const canAdd=records?records.can_add!==false&&(records.allowed_record_types||[]).length>0:false
  const addFor=type=>{setStartType(type||'');setResult(null);setView('add')}
  async function saved(item){
    setResult(statusMessage(item,records?.current_odometer_km))
    await load();setView('records');setFilter('')
  }
  const sub=<div className="tk-bar" role="tablist" aria-label={t('Maintenance')}>
    {[['summary','Summary'],['records','Records'],['add','Add record']].map(([key,label])=>(key!=='add'||canAdd)&&<Chip key={key} tone="info" selected={view===key} onClick={()=>addFor_(key)}>{t(label)}</Chip>)}
    <span className="tk-grow"/>
    {records&&<span className="tk-line">{t('Odometer')}: <strong>{kmText(records.current_odometer_km)}</strong>{records.odometer_updated_at&&<> · {t('updated')} {formatDateTime(records.odometer_updated_at)}</>}</span>}
  </div>
  function addFor_(key){if(key==='add')addFor('');else{setView(key);if(key==='summary')setResult(null)}}

  if(error&&!records)return <div className="tk-pane"><p className="tk-line is-warn" role="status">{explain(error).text}</p><div className="tk-bar"><button type="button" className="ui-button ui-button-secondary" onClick={load}>{t('Try again')}</button></div></div>
  if(!records)return <p role="status">{t('Loading maintenance…')}</p>

  const totals=records.totals||{}
  return <div className="tk-pane mt-pane">
    {sub}
    {result&&<p className={`tk-line${result.tone==='warn'?' is-warn':''}`} role="status">{result.tone==='ok'?'✓ ':''}{result.text}</p>}
    {view==='summary'&&<>
      {sumError&&<p className="tk-line is-warn" role="status">{explain(sumError).text}</p>}
      {summary?.estimate_note&&<p className="tk-line">{t(summary.estimate_note)}</p>}
      {summary&&summary.items?.length>0
        ?<><div className="bk-list pl-list mt-list">{(summary.items||[]).map(item=>{const [tone,label,icon]=STATUS[item.status]||['muted',codeEnglish(item.status)]
          const left=item.remaining_km!=null?`${kmText(Math.abs(Number(item.remaining_km)))} ${Number(item.remaining_km)<0?t('overdue'):t('left')}`:null
          const due=item.estimated_due_date?`${t('Due about')} ${dateOnly(item.estimated_due_date)}`:item.next_due_odometer_km!=null&&item.estimate_note?t('Estimated date unavailable'):null
          const cal=item.genuine_calendar_due_date?`${t('Due date')} ${dateOnly(item.genuine_calendar_due_date)}`:null
          const meta=[left,due,cal].filter(Boolean).join(' · ')||(item.status==='NOT_RECORDED'?t('No record yet'):item.status==='NO_LIMIT_SET'?t('Done, but no next limit was given'):'')
          return <article className={'bc-card pl-card is-'+tone} key={item.task}><span className="pl-ico"><Icon name={tone==='danger'?'alert':tone==='success'?'check':'settings'} size={22}/></span><div className="bc-body"><strong className="bc-name">{typeLabel(item.task)}</strong>{meta&&<span className="bc-sub">{meta}</span>}</div>
            <div className="bc-side pl-side"><Chip tone={tone} icon={icon}>{t(label)}</Chip>{canAdd&&(records.allowed_record_types||[]).includes(item.task)&&<button type="button" className="ui-button ui-button-secondary" onClick={()=>addFor(item.task)}>{t('Record')}</button>}</div></article>})}</div></>
        :summary&&<Empty>{canAdd?t('No maintenance tasks to show yet. Add a service record to start tracking when each task is due.'):t('No maintenance tasks to show yet.')}</Empty>}
      {!summary&&!sumError&&<p role="status">{t('Loading maintenance…')}</p>}
    </>}
    {view==='records'&&<>
      <div className="tk-bar"><Chip tone="muted">{t('Fuel')} {moneyText(totals.currency,totals.fuel)}</Chip>{(records.allowed_record_types||[]).includes('EV_CHARGING')&&<Chip tone="muted">{t('Charging')} {moneyText(totals.currency,totals.charging)}</Chip>}<Chip tone="muted">{t('Maintenance')} {moneyText(totals.currency,totals.maintenance)}</Chip>
        <span className="tk-grow"/>
        <select aria-label={t('Type of record')} name="records-filter" value={filter} onChange={e=>{setFilter(e.target.value);recordPage.setPage(0)}} style={{minWidth:200}}><option value="">{t('All types')}</option>{(records.allowed_record_types||[]).map(x=><option key={x} value={x}>{typeLabel(x)}</option>)}</select></div>
      {list.length
        ?<><div className="bk-list pl-list mt-list">{list.map(item=>{
          const reading=item.odometer_km!=null?kmText(item.odometer_km):item.start_odometer_km!=null?`${kmText(item.start_odometer_km)} → ${kmText(item.end_odometer_km)}`:null
          const meta=[formatDateTime(item.recorded_at),reading,item.service_provider,item.quantity!=null?`${Number(item.quantity)} ${item.unit||'L'}`:null,item.charging_kwh!=null?`${Number(item.charging_kwh)} kWh`:null].filter(Boolean).join(' · ')
          return <article className={'bc-card pl-card'+(item.review_status==='NEEDS_REVIEW'?' is-danger':'')} key={item.id}><span className="pl-ico"><Icon name={['FUEL_PURCHASE','EV_CHARGING'].includes(item.record_type)?'wallet':item.record_type==='ODOMETER_UPDATE'||item.record_type==='PERSONAL_EXTRA_USE'?'route':'settings'} size={22}/></span><div className="bc-body"><strong className="bc-name">{typeLabel(item.record_type)}</strong>{meta&&<span className="bc-sub">{meta}</span>}</div>
            <div className="bc-side pl-side">{item.amount!=null&&<strong className="bc-price">{moneyText(item.currency,item.amount)}</strong>}{item.review_status==='NEEDS_REVIEW'&&<><Chip tone="danger" icon="alert">{t('Needs review')}</Chip><InfoTip>{t('This reading was lower than the vehicle’s newer reading. It is saved but did not change the odometer.')}</InfoTip></>}</div></article>})}</div></>
        :<Empty>{records.items?.length?t('No records of this type.'):t('No records yet. Add the first service, fuel or odometer record for this vehicle.')}</Empty>}
    </>}
    {view==='add'&&<AddRecord data={records} startType={startType} Footer={Footer} onSaved={saved} onCancel={()=>setView('summary')}/>}
    {view!=='add'&&<Footer>{canAdd&&<button type="button" className="ui-button ui-button-primary" onClick={()=>addFor('')}>{t('Add record')}</button>}</Footer>}
  </div>
}
