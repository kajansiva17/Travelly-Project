import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { t } from '../../i18n/language.js'
import { api, hasSession } from '../../services/api'
import { Header, ErrorNotice } from '../../components/components'
import { FlowShell } from '../booking/flow/FlowParts'
import { EmptyCard, PersonCard, StatStrip } from '../people/PeopleParts'
import { DriverReportPane } from '../reports/DriverReport'
import { Field, Compact } from '../owner/OwnerRates'
import Chip from '../../components/ui/Chip'
import { displayTime } from '../../hooks/workspaceData'
import '../../styles/rates.css'

const post = (path, body) => api(path, { method: 'POST', body: JSON.stringify(body || {}) })
const methodLabel = method => method === 'CASH' ? t('Cash') : t('Online transfer')

const todayIso = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}` }

/* The form to record what the Owner paid one Driver for one completed trip. An Owner may pay days after the trip, so the day paid is chosen (today by default). */
function PayForm({ tripId, onDone }) {
  const [busy, setBusy] = useState(false), [error, setError] = useState(null)
  const [form, setForm] = useState({ amount: '', method: 'CASH', reference: '', paidOn: todayIso() })
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError(null)
    try {
      await post(`/trips/${tripId}/driver-payment`, { amount: form.amount, method: form.method, reference: form.method === 'ONLINE' ? form.reference.trim() : null, paid_on: form.paidOn || null })
      await onDone()
    } catch (err) { setError(err) } finally { setBusy(false) }
  }
  return <Compact.Provider value={true}>
    <ErrorNotice error={error}/>
    <form onSubmit={submit}><fieldset disabled={busy} style={{ border: 0, padding: 0, margin: 0, display: 'grid', gap: 8 }}>
      <Field label="Amount" unit="LKR"><input name="amount" type="number" min="0.01" step="0.01" required inputMode="decimal" value={form.amount} onChange={e => setForm({ ...form, amount: e.target.value })}/></Field>
      <Field label="How did you pay?"><select name="method" value={form.method} onChange={e => setForm({ ...form, method: e.target.value })}>
        <option value="CASH">{t('Cash')}</option><option value="ONLINE">{t('Online transfer')}</option></select></Field>
      {form.method === 'ONLINE' && <Field label="Transfer reference"><input name="reference" required minLength={3} maxLength={80} value={form.reference} onChange={e => setForm({ ...form, reference: e.target.value })}/></Field>}
      <Field label="Paid on"><input name="paidOn" type="date" required max={todayIso()} value={form.paidOn} onChange={e => setForm({ ...form, paidOn: e.target.value })}/></Field>
      <button type="submit" className="ui-button ui-button-primary">{busy ? t('Recording…') : t('Record payment')}</button>
    </fieldset></form>
  </Compact.Provider>
}

/* Owner: on a completed trip that had a separate Driver (booking > Payment tab). Record what you paid the Driver.
   An online transfer is final at once; cash waits until the Driver confirms they received it. */
export function PayDriverPanel({ tripId }) {
  const [state, setState] = useState(null), [error, setError] = useState(null)
  const load = () => api(`/trips/${tripId}/driver-payment`).then(setState).catch(setError)
  useEffect(() => { load() }, [tripId])
  if (!state) return error ? <ErrorNotice error={error}/> : <p role="status">{t('Loading…')}</p>
  const payment = state.payment, live = payment && payment.status !== 'DECLINED'
  if (!live && !state.can_record) return null
  return <section className="flow-note" aria-label={t('Driver payment')}>
    <h2>{t('Pay your Driver')}</h2>
    {live && <p>
      <strong>{t('LKR')} {payment.amount}</strong> · {methodLabel(payment.method)}{payment.reference ? ` · ${payment.reference}` : ''} · {t('Paid on')} {payment.paid_on}{' '}
      {payment.status === 'CONFIRMED' ? <Chip tone="success">{t('Confirmed')}</Chip> : <Chip tone="muted">{t('Waiting for the Driver to confirm the cash.')}</Chip>}
    </p>}
    {!live && <>
      {payment && payment.status === 'DECLINED' && <p role="status">{t('The Driver said the cash was not received: {value0}', { value0: payment.driver_note || '' })} {t('Record it again below.')}</p>}
      <PayForm tripId={tripId} onDone={load}/>
    </>}
  </section>
}

/* Owner: My drivers > Pay Drivers tab. Completed trips that had a separate Driver and are not paid yet, and what was already paid.
   The Owner may pay days after the trip; record it here whenever it is paid. Shown inside the My drivers page, so the tab bar stays. */
export function PayDriversPane() {
  const [due, setDue] = useState(null), [paid, setPaid] = useState(null), [error, setError] = useState(null), [sub, setSub] = useState(0), [openId, setOpenId] = useState(null)
  const load = () => Promise.all([api('/owners/me/driver-payments/due'), api('/owners/me/driver-payments')])
    .then(([d, p]) => { setDue(d); setPaid(p); setOpenId(null); setError(null) }).catch(setError)
  useEffect(() => { if (hasSession()) load() }, [])
  const dueItems = due?.items || [], paidItems = paid?.items || [], loading = (due === null || paid === null) && !error, totals = paid?.totals
  const shown = sub === 0 ? dueItems : paidItems
  return <>
    <ErrorNotice error={error}/>
    <div className="bk-groups" role="tablist"><Chip selected={sub === 0} onClick={() => setSub(0)}>{t('Drivers to pay')} ({dueItems.length})</Chip><Chip selected={sub === 1} onClick={() => setSub(1)}>{t('Paid')} ({paidItems.length})</Chip></div>
    {sub === 1 && totals && <StatStrip items={[{ icon: 'check', tone: 'success', label: t('Confirmed'), value: `${t('LKR')} ${totals.confirmed_total}` }, { icon: 'clock', tone: 'warning', label: t('Waiting for the Driver'), value: `${t('LKR')} ${totals.waiting_total}` }]}/>}
    {loading && <p role="status">{t('Loading…')}</p>}
    {!loading && !error && !shown.length && <EmptyCard icon="wallet" title={sub === 0 ? t('Nothing is waiting to be paid to a Driver.') : t('No Driver payments recorded yet.')}/>}
    {shown.length > 0 && <div className="bk-list pl-list">{sub === 0 ? dueItems.map(item => <PersonCard key={item.trip_id} name={item.driver?.name || t('Driver')} photo={item.driver?.profile_image_url} icon="wallet"
      lines={[item.trip_reference, displayTime(item.trip_date), item.declined_note && t('The Driver said the cash was not received: {value0}', { value0: item.declined_note })]}
      chips={item.declined_note ? <Chip tone="danger">{t('Cash not received')}</Chip> : <Chip tone="warning">{t('To pay')}</Chip>}
      actions={openId === item.trip_id ? null : <button type="button" className="ui-button ui-button-primary" onClick={() => setOpenId(item.trip_id)}>{t('Pay Driver')}</button>}
      extra={openId === item.trip_id ? <div className="pl-payform"><PayForm tripId={item.trip_id} onDone={load}/><button type="button" className="ui-button ui-button-secondary" onClick={() => setOpenId(null)}>{t('Cancel')}</button></div> : null}/>)
      : paidItems.map(p => <PersonCard key={p.id} name={p.other_party?.name || t('Driver')} photo={p.other_party?.profile_image_url} icon="wallet" tone={p.status === 'CONFIRMED' ? 'paid' : 'waiting'}
        lines={[`${p.trip_reference} · ${t('Paid on')} ${p.paid_on}`, `${methodLabel(p.method)}${p.reference ? ` · ${p.reference}` : ''}`]}
        actions={<><strong className="bc-price">{t('LKR')} {p.amount}</strong>{p.status === 'CONFIRMED' ? <Chip tone="success">{t('Confirmed')}</Chip> : <Chip tone="muted">{t('Waiting for the Driver to confirm the cash.')}</Chip>}</>}/>)}</div>}
  </>
}

const EARN_GROUPS = [['Waiting for you', 'PENDING_DRIVER', 'warning'], ['Confirmed', 'CONFIRMED', 'success'], ['Not received', 'DECLINED', 'danger']]

/* Driver: sidebar > Earnings. What your Owners recorded they paid you, in groups, with the Monthly report as a tab beside it.
   Cash counts only after you confirm it. */
export default function DriverEarnings({ initialTab = 0 }) {
  const [data, setData] = useState(null), [error, setError] = useState(null), [busy, setBusy] = useState(false), [tab, setTab] = useState(initialTab)
  const [askId, setAskId] = useState(null), [note, setNote] = useState(''), [group, setGroup] = useState(0), [picked, setPicked] = useState(false)
  const items = data?.items || []
  const load = () => api('/drivers/me/payments').then(setData).catch(setError)
  useEffect(() => { if (hasSession()) load() }, [])
  async function run(fn) {
    setBusy(true); setError(null)
    try { await fn(); setAskId(null); setNote(''); await load() } catch (err) { setError(err) } finally { setBusy(false) }
  }
  const confirm = p => run(() => post(`/driver-payments/${p.id}/confirm`))
  const decline = p => run(() => post(`/driver-payments/${p.id}/decline`, { note: note.trim() }))
  if (!hasSession()) return <Navigate to="/login" replace/>
  const totals = data?.totals, inGroup = i => items.filter(p => p.status === EARN_GROUPS[i][1])
  const active = picked ? group : Math.max(0, EARN_GROUPS.findIndex((_, i) => inGroup(i).length)), shown = inGroup(active)
  return <><Header/><FlowShell heading={t('Earnings')} title={tab === 0 ? t('Payments from your Owners') : t('Monthly report')} icon={tab === 0 ? 'wallet' : 'chart'}
    info={tab === 0 ? t('Owners record what they paid you for each completed trip. Cash counts only after you confirm it.') : t('Your trips and the payments your Owners recorded for one month.')}
    tabs={[{ label: t('Payments'), icon: 'wallet', active: tab === 0, onClick: () => setTab(0) }, { label: t('Monthly report'), icon: 'chart', active: tab === 1, onClick: () => setTab(1) }]}>
    <Compact.Provider value={true}>
      {tab === 0 && <div className="flow-wizard-form booking-pane">
        <ErrorNotice error={error}/>
        {totals && <StatStrip items={[{ icon: 'check', tone: 'success', label: t('Confirmed'), value: `${t('LKR')} ${totals.confirmed_total}` }, { icon: 'clock', tone: 'warning', label: t('Waiting for you'), value: `${t('LKR')} ${totals.waiting_total}` }]}/>}
        <div className="bk-groups" role="tablist">{EARN_GROUPS.map(([label], i) => <Chip key={label} selected={active === i} onClick={() => { setGroup(i); setPicked(true) }}>{t(label)} ({inGroup(i).length})</Chip>)}</div>
        {data === null && !error && <p role="status">{t('Loading…')}</p>}
        {data && !shown.length && <EmptyCard icon="wallet" title={items.length ? t('Nothing in this tab yet.') : t('No payments yet.')}>{!items.length && t('When an Owner records a payment for a completed trip, it shows up here.')}</EmptyCard>}
        {shown.length > 0 && <div className="bk-list pl-list">{shown.map(p => <PersonCard key={p.id} name={p.other_party?.name || t('Owner')} photo={p.other_party?.profile_image_url} icon="wallet" tone={p.status === 'CONFIRMED' ? 'paid' : p.status === 'DECLINED' ? 'failed' : 'waiting'}
          lines={[`${p.trip_reference} · ${t('Paid on')} ${p.paid_on}`, `${methodLabel(p.method)}${p.reference ? ` · ${p.reference}` : ''}`]}
          actions={<><strong className="bc-price">{t('LKR')} {p.amount}</strong>{p.status === 'CONFIRMED' ? <Chip tone="success">{t('Confirmed')}</Chip> : p.status === 'DECLINED' ? <Chip tone="danger">{t('Not received')}</Chip> : <Chip tone="warning">{t('Waiting for your confirmation')}</Chip>}</>}
          extra={p.status === 'PENDING_DRIVER' ? (askId === p.id
            ? <div className="pl-payform is-row"><input aria-label={t('Tell the Owner what happened')} placeholder={t('Tell the Owner what happened')} maxLength={300} value={note} onChange={e => setNote(e.target.value)}/>
                <button type="button" className="ui-button ui-button-primary" disabled={busy || !note.trim()} onClick={() => decline(p)}>{t('Send')}</button>
                <button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={() => { setAskId(null); setNote('') }}>{t('Cancel')}</button></div>
            : <div className="pl-payform is-row"><button type="button" className="ui-button ui-button-primary" disabled={busy} onClick={() => confirm(p)}>{t('Cash received')}</button>
                <button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={() => setAskId(p.id)}>{t('Not received')}</button></div>) : null}/>)}</div>}
      </div>}
      {tab === 1 && <DriverReportPane/>}
    </Compact.Provider>
  </FlowShell></>
}
