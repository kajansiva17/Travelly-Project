import { t } from '../../i18n/language.js'
import {useState} from 'react'
import {Navigate} from 'react-router-dom'
import {hasSession} from '../../services/api'
import {Header} from '../../components/components'
import Chip from '../../components/ui/Chip'
import {FlowShell} from '../booking/flow/FlowParts'
import {money} from '../passenger/TicketCancel'
import {formatDate,formatDateTime} from '../../i18n/dateTime.js'
import {DataTable,MonthPicker,Tiles,usePdf,useReport} from './ReportParts'
import {previousMonth,validPeriod} from './reportModel'

/* Driver > Earnings > Monthly report: GET /drivers/me/reports/monthly/{YYYY-MM}. The month's completed trips and the payments your Owners
   recorded for them (cash counts once you confirm it), and Download PDF (saved as travelly-driver-report-YYYY-MM.pdf). */
const km=value=>`${Number(value||0).toLocaleString('en-LK',{maximumFractionDigits:1})} km`
const day=value=>value?formatDate(value):'—'

/* The month's report as a pane: month picker, Payments / Trips as chips, the tables and Download PDF. It sits inside Earnings (tab Monthly report). */
export function DriverReportPane(){
  const [period,setPeriod]=useState(previousMonth()),[tab,setTab]=useState(0)
  const ok=validPeriod(period),report=useReport(ok?`/drivers/me/reports/monthly/${period}`:'',ok)
  const pdf=usePdf({path:`/drivers/me/reports/monthly/${period}/pdf`,filename:`travelly-driver-report-${period}.pdf`,download:true})
  const d=report.data,cur=d?.currency||'LKR',m=v=>money(cur,v),sum=d?.summary||{},empty=t('Nothing in this month')
  const tiles=d&&<Tiles items={[
    {key:'r',label:t('Received'),value:m(sum.received_total),tone:'good'},{key:'w',label:t('Waiting for you'),value:m(sum.waiting_total)},
    {key:'t',label:t('Completed trips'),value:sum.completed_trips},{key:'k',label:t('Total km'),value:km(sum.total_km)},
    {key:'n',label:t('Trips without a recorded payment'),value:sum.trips_without_payment,tone:Number(sum.trips_without_payment)>0?'bad':''}]}/>
  const view=[
    d&&<div className="rp-pane" key="p">{tiles}
      <DataTable label={t('Payments')} empty={empty} rows={d.payments?.items} columns={[
        {key:'paid_on',label:t('Paid on'),top:true,render:r=>day(r.paid_on)},{key:'amount',label:t('Amount'),top:true,render:r=>m(r.amount)},{key:'trip',label:t('Trip')},{key:'owner',label:t('Owner')},
        {key:'method',label:t('Method')},{key:'reference',label:t('Reference')},{key:'status',label:t('Status'),render:r=>r.status==='Confirmed'?t('Confirmed'):t('Waiting for you')}]}/></div>,
    d&&<div className="rp-pane" key="t">{tiles}
      <DataTable label={t('Trips')} empty={empty} rows={d.trips?.items} columns={[
        {key:'date',label:t('Date'),top:true,render:r=>day(r.date)},{key:'distance_km',label:t('km'),top:true,render:r=>km(r.distance_km)},{key:'trip',label:t('Trip')},{key:'route',label:t('Route')},
        {key:'vehicle',label:t('Vehicle')},{key:'owner',label:t('Owner')},{key:'payment',label:t('Payment'),render:r=>r.payment==='Recorded'?t('Recorded'):t('Not recorded yet')}]}/></div>
  ][tab]
  return <div className="rp-page">
    <div className="rp-bar"><MonthPicker value={period} onChange={setPeriod}/>
      <span className="bk-groups rp-chips" role="tablist">{['Payments','Trips'].map((name,i)=><Chip key={name} selected={tab===i} onClick={()=>setTab(i)}>{t(name)}</Chip>)}</span>
      {report.loading&&ok&&<span role="status">{t('Loading…')}</span>}</div>
    {report.error&&<p className="tk-line is-warn" role="alert">{report.error}</p>}
    {pdf.error&&<p className="tk-line is-warn" role="alert">{pdf.error}</p>}
    <div className="rp-view">{view}</div>
    <div className="flow-actions rp-actions"><span/><button type="button" className="ui-button ui-button-primary rp-pdf" disabled={!d||pdf.busy} onClick={pdf.run}>{pdf.busy?t('Please wait…'):t('Download PDF')}</button></div>
  </div>
}

export default function DriverReport(){
  if(!hasSession())return <Navigate to="/login" replace/>
  return <><Header/><FlowShell heading={t('Reports')} icon="chart" title={t('Monthly report')} info={t('Your trips and the payments your Owners recorded for one month.')}><DriverReportPane/></FlowShell></>
}
