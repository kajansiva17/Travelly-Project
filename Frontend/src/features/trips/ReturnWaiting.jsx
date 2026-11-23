import { t } from '../../i18n/language.js'
import { useCallback, useEffect, useState } from 'react'
import { api } from '../../services/api'
import { Button } from '../../components/ui'
import { ErrorNotice } from '../../components/components'
import { usePoll } from './usePoll'

const money = value => (Math.round(value * 100) / 100).toFixed(2)
const RUNNING = ['IN_PROGRESS', 'BREAKDOWN', 'ASSISTANCE_REQUIRED']

// Book now return trip: the free waiting minutes and the waiting rate are shown up front, then the waiting is timed. The Passenger never chooses a waiting time;
// the person driving taps "Waiting started" at the destination and "Return started" when the Passenger comes back. Only the minutes after the free ones are charged.
export default function ReturnWaiting({ tripId, trip: given, operator = false, onChanged }) {
  const [own, setOwn] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const [now, setNow] = useState(Date.now())
  const read = useCallback(async () => {
    try { setOwn(await api(`/trips/${encodeURIComponent(tripId)}`, { cache: 'no-store' })) } catch { /* the next read tries again */ }
  }, [tripId])
  useEffect(() => { if (!given && tripId) read() }, [given, tripId, read])
  usePoll(read, !given && Boolean(tripId), 15000)
  const trip = given || own
  const wait = trip?.wait
  useEffect(() => {
    if (wait?.state !== 'WAITING') return undefined
    const timer = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(timer)
  }, [wait?.state])
  if (!wait) return null

  const free = Number(wait.free_minutes)
  const hourRate = Number(wait.hour_rate)
  const minutes = wait.state === 'WAITING' ? Math.max(0, (now - Date.parse(wait.started_at)) / 60000) : Number(wait.minutes)
  const charge = wait.state === 'RETURNING' ? Number(wait.charge) : Math.max(0, minutes - free) / 60 * hourRate
  const running = RUNNING.includes(trip.status)

  async function step(action, extra = {}) {
    setBusy(true); setError(null)
    try {
      await api(`/trips/${encodeURIComponent(trip.id)}/${action}`, { method: 'POST', body: JSON.stringify({ expected_version: trip.version, ...extra }) })
      if (onChanged) await onChanged(); else await read()
    } catch (failure) { setError(failure) }
    finally { setBusy(false) }
  }

  return <section role="status" className="dash-row" style={{ padding: '12px 0' }}>
    <strong>{t('Return trip')}</strong>
    <div>{t('Free waiting: {free} min. After that LKR {hour} per hour (LKR {minute} per minute), for the time actually waited.', { free: wait.free_minutes, hour: money(hourRate), minute: money(hourRate / 60) })}</div>
    {wait.state === 'WAITING' && <>
      <div>{t('Waiting time: {minutes} min', { minutes: minutes.toFixed(1) })}</div>
      <div>{minutes < free ? t('Still free: {minutes} min', { minutes: (free - minutes).toFixed(1) }) : t('Waiting charge so far: LKR {charge}', { charge: money(charge) })}</div>
    </>}
    {wait.state === 'MOVED' && <>
      <div>{t('Waiting time: {minutes} min', { minutes: minutes.toFixed(1) })}</div>
      <div>{operator ? t('The vehicle moved away from the waiting spot. Is the waiting over?') : t('The vehicle moved away. The Driver is confirming whether the waiting is over. The waiting time stopped when it left.')}</div>
    </>}
    {wait.state === 'RETURNING' && <div>{t('Waiting finished: {minutes} min · charge LKR {charge}', { minutes: minutes.toFixed(1), charge: money(charge) })}</div>}
    {wait.source === 'GPS' && <div>{t('Ended automatically when the vehicle moved away.')}</div>}
    {wait.source === 'MANUAL' && <div>{t('Added by the Driver without the timer.')}</div>}
    <div>{t('The waiting charge is added to the fare and paid after the trip.')}</div>
    {error && <ErrorNotice error={error}/>}
    {operator && running && wait.state === 'NOT_STARTED' && <div className="flow-actions"><Button disabled={busy} onClick={() => step('wait/start')}>{t('Waiting started')}</Button></div>}
    {operator && running && wait.state === 'MOVED' && <div className="flow-actions">
      <Button disabled={busy} onClick={() => step('wait/answer', { still_waiting: false })}>{t('Passenger is back')}</Button>
      <Button variant="secondary" disabled={busy} onClick={() => step('wait/answer', { still_waiting: true })}>{t('Still waiting')}</Button>
    </div>}
    {operator && running && wait.state === 'WAITING' && <div className="flow-actions"><Button disabled={busy} onClick={() => step('wait/end')}>{t('Return started')}</Button></div>}
  </section>
}
