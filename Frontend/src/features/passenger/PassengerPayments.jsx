import { t } from '../../i18n/language.js'
import { useEffect, useState } from 'react'
import {Link} from 'react-router-dom'
import { api } from '../../services/api'
import { ErrorNotice,Icon } from '../../components/components'
import Chip from '../../components/ui/Chip'
import { FlowActions, FlowShell, StateCard,usePaged,useRowCount } from '../booking/flow/FlowParts'
import { formatDateTime } from '../../i18n/dateTime.js'
import {paymentRow,paymentStatusText} from './passengerPaymentsModel.js'

const tone=status=>status==='PAID'?'success':status==='FAILED'?'danger':['REFUNDED','PARTIALLY_REFUNDED'].includes(status)?'muted':'info'

export default function PassengerPayments() {
  const [payments, setPayments] = useState(null)
  const [error, setError] = useState(null)
  const paged=usePaged(payments||[],useRowCount(72))

  async function load() {
    setError(null)
    try {
      const result=await api('/bookings?as=passenger'),bookings=result.items||[],histories=new Array(bookings.length)
      let next=0
      await Promise.all(Array.from({length:Math.min(4,bookings.length)},async()=>{while(next<bookings.length){const index=next++;histories[index]=await api(`/bookings/${bookings[index].id}/payments`)}}))
      setPayments(bookings.map((booking,index)=>paymentRow(booking,histories[index])).filter(Boolean))
    } catch (problem) { setError(problem) }
  }

  useEffect(() => { load() }, [])
  if (!payments && !error) return <StateCard busy title={t('Loading payment history')}/>
  if (!payments) return <StateCard icon="alert" title={t('Payment history unavailable')} actions={<button type="button" onClick={load}>{t('Try again')}</button>}><ErrorNotice error={error}/></StateCard>

  return <FlowShell heading={t('Payments')} title={t('Payment history')} icon="wallet" info={t('Open a booking to review its payment details and receipts.')}>
    <div className="flow-wizard-form booking-pane">
      {error && <ErrorNotice error={error}/>}
      {payments.length===0?<p>{t('No payments yet.')}</p>:<div className="bk-list">{paged.slice.map(item=><article className="bk-card" key={item.id}>
        <span className="bk-icon"><Icon name="wallet" size={22} aria-hidden="true"/></span>
        <div className="bk-main"><strong>{t(item.service)}</strong><span className="bk-ref">{t('Booking reference')}: {item.reference}</span>
          <span className="bk-facts"><span><strong>{t('Amount')}:</strong> {item.currency} {item.amount??'—'}</span><span><strong>{t('Date')}:</strong> {formatDateTime(item.date)||'—'}</span></span></div>
        <div className="bk-side"><Chip tone={tone(item.status)}>{t(paymentStatusText(item.status))}</Chip><Link className="bk-open" to={`/bookings/${item.id}?payment=1`}>{t('Open payment')}<Icon name="arrow" size={15}/></Link></div>
      </article>)}</div>}
      <FlowActions><button type="button" className="ui-button ui-button-secondary" onClick={load}>{t('Refresh')}</button>{paged.pager}</FlowActions>
    </div>
  </FlowShell>
}
