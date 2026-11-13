import { t } from '../../i18n/language.js'
import {useRef,useState} from 'react'
import {Link,useNavigate} from '../passenger/travelRouter'
import {api,hasSession,publicRequest} from '../../services/api'
import {Header} from '../../components/components'
import {FlowShell,FlowBanner,FlowVehicleCard,Pager,useFitCount} from '../booking/flow/FlowParts'
import {Button,Chip} from '../../components/ui'
import {Field,Compact,RateErrors} from '../owner/OwnerRates'
import NotAvailableNotice from '../../components/NotAvailableNotice'
import {money} from '../passenger/TicketCancel'
import {newKey} from '../passenger/TicketPayment'
import {fieldErrorMap} from '../../services/fieldErrors.js'
import {RENTAL_LIMITS,extraAmount,previewTotal,validDays,validLicence} from './rentalModel'

/* Self-drive rental (contract 03RN): when and how long, a vehicle with optional extras, the licence number, then the request.
   POST /rentals/search {start_at, days} lists the vehicles free for those dates; POST /rentals asks (one idempotency key per request, reused on retry).
   The renter drives; the final price is worked out when the vehicle comes back. */
const steps=['When and how long','Choose a vehicle','Licence and request','Request sent']
const vehicleName=v=>[v?.make,v?.model].filter(Boolean).join(' ')||v?.reference||t('Vehicle')
const startIso=(date,time)=>new Date(`${date}T${time||'00:00'}:00`).toISOString()

