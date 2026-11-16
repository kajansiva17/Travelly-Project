import { t } from '../../i18n/language.js'
import { useEffect, useState } from 'react'
import { api } from '../../services/api'
import { ErrorNotice } from '../../components/components'
import InfoTip from '../../components/ui/InfoTip'
import { FlowActions, FlowShell, StateCard } from '../booking/flow/FlowParts'
import { formatDateTime } from '../../i18n/dateTime.js'

const allowed = new Set(['PENDING', 'PAID', 'CASH_AWAITING_CONFIRMATION', 'FAILED', 'REFUNDED'])
const statusText = value => ({
  PENDING: 'Pending',
  PAID: 'Paid',
  CASH_AWAITING_CONFIRMATION: 'Cash awaiting confirmation',
  FAILED: 'Failed',
  REFUNDED: 'Refunded',
}[value] || value)

export default function PassengerPayments() {
  const [payments, setPayments] = useState(null)
  const [error, setError] = useState(null)

  async function load() {
    setError(null)
    try {
      let result
      try { result = await api('/bookings?passenger=me') }
      catch (problem) {
        if (problem.status !== 422) throw problem
        result = await api('/bookings?as=passenger')
      }
      const items = (result?.items || result || []).filter(item => allowed.has(item.payment_status_snapshot || item.payment_status))
      setPayments(items.slice(0, 6))
    } catch (problem) { setError(problem) }
  }

  useEffect(() => { load() }, [])
  if (!payments && !error) return <StateCard busy title={t('Loading payment history')}/>
  if (!payments) return <StateCard icon="alert" title={t('Payment history unavailable')} actions={<button type="button" onClick={load}>{t('Try again')}</button>}><ErrorNotice error={error}/></StateCard>

  return <FlowShell title="Payment history" icon="wallet" info={t('Your six most recent booking payments are shown here. Open the booking for full payment details and receipts.')}>
    <div className="booking-pane">
      {error && <ErrorNotice error={error}/>}
      {payments.length === 0 ? <p>{t('No payments yet.')}</p> : <table>
        <thead><tr>
          <th>{t('Booking reference')}<InfoTip>{t('The public reference for the booking linked to this payment.')}</InfoTip></th>
          <th>{t('Amount')}</th><th>{t('Status')}</th><th>{t('Date')}</th>
        </tr></thead>
        <tbody>{payments.map(item => <tr key={item.id}>
          <td>{item.booking_reference || item.reference || '—'}</td>
          <td>{t('LKR')} {item.total_amount ?? item.amount ?? '—'}</td>
          <td>{t(statusText(item.payment_status_snapshot || item.payment_status))}</td>
          <td>{formatDateTime(item.paid_at || item.updated_at || item.created_at || item.start_at)}</td>
        </tr>)}</tbody>
      </table>}
      <FlowActions><button type="button" onClick={load}>{t('Refresh')}</button></FlowActions>
    </div>
  </FlowShell>
}
