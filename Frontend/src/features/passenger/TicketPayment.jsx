import { t } from '../../i18n/language.js'
import React,{useEffect,useRef,useState} from 'react'
import {api} from '../../services/api'
import Chip from '../../components/ui/Chip'
import InfoTip from '../../components/ui/InfoTip'
import {Field} from '../owner/OwnerRates'

// Pay button for a held Ticket booking (Payments contract 03P, section A). The screen is drawn only from the
// ticket read (GET /bookings/{id}/ticket): payment_status and latest_payment. Nothing here proves payment by itself.
export const newKey=()=>(globalThis.crypto?.randomUUID?.()||`${Date.now()}-${Math.random().toString(36).slice(2)}`).replace(/[^A-Za-z0-9_-]/g,'').slice(0,40)
const WAIT_MS=120000,POLL_MS=4000

// Build a hidden form from the server's checkout object and submit it (full navigation). Fields are sent exactly as given.
function submitCheckout(checkout){
  const form=document.createElement('form')
  form.method=(checkout.method||'POST').toUpperCase();form.action=checkout.action;form.style.display='none'
  Object.entries(checkout.fields||{}).forEach(([name,value])=>{const input=document.createElement('input');input.type='hidden';input.name=name;input.value=String(value);form.appendChild(input)})
  document.body.appendChild(form);form.submit()
}

