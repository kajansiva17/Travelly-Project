import { t } from '../../i18n/language.js'
import React,{useEffect,useRef,useState} from 'react'
import {api} from '../../services/api'
import {Field,RateErrors} from '../owner/OwnerRates'
import Chip from '../../components/ui/Chip'
import {newKey} from '../passenger/TicketPayment'
import {money,REFUND_STATUS} from '../passenger/TicketCancel'
import {formatDateTime} from '../../i18n/dateTime.js'
import AdminList,{Facts} from './AdminList'

// Admin refunds (Payments contract 03P, section E2 to E5). Lists never show tokens, card or bank details:
// only references, amounts, status and dates that the refund item itself carries.
const causes={PASSENGER_CANCELLATION:'Passenger cancelled',PAYMENT_AFTER_HOLD:'Paid after the hold ended',ADMIN:'Admin refund'}
const filters=[['','All refunds'],['WAITING','Waiting'],['PAID','Refunded'],['FAILED','Declined']]
const when=value=>formatDateTime(value)||'—'
const isWaiting=row=>row.status==='PENDING'||row.status==='PROCESSING'

// Friendly text for every error code in E3 to E5. Returns {field?, text}.
function explain(error,fallback){
  const code=error.code,fields=error.fields||[]
  if(error instanceof TypeError||code==='API_TIMEOUT')return {text:t('We could not reach Travelly. Please try again.')}
  if(code==='REASON_REQUIRED')return {field:'reason',text:t('Write a reason for rejecting this refund.')}
  if(code==='REFUND_ALREADY_DECIDED')return {reload:true,text:t('Someone has already decided this refund. The list was refreshed.')}
  if(code==='VERSION_CONFLICT')return {reload:true,text:t('This refund changed while you were looking. The list was refreshed, so check it and try again.')}
  if(code==='REFUND_NOT_FOUND'||(error.status===404&&!code))return {reload:true,text:t('We could not find this refund. The list was refreshed.')}
  if(code==='REFUND_NOT_RETRYABLE')return {reload:true,text:t('This refund cannot be sent to PayHere again. It may already be paid, waiting for PayHere, or not a card payment. The list was refreshed.')}
  if(code==='PAYHERE_REFUND_API_OFF')return {text:t('The PayHere Refund API is not set up, so it cannot be sent from here. Refund it in the PayHere portal and record it.')}
  if(code==='REFUND_NOT_PROCESSING')return {reload:true,text:t('This refund is not waiting to be recorded. The list was refreshed.')}
  if(code==='REFUND_AMOUNT_INVALID')return {field:'amount',text:t('That is more than can still be refunded. The most you can refund is {value0}.',{value0:fields[0]?.message||''})}
  if(code==='PAYMENT_NOT_REFUNDABLE')return {reload:true,text:t('This payment cannot be refunded. It may not be paid, or it has already been refunded in full.')}
  if(code==='VALIDATION_ERROR'&&fields.length)return {fields:Object.fromEntries(fields.map(f=>[f.field,f.message])),text:t('Please check the highlighted fields.')}
  return {text:error.message||fallback}
}

// What each PayHere refund state means and what to do (contract 03P, E6).
const PAYHERE_STATES={
  PAYHERE_REFUND_FAILED:'PayHere refused the refund or could not be reached. Send it again, or refund it in the PayHere portal and record it.',
  PAYHERE_MANUAL_REQUIRED:'This was not a card payment, and PayHere refunds cards only. Refund it by bank transfer, then record it here.',
  PAYHERE_REQUESTED:'The refund was sent to PayHere but the answer was not recorded. It is never sent again automatically.'
}
export const failureLine=row=>row.failure_code&&PAYHERE_STATES[row.failure_code]?{code:row.failure_code,meaning:PAYHERE_STATES[row.failure_code],message:row.failure_message}:null
const StatusChip=({status})=>{const [tone,label]=REFUND_STATUS[status]||['muted',status||'—'];return <Chip tone={tone}>{t(label)}</Chip>}

