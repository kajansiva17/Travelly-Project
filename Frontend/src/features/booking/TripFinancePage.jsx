import React,{useEffect,useState} from 'react'
import {Link,useParams} from 'react-router-dom'
import {api} from '../../services/api'
import {ErrorNotice,Icon} from '../../components/components'
import {useWorkspace} from '../../context/workspaceContext'
import {t} from '../../i18n/language.js'
import {InfoTip} from '../../components/ui'
import {FlowShell} from './flow/FlowParts'

export default function TripFinancePage(){
 const {tripId}=useParams(),{role,user}=useWorkspace(),[data,setData]=useState(null),[error,setError]=useState(null),[busy,setBusy]=useState(false)
 const load=()=>api('/trips/'+tripId+'/financials').then(setData).catch(setError)
 useEffect(()=>{load()},[tripId])
 async function post(path,body){setBusy(true);setError(null);try{await api(path,{method:'POST',body:JSON.stringify(body)});await load()}catch(problem){setError(problem)}finally{setBusy(false)}}
 const payment=data?.payments?.[0],settlement=data?.settlements?.[0],fare=data?.final_fare,back=role==='OWNER'?'/owner/operations':role==='DRIVER'?'/driver/operate-trip':'/bookings'
 const amount=fare?.total_amount||'—',passenger=payment?.payer_user_id===user?.id||role==='PASSENGER',driver=payment?.held_by_driver_user_id===user?.id||role==='DRIVER',owner=role==='OWNER',bookingVersion=data?.booking_version
 const pay=(label,primary,path,body)=><button type="button" className={'ui-button '+(primary?'ui-button-primary':'ui-button-secondary')} disabled={busy} onClick={()=>post(path,body)}>{t(label)}</button>
 const actions=[]
 if(data){
  if(!payment&&passenger&&fare){actions.push(pay('I Paid Cash',false,'/trips/'+tripId+'/payments/cash-confirmations',{expected_version:bookingVersion}));actions.push(pay('Create sandbox online payment',true,'/trips/'+tripId+'/payments/online-intents',{expected_version:bookingVersion}))}
  if(payment&&payment.status==='CASH_PASSENGER_CONFIRMED'&&driver)actions.push(pay('Confirm cash received',true,'/payments/'+payment.id+'/cash-received',{expected_version:payment.version,amount:payment.amount}))
  if(payment&&payment.status==='CASH_HELD_BY_DRIVER'&&driver)actions.push(pay('Record cash handover to Owner',true,'/payments/'+payment.id+'/cash-handover',{expected_version:payment.version}))
  if(payment&&payment.status==='CASH_OWNER_SETTLEMENT_PENDING'&&owner)actions.push(pay('Confirm cash settlement receipt',true,'/payments/'+payment.id+'/owner-settlement-receipt',{expected_version:payment.version}))
 }
 return <FlowShell heading={t('Finance')} title={t('Final fare and settlement')} icon="wallet" info={t('Sandbox financial records only. Travelly does not hold funds or initiate real payouts.')}><ErrorNotice error={error}/>{!data?<p role="status">{t('Loading financial records...')}</p>:<div className="flow-wizard-form"><div className="finance-cols">
 <section className="finance-card"><div className="pane-head"><strong>{t('Final fare')}</strong></div><strong className="finance-amount">LKR {amount}</strong><p className="flow-note">{fare?t('Calculated from the frozen accepted rate card and operational records.'):t('Owner finalization is required before payment.')}</p></section>
 <section className="finance-card"><div className="pane-head"><strong>{t('Payment')}</strong>{payment&&payment.payment_method==='ONLINE'&&<InfoTip>{t('Online payment remains pending until the sandbox provider callback reports success.')}</InfoTip>}</div>{payment?<dl className="finance-ledger"><div><dt>{t('Method')}</dt><dd>{t(payment.payment_method)}</dd></div><div><dt>{t('Status')}</dt><dd>{t(payment.status.replaceAll('_',' '))}</dd></div><div><dt>{t('Reference')}</dt><dd>{payment.provider_reference||t('Cash confirmation')}</dd></div></dl>:<p className="flow-note">{t('No payment has been recorded yet.')}</p>}</section>
 <section className="finance-card"><div className="pane-head"><strong>{t('Owner settlement ledger')}</strong><InfoTip>{t('Provider fees default to LKR 0.00 until the sandbox provider returns an actual fee. They are absorbed by the platform and never added to the passenger fare.')}</InfoTip></div>{settlement?<dl className="finance-ledger"><div><dt>{t('Gross fare')}</dt><dd>LKR {settlement.gross_fare_amount}</dd></div><div><dt>{t('Platform fee')}</dt><dd>{Number(settlement.platform_fee_rate)*100}% · LKR {settlement.platform_fee_amount}</dd></div><div><dt>{t('Provider fee')}</dt><dd>LKR {settlement.provider_fee_amount}</dd></div><div><dt>{t('Expense reimbursement')}</dt><dd>LKR {settlement.reimbursement_amount}</dd></div><div><dt>{t('Owner payable')}</dt><dd>LKR {settlement.owner_payable_amount}</dd></div><div><dt>{t('Status')}</dt><dd>{t(settlement.status.replaceAll('_',' '))}</dd></div></dl>:<p className="flow-note">{t('Settlement values appear only after a payment is confirmed.')}</p>}</section>
 </div><div className="flow-actions"><Link className="ui-button ui-button-secondary" to={back}><Icon name="arrow" size={18} className="ui-back-arrow" aria-hidden="true"/><span>{t('Back')}</span></Link><span className="footer-slot">{actions}</span></div></div>}</FlowShell>
}
