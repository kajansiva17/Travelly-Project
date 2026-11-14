import { t } from '../../i18n/language.js'
import {useState} from 'react'
import {Link} from 'react-router-dom'
import {Header} from '../../components/components'
import {FlowShell} from '../booking/flow/FlowParts'
import {money} from '../passenger/TicketCancel'
import {formatDate,formatDateTime} from '../../i18n/dateTime.js'
import {DataTable,MonthPicker,ResultCard,Tiles,usePdf,useReport} from './ReportParts'
import {attentionTone,bookingsMade,pdfName,previousMonth,validPeriod} from './reportModel'

/* Admin → Reports (contract 03RP, second half): GET /admin/reports/monthly/{YYYY-MM}. Tiles, money, people, "Needs attention" lists with links to
   the matching Admin screens, and Download PDF (blob with the Bearer token, opened from an object URL in a new tab). Field names are those the API
   returns: summary, money, people, attention, result. */
const km=value=>`${Number(value||0).toLocaleString('en-LK',{maximumFractionDigits:1})} km`
const day=value=>value?formatDate(value):'—'
// Where each "Needs attention" list is handled.
const LINKS={departures:'/admin/services-routes/tickets',refunds:'/admin/payments',documents:'/admin/documents',applications:'/admin/applications'}

export default function AdminReport(){
  const [period,setPeriod]=useState(previousMonth()),[tab,setTab]=useState(0)
  const ok=validPeriod(period),report=useReport(ok?`/admin/reports/monthly/${period}`:'',ok)
  const pdf=usePdf({path:`/admin/reports/monthly/${period}/pdf`,filename:pdfName(period,true),download:false})
  const d=report.data,cur=d?.currency||'LKR',m=v=>money(cur,v),sum=d?.summary||{},res=d?.result||{},att=d?.attention||{},bal=d?.money?.open_balance_today||{}
  const empty=t('Nothing in this month')
  const attentionCount=Number(sum.needs_attention||0)
  const income=<ResultCard compact={tab!==0} loss={false} ops={['+','=']} labels={[t('Commission online'),t('Commission cash'),t('Travelly income')]} income={m(res.commission_online)} expenses={m(res.commission_cash)} profit={m(res.income)}/>
  const tabs=[t('Overview'),t('Money'),t('People'),`${t('Needs attention')} (${attentionCount})`].map((label,i)=>({label,icon:['chart','wallet','users','alert'][i],active:tab===i,onClick:()=>setTab(i)}))
  const list=(key,title,columns)=><section className="rp-attn" key={key}><header><h4 className="rp-h">{title} ({(att[key]||[]).length})</h4><Link className="ui-button ui-button-secondary" to={LINKS[key]}>{t('Open')}</Link></header>
    <DataTable label={title} empty={t('Nothing needs attention here.')} rows={att[key]} columns={columns}/></section>
  const view=[
    d&&<div className="rp-pane" key="o">{income}
      <Tiles items={[
        {key:'b',label:t('Bookings'),value:bookingsMade(sum)},{key:'t',label:t('Trips'),value:sum.completed_trips},{key:'k',label:t('km'),value:km(sum.total_km)},{key:'u',label:t('New users'),value:sum.new_users},
        {key:'c',label:t('Collected'),value:m(sum.collected_total)},{key:'i',label:t('Travelly income'),value:m(sum.travelly_commission),tone:'good'},{key:'p',label:t('Paid to Owners'),value:m(sum.payouts_paid)},
        {key:'a',label:t('Needs attention'),value:attentionCount,tone:attentionTone(attentionCount)==='danger'?'bad':'',onClick:()=>setTab(3)}]}/>
      <p className="rp-note">{t('Private hire (includes Event hire)')} {sum.private_hire_bookings??0} · {t('Ticket')} {sum.ticket_bookings??0} · {t('Rental')} {sum.rental_bookings??0} · {t('Cancelled')} {sum.cancelled_bookings??0}</p>
      <p className="rp-note">{t('Of which still to collect from Owners')}: {m(res.cash_commission_still_due)}{res.note?` — ${res.note}`:''}</p></div>,
    d&&<div className="rp-pane" key="m"><Tiles items={[
        {key:'o',label:t('Collected online'),value:m(sum.collected_online)},{key:'h',label:t('Collected in cash'),value:m(sum.collected_cash)},{key:'r',label:t('Refunds paid'),value:m(sum.refunds_paid)},
        {key:'ow',label:t('Owed to Owners'),value:m(bal.owed_to_owners)},{key:'cd',label:t('Commission due from Owners'),value:m(bal.commission_due_from_owners)},{key:'rw',label:t('Refunds waiting'),value:`${bal.refunds_waiting??0} · ${m(bal.refunds_waiting_amount)}`}]}/>
      <DataTable label={t('Per service')} empty={empty} rows={d.money?.per_service} columns={[
        {key:'service',label:t('Service'),top:true},{key:'collected',label:t('Collected'),top:true,render:r=>m(r.collected)},{key:'payments',label:t('Payments')},
        {key:'commission',label:t('Commission'),render:r=>m(r.commission)},{key:'owner_share',label:t('Owner share'),render:r=>m(r.owner_share)},{key:'refunded',label:t('Refunded'),render:r=>m(r.refunded)}]}/></div>,
    d&&<div className="rp-pane" key="p"><DataTable label={t('Applications this month')} empty={empty} rows={d.people?.roles} columns={[
        {key:'role',label:t('Role'),top:true},{key:'approved',label:t('Approved')},{key:'rejected',label:t('Rejected')},{key:'waiting_now',label:t('Waiting now')},{key:'suspended_now',label:t('Suspended now')}]}/>
      <h4 className="rp-h">{t('Approvals')}</h4>
      <DataTable label={t('Approvals')} empty={empty} rows={d.people?.approved} columns={[{key:'date',label:t('Date'),top:true,render:r=>day(r.date)},{key:'name',label:t('Name'),top:true},{key:'reference',label:t('Reference')},{key:'role',label:t('Role')}]}/></div>,
    d&&<div className="rp-pane" key="n">
      {list('departures',t('Departures'),[{key:'departs',label:t('Departs'),top:true},{key:'status',label:t('Status'),top:true},{key:'reference',label:t('Reference')},{key:'route',label:t('Route')}])}
      {list('refunds',t('Refunds'),[{key:'since',label:t('Since'),top:true,render:r=>day(r.since)},{key:'amount',label:t('Amount'),top:true,render:r=>m(r.amount)},{key:'booking',label:t('Booking')},{key:'method',label:t('Method')},{key:'status',label:t('Status')},{key:'problem',label:t('Problem')}])}
      {list('documents',t('Documents'),[{key:'expiry_date',label:t('Expiry date'),top:true,render:r=>day(r.expiry_date)},{key:'state',label:t('State'),top:true},{key:'document',label:t('Document')},{key:'holder',label:t('Holder')},{key:'vehicle',label:t('Vehicle')},{key:'number',label:t('Number')}])}
      {list('applications',t('Applications'),[{key:'waiting_days',label:t('Waiting days'),top:true},{key:'name',label:t('Name'),top:true},{key:'reference',label:t('Reference')},{key:'role',label:t('Role')}])}</div>
  ][tab]
  return <><Header/><FlowShell heading={t('Reports')} icon="chart" title={d?.period_label||t('Monthly report')} tabs={tabs}
    info={d?.generated_at?`${t('Made on')} ${formatDateTime(d.generated_at)}`:t('The whole platform for one month.')}>
    <div className="rp-page">
      <div className="rp-bar"><MonthPicker value={period} onChange={setPeriod}/>{report.loading&&ok&&<span role="status">{t('Loading…')}</span>}</div>
      {report.error&&<p className="tk-line is-warn" role="alert">{report.error}</p>}
      {pdf.error&&<p className="tk-line is-warn" role="alert">{pdf.error}</p>}
      <div className="rp-view">{view}</div>
      <div className="flow-actions rp-actions"><span/><button type="button" className="ui-button ui-button-primary rp-pdf" disabled={!d||pdf.busy} onClick={pdf.run}>{pdf.busy?t('Please wait…'):t('Download PDF')}</button></div>
    </div>
  </FlowShell></>
}
