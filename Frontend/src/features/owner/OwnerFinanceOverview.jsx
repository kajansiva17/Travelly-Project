import { t } from '../../i18n/language.js'
import {useEffect,useState} from 'react'
import {api} from '../../services/api'
import {Header,ErrorNotice} from '../../components/components'
import Chip from '../../components/ui/Chip'
import EmptyState from '../../components/ui/EmptyState'
import {FlowShell,useRowCount,usePaged} from '../booking/flow/FlowParts'
import {money} from '../passenger/TicketCancel'
import {formatDateTime} from '../../i18n/dateTime.js'
import CommissionBanner from '../settlements/CommissionBanner'
import {codeEnglish} from '../../i18n/codeLabels.js'

/* Owner settlements (Payments contract 03P, section F5): what Travelly owes the Owner, what the Owner owes Travelly,
   items waiting for Admin review, and recent settled rows. Every payable row shows payable_amount, the amount the
   payout will use (pro rata when the payment was partly refunded). Only fields the API returns are shown. */
const TABS=[
  {key:'payable',label:'To be paid to you',icon:'wallet',empty:'Nothing is waiting to be paid to you.',hint:'Online money Travelly holds for you. It is paid out after the trip, as the amount shown on each row.'},
  {key:'commission_due',label:'Commission you owe',icon:'chart',empty:'You owe no commission.',hint:'You collected this cash yourself, so the commission is paid to Travelly.'},
  {key:'needs_review',label:'Waiting for review',icon:'clock',empty:'Nothing is waiting for review.',hint:'A refund on these payments is still waiting. They cannot be paid out until it is settled.'},
  {key:'settled',label:'Paid and settled',icon:'check',empty:'Nothing has been settled yet.',hint:'Your latest settled payments.'}
]
const STATUS={OWNER_PAYABLE:['info','Payable'],OWNER_PAID:['success','Paid out'],COMMISSION_DUE:['danger','Commission due'],COMMISSION_PAID:['success','Commission paid']}
const day=value=>value?formatDateTime(value):'—'
function Row({row,tab,currency}){
  const [tone,label]=tab==='needs_review'?['info','Refund waiting']:STATUS[row.owner_settlement_status]||['muted',row.owner_settlement_status?codeEnglish(row.owner_settlement_status):'—']
  const cur=row.currency||currency
  return <article className="tk-row"><div className="tk-row-main"><strong>{row.booking_reference||row.payment_reference} · {money(cur,row.amount)}</strong>
    <span>{row.payment_reference} · {tab==='settled'?day(row.owner_paid_at||row.captured_at):tab==='payable'&&row.owner_payable_at?day(row.owner_payable_at):day(row.captured_at||row.created_at)}{row.commission_amount?` · ${t('Commission')} ${money(cur,row.commission_amount)}`:''}</span></div>
    <div className="tk-row-actions">
      {tab==='payable'&&<strong className="tk-line" title={t('The amount the payout will use')}>{t('Payable')} {money(cur,row.payable_amount)}</strong>}
      <Chip tone={tone}>{t(label)}</Chip></div></article>
}
export default function OwnerFinanceOverview(){
  const [data,setData]=useState(null),[error,setError]=useState(null),[tab,setTab]=useState(0),size=Math.max(2,useRowCount(64))
  const load=()=>api('/owners/me/settlements',{cache:'no-store'}).then(result=>{setData(result);setError(null)}).catch(setError)
  useEffect(()=>{load()},[])
  const current=TABS[tab],rows=(data&&data[current.key])||[],paged=usePaged(rows,size)
  const tabs=TABS.map((x,i)=>({label:t(x.label),icon:x.icon,active:tab===i,onClick:()=>setTab(i)}))
  const currency=data?.currency||'LKR'
  return <><Header/><FlowShell heading={t('Settlements')} title={t(current.label)} icon="wallet" tabs={tabs} info={t(current.hint)}>
    <ErrorNotice error={error}/>
    <CommissionBanner standing={data?.commission_standing} currency={data?.currency||'LKR'}/>
    {error&&<div className="flow-actions"><span/><button type="button" className="ui-button ui-button-secondary" onClick={load}>{t('Try again')}</button></div>}
    {!data&&!error?<p role="status">{t('Loading your settlements…')}</p>:data&&<div className="tk-pane">
      <div className="tk-bar"><Chip tone="info" icon="wallet">{t('Payable to you')} {money(currency,data.payable_amount)}</Chip><Chip tone={Number(data.commission_due_amount)>0?'danger':'muted'} icon="chart">{t('Commission you owe')} {money(currency,data.commission_due_amount)}</Chip></div>
      {rows.length?<div className="tk-rows">{paged.slice.map(row=><Row key={row.id} row={row} tab={current.key} currency={currency}/>)}</div>:<EmptyState icon={current.icon} title={t(current.empty)}/>}
      <div className="flow-actions">{paged.pages>1?paged.pager:<span/>}<span/></div></div>}
  </FlowShell></>
}