// One decision with a confirmation step: nothing is sent until "Yes".
function Decide({row,onChanged,onProblem,extra}){
  const [mode,setMode]=useState(null),[reason,setReason]=useState(''),[reference,setReference]=useState(''),[busy,setBusy]=useState(false),[errors,setErrors]=useState({}),[message,setMessage]=useState('')
  const hire=row.provider_name==='PAYHERE',failure=failureLine(row)
  async function send(path,body){
    setBusy(true);setErrors({});setMessage('')
    try{const saved=await api(`/admin/refunds/${row.id}/${path}`,{method:'POST',body:JSON.stringify(body)});setMode(null);setReason('');setReference('');onChanged(saved)}
    catch(error){
      const out=explain(error,t('The change could not be saved. Please try again.'))
      if(out.reload){setMode(null);onProblem(out.text);return}
      if(out.field==='reason'||out.fields?.reason)setMode('reject-form')
      setErrors(out.fields||(out.field?{[out.field]:out.text}:{}));setMessage(out.field?'':out.text)
    }finally{setBusy(false)}
  }
  const amount=money(row.currency,row.amount)
  if(row.status==='PAID')return <div className="tk-bar"><StatusChip status="PAID"/><span className="tk-line">{t('This refund is complete.')} {row.provider_reference&&<strong>{row.provider_reference}</strong>}</span>{extra}</div>
  if(row.status==='FAILED')return <div className="tk-bar"><StatusChip status="FAILED"/><span className="tk-line">{row.failure_code==='REFUND_REJECTED'?t('This refund was rejected. The payment stays paid.'):t('This refund did not go through.')}</span>{extra}</div>
  return <RateErrors.Provider value={errors}><div className="tk-pane">
    {message&&<p className="tk-line is-warn" role="status">{message}</p>}
    {row.status==='PENDING'&&!mode&&<div className="tk-bar"><button type="button" className="ui-button ui-button-primary" onClick={()=>setMode('approve')}>{t('Approve refund')}</button><button type="button" className="ui-button ui-button-secondary" onClick={()=>setMode('reject-form')}>{t('Reject refund')}</button>{extra}</div>}
    {mode==='approve'&&<div className="tk-hold"><p className="tk-line"><strong>{t('Approve this refund of {value0}?',{value0:amount})}</strong> {hire?t('You then refund it in the PayHere portal and record it here.'):t('The Sandbox refund is paid at once.')}</p>
      <div className="tk-bar"><button type="button" className="ui-button ui-button-primary" disabled={busy} onClick={()=>send('decision',{expected_version:row.version,decision:'APPROVE'})}>{busy?t('Please wait…'):t('Yes, approve')}</button><button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={()=>setMode(null)}>{t('Not yet')}</button></div></div>}
    {(mode==='reject-form'||mode==='reject')&&<div className="tk-hold">
      <Field label="Reason for rejecting"><input name="reason" maxLength="500" value={reason} disabled={mode==='reject'} onChange={e=>setReason(e.target.value)}/></Field>
      {mode==='reject'&&<p className="tk-line"><strong>{t('Reject this refund of {value0}?',{value0:amount})}</strong> {t('The payment stays paid and the Passenger is told.')}</p>}
      <div className="tk-bar">{mode==='reject'
        ?<><button type="button" className="ui-button ui-button-primary" disabled={busy} onClick={()=>send('decision',{expected_version:row.version,decision:'REJECT',reason:reason.trim()})}>{busy?t('Please wait…'):t('Yes, reject')}</button><button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={()=>setMode('reject-form')}>{t('Back')}</button></>
        :<><button type="button" className="ui-button ui-button-primary" disabled={!reason.trim()} onClick={()=>{setErrors({});setMessage('');setMode('reject')}}>{t('Reject refund')}</button><button type="button" className="ui-button ui-button-secondary" onClick={()=>{setMode(null);setReason('');setErrors({});setMessage('')}}>{t('Not yet')}</button></>}</div></div>}
    {row.status==='PROCESSING'&&!['complete','record'].includes(mode)&&(failure&&row.provider_name==='PAYHERE'
      ?<div className="tk-pane">
        <p className="tk-line is-warn" role="status"><strong>{failure.code}</strong> · {t(failure.meaning)}{failure.message&&<> {failure.message}</>}</p>
        <div className="tk-bar">
          {row.failure_code==='PAYHERE_REFUND_FAILED'&&!mode&&<button type="button" className="ui-button ui-button-primary" onClick={()=>setMode('again')}>{t('Send to PayHere again')}</button>}
          {!mode&&<button type="button" className={'ui-button '+(row.failure_code==='PAYHERE_REFUND_FAILED'?'ui-button-secondary':'ui-button-primary')} onClick={()=>setMode('record')}>{row.failure_code==='PAYHERE_MANUAL_REQUIRED'?t('Do the bank transfer, then record it'):row.failure_code==='PAYHERE_REQUESTED'?t('Check the PayHere portal, then record it'):t('Refund in the PayHere portal, then record it')}</button>}
          {mode==='again'&&<><button type="button" className="ui-button ui-button-primary" disabled={busy} onClick={()=>send('payhere',{})}>{busy?t('Please wait…'):t('Yes, send it again')}</button><button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={()=>setMode(null)}>{t('Back')}</button></>}
          {extra}</div>
        {mode==='again'&&<p className="tk-line"><strong>{t('Send this refund of {value0} to PayHere again?',{value0:amount})}</strong> {t('PayHere is asked once more. If it answers, the refund is paid; if not, you will see the new answer here.')}</p>}
      </div>
      :<>
      <div className="tk-grid" style={{'--cols':2}}><Field label="PayHere refund number" help="Refund this payment in the PayHere portal first, then enter the number PayHere shows."><input name="provider_reference" maxLength="120" value={reference} onChange={e=>setReference(e.target.value)}/></Field></div>
      <div className="tk-bar"><button type="button" className="ui-button ui-button-primary" disabled={!reference.trim()} onClick={()=>setMode('complete')}>{t('Record as refunded')}</button>{extra}</div></>)}
    {mode==='record'&&<div className="tk-hold">
      <div className="tk-grid" style={{'--cols':2}}><Field label={row.failure_code==='PAYHERE_MANUAL_REQUIRED'?'Bank transfer reference':'PayHere refund number'} help={row.failure_code==='PAYHERE_MANUAL_REQUIRED'?'Refund the money by bank transfer first, then enter the transfer reference.':'Check the refund in the PayHere portal first, then enter the number PayHere shows.'}><input name="provider_reference" maxLength="120" value={reference} onChange={e=>setReference(e.target.value)}/></Field></div>
      <div className="tk-bar"><button type="button" className="ui-button ui-button-primary" disabled={!reference.trim()} onClick={()=>setMode('complete')}>{t('Record as refunded')}</button><button type="button" className="ui-button ui-button-secondary" onClick={()=>setMode(null)}>{t('Back')}</button></div></div>}
    {mode==='complete'&&<div className="tk-hold"><p className="tk-line"><strong>{t('Record this refund of {value0} as paid?',{value0:amount})}</strong> {t('PayHere refund number')}: {reference.trim()}</p>
      <div className="tk-bar"><button type="button" className="ui-button ui-button-primary" disabled={busy} onClick={()=>send('complete',{expected_version:row.version,provider_reference:reference.trim()})}>{busy?t('Please wait…'):t('Yes, record it')}</button><button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={()=>setMode(failure?'record':null)}>{t('Back')}</button></div></div>}
  </div></RateErrors.Provider>
}

