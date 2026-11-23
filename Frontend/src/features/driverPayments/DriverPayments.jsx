import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { t } from '../../i18n/language.js'
import { api, hasSession } from '../../services/api'
import { Header, ErrorNotice } from '../../components/components'
import { FlowShell, usePaged, useRowCount } from '../booking/flow/FlowParts'
import { Field, Compact } from '../owner/OwnerRates'
import Chip from '../../components/ui/Chip'
import { displayTime } from '../../hooks/workspaceData'
import '../../styles/rates.css'

const post = (path, body) => api(path, { method: 'POST', body: JSON.stringify(body || {}) })
const methodLabel = method => method === 'CASH' ? t('Cash') : t('Online transfer')

/* Owner: on a completed trip that had a separate Driver (booking > Payment tab). Record what you paid the Driver.
   An online transfer is final at once; cash waits until the Driver confirms they received it. */
export function PayDriverPanel({ tripId }) {
  const [state, setState] = useState(null), [error, setError] = useState(null), [busy, setBusy] = useState(false)
  const [form, setForm] = useState({ amount: '', method: 'CASH', reference: '' })
  const load = () => api(`/trips/${tripId}/driver-payment`).then(setState).catch(setError)
  useEffect(() => { load() }, [tripId])
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError(null)
    try {
      await post(`/trips/${tripId}/driver-payment`, { amount: form.amount, method: form.method, reference: form.method === 'ONLINE' ? form.reference.trim() : null })
      setForm({ amount: '', method: 'CASH', reference: '' }); await load()
    } catch (err) { setError(err) } finally { setBusy(false) }
  }
  if (!state) return error ? <ErrorNotice error={error}/> : <p role="status">{t('Loading…')}</p>
  const payment = state.payment, live = payment && payment.status !== 'DECLINED'
  if (!live && !state.can_record) return null
  return <section className="flow-note" aria-label={t('Driver payment')}>
    <ErrorNotice error={error}/>
    <h2>{t('Pay your Driver')}</h2>
    {live && <p>
      <strong>{t('LKR')} {payment.amount}</strong> · {methodLabel(payment.method)}{payment.reference ? ` · ${payment.reference}` : ''}{' '}
      {payment.status === 'CONFIRMED' ? <Chip tone="success">{t('Confirmed')}</Chip> : <Chip tone="muted">{t('Waiting for the Driver to confirm the cash.')}</Chip>}
    </p>}
    {!live && <>
      {payment && payment.status === 'DECLINED' && <p role="status">{t('The Driver said the cash was not received: {value0}', { value0: payment.driver_note || '' })} {t('Record it again below.')}</p>}
      <Compact.Provider value={true}>
        <form onSubmit={submit}><fieldset disabled={busy} style={{ border: 0, padding: 0, margin: 0, display: 'grid', gap: 8 }}>
          <Field label="Amount" unit="LKR"><input name="amount" type="number" min="0.01" step="0.01" required inputMode="decimal" value={form.amount} onChange={e => setForm({ ...form, amount: e.target.value })}/></Field>
          <Field label="How did you pay?"><select name="method" value={form.method} onChange={e => setForm({ ...form, method: e.target.value })}>
            <option value="CASH">{t('Cash')}</option><option value="ONLINE">{t('Online transfer')}</option></select></Field>
          {form.method === 'ONLINE' && <Field label="Transfer reference"><input name="reference" required minLength={3} maxLength={80} value={form.reference} onChange={e => setForm({ ...form, reference: e.target.value })}/></Field>}
          <button type="submit" className="ui-button ui-button-primary">{busy ? t('Recording…') : t('Record payment')}</button>
        </fieldset></form>
      </Compact.Provider>
    </>}
  </section>
}

/* Driver: sidebar > Earnings. What your Owners recorded they paid you. Cash counts only after you confirm it. */
export default function DriverEarnings() {
  const [data, setData] = useState(null), [error, setError] = useState(null), [busy, setBusy] = useState(false)
  const [askId, setAskId] = useState(null), [note, setNote] = useState('')
  const rows = useRowCount(66)
  const items = data?.items || []
  const { slice, pager } = usePaged(items, Math.max(2, Math.min(rows, 4)))
  const load = () => api('/drivers/me/payments').then(setData).catch(setError)
  useEffect(() => { if (hasSession()) load() }, [])
  async function run(fn) {
    setBusy(true); setError(null)
    try { await fn(); setAskId(null); setNote(''); await load() } catch (err) { setError(err) } finally { setBusy(false) }
  }
  const confirm = p => run(() => post(`/driver-payments/${p.id}/confirm`))
  const decline = p => run(() => post(`/driver-payments/${p.id}/decline`, { note: note.trim() }))
  if (!hasSession()) return <Navigate to="/login" replace/>
  const totals = data?.totals
  return <><Header/><FlowShell heading={t('Earnings')} title={t('Payments from your Owners')} icon="wallet"
    info={t('Owners record what they paid you for each completed trip. Cash counts only after you confirm it.')}>
    <Compact.Provider value={true}>
      <ErrorNotice error={error}/>
      {totals && <p className="flow-note"><strong>{t('Confirmed')}</strong>: {t('LKR')} {totals.confirmed_total} · <strong>{t('Waiting for you')}</strong>: {t('LKR')} {totals.waiting_total}</p>}
      {data === null && !error && <p role="status">{t('Loading…')}</p>}
      {data && !items.length && <p className="flow-note" role="status">{t('No payments yet.')}</p>}
      <div className="vehicle-rows">{slice.map(p => <article className="trip-vehicle-card" key={p.id}>
        <h2>{t('LKR')} {p.amount}</h2>
        <p>{p.trip_reference} · {p.other_party?.name} · {displayTime(p.recorded_at)}</p>
        <p>{methodLabel(p.method)}{p.reference ? ` · ${p.reference}` : ''}{' '}
          {p.status === 'CONFIRMED' ? <Chip tone="success">{t('Confirmed')}</Chip> : <Chip tone="muted">{t('Waiting for your confirmation')}</Chip>}</p>
        {p.status === 'PENDING_DRIVER' && (askId === p.id
          ? <span className="vehicle-row-actions">
              <input aria-label={t('Tell the Owner what happened')} placeholder={t('Tell the Owner what happened')} maxLength={300} value={note} onChange={e => setNote(e.target.value)}/>
              <button type="button" className="ui-button ui-button-primary" disabled={busy || !note.trim()} onClick={() => decline(p)}>{t('Send')}</button>
              <button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={() => { setAskId(null); setNote('') }}>{t('Cancel')}</button></span>
          : <span className="vehicle-row-actions">
              <button type="button" className="ui-button ui-button-primary" disabled={busy} onClick={() => confirm(p)}>{t('Cash received')}</button>
              <button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={() => setAskId(p.id)}>{t('Not received')}</button></span>)}
      </article>)}</div>{items.length > 0 && pager}
    </Compact.Provider>
  </FlowShell></>
}
