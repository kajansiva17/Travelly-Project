import { t } from '../../i18n/language.js'
import React,{useEffect,useState} from 'react'
import {api} from '../../services/api'
import {Field,RateErrors} from '../owner/OwnerRates'
import AdminList from './AdminList'
import {fieldErrors,fieldErrorMap,firstFieldMessage} from '../../services/fieldErrors.js'

// Admin payment settings (Payments contract 03P, section B): provider, commission % and gateway fee % per service type.
const money=value=>Number(value||0).toLocaleString('en-LK',{minimumFractionDigits:0,maximumFractionDigits:2})
const asNumber=value=>{const n=Number(String(value).trim());return Number.isFinite(n)?n:0}

function Example({commission,fee}){
  const c=asNumber(commission),f=asNumber(fee),owner=1000-(1000*c/100)-(1000*f/100)
  return <p className="tk-line">{t('On LKR 1,000: Travelly {value0}, gateway {value1}, Owner {value2}',{value0:money(1000*c/100),value1:money(1000*f/100),value2:money(owner)})}</p>
}

function PaymentForm({row,onSaved,onConflict}){
  const [provider,setProvider]=useState(row.payment_provider),[commission,setCommission]=useState(row.commission_percent||''),[fee,setFee]=useState(row.gateway_fee_percent||'')
  const [busy,setBusy]=useState(false),[errors,setErrors]=useState({}),[message,setMessage]=useState('')
  const providers=row.available_providers?.length?row.available_providers:[row.payment_provider]
  async function save(event){
    event.preventDefault();setBusy(true);setErrors({});setMessage('')
    try{
      const saved=await api(`/admin/service-types/${row.id}/payment-settings`,{method:'PATCH',body:JSON.stringify({expected_version:row.version,payment_provider:provider,commission_percent:String(commission).trim(),gateway_fee_percent:String(fee).trim()})})
      onSaved(saved)
    }catch(error){
      const fields=fieldErrors(error)
      if(error.code==='VERSION_CONFLICT'){onConflict();return}
      if(error.code==='PAYMENT_SETTINGS_INVALID')setErrors({gateway_fee_percent:firstFieldMessage(error)||t('Commission and gateway fee together must not be more than 100%.')})
      else if(error.code==='PAYMENT_PROVIDER_UNAVAILABLE')setErrors({payment_provider:t('PayHere is not set up on the server yet.')})
      else if(error.code==='VALIDATION_ERROR'&&fields.length)setErrors(fieldErrorMap(error))
      else setMessage(error.message||t('The settings could not be saved. Please try again.'))
    }finally{setBusy(false)}
  }
  return <RateErrors.Provider value={errors}><form className="flow-wizard-form tk-pane" onSubmit={save} noValidate>
    <div className="tk-grid" style={{'--cols':3}}>
      <Field label="Payment provider" help="Sandbox is a test payment with no real money. PayHere takes real card payments."><select name="payment_provider" value={provider} onChange={e=>setProvider(e.target.value)}>{providers.map(p=><option key={p} value={p}>{p==='PAYHERE'?'PayHere':t('Sandbox')}</option>)}</select></Field>
      <Field label="Commission (%)" help="Travelly's income from each booking."><input required name="commission_percent" type="number" min="0" max="100" step="0.01" inputMode="decimal" value={commission} onChange={e=>setCommission(e.target.value)}/></Field>
      <Field label="Gateway fee (%)" help="Taken from the Owner's share. It is never Travelly income. For PayHere use its plan rate, for example 3.30."><input required name="gateway_fee_percent" type="number" min="0" max="100" step="0.01" inputMode="decimal" value={fee} onChange={e=>setFee(e.target.value)}/></Field>
    </div>
    <Example commission={commission} fee={fee}/>
    <p className="tk-line">{t('The gateway fee comes out of the Owner’s share and is never Travelly income. Travelly earns only the commission. A change applies to new payments only.')}</p>
    {message&&<p className="tk-line is-warn" role="alert">{message}</p>}
    <div className="flow-actions"><span/><button type="submit" className="ui-button ui-button-primary" disabled={busy}>{busy?t('Saving…'):t('Save payment settings')}</button></div>
  </form></RateErrors.Provider>
}

export default function AdminPaymentSettings({base}){
  const [items,setItems]=useState(null),[error,setError]=useState(null),[notice,setNotice]=useState('')
  const load=()=>api('/admin/payment-settings').then(result=>setItems(result.items||[])).catch(setError)
  useEffect(()=>{load()},[])
  const saved=row=>{setItems(list=>(list||[]).map(item=>item.id===row.id?{...item,...row}:item));setNotice(t('Payment settings saved.'))}
  const conflict=()=>{setNotice(t('Changed by someone else — the list was reloaded. Check the values and save again.'));load()}
  return <AdminList {...base} title={t('Payment settings')} error={error||base.error} notice={notice} items={items} empty={t('No services found.')}
    row={item=>({key:item.id,title:item.name,meta:`${item.payment_provider==='PAYHERE'?'PayHere':t('Sandbox')} · ${t('Commission')} ${item.commission_percent}% · ${t('Gateway fee')} ${item.gateway_fee_percent}%`,status:item.is_active?t('ACTIVE'):t('INACTIVE'),tone:item.is_active?'success':'muted'})}
    detailTitle={item=>item.name} detailLabel="Edit"
    detail={item=><PaymentForm key={`${item.id}-${item.version}`} row={item} onSaved={saved} onConflict={conflict}/>}/>
}