// Admin refunds part or all of one payment straight away (E5). Amount is capped by the payment; the server has the final word.
export function DirectRefund({payment,onDone,onBack}){
  const [full,setFull]=useState(true),[amount,setAmount]=useState(''),[reason,setReason]=useState(''),[ask,setAsk]=useState(false),[busy,setBusy]=useState(false),[errors,setErrors]=useState({}),[message,setMessage]=useState(''),[done,setDone]=useState(null)
  const retry=useRef(null)
  const cap=Number(payment.amount),entered=Number(amount),amountBad=!full&&!(entered>0&&entered<=cap)
  const ready=reason.trim()&&!amountBad
  async function send(){
    setBusy(true);setErrors({});setMessage('')
    const body=full?{full:true,reason:reason.trim()}:{full:false,amount:entered.toFixed(2),reason:reason.trim()}
    const signature=JSON.stringify(body),key=retry.current?.signature===signature?retry.current.key:newKey();retry.current=null
    try{setDone(await api(`/payments/${payment.id}/refunds`,{method:'POST',body:JSON.stringify({...body,idempotency_key:key})}));setAsk(false);onDone&&onDone()}
    catch(error){
      if(error instanceof TypeError||error.code==='API_TIMEOUT')retry.current={signature,key}
      const out=explain(error,t('The refund could not be created. Please try again.'))
      setAsk(false);setErrors(out.fields||(out.field?{[out.field]:out.text}:{}));setMessage(out.field?'':out.text)
    }finally{setBusy(false)}
  }
  const left=full?money(payment.currency,payment.amount):money(payment.currency,entered||0)
  if(done)return <div className="tk-pane"><p className="tk-line"><StatusChip status={done.status}/> <strong>{t('Refund {value0} created.',{value0:money(done.currency,done.amount)})}</strong> {done.payment_reference}</p>
    <p className="tk-line">{done.status==='PROCESSING'?t('Refund it in the PayHere portal, then record it under Refunds.'):t('The money has gone back to the Passenger.')}</p>
    <div className="tk-bar"><button type="button" className="ui-button ui-button-secondary" onClick={onBack}>{t('Back')}</button></div></div>
  return <RateErrors.Provider value={errors}><div className="tk-pane">
    <p className="tk-line"><strong>{payment.payment_reference}</strong> · {money(payment.currency,payment.amount)} · {payment.provider_name==='PAYHERE'?'PayHere':t('Sandbox')} · {t(payment.status==='PAID'?'Paid':String(payment.status||'').replaceAll('_',' '))}</p>
    {message&&<p className="tk-line is-warn" role="status">{message}</p>}
    <div className="tk-bar" role="group" aria-label={t('How much?')}><Chip tone="info" selected={full} onClick={()=>{setFull(true);setAsk(false)}}>{t('Refund in full')}</Chip><Chip tone="info" selected={!full} onClick={()=>{setFull(false);setAsk(false)}}>{t('Part of it')}</Chip></div>
    <div className="tk-grid" style={{'--cols':full?1:3}}>
      {!full&&<Field label="Amount (LKR)" help="At most the payment amount. The server checks what is still left to refund."><input name="amount" type="number" min="0.01" max={cap} step="0.01" inputMode="decimal" value={amount} onChange={e=>{setAmount(e.target.value);setAsk(false)}}/></Field>}
      <div style={{gridColumn:full?'auto':'span 2'}}><Field label="Reason"><input name="reason" maxLength="500" value={reason} onChange={e=>{setReason(e.target.value);setAsk(false)}}/></Field></div>
    </div>
    {ask
      ?<div className="tk-hold"><p className="tk-line"><strong>{t('Refund {value0} to the Passenger now?',{value0:left})}</strong> {t('It is approved at once and recorded with your reason.')}</p>
        <div className="tk-bar"><button type="button" className="ui-button ui-button-primary" disabled={busy} onClick={send}>{busy?t('Please wait…'):t('Yes, refund')}</button><button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={()=>setAsk(false)}>{t('Not yet')}</button></div></div>
      :<div className="tk-bar"><button type="button" className="ui-button ui-button-primary" disabled={!ready} onClick={()=>setAsk(true)}>{t('Refund payment')}</button><button type="button" className="ui-button ui-button-secondary" onClick={onBack}>{t('Back')}</button></div>}
  </div></RateErrors.Provider>
}