// hire=true: the same Pay flow for a private-hire booking after the trip (amount comes from the payment summary).
export default function TicketPayment({booking,refresh,returned,onChooseSeats,hire=false}){
  const [busy,setBusy]=useState(false),[message,setMessage]=useState(null)
  const [payer,setPayer]=useState({address:'',city:'',phone:'',email:''}),[payerFor,setPayerFor]=useState(null),[sandbox,setSandbox]=useState(null)
  const [unavailable,setUnavailable]=useState(false),[waitedOut,setWaitedOut]=useState(false),[cancelledSeen,setCancelledSeen]=useState(returned==='cancelled')
  const lastNetwork=useRef(null),startedAt=useRef(Date.now())
  // The ticket tells us which flow to use: payment_provider, payment_method and payer_details_required.
  const provider=booking.payment_provider||null,method=booking.payment_method||null
  const latest=booking.latest_payment||null,paid=booking.payment_status==='PAID'||(!hire&&booking.status==='CONFIRMED')
  const pendingSandbox=latest&&latest.status==='PENDING'&&latest.provider_name==='SANDBOX'?latest.id:null
  const pendingPayHere=latest&&latest.status==='PENDING'&&latest.provider_name!=='SANDBOX'
  const sandboxId=sandbox?.id||pendingSandbox

  // After PayHere sends the passenger back, only the server's own record counts: read it again until it settles.
  const watching=returned==='returned'&&!paid&&pendingPayHere&&!waitedOut
  useEffect(()=>{
    if(!watching)return undefined
    const timer=setInterval(()=>{if(Date.now()-startedAt.current>WAIT_MS){setWaitedOut(true);return}refresh().catch(()=>{})},POLL_MS)
    return ()=>clearInterval(timer)
  },[watching])

  function keyFor(signature){
    if(lastNetwork.current?.signature===signature){const key=lastNetwork.current.key;lastNetwork.current=null;return key}
    return newKey()
  }
  function problem(error,signature,key){
    const code=error.code,fields=error.fields||[]
    if(error instanceof TypeError||code==='API_TIMEOUT'){lastNetwork.current={signature,key};return {tone:'warn',text:t('We could not reach Travelly. Please try again.')}}
    if(error.status===410||code==='HOLD_EXPIRED'){refresh().catch(()=>{});return {tone:'warn',text:t('Hold ended — choose seats again'),seats:true}}
    if(code==='PAYMENT_AMOUNT_MISMATCH'){refresh().catch(()=>{});return {tone:'warn',text:t('The amount changed. It is now {value0}.',{value0:fields[0]?.message||''})}}
    if(code==='BOOKING_ALREADY_PAID'||code==='HOLD_NOT_ACTIVE'){refresh().catch(()=>{});return {tone:'info',text:code==='BOOKING_ALREADY_PAID'?t('This booking is already paid.'):t('This hold is no longer active.')}}
    if(code==='PAYMENT_NOT_DUE'){refresh().catch(()=>{});return {tone:'info',text:t('Payment opens when the trip is completed.')}}
    if(code==='PAYMENT_IN_PROGRESS'){if(provider==='SANDBOX'&&fields[0]?.message)setSandbox({id:fields[0].message});refresh().catch(()=>{});return {tone:'info',text:hire?t('A payment for this booking is already waiting. Finish or wait for it first.'):t('A payment for this booking is already waiting. Finish it below.')}}
    if(code==='PAYMENT_PROVIDER_UNAVAILABLE'){return {tone:'warn',text:t('Online payment is not available right now.')}}
    if(code==='PAYMENT_NOT_AVAILABLE'){setUnavailable(true);return null}
    return {tone:'warn',text:error.message||t('The payment could not be started. Please try again.')}
  }
  function handleIntent(result){
    const checkout=result.checkout||{}
    if(checkout.provider==='SANDBOX'){setSandbox(result);setPayerFor(null);return refresh()}
    submitCheckout(checkout)   // leaves the page; nothing else to do
    return Promise.resolve()
  }
  const payerBody=()=>{const out={};asked.forEach(name=>{out[name]=payer[name].trim()});return out}
  async function pay(){
    setBusy(true);setMessage(null);setCancelledSeen(false)
    const body={amount:booking.total_amount,currency:booking.currency||'LKR',method}
    if(asked.length)body.payer=payerBody()
    const signature=JSON.stringify(body),key=keyFor(signature)
    try{
      await handleIntent(await api(`/bookings/${booking.id}/payment-intents`,{method:'POST',body:JSON.stringify({...body,idempotency_key:key})}))
    }catch(error){
      if(error.code==='PAYER_DETAILS_REQUIRED'){setPayerFor((error.fields||[]).map(f=>String(f.field).replace(/^payer\./,'')));setMessage({tone:'info',text:t('Needed by PayHere for this payment. Travelly does not keep it.')})}   // safety net
      else if(error.code==='IDEMPOTENCY_KEY_REUSED'){lastNetwork.current=null;setMessage({tone:'info',text:t('Please press Pay again.')})}
      else setMessage(problem(error,signature,key))
    }finally{setBusy(false)}
  }
  async function outcome(kind){
    setBusy(true);setMessage(null)
    try{await api(`/payments/${sandboxId}/sandbox-outcome`,{method:'POST',body:JSON.stringify({outcome:kind})});setSandbox(null);await refresh()}
    catch(error){
      if(error.code==='PAYMENT_NOT_PENDING'){setSandbox(null);refresh().catch(()=>{});setMessage({tone:'info',text:t('That payment is already finished. Press Pay to start a new one.')})}
      else setMessage(problem(error,'outcome',''))
    }finally{setBusy(false)}
  }
  async function continuePayHere(){
    setBusy(true);setMessage(null)
    const body={payer:payerBody()}
    try{const result=await api(`/payments/${latest.id}/checkout`,{method:'POST',body:JSON.stringify(body)});submitCheckout(result.checkout)}
    catch(error){
      if(error.code==='PAYER_DETAILS_REQUIRED'){setPayerFor((error.fields||[]).map(f=>String(f.field).replace(/^payer\./,'')));setMessage({tone:'info',text:t('Needed by PayHere for this payment. Travelly does not keep it.')})}
      else if(error.code==='PAYMENT_NOT_PENDING'){refresh().catch(()=>{});setMessage({tone:'info',text:t('That payment is already finished. Press Pay to start a new one.')})}
      else setMessage(problem(error,'checkout',''))
    }finally{setBusy(false)}
  }

  // ask exactly the fields the ticket lists (plus any the server names in a PAYER_DETAILS_REQUIRED safety-net answer)
  const wanted=new Set([...(booking.payer_details_required||[]),...(payerFor||[])]),asked=['address','city','phone','email'].filter(name=>wanted.has(name))
  const need=name=>asked.includes(name),missing=asked.some(name=>!payer[name].trim())
  const statusChip=booking.payment_status==='PAID'?<Chip tone="success">{t('Paid')}</Chip>:booking.payment_status==='PENDING'?<Chip tone="info" icon="clock">{t('Payment pending')}</Chip>:booking.payment_status==='FAILED'?<Chip tone="danger" icon="alert">{t('Payment failed')}</Chip>:null

  if(paid)return <div className="tk-pay">
    <p className="tk-line"><Chip tone="success">{hire?t('Paid'):t('Seats confirmed')}</Chip> {latest?.payment_reference&&<strong>{latest.payment_reference}</strong>}</p>
  </div>
  if(booking.status==='CANCELLED')return <div className="tk-pay"><p className="tk-line is-warn" role="status">{t('Hold ended — choose seats again')}</p>{onChooseSeats&&<button type="button" className="ui-button ui-button-secondary" onClick={onChooseSeats}>{t('Choose seats again')}</button>}</div>
  if(unavailable)return <p className="tk-line">{t('Online payment is not available for this booking.')}</p>
  if(!provider&&!pendingSandbox&&!pendingPayHere&&!sandbox)return <p className="tk-line" role="status">{t('Online payment is not available right now.')}</p>

  return <div className="tk-pay">
    {message&&<p className={`tk-line${message.tone==='warn'?' is-warn':''}`} role="status">{message.text} {message.seats&&onChooseSeats&&<button type="button" className="tk-link" onClick={onChooseSeats}>{t('Choose seats again')}</button>}</p>}
    {cancelledSeen&&!pendingSandbox&&<p className="tk-line is-warn" role="status">{hire?t('The payment was cancelled. No money was taken. You can try again.'):t('The payment was cancelled. No money was taken. You can try again while the seats are held.')}</p>}
    {booking.payment_status==='FAILED'&&latest?.failure_message&&!message&&<p className="tk-line is-warn" role="status">{latest.failure_message}</p>}
    {sandboxId&&provider==='SANDBOX'&&<>
        <p className="tk-line"><Chip tone="info" icon="alert">{t('Sandbox / test payment, no real money')}</Chip> {sandbox?.checkout?.message}</p>
        <div className="tk-bar">
          <button type="button" className="ui-button ui-button-primary" disabled={busy} onClick={()=>outcome('SUCCEEDED')}>{t('Simulate success')}</button>
          <button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={()=>outcome('FAILED')}>{t('Simulate failure')}</button>
        </div>
      </>}
    {pendingPayHere&&!sandboxId&&<p className="tk-line" role="status">{watching?t('Waiting for PayHere to confirm your payment...'):waitedOut?t('Still pending. We will update it as soon as PayHere confirms.'):t('Waiting for PayHere…')}</p>}
    {pendingPayHere&&!sandboxId&&waitedOut&&<div className="tk-bar"><button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={()=>{setBusy(true);refresh().catch(()=>{}).finally(()=>setBusy(false))}}>{t('Refresh')}</button></div>}
    {!sandboxId&&asked.length>0&&<div className="tk-grid" style={{'--cols':Math.min(asked.length,4)}}>
      {need('address')&&<Field label="Address"><input name="payer-address" maxLength="150" value={payer.address} onChange={e=>setPayer({...payer,address:e.target.value})} autoComplete="street-address"/></Field>}
      {need('city')&&<Field label="City"><input name="payer-city" maxLength="80" value={payer.city} onChange={e=>setPayer({...payer,city:e.target.value})} autoComplete="address-level2"/></Field>}
      {need('phone')&&<Field label="Phone"><input name="payer-phone" type="tel" placeholder="+94771234567" value={payer.phone} onChange={e=>setPayer({...payer,phone:e.target.value})}/></Field>}
      {need('email')&&<Field label="Email address"><input name="payer-email" type="email" value={payer.email} onChange={e=>setPayer({...payer,email:e.target.value})}/></Field>}
    </div>}
    {!sandboxId&&<div className="tk-bar">
      {statusChip}
      {pendingPayHere
        ?<button type="button" className="ui-button ui-button-primary" disabled={busy||missing} onClick={continuePayHere}>{t('Continue to PayHere')}</button>
        :<button type="button" className="ui-button ui-button-primary" disabled={busy||!method||missing} onClick={pay}>{busy?t('Please wait…'):t('Pay {value0} {value1}',{value0:booking.currency||'LKR',value1:booking.total_amount})}</button>}
      <InfoTip>{hire?t('Your booking is marked paid only after the payment is received.'):t('Your seats are confirmed only after the payment is received.')}</InfoTip>
    </div>}
  </div>
}
