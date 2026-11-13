import { t } from '../../i18n/language.js'
import React,{useEffect,useRef,useState} from 'react'
import {api} from '../../services/api'
import {Field,RateErrors} from '../owner/OwnerRates'
import {Checkbox} from '../../components/ui'
import Chip from '../../components/ui/Chip'
import EmptyState from '../../components/ui/EmptyState'
import {usePaged,useRowCount} from '../booking/flow/FlowParts'
import {newKey} from '../passenger/TicketPayment'
import {money} from '../passenger/TicketCancel'
import {formatDate,formatDateTime} from '../../i18n/dateTime.js'
import {daysOpenMessage,nothingTakenOut,owesCommission,stageChip} from '../settlements/commissionStanding'
import AdminList,{Facts} from './AdminList'
import {fieldErrors,fieldErrorMap,settlementIds} from '../../services/fieldErrors.js'

/* Admin payments and Owner settlement (Payments contract 03P, section F).
   F1 totals and the payments list, F2 the Owners Travelly owes or is owed by, F3 record a payout after the bank transfer,
   F4 record commission received from an Owner. Only references, amounts, states and dates the API returns are shown. */
const SETTLEMENT={OWNER_PAYABLE:['info','Payable'],OWNER_PAID:['success','Paid out'],COMMISSION_DUE:['danger','Commission due'],COMMISSION_PAID:['success','Commission paid']}
const TYPES={PAYMENT:'Payment',FULL_REFUND:'Full refund',PARTIAL_REFUND:'Partial refund',OWNER_PAYOUT:'Owner payout'}
const typeFilters=[['','All transactions'],['PAYMENT','Payments'],['REFUND','Refunds'],['OWNER_PAYOUT','Owner payouts']]
const TOTALS=[['collected_online','Collected online'],['collected_cash','Collected in cash'],['refunded','Refunded'],['refunds_waiting','Refunds waiting'],['commission_earned','Commission earned'],['owner_payable','Payable to Owners'],['owner_paid','Paid to Owners'],['commission_due_from_owners','Commission due from Owners']]
const when=value=>value?formatDateTime(value):'—'
const label=code=>t(TYPES[code]||String(code||'').replaceAll('_',' ').toLowerCase().replace(/^./,c=>c.toUpperCase()))
const settlementChip=code=>SETTLEMENT[code]?[SETTLEMENT[code][0],t(SETTLEMENT[code][1])]:['muted',code?t(String(code).replaceAll('_',' ').toLowerCase().replace(/^./,c=>c.toUpperCase())):'']
// Cash commission standing (contract 03CM): stage chip and days open per Owner.
const standingChip=standing=>{const [tone,name]=stageChip(standing);return [tone,t(name)]}
const standingLine=standing=>standing&&standing.stage&&standing.stage!=='NONE'?[t(...daysOpenMessage(standing.days_open)),standing.extended_until?t('Extended until {value0}',{value0:formatDate(standing.extended_until)}):''].filter(Boolean).join(' · '):''
const sum=(rows,key)=>rows.reduce((total,row)=>total+Number(row[key]||0),0)
const refText=row=>row.booking_reference||row.payment_reference

function explain(error,rows){
  const code=error.code
  if(error instanceof TypeError||code==='API_TIMEOUT')return {text:t('We could not reach Travelly. Please try again.')}
  if(code==='SETTLEMENT_NOT_ALLOWED'){
    // field_errors list the ids that cannot be settled; show their references.
    const ids=settlementIds(error),refs=rows.filter(r=>ids.has(r.id)).map(refText)
    return {reload:true,ids,text:(error.message||t('Some of these payments can no longer be settled.'))+(refs.length?' '+refs.join(', '):'')}
  }
  if(error.status===403)return {text:t('Only an Admin can do this.')}
  if(code==='VALIDATION_ERROR'&&fieldErrors(error).length)return {fields:fieldErrorMap(error),text:t('Please check the highlighted fields.')}
  return {text:error.message||t('The change could not be saved. Please try again.')}
}

