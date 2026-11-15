import { t } from '../../i18n/language.js'
import {useCallback,useEffect,useRef,useState} from 'react'
import {api} from '../../services/api'
import Chip from '../../components/ui/Chip'
import {Checkbox} from '../../components/ui'
import {Field,RateErrors} from '../owner/OwnerRates'
import {Notice} from '../ticketing/TicketParts'
import {money} from '../passenger/TicketCancel'
import {fieldErrorMap,fieldErrorText} from '../../services/fieldErrors.js'
import {RENTAL_LIMITS,checkExtra,checkRates,newExtraId,readRates,toRatesBody} from './rentalModel'

/* Vehicle → Rental rates (contract 03RN): GET/PUT /vehicles/{id}/rental. Day rate, free km per day, extra km rate, late hour rate, longest rental,
   notes the renter reads before asking, cash, and up to 10 paid extras (per DAY or ONCE). Rates saved later never change an accepted rental. */
const HINT={AMOUNT:'Use an amount with at most two decimals.',DAYS:'A whole number from 1 to 30.',NOTES:'Up to 500 characters.',NAME:'Enter a name (up to 80 characters).',PRICE:'Above 0, with at most two decimals.'}

export default function RentalRates({vehicle,Footer}){
  const [state,setState]=useState(null),[saved,setSaved]=useState(null),[view,setView]=useState('rates'),[editing,setEditing]=useState(null),[removing,setRemoving]=useState(null)
  const [busy,setBusy]=useState(false),[message,setMessage]=useState({text:'',warn:false}),[errors,setErrors]=useState({}),[loadError,setLoadError]=useState(''),sending=useRef(false)
  const load=useCallback(async(keep=false)=>{
    try{const current=readRates(await api(`/vehicles/${vehicle.id}/rental`,{cache:'no-store'}));setState(current);setSaved(JSON.stringify(current));setLoadError('');if(!keep)setMessage({text:'',warn:false})}
    catch(error){setLoadError(fieldErrorText(error))}
  },[vehicle.id])
  useEffect(()=>{load()},[load])
  if(loadError)return <p className="tk-line is-warn" role="alert">{loadError} <button type="button" className="inline-link" onClick={()=>load()}>{t('Try again')}</button></p>
  if(!state)return <p role="status">{t('Loading…')}</p>
  const problems=checkRates({...state.rates,extras:state.extras}),dirty=JSON.stringify(state)!==saved
  const setRate=name=>e=>setState(c=>({...c,rates:{...c.rates,[name]:e.target.value}}))
  const hint=code=>t(HINT[code]||HINT.AMOUNT)
  function commit(){
    const bad=checkExtra(editing)
    if(Object.keys(bad).length){setErrors(Object.fromEntries(Object.entries(bad).map(([k,v])=>[k,hint(v==='PER'?'NAME':v)])));return}
    const item={...editing,name:editing.name.trim()}
    setState(c=>({...c,extras:c.extras.some(x=>x.id===item.id)?c.extras.map(x=>x.id===item.id?item:x):[...c.extras,item]}));setEditing(null);setErrors({})
  }
  async function save(){
    if(sending.current)return
    sending.current=true;setBusy(true);setMessage({text:'',warn:false});setErrors({})
    try{
      const result=await api(`/vehicles/${vehicle.id}/rental`,{method:'PUT',body:JSON.stringify(toRatesBody({version:state.version,enabled:state.enabled,rates:state.rates,extras:state.extras,cashAccepted:state.cashAccepted}))})
      setMessage({text:result?.message||t('Rental rates saved.'),warn:false});await load(true)
    }catch(error){
      setMessage({text:fieldErrorText(error),warn:true});setErrors(fieldErrorMap(error))
      if(error.code==='VERSION_CONFLICT')await load(true)   // the newest rates come back; the server message says to reload before editing again
    }finally{sending.current=false;setBusy(false)}
  }
  const rate=(name,label,help)=><Field label={label} help={help}><input name={name} inputMode="decimal" value={state.rates[name]} onChange={setRate(name)}/></Field>
  return <RateErrors.Provider value={errors}><div className="ep-pane">
    {message.text&&(message.warn?<div className="notice error" role="alert">{message.text}</div>:<Notice>{message.text}</Notice>)}
    {editing
      ?<div className="ep-editor"><div className="tk-grid" style={{'--cols':3}}>
          <Field label="Extra name"><input name="name" maxLength={RENTAL_LIMITS.extraName} value={editing.name} onChange={e=>setEditing(c=>({...c,name:e.target.value}))}/></Field>
          <Field label="Price (LKR)"><input name="price" inputMode="decimal" value={editing.price} onChange={e=>setEditing(c=>({...c,price:e.target.value}))}/></Field>
          <Field label="Charged"><select name="per" value={editing.per} onChange={e=>setEditing(c=>({...c,per:e.target.value}))}><option value="DAY">{t('Per day')}</option><option value="ONCE">{t('Once')}</option></select></Field></div>
        <div className="tk-bar"><button type="button" className="ui-button ui-button-secondary" onClick={()=>{setEditing(null);setErrors({})}}>{t('Cancel')}</button><button type="button" className="ui-button ui-button-primary" onClick={commit}>{t('Done')}</button></div></div>
      :<>
        <div className="tk-bar" role="group" aria-label={t('Rental rates')}>
          <Chip tone="info" selected={view==='rates'} onClick={()=>setView('rates')}>{t('Rates')}</Chip>
          <Chip tone="info" selected={view==='extras'} onClick={()=>setView('extras')}>{t('Extras')} ({state.extras.length})</Chip>
          <Checkbox checked={state.enabled} onChange={e=>setState(c=>({...c,enabled:e.target.checked}))}>{t('Enabled')}</Checkbox>
          <Checkbox checked={state.cashAccepted} onChange={e=>setState(c=>({...c,cashAccepted:e.target.checked}))}>{t('Cash accepted')}</Checkbox></div>
        {view==='rates'
          ?<><div className="tk-grid" style={{'--cols':3}}>
              {rate('day_rate','Day rate (LKR)','Price for one booked day.')}
              {rate('free_km_per_day','Free km per day','Free km are pooled over all booked days.')}
              {rate('extra_km_rate','Extra km rate (LKR)','For each km beyond the free km.')}
              {rate('late_hour_rate','Late hour rate (LKR)','For each started hour after the 1 hour grace.')}
              <Field label="Longest rental (days)" help="From 1 to 30 days."><input name="max_days" inputMode="numeric" value={state.rates.max_days} onChange={setRate('max_days')}/></Field>
              <Field label="Notes" optional help="Deposit, fuel and damage rules. The renter reads them before asking."><input name="notes" maxLength={RENTAL_LIMITS.notes} value={state.rates.notes} onChange={setRate('notes')}/></Field></div>
              {Object.keys(problems).length>0&&dirty&&<p className="tk-line is-warn" role="status">{Object.entries(problems).map(([k,v])=>k==='extras'?null:hint(v)).filter(Boolean).filter((x,i,a)=>a.indexOf(x)===i).join(' ')}</p>}</>
          :<>
            <div className="tk-bar"><Chip tone="info">{t('{value0} of {value1} extras',{value0:state.extras.length,value1:RENTAL_LIMITS.extras})}</Chip>
              <button type="button" className="ui-button ui-button-secondary" disabled={state.extras.length>=RENTAL_LIMITS.extras} onClick={()=>{setMessage({text:'',warn:false});setEditing({id:newExtraId(),name:'',price:'',per:'DAY'})}}>{t('Add an extra')}</button></div>
            {!state.extras.length&&<p className="tk-line" role="status">{t('No extras yet.')}</p>}
            <div className="ep-list">{state.extras.map(x=>removing===x.id
              ?<article className="tk-row tk-hold" key={x.id}><div className="tk-row-main"><strong>{t('Remove {value0}?',{value0:x.name})}</strong></div>
                <div className="tk-row-actions"><button type="button" className="ui-button ui-button-primary" onClick={()=>{setState(c=>({...c,extras:c.extras.filter(y=>y.id!==x.id)}));setRemoving(null)}}>{t('Yes, remove')}</button><button type="button" className="ui-button ui-button-secondary" onClick={()=>setRemoving(null)}>{t('Back')}</button></div></article>
              :<article className="tk-row" key={x.id}><div className="tk-row-main"><strong>{x.name}</strong><span>{money('LKR',x.price)} · {x.per==='DAY'?t('Per day'):t('Once')}</span></div>
                <div className="tk-row-actions"><button type="button" className="ui-button ui-button-secondary" onClick={()=>{setMessage({text:'',warn:false});setEditing({...x})}}>{t('Edit')}</button><button type="button" className="ui-button ui-button-secondary" onClick={()=>setRemoving(x.id)}>{t('Remove')}</button></div></article>)}</div></>}
      </>}
    <Footer>{!editing&&<button type="button" className="ui-button ui-button-primary" disabled={busy||!dirty||Object.keys(problems).length>0} onClick={save}>{busy?t('Saving…'):t('Save rental rates')}</button>}</Footer>
  </div></RateErrors.Provider>
}