// Find the payments of one booking (A4) and pick one to refund.
function PayLookup({onPick,onBack,start}){
  const [bookingId,setBookingId]=useState(''),[rows,setRows]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState('')
  async function find(event){
    event.preventDefault();setBusy(true);setError('');setRows(null)
    try{const result=await api(`/bookings/${bookingId.trim()}/payments`);setRows((result.items||[]).filter(x=>x.transaction_type==='PAYMENT'))}
    catch(problem){setError(problem.code==='BOOKING_NOT_FOUND'||problem.status===404?t('We could not find this booking.'):problem.message||t('The payments could not be loaded. Please try again.'))}
    finally{setBusy(false)}
  }
  return <form className="tk-pane" onSubmit={find}>
    <div className="tk-grid" style={{'--cols':2}}><Field label="Booking ID" help="The booking's ID from the refund details or the Passenger's booking link."><input name="booking" required maxLength="60" value={bookingId} onChange={e=>setBookingId(e.target.value)}/></Field></div>
    {error&&<p className="tk-line is-warn" role="status">{error}</p>}
    {rows&&(rows.length?<div className="tk-rows">{rows.slice(0,3).map(p=><article className="tk-row" key={p.id}><div className="tk-row-main"><strong>{p.payment_reference} · {money(p.currency,p.amount)}</strong><span>{p.provider_name==='PAYHERE'?'PayHere':t('Sandbox')} · {when(p.captured_at||p.created_at)}</span></div>
      <div className="tk-row-actions"><Chip tone={p.status==='PAID'?'success':'muted'}>{t(p.status==='PAID'?'Paid':String(p.status).replaceAll('_',' '))}</Chip><button type="button" className="ui-button ui-button-secondary" disabled={p.status!=='PAID'&&p.status!=='PARTIALLY_REFUNDED'} onClick={()=>onPick(p)}>{t('Refund')}</button></div></article>)}</div>:<p className="tk-line">{t('This booking has no payments to refund.')}</p>)}
    <div className="tk-bar"><button type="submit" className="ui-button ui-button-primary" disabled={busy||!bookingId.trim()}>{busy?t('Please wait…'):t('Find payments')}</button><button type="button" className="ui-button ui-button-secondary" onClick={onBack}>{t('Back')}</button></div>
  </form>
}

