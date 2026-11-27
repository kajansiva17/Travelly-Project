import { t } from '../../i18n/language.js'
import { useEffect, useMemo, useState } from 'react'
import { api } from '../../services/api'
import { ErrorNotice, Icon } from '../../components/components'
import Chip from '../../components/ui/Chip'
import { FlowShell, StateCard } from '../booking/flow/FlowParts'
import { Thumb } from '../booking/BookingCardParts'
import { EmptyCard } from '../people/PeopleParts'

const sriLankaDay = date => `${date}T00:00:00+05:30`
const nextDay = date => {
  const value = new Date(`${date}T12:00:00Z`)
  value.setUTCDate(value.getUTCDate() + 1)
  return value.toISOString().slice(0, 10)
}
const today = () => new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Colombo' })

/* Driver > Availability. The assigned vehicle as a card, the next seven days as day cards (green = free, red = blocked), and one button to block the chosen day. */
export default function Availability() {
  const [vehicles, setVehicles] = useState(null)
  const [vehicleId, setVehicleId] = useState('')
  const [date, setDate] = useState(today)
  const [picked, setPicked] = useState(today)
  const [events, setEvents] = useState([])
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const days = useMemo(() => Array.from({ length: 7 }, (_, index) => {
    const value = new Date(`${date}T12:00:00Z`)
    value.setUTCDate(value.getUTCDate() + index)
    return value.toISOString().slice(0, 10)
  }), [date])

  useEffect(() => {
    api('/drivers/me/vehicles').then(result => {
      const items = result?.items || []
      setVehicles(items)
      setVehicleId(current => current || items[0]?.id || '')
    }).catch(setError)
  }, [])

  async function load(id = vehicleId) {
    if (!id) return
    setError(null)
    try {
      const query = new URLSearchParams({ start_at: sriLankaDay(date), end_at: sriLankaDay(nextDay(days[6])) })
      const result = await api(`/vehicles/${id}/calendar?${query}`)
      setEvents(result?.events || [])
    } catch (problem) { setError(problem) }
  }

  useEffect(() => { if (vehicleId) load(vehicleId) }, [vehicleId, date])

  async function block(event) {
    event.preventDefault()
    if (!vehicleId || !picked || busy) return
    setBusy(true); setError(null)
    try {
      await api(`/vehicles/${vehicleId}/availability-blocks`, { method: 'POST', body: JSON.stringify({ kind: 'PERSONAL', start_at: sriLankaDay(picked), end_at: sriLankaDay(nextDay(picked)), reason: 'Driver unavailable' }) })
      await load()
    } catch (problem) { setError(problem) }
    finally { setBusy(false) }
  }

  if (!vehicles && !error) return <StateCard busy title={t('Loading availability')}/>
  if (!vehicles) return <StateCard icon="alert" title={t('Availability unavailable')}><ErrorNotice error={error}/></StateCard>

  const blocked = day => events.some(item => item.restricts && new Date(item.start_at) < new Date(sriLankaDay(nextDay(day))) && new Date(item.end_at) > new Date(sriLankaDay(day)))
  const vehicle = vehicles.find(v => v.id === vehicleId) || vehicles[0]
  const dayText = day => new Date(`${day}T12:00:00Z`).toLocaleDateString(undefined, { weekday: 'short', day: 'numeric', month: 'short', timeZone: 'UTC' })

  return <FlowShell title="Driver availability" icon="calendar" info={t('Mark a date unavailable only when you cannot drive the assigned vehicle. Existing protected bookings are never changed automatically.')}>
    <form className="flow-wizard-form booking-pane av-pane" onSubmit={block}>
      {error && <ErrorNotice error={error}/>}
      {vehicles.length === 0 ? <EmptyCard icon="car" title={t('No vehicle is assigned to you yet.')}>{t('When an Owner assigns you a vehicle, you can mark the days you cannot drive it here.')}</EmptyCard> : <>
        {vehicles.length > 1
          ? <div className="bk-groups" role="tablist" aria-label={t('Assigned vehicle')}>{vehicles.map(v => <Chip key={v.id} selected={v.id === vehicleId} onClick={() => setVehicleId(v.id)}>{v.label || v.reference}</Chip>)}</div>
          : <section className="bc-card av-vehicle"><Thumb src={vehicle?.profile_image_url} icon="car" size={56}/><div className="bc-body"><span className="bc-sub">{t('Assigned vehicle')}</span><strong className="bc-name">{vehicle?.label || vehicle?.reference}</strong></div></section>}
        <div className="av-bar"><label className="av-from">{t('Show from')}<input type="date" min={today()} value={date} onChange={event => { setDate(event.target.value); setPicked(event.target.value) }}/></label>
          <button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={() => load()}>{t('Refresh')}</button></div>
        <div className="av-days" role="group" aria-label={t('Unavailable date')}>{days.map(day => {
          const off = blocked(day), on = picked === day
          return <button type="button" key={day} className={'bc-card av-day' + (off ? ' is-off' : ' is-free') + (on ? ' is-picked' : '')} aria-pressed={on} disabled={off || day < today()} onClick={() => setPicked(day)}>
            <strong>{new Date(`${day}T12:00:00Z`).toLocaleDateString(undefined, { weekday: 'short', timeZone: 'UTC' })}</strong>
            <span className="av-num">{new Date(`${day}T12:00:00Z`).getUTCDate()}</span>
            <Chip tone={off ? 'danger' : 'success'}>{off ? t('Unavailable') : t('Available')}</Chip></button>
        })}</div>
        <div className="av-foot"><span className="bc-sub"><Icon name="calendar" size={14}/> {picked ? dayText(picked) : ''}</span>
          <button type="submit" className="ui-button ui-button-primary" disabled={busy || !picked || blocked(picked)}>{busy ? t('Saving…') : t('Mark unavailable')}</button></div>
      </>}
    </form>
  </FlowShell>
}