function SettleRow({row,tab,selectable,checked,onToggle}){
  const [tone,state]=settlementChip(row.owner_settlement_status),cur=row.currency
  return <article className="tk-row">
    {selectable&&<label className="ap-check"><input type="checkbox" checked={checked} onChange={()=>onToggle(row.id)} aria-label={t('Select {value0}',{value0:refText(row)})}/></label>}
    <div className="tk-row-main"><strong>{refText(row)} · {money(cur,row.amount)}</strong>
      <span>{row.payment_reference} · {when(tab==='settled'?row.owner_paid_at||row.captured_at:row.owner_payable_at||row.captured_at||row.created_at)}{row.commission_amount?` · ${t('Commission')} ${money(cur,row.commission_amount)}`:''}</span></div>
    <div className="tk-row-actions">{tab==='payable'&&<strong className="tk-line" title={t('The amount the payout will use')}>{t('Payable')} {money(cur,row.payable_amount)}</strong>}
      {tab==='commission_due'&&<strong className="tk-line">{t('Commission')} {money(cur,row.commission_amount)}</strong>}
      <Chip tone={tab==='needs_review'?'info':tone}>{tab==='needs_review'?t('Refund waiting'):state}</Chip></div></article>
}

const SECTIONS=[['payable','To be paid'],['commission_due','Commission due'],['needs_review','Waiting for review'],['settled','Paid and settled']]
const EMPTY={payable:'Nothing is waiting to be paid to this Owner.',commission_due:'This Owner owes no commission.',needs_review:'Nothing is waiting for review.',settled:'Nothing has been settled yet.'}
// One Owner: choose payments, then record the payout (F3) or the commission received (F4). Nothing is sent before the confirm step.
function OwnerSettlement({owner,onChanged}){
  const [section,setSection]=useState(owner.payable?.length||!owner.commission_due?.length?'payable':'commission_due'),[selected,setSelected]=useState(new Set()),[reference,setReference]=useState('')
  const [settleCommission,setSettleCommission]=useState(false),[extend,setExtend]=useState(null),[mode,setMode]=useState(null),[busy,setBusy]=useState(false),[errors,setErrors]=useState({}),[message,setMessage]=useState(''),[done,setDone]=useState(null),retry=useRef(null)
  const showTick=owesCommission(owner.commission_standing)
  const rows=owner[section]||[],pay=section==='payable',selectable=pay||section==='commission_due'
  const size=Math.max(2,useRowCount(96)),paged=usePaged(rows,size)
  const chosen=rows.filter(r=>selected.has(r.id)),total=sum(chosen,pay?'payable_amount':'commission_amount'),cur=owner.currency||rows[0]?.currency
  const pick=code=>{setSection(code);setSelected(new Set());setMode(null);setMessage('');setErrors({});setReference('')}
  const toggle=id=>{setSelected(c=>{const n=new Set(c);n.has(id)?n.delete(id):n.add(id);return n});setMode(null)}
  const toggleAll=()=>{setSelected(c=>c.size===rows.length?new Set():new Set(rows.map(r=>r.id)));setMode(null)}
  async function send(){
    const ids=[...selected].sort(),text=reference.trim()
    // One idempotency key per press. A retry after a lost answer reuses it, so the same payout is never recorded twice.
    const signature=JSON.stringify([section,ids,text,pay&&showTick&&settleCommission]),key=retry.current?.signature===signature?retry.current.key:newKey();retry.current=null
    setBusy(true);setMessage('');setErrors({})
    try{
      const body=pay?{payment_ids:ids,bank_reference:text,idempotency_key:key,...(settleCommission&&showTick?{settle_commission:true}:{})}:{payment_ids:ids,reference:text,idempotency_key:key}
      const result=await api(`/admin/owner-settlements/${owner.owner_user_id}/${pay?'payouts':'commission-receipts'}`,{method:'POST',body:JSON.stringify(body)})
      setDone({pay,total:result.total,count:(pay?result.payouts:result.payments||[]).length||ids.length,reference:text,currency:cur,setOff:pay&&settleCommission&&showTick&&result.bank_transfer_total!=null?{commission:result.commission_set_off,bank:result.bank_transfer_total}:null});setMode(null);onChanged()
    }catch(error){
      if(error instanceof TypeError||error.code==='API_TIMEOUT')retry.current={signature,key}
      const out=explain(error,rows)
      setMode(null);setMessage(out.text);setErrors(out.fields||{})
      if(out.reload){setSelected(c=>new Set([...c].filter(id=>!out.ids.has(id))));onChanged()}
    }finally{setBusy(false)}
  }
  const extending=useRef(false)
  async function extendDays(){
    if(extending.current)return   // a double click must not send twice (the Owner is notified each time)
    extending.current=true;setBusy(true);setMessage('');setErrors({})
    try{
      const result=await api(`/admin/owner-settlements/${owner.owner_user_id}/commission-extension`,{method:'POST',body:JSON.stringify({days:Number(extend.days),reason:extend.reason.trim()})})
      setExtend(null);setDone({extended:true,standing:result?.commission_standing||result});onChanged()
    }catch(error){const out=explain(error,[]);setExtend(c=>({...c,confirm:false}));setMessage(out.text);setErrors(out.fields||{})}
    finally{extending.current=false;setBusy(false)}
  }
  if(done?.extended)return <div className="tk-pane"><p className="tk-line"><Chip tone="success" icon="check">{t('Days extended')}</Chip> {standingLine(done.standing)}</p><p className="tk-line">{t('The Owner is told. When the extra days pass, new bookings stop again.')}</p>
    <div className="tk-bar"><button type="button" className="ui-button ui-button-secondary" onClick={()=>setDone(null)}>{t('Back')}</button></div></div>
  if(extend)return <RateErrors.Provider value={errors}><div className="tk-pane cm-extend">
    {message&&<p className="tk-line is-warn" role="status">{message}</p>}
    {extend.confirm
      ?<div className="tk-hold"><p className="tk-line"><strong>{t('Give this Owner {value0} more days before new bookings stop?',{value0:extend.days})}</strong> {extend.reason.trim()}</p>
        <div className="tk-bar"><button type="button" className="ui-button ui-button-primary" disabled={busy} onClick={extendDays}>{busy?t('Please wait…'):t('Yes, extend days')}</button><button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={()=>setExtend(c=>({...c,confirm:false}))}>{t('Back')}</button></div></div>
      :<><div className="tk-grid" style={{'--cols':2}}>
        <Field label="Days" help="How many more days the Owner has before new bookings stop (1 to 30)."><input name="days" type="number" min="1" max="30" step="1" inputMode="numeric" value={extend.days} onChange={e=>setExtend(c=>({...c,days:e.target.value}))}/></Field>
        <Field label="Reason" help="Why the days are extended. It is kept in the audit record."><input name="reason" maxLength="500" value={extend.reason} onChange={e=>setExtend(c=>({...c,reason:e.target.value}))}/></Field></div>
        <div className="tk-bar"><button type="button" className="ui-button ui-button-secondary" onClick={()=>{setExtend(null);setMessage('');setErrors({})}}>{t('Back')}</button><button type="button" className="ui-button ui-button-primary" disabled={busy||!extend.days||!extend.reason.trim()} onClick={()=>{setMessage('');setErrors({});setExtend(c=>({...c,confirm:true}))}}>{t('Extend days')}</button></div></>}
  </div></RateErrors.Provider>
  if(done)return <div className="tk-pane"><p className="tk-line"><Chip tone="success" icon="check">{done.pay?t('Payout recorded'):t('Commission recorded')}</Chip> <strong>{money(done.currency,done.total)}</strong> · {t('{value0} payments',{value0:done.count})} · {done.reference}</p>
    {done.setOff&&<p className="tk-line">{nothingTakenOut(done.setOff.commission)?t('No commission was taken out'):t('Commission taken out of this payout: {value0}',{value0:money(done.currency,done.setOff.commission)})} · <strong>{t('Amount to send to the bank: {value0}',{value0:money(done.currency,done.setOff.bank)})}</strong></p>}
    <p className="tk-line">{done.pay?t('The payments are marked as paid out and the Owner is told.'):t('The payments are marked as commission paid.')}</p></div>
  return <RateErrors.Provider value={errors}><div className="tk-pane">
    {owner.commission_standing&&owner.commission_standing.stage!=='NONE'&&<div className="tk-bar"><Chip tone={standingChip(owner.commission_standing)[0]}>{standingChip(owner.commission_standing)[1]}</Chip><span className="tk-line">{standingLine(owner.commission_standing)} · {t('Commission due')} {money(cur,owner.commission_standing.amount_due)}</span>
      <button type="button" className="ui-button ui-button-secondary" onClick={()=>setExtend({days:'',reason:'',confirm:false})}>{t('Extend days')}</button></div>}
    <div className="tk-bar" role="group" aria-label={t('Settlement sections')}>{SECTIONS.map(([code,name])=><Chip key={code} tone="info" selected={section===code} onClick={()=>pick(code)}>{t(name)} ({(owner[code]||[]).length})</Chip>)}</div>
    {message&&<p className="tk-line is-warn" role="status">{message}</p>}
    {rows.length
      ?<div className="tk-rows">{paged.slice.map(row=><SettleRow key={row.id} row={row} tab={section} selectable={selectable} checked={selected.has(row.id)} onToggle={toggle}/>)}</div>
      :<EmptyState icon="wallet" title={t(EMPTY[section])}/>}
    {selectable&&rows.length>0&&(mode==='confirm'
      ?<div className="tk-hold"><p className="tk-line"><strong>{pay?t('Record a payout of {value0} for {value1} payments?',{value0:money(cur,total),value1:chosen.length}):t('Record commission of {value0} received for {value1} payments?',{value0:money(cur,total),value1:chosen.length})}</strong> {pay?t('Do this only after the bank transfer is made. The Owner is told.'):t('The payments are marked as commission paid.')} {reference.trim()}</p>
        <div className="tk-bar"><button type="button" className="ui-button ui-button-primary" disabled={busy} onClick={send}>{busy?t('Please wait…'):pay?t('Yes, record payout'):t('Yes, record commission')}</button><button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={()=>setMode(null)}>{t('Back')}</button></div></div>
      :<div className="tk-bar ap-record">
        {pay&&showTick&&<Checkbox checked={settleCommission} onChange={e=>{setSettleCommission(e.target.checked);setMode(null)}}>{t('Take commission out of this payout')}</Checkbox>}
        <button type="button" className="ui-button ui-button-secondary" onClick={toggleAll}>{selected.size===rows.length?t('Clear selection'):t('Select all')}</button>
        <div className="ap-reference"><Field label={pay?'Bank reference':'Reference'} help={pay?'The reference of the bank transfer you made.':'For example a cash deposit or transfer reference.'}><input name={pay?'bank_reference':'reference'} maxLength="120" value={reference} onChange={e=>{setReference(e.target.value);setMode(null)}}/></Field></div>
        <button type="button" className="ui-button ui-button-primary" disabled={!selected.size||!reference.trim()} onClick={()=>{setMessage('');setMode('confirm')}}>{pay?t('Record payout'):t('Record commission')}{selected.size?` · ${money(cur,total)}`:''}</button></div>)}
    <div className="flow-actions">{paged.pages>1?paged.pager:<span/>}<span/></div>
  </div></RateErrors.Provider>
}

