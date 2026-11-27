import { t } from '../../i18n/language.js'
import { useEffect, useState } from 'react'
import {Link} from 'react-router-dom'
import { api } from '../../services/api'
import { ErrorNotice,Icon } from '../../components/components'
import Chip from '../../components/ui/Chip'
import { FlowActions, FlowShell, StateCard } from '../booking/flow/FlowParts'
import { Thumb } from '../booking/BookingCardParts'
import { formatDateTime } from '../../i18n/dateTime.js'
import {paymentRow,paymentStatusText} from './passengerPaymentsModel.js'

// Each payment falls in one group, so the Passenger sees paid, waiting, failed and refunded money separately.
const GROUPS=[
  {key:'all',label:'All',test:()=>true},
  {key:'paid',label:'Paid',test:s=>s==='PAID',tone:'success',hint:'Payment received.'},
  {key:'waiting',label:'Waiting',test:s=>['PENDING','PROCESSING','CASH_AWAITING_CONFIRMATION'].includes(s),tone:'info',hint:'Waiting for the payment to finish.'},
  {key:'failed',label:'Failed',test:s=>s==='FAILED',tone:'danger',hint:'The payment did not go through. Open it to try again.'},
  {key:'refunded',label:'Refunded',test:s=>['REFUNDED','PARTIALLY_REFUNDED'].includes(s),tone:'muted',hint:'Money was returned to you.'}]
const groupOf=status=>GROUPS.slice(1).find(g=>g.test(status))||GROUPS[2]
const tone=status=>status==='PAID'?'success':status==='FAILED'?'danger':['REFUNDED','PARTIALLY_REFUNDED'].includes(status)?'muted':'info'

export default function PassengerPayments() {
  const [payments, setPayments] = useState(null)
  const [error, setError] = useState(null)
  const [group,setGroup]=useState(0)

  async function load() {
    setError(null)
    try {
      const result=await api('/bookings?as=passenger'),bookings=result.items||[],histories=new Array(bookings.length)
      let next=0
      await Promise.all(Array.from({length:Math.min(4,bookings.length)},async()=>{while(next<bookings.length){const index=next++;histories[index]=await api(`/bookings/${bookings[index].id}/payments`)}}))
      const vehicles=result.vehicles||{}
      setPayments(bookings.map((booking,index)=>{const row=paymentRow(booking,histories[index]);return row&&{...row,vehicle:vehicles[booking.vehicle_id]||null}}).filter(Boolean))
    } catch (problem) { setError(problem) }
  }

  useEffect(() => { load() }, [])
  if (!payments && !error) return <StateCard busy title={t('Loading payment history')}/>
  if (!payments) return <StateCard icon="alert" title={t('Payment history unavailable')} actions={<button type="button" onClick={load}>{t('Try again')}</button>}><ErrorNotice error={error}/></StateCard>

  const shown=payments.filter(p=>GROUPS[group].test(p.status)).sort((x,y)=>new Date(y.date||0)-new Date(x.date||0))
  return <FlowShell heading={t('Payments')} title={t('Payment history')} icon="wallet" info={t('Open a booking to review its payment details and receipts.')}>
    <div className="flow-wizard-form booking-pane">
      {error && <ErrorNotice error={error}/>}
      {payments.length===0?<p>{t('No payments yet.')}</p>:<>
        <div className="bk-groups" role="tablist">{GROUPS.map((g,i)=><Chip key={g.key} selected={group===i} onClick={()=>setGroup(i)}>{t(g.label)} ({payments.filter(p=>g.test(p.status)).length})</Chip>)}</div>
        {shown.length===0?<p className="tk-line">{t('Nothing in this tab yet.')}</p>:<div className="bk-list pc-list">{shown.map(item=>{const g=groupOf(item.status);return <article className={'bc-card pc-card is-'+g.key} key={item.id}>
          <Thumb src={item.vehicle?.profile_image_url} icon="wallet" size={64}/>
          <div className="bc-body"><strong className="bc-name">{t(item.service)}</strong>
            <span className="bc-sub">{t('Booking reference')}: {item.reference}</span>
            <span className="bc-line"><Icon name="clock" size={15}/>{formatDateTime(item.date)||'—'}</span>
            <span className="pc-hint">{t(g.hint)}</span></div>
          <div className="bc-side"><strong className="bc-price">{item.currency} {item.amount??'—'}</strong><Chip tone={tone(item.status)}>{t(paymentStatusText(item.status))}</Chip>
            <Link className="ui-button ui-button-secondary" to={`/bookings/${item.id}?payment=1`}>{t('Open payment')}</Link></div>
        </article>})}</div>}</>}
      <FlowActions><button type="button" className="ui-button ui-button-secondary" onClick={load}>{t('Refresh')}</button><span/></FlowActions>
    </div>
  </FlowShell>
}
