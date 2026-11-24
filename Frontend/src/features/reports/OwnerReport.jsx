import { t } from '../../i18n/language.js'
import {useState} from 'react'
import {Header} from '../../components/components'
import Chip from '../../components/ui/Chip'
import {FlowShell} from '../booking/flow/FlowParts'
import {money} from '../passenger/TicketCancel'
import {formatDate,formatDateTime} from '../../i18n/dateTime.js'
import {DataTable,MonthPicker,ResultCard,Tiles,usePdf,useReport} from './ReportParts'
import {isLoss,pdfName,previousMonth,validPeriod} from './reportModel'

/* Owner → Reports (contract 03RP, first half): GET /owners/me/reports/monthly/{YYYY-MM}. A month picker (default: last month, never past
   this month), the month result, summary tiles and short tables for trips, earnings, maintenance and documents, and Download PDF
   (GET .../pdf as a blob with the Bearer token, saved as travelly-report-YYYY-MM.pdf). */
const km=value=>`${Number(value||0).toLocaleString('en-LK',{maximumFractionDigits:1})} km`
const day=value=>value?formatDate(value):'—'

export default function OwnerReport(){
  const [period,setPeriod]=useState(previousMonth()),[tab,setTab]=useState(0)
  const ok=validPeriod(period),report=useReport(ok?`/owners/me/reports/monthly/${period}`:'',ok)
  const pdf=usePdf({path:`/owners/me/reports/monthly/${period}/pdf`,filename:pdfName(period),download:true})
  const d=report.data,cur=d?.currency||'LKR',m=v=>money(cur,v)
  const sum=d?.summary||{},res=d?.result||{},loss=isLoss(res)
  const strip=d&&<ResultCard compact loss={loss} labels={[t('Income'),t('Expenses'),loss?t('Loss'):t('Profit')]} income={m(res.income)} expenses={m(res.expenses_total)} profit={m(res.profit)}/>
  const empty=t('Nothing in this month')
  const tabs=['Overview','Trips and km','Earnings','Maintenance','Documents','Driver payments'].map((name,i)=>({label:t(name),icon:['chart','route','wallet','settings','document','user'][i],active:tab===i,onClick:()=>setTab(i)}))
  const view=[
    // 0 overview: the month result card first, then the summary tiles
    d&&<div className="rp-pane" key="o"><ResultCard loss={loss} labels={[t('Income'),t('Expenses'),loss?t('Loss'):t('Profit')]} income={m(res.income)} expenses={m(res.expenses_total)} profit={m(res.profit)}>
        <p className="rp-note">{t('Service and repair')} {m(res.expenses_service_and_repair)} · {t('Fuel and charging')} {m(res.expenses_fuel_and_charging)} · {t('Paid to Drivers')} {m(res.expenses_driver_payments)}{res.note?` — ${t(res.note)}`:''}</p></ResultCard>
      <Tiles items={[
        {key:'v',label:t('Vehicles'),value:sum.vehicles},{key:'t',label:t('Completed trips'),value:sum.completed_trips},{key:'k',label:t('Total km'),value:km(sum.total_km)},
        {key:'g',label:t('Gross collected'),value:m(sum.gross_collected)},{key:'c',label:t('Commission'),value:m(sum.commission)},{key:'r',label:t('Refunded'),value:m(sum.refunded)},
        {key:'n',label:t('Owner net'),value:m(sum.owner_net)},{key:'p',label:t('Payouts received'),value:m(sum.payouts_received)},{key:'m',label:t('Maintenance spend'),value:m(sum.maintenance_spend)},
        {key:'f',label:t('Fuel and charging spend'),value:m(sum.fuel_and_charging_spend)},{key:'d',label:t('Documents needing attention'),value:sum.documents_needing_attention,tone:Number(sum.documents_needing_attention)>0?'bad':''},
        {key:'dp',label:t('Paid to Drivers'),value:m(sum.driver_payments_paid)},{key:'e',label:t('Expenses'),value:m(sum.expenses_total)}]}/></div>,
    // 1 trips
    d&&<div className="rp-pane" key="t">{strip}
      {(d.trips?.per_vehicle||[]).length>0&&<div className="rp-chips">{d.trips.per_vehicle.map(v=><Chip key={v.vehicle} tone="info">{v.vehicle} · {t('{value0} trips',{value0:v.trips})} · {km(v.km)}</Chip>)}</div>}
      <DataTable label={t('Trips and km')} empty={empty} rows={d.trips?.items} columns={[
        {key:'date',label:t('Date'),top:true,render:r=>day(r.date)},{key:'distance_km',label:t('km'),top:true,render:r=>km(r.distance_km)},{key:'reference',label:t('Reference')},{key:'kind',label:t('Kind')},
        {key:'route',label:t('Route')},{key:'vehicle',label:t('Vehicle')},{key:'driver',label:t('Driver')},{key:'start_km',label:t('Start km')},{key:'end_km',label:t('End km')}]}/></div>,
    // 2 earnings
    d&&<div className="rp-pane" key="e">{strip}
      <Tiles items={[{key:'a',label:t('Payable to you'),value:m(d.earnings?.open_balance_today?.payable_to_you)},{key:'b',label:t('Commission due from you'),value:m(d.earnings?.open_balance_today?.commission_due_from_you),tone:Number(d.earnings?.open_balance_today?.commission_due_from_you)>0?'bad':''},{key:'c',label:t('Waiting for refunds'),value:d.earnings?.open_balance_today?.waiting_for_refunds}]}/>
      <DataTable label={t('Earnings')} empty={empty} rows={d.earnings?.items} columns={[
        {key:'date',label:t('Date'),top:true,render:r=>day(r.date)},{key:'amount',label:t('Amount'),top:true,render:r=>m(r.amount)},{key:'booking',label:t('Booking')},{key:'method',label:t('Method')},{key:'type',label:t('Type')},
        {key:'commission',label:t('Commission'),render:r=>m(r.commission)},{key:'refunded',label:t('Refunded'),render:r=>m(r.refunded)},{key:'owner_net',label:t('Owner net'),render:r=>m(r.owner_net)},{key:'status',label:t('Status')}]}/>
      {(d.earnings?.payouts||[]).length>0&&<><h4 className="rp-h">{t('Payouts')}</h4><DataTable label={t('Payouts')} empty={empty} rows={d.earnings.payouts} columns={[
        {key:'date',label:t('Date'),top:true,render:r=>day(r.date)},{key:'amount',label:t('Amount'),top:true,render:r=>m(r.amount)},{key:'reference',label:t('Reference')},{key:'method',label:t('Method')}]}/></>}</div>,
    // 3 maintenance
    d&&<div className="rp-pane" key="m">{strip}
      <DataTable label={t('Maintenance')} empty={empty} rows={d.maintenance?.items} columns={[
        {key:'date',label:t('Date'),top:true,render:r=>day(r.date)},{key:'amount',label:t('Amount'),top:true,render:r=>m(r.amount)},{key:'vehicle',label:t('Vehicle')},{key:'type',label:t('Type')},
        {key:'odometer_km',label:t('Odometer'),render:r=>km(r.odometer_km)},{key:'provider',label:t('Provider')},{key:'notes',label:t('Notes')}]}/>
      {(d.maintenance?.coming_up_today||[]).length>0&&<><h4 className="rp-h">{t('Coming up')}</h4><DataTable label={t('Coming up')} empty={empty} rows={d.maintenance.coming_up_today} columns={[
        {key:'due',label:t('Due'),top:true,render:r=>day(r.due)},{key:'status',label:t('Status'),top:true},{key:'vehicle',label:t('Vehicle')},{key:'task',label:t('Task')},{key:'remaining_km',label:t('Remaining km'),render:r=>km(r.remaining_km)}]}/></>}</div>,
    // 4 documents
    d&&<div className="rp-pane" key="x">{strip}
      <DataTable label={t('Documents')} empty={empty} rows={d.documents?.items} columns={[
        {key:'expiry_date',label:t('Expiry date'),top:true,render:r=>day(r.expiry_date)},{key:'state',label:t('State'),top:true},{key:'document',label:t('Document')},{key:'for',label:t('For')},{key:'number',label:t('Number')},{key:'status',label:t('Status')}]}/></div>
    ,
    // 5 driver payments: what you recorded paying Drivers, by the day paid. Cash counts after the Driver confirms it.
    d&&<div className="rp-pane" key="dp">{strip}
      <Tiles items={[{key:'a',label:t('Confirmed'),value:m(d.driver_payments?.paid_total)},{key:'b',label:t('Waiting for the Driver'),value:m(d.driver_payments?.waiting_total)}]}/>
      <DataTable label={t('Driver payments')} empty={empty} rows={d.driver_payments?.items} columns={[
        {key:'paid_on',label:t('Paid on'),top:true,render:r=>day(r.paid_on)},{key:'amount',label:t('Amount'),top:true,render:r=>m(r.amount)},{key:'trip',label:t('Trip')},{key:'driver',label:t('Driver')},
        {key:'method',label:t('Method')},{key:'reference',label:t('Reference')},{key:'status',label:t('Status'),render:r=>r.status==='Confirmed'?t('Confirmed'):t('Waiting for the Driver')}]}/></div>
  ][tab]
  return <><Header/><FlowShell heading={t('Reports')} icon="chart" title={d?.period?formatDate(`${d.period}-01`,{day:undefined,month:'long'}):(d?.period_label||t('Monthly report'))} tabs={tabs}
    info={d?.generated_at?`${t('Made on')} ${formatDateTime(d.generated_at)}`:t('Your trips, earnings, maintenance and documents for one month.')}>
    <div className="rp-page">
      <div className="rp-bar"><MonthPicker value={period} onChange={setPeriod}/>{report.loading&&ok&&<span role="status">{t('Loading…')}</span>}</div>
      {report.error&&<p className="tk-line is-warn" role="alert">{report.error}</p>}
      {pdf.error&&<p className="tk-line is-warn" role="alert">{pdf.error}</p>}
      <div className="rp-view">{view}</div>
      <div className="flow-actions rp-actions"><span/><button type="button" className="ui-button ui-button-primary rp-pdf" disabled={!d||pdf.busy} onClick={pdf.run}>{pdf.busy?t('Please wait…'):t('Download PDF')}</button></div>
    </div>
  </FlowShell></>
}