export default function AdminPayments(){
  const [tab,setTab]=useState(0),[payments,setPayments]=useState(null),[owners,setOwners]=useState(null),[error,setError]=useState(null),[filter,setFilter]=useState(''),[overdue,setOverdue]=useState(false)
  const loadPayments=()=>api('/admin/payments',{cache:'no-store'}).then(r=>{setPayments(r);setError(null)}).catch(setError)
  const loadOwners=(only=overdue)=>api('/admin/owner-settlements'+(only?'?overdue=true':''),{cache:'no-store'}).then(r=>{setOwners(r.items||[]);setError(null)}).catch(setError)
  useEffect(()=>{loadPayments()},[])
  useEffect(()=>{setOwners(null);loadOwners(overdue)},[overdue])
  const changed=()=>{loadOwners(overdue);loadPayments()}
  const tabs=[['Totals','chart'],['Payments','wallet'],['Owner settlements','users']].map(([name,icon],i)=>({label:t(name),icon,active:tab===i,onClick:()=>setTab(i)}))
  const base={heading:t('Payments'),icon:'wallet',tabs,error,info:t('Money Travelly holds for an Owner is paid out only after the trip. Record a payout after you make the bank transfer.')}
  if(tab===0){
    const totals=payments?.totals
    return <AdminList {...base} title={t('Totals')} items={null} custom={!totals?(error?null:<p role="status">{t('Loading…')}</p>)
      :<div className="tk-pane"><Facts cols={4} entries={TOTALS.map(([key,name])=>[t(name),money(totals.currency,totals[key])])}/></div>}/>
  }
  if(tab===1){
    const shown=payments&&(payments.items||[]).filter(r=>!filter||(filter==='REFUND'?/REFUND$/.test(r.transaction_type||''):r.transaction_type===filter))
    return <AdminList {...base} title={t('Payments')} items={shown} empty={t('No payments match this filter.')}
      filters={<Field label="Show"><select name="payment-filter" value={filter} onChange={e=>setFilter(e.target.value)}>{typeFilters.map(([value,name])=><option key={value} value={value}>{t(name)}</option>)}</select></Field>} filterCols={4}
      row={r=>{const [tone,state]=settlementChip(r.owner_settlement_status);return {key:r.id,title:`${r.payment_reference} · ${money(r.currency,r.amount)}`,meta:`${r.booking_reference||'—'} · ${label(r.transaction_type)} · ${r.provider_name==='PAYHERE'?'PayHere':r.provider_name==='SANDBOX'?t('Sandbox'):r.provider_name||'—'} · ${when(r.captured_at||r.created_at)}`,status:state||label(r.status),tone}}}
      detailTitle={r=>r.payment_reference}
      detail={r=><Facts cols={3} entries={[[t('Booking'),r.booking_reference||'—'],[t('Type'),label(r.transaction_type)],[t('Status'),label(r.status)],[t('Amount'),money(r.currency,r.amount)],[t('Commission'),r.commission_amount?money(r.currency,r.commission_amount):'—'],[t('Owner share'),r.owner_net_amount?money(r.currency,r.owner_net_amount):'—'],
        [t('Settlement'),settlementChip(r.owner_settlement_status)[1]||'—'],[t('Method'),label(r.payment_method)],[t('Captured'),when(r.captured_at)],[t('Payable from'),when(r.owner_payable_at)],[t('Paid out'),when(r.owner_paid_at)],[t('Provider reference'),r.provider_reference||'—']]}/>}/>
  }
  return <AdminList {...base} title={t('Owner settlements')} items={owners} empty={overdue?t('No Owner has overdue commission.'):t('No Owner has anything payable, owed or waiting for review.')}
    filters={<Chip tone="info" selected={overdue} onClick={()=>setOverdue(v=>!v)}>{t('Commission overdue')}</Chip>} filterCols={4}
    row={o=>({key:o.owner_user_id,title:`${o.owner_name||'—'} · ${o.owner_reference||''}`,meta:`${t('Payable')} ${money(o.currency,o.payable_amount)} · ${t('Commission due')} ${money(o.currency,o.commission_due_amount)} · ${t('{value0} waiting for review',{value0:(o.needs_review||[]).length})}${standingLine(o.commission_standing)?' · '+standingLine(o.commission_standing):''}`,actions:o.commission_standing&&o.commission_standing.stage!=='NONE'?<Chip tone={standingChip(o.commission_standing)[0]}>{standingChip(o.commission_standing)[1]}</Chip>:null,status:Number(o.payable_amount)>0?t('Payable'):Number(o.commission_due_amount)>0?t('Commission due'):t('Waiting for review'),tone:Number(o.payable_amount)>0?'info':Number(o.commission_due_amount)>0?'danger':'muted'})}
    detailTitle={o=>`${o.owner_name||''} · ${o.owner_reference||''}`}
    detail={o=><OwnerSettlement key={o.owner_user_id} owner={o} onChanged={changed}/>}/>
}