export default function AdminRefunds({base}){
  const [items,setItems]=useState(null),[error,setError]=useState(null),[notice,setNotice]=useState(''),[filter,setFilter]=useState(''),[view,setView]=useState('list'),[payment,setPayment]=useState(null)
  const load=()=>api('/admin/refunds').then(result=>{setItems(result.items||[]);setError(null)}).catch(setError)
  useEffect(()=>{load()},[])
  const changed=saved=>{setItems(list=>(list||[]).map(x=>x.id===saved.id?{...x,...saved}:x));setNotice(saved.status==='FAILED'?t('Refund rejected.'):saved.status==='PAID'?t('Refund recorded as paid.'):saved.failure_code?t('PayHere has not completed this refund yet. See the details.'):t('Refund approved. Record it once it is refunded in PayHere.'))}
  const problem=text=>{setNotice(text);load()}
  const shown=items&&items.filter(x=>!filter||(filter==='WAITING'?isWaiting(x):x.status===filter))
  const waiting=(items||[]).filter(isWaiting).length
  if(view!=='list')return <AdminList {...base} title={t('Refund a payment')} custom={payment
    ?<DirectRefund payment={payment} onDone={load} onBack={()=>{setPayment(null);setView('list')}}/>
    :<PayLookup onPick={setPayment} onBack={()=>setView('list')}/>}/>
  return <AdminList {...base} title={t('Refunds')} notice={notice} error={error||base.error} items={shown} empty={t('No refunds match this filter.')}
    filters={<Field label="Show"><select name="refund-filter" value={filter} onChange={e=>setFilter(e.target.value)}>{filters.map(([value,label])=><option key={value} value={value}>{t(label)}</option>)}</select></Field>} filterCols={4}
    footer={<div className="tk-bar"><button type="button" className="ui-button ui-button-secondary" onClick={()=>{setPayment(null);setView('direct')}}>{t('Refund a payment')}</button><span className="tk-line">{t('{value0} waiting for a decision',{value0:waiting})}</span></div>}
    row={item=>({key:item.id,title:`${item.payment_reference} · ${money(item.currency,item.amount)}`,meta:`${item.booking_reference||'—'} · ${t(causes[item.cause]||'Refund')} · ${when(item.created_at)}`,status:t((REFUND_STATUS[item.status]||[0,item.status])[1]),tone:(REFUND_STATUS[item.status]||['muted'])[0]})}
    detailTitle={item=>item.payment_reference} detail={item=><>
      <Facts cols={3} entries={[
        [t('Booking'),item.booking_reference||'—'],[t('Original payment'),`${item.original_payment_reference||'—'} · ${money(item.currency,item.original_amount)}`],[t('Reason for refund'),t(causes[item.cause]||'Refund')],
        [t('Provider'),item.provider_name==='PAYHERE'?'PayHere':t('Sandbox')],[t('Requested'),when(item.created_at)],
        item.cancellation?[t('Refund percent'),`${item.cancellation.refund_percent}% · ${Math.round(item.cancellation.hours_before_departure)} h`]:[t('Refunded'),when(item.refunded_at)]]}/>
      <Decide key={`${item.id}-${item.version}-${item.status}`} row={item} onChanged={changed} onProblem={problem} extra={item.original_payment_id&&<button type="button" className="ui-button ui-button-secondary" onClick={()=>{setPayment({id:item.original_payment_id,payment_reference:item.original_payment_reference,amount:item.original_amount,currency:item.currency,provider_name:item.provider_name,status:'PAID'});setView('direct')}}>{t('Refund more of the original payment')}</button>}/>
    </>}/>
}