export function PassengerRental(){
  const navigate=useNavigate(),[step,setStep]=useState(0),[when,setWhen]=useState({date:'',time:'09:00',days:'1'}),[items,setItems]=useState(null),[note,setNote]=useState(''),[error,setError]=useState(null)
  const [vehicle,setVehicle]=useState(null),[extraIds,setExtraIds]=useState({}),[licence,setLicence]=useState(''),[busy,setBusy]=useState(false),[errors,setErrors]=useState({}),[created,setCreated]=useState(null),[page,setPage]=useState(0)
  const key=useRef(null),sending=useRef(false),fit=useFitCount()
  const set=name=>e=>{setWhen(c=>({...c,[name]:e.target.value}))}
  const chosen=vehicle?(vehicle.rental.extras||[]).filter(x=>extraIds[vehicle.id+x.id]):[]
  const days=Number(when.days)

  async function search(e){
    e.preventDefault();if(sending.current||!validDays(when.days)||!when.date)return
    sending.current=true;setBusy(true);setError(null);setNote('');setItems(null);setPage(0)
    try{const result=await publicRequest('/rentals/search',{start_at:startIso(when.date,when.time),days});setItems(result.items||[]);setNote(result.message||'');setStep(1)}
    catch(err){setError(err)}finally{sending.current=false;setBusy(false)}
  }
  async function request(){
    if(sending.current||!validLicence(licence))return
    if(!hasSession()){navigate('/login');return}
    sending.current=true;setBusy(true);setError(null);setErrors({})
    // One key per request; a retry after a lost answer reuses it so the same rental is never made twice.
    const ids=chosen.map(x=>x.id),signature=JSON.stringify([vehicle.id,startIso(when.date,when.time),days,licence.trim(),ids])
    if(key.current?.signature!==signature)key.current={signature,value:newKey()}
    try{
      const booking=await api('/rentals',{method:'POST',body:JSON.stringify({vehicle_id:vehicle.id,start_at:startIso(when.date,when.time),days,licence_number:licence.trim(),idempotency_key:key.current.value,...(ids.length?{extras:ids}:{})})})
      setCreated(booking);setStep(3);key.current=null
    }catch(err){setError(err);setErrors(fieldErrorMap(err))}
    finally{sending.current=false;setBusy(false)}
  }
  const pages=Math.max(1,Math.ceil((items||[]).length/fit)),shown=(items||[]).slice(Math.min(page,pages-1)*fit,(Math.min(page,pages-1)+1)*fit)
  const estimate=created?.price?.estimate

  return <><Header/><FlowShell heading={t('Travel & Booking')} title={t(steps[step])} info={step===0?t('Choose a specific matching vehicle before package price and rental rules can be shown.'):undefined} icon="key" steps={steps.map(s=>t(s))} current={step} onStepSelect={i=>{if(i<step&&step<3&&!busy)setStep(i)}}>
    <Compact.Provider value={true}><RateErrors.Provider value={errors}>
      {error&&<NotAvailableNotice error={error} action={<button type="button" className="ui-button ui-button-secondary" onClick={()=>{setError(null);setStep(0)}}>{t('Search again')}</button>}/>}
      {step===0&&<form className="tk-pane" onSubmit={search}>
        <div className="tk-grid" style={{'--cols':3}}>
          <Field label="Pickup date"><input name="date" type="date" required value={when.date} onChange={set('date')}/></Field>
          <Field label="Pickup time"><input name="time" type="time" required value={when.time} onChange={set('time')}/></Field>
          <Field label="Rental days" help="From 1 to 30 days."><input name="days" type="number" min="1" max={RENTAL_LIMITS.maxDaysTop} step="1" required value={when.days} onChange={set('days')}/></Field></div>
        <div className="flow-actions"><span/><Button type="submit" arrow disabled={busy||!when.date||!validDays(when.days)}>{busy?t('Searching…'):t('Find vehicles')}</Button></div></form>}
      {step===1&&<div className="tk-pane">
        {note&&<p className="tk-line" role="status">{note}</p>}
        {!items?.length?<p className="tk-line" role="status">{t('No vehicle is free for these dates.')}</p>
          :<div className="flow-vehicle-list">{shown.map(v=>{const r=v.rental||{},on=vehicle?.id===v.id,list=r.extras||[],picked=list.filter(x=>extraIds[v.id+x.id])
            return <FlowVehicleCard key={v.id} vehicle={v} selected={on} title={vehicleName(v)} specs={[{icon:'seat',label:`${v.passenger_seats??'—'} ${t('passenger seats')}`},{icon:'grid',label:`${v.large_luggage??'—'} ${t('large luggage')}`}]}
              chips={<><div className="flow-packages"><Chip icon="wallet" tone="info">{t('{value0} per day',{value0:money('LKR',r.day_rate)})}</Chip><Chip tone="muted">{t('{value0} km free',{value0:r.free_km_total})}</Chip><Chip tone="muted">{t('{value0} per extra km',{value0:money('LKR',r.extra_km_rate)})}</Chip></div>
                {list.length>0&&<div className="flow-packages" role="group" aria-label={t('Extras')}>{list.map(x=><Chip key={x.id} tone="info" selected={Boolean(extraIds[v.id+x.id])} onClick={()=>setExtraIds(c=>({...c,[v.id+x.id]:!c[v.id+x.id]}))}>{x.name} · {money('LKR',extraAmount(x))}</Chip>)}</div>}
                {r.notes&&<p className="tk-line" title={r.notes}>{r.notes}</p>}
                <strong>{t('Estimate')}: {money('LKR',previewTotal(r,picked))}</strong></>}
              action={<Button arrow onClick={()=>{setVehicle(v);setStep(2)}}>{t('Select vehicle')}</Button>}/>})}</div>}
        <div className="flow-actions"><button type="button" className="ui-button ui-button-secondary" onClick={()=>setStep(0)}>{t('Back')}</button>{pages>1?<Pager page={Math.min(page,pages-1)} pages={pages} onPage={setPage}/>:<span/>}</div></div>}
      {step===2&&vehicle&&<div className="tk-pane">
        <dl className="flow-review"><div><dt>{t('Vehicle')}</dt><dd>{vehicleName(vehicle)}</dd></div><div><dt>{t('Pickup date')}</dt><dd>{when.date} {when.time}</dd></div><div><dt>{t('Rental days')}</dt><dd>{days}</dd></div>
          {chosen.length>0&&<div><dt>{t('Extras')}</dt><dd>{chosen.map(x=>x.name).join(', ')}</dd></div>}<div><dt>{t('Estimate')}</dt><dd>{money('LKR',previewTotal(vehicle.rental,chosen))}</dd></div></dl>
        <div className="tk-grid" style={{'--cols':2}}><Field label="Driving licence number" help="The Owner checks your licence when you collect the vehicle."><input name="licence_number" maxLength={RENTAL_LIMITS.licenceMax} value={licence} onChange={e=>{setLicence(e.target.value);setErrors({})}}/></Field></div>
        <p className="tk-line">{t('The final price is worked out when the vehicle is returned, from the odometer readings and these rates.')}</p>
        <div className="flow-actions"><button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={()=>setStep(1)}>{t('Back')}</button><Button arrow disabled={busy||!validLicence(licence)} onClick={request}>{busy?t('Sending…'):t('Request this rental')}</Button></div></div>}
      {step===3&&created&&<div className="tk-pane">
        <FlowBanner tone="info" icon="clock" title={t('Owner review is pending')} aside={<Chip tone="info">{t('Requested')}</Chip>}>{t('The Owner accepts or declines your request. You can follow it in My trips.')}</FlowBanner>
        <dl className="flow-review"><div><dt>{t('Reference')}</dt><dd>{created.reference}</dd></div><div><dt>{t('Rental days')}</dt><dd>{estimate?.days??days}</dd></div>
          {estimate&&<><div><dt>{t('Extras')}</dt><dd>{money('LKR',estimate.extras_price)}</dd></div><div><dt>{t('Estimate')}</dt><dd>{money('LKR',estimate.base_price)}</dd></div></>}</dl>
        <div className="flow-actions"><Link className="ui-button ui-button-secondary" to="/bookings">{t('My trips')}</Link><Link className="ui-button ui-button-primary" to={`/bookings/${created.id}`}>{t('Open this rental')}</Link></div></div>}
    </RateErrors.Provider></Compact.Provider>
  </FlowShell></>
}
