import { t } from '../../i18n/language.js'
import { useEffect, useMemo, useState } from 'react'
import { api } from '../../services/api'
import { ErrorNotice } from '../../components/components'
import InfoTip from '../../components/ui/InfoTip'
import { FlowActions, FlowShell, StateCard } from '../booking/flow/FlowParts'

const sriLankaDay = date => `${date}T00:00:00+05:30`
const nextDay = date => {
  const value = new Date(`${date}T12:00:00Z`)
  value.setUTCDate(value.getUTCDate() + 1)
  return value.toISOString().slice(0, 10)
}
const today = () => new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Colombo' })

export default function Availability() {
  const [vehicles, setVehicles] = useState(null)
  const [vehicleId, setVehicleId] = useState('')
  const [date, setDate] = useState(today)
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
    if (!vehicleId || !date || busy) return
    setBusy(true); setError(null)
    try {
      await api(`/vehicles/${vehicleId}/availability-blocks`, { method: 'POST', body: JSON.stringify({ kind: 'PERSONAL', start_at: sriLankaDay(date), end_at: sriLankaDay(nextDay(date)), reason: 'Driver unavailable' }) })
      await load()
    } catch (problem) { setError(problem) }
    finally { setBusy(false) }
  }

  if (!vehicles && !error) return <StateCard busy title={t('Loading availability')}/>
  if (!vehicles) return <StateCard icon="alert" title={t('Availability unavailable')}><ErrorNotice error={error}/></StateCard>

  return <FlowShell title="Driver availability" icon="calendar" info={t('Mark a date unavailable only when you cannot drive the assigned vehicle. Existing protected bookings are never changed automatically.')}>
    <form className="booking-pane" onSubmit={block}>
      {error && <ErrorNotice error={error}/>}
      {vehicles.length === 0 ? <p>{t('No vehicle is assigned to you yet.')}</p> : <>
        <label>{t('Assigned vehicle')}<InfoTip>{t('Availability is recorded against the selected assigned vehicle.')}</InfoTip>
          <select value={vehicleId} onChange={event => setVehicleId(event.target.value)}>{vehicles.map(vehicle => <option key={vehicle.id} value={vehicle.id}>{vehicle.label || vehicle.reference}</option>)}</select>
        </label>
        <label>{t('Unavailable date')}<input type="date" min={today()} value={date} onChange={event => setDate(event.target.value)}/></label>
        <table><thead><tr>{days.map(day => <th key={day}>{new Date(`${day}T12:00:00Z`).toLocaleDateString(undefined, { weekday: 'short', day: 'numeric' })}</th>)}</tr></thead>
          <tbody><tr>{days.map(day => <td key={day}>{events.some(item => item.restricts && new Date(item.start_at) < new Date(sriLankaDay(nextDay(day))) && new Date(item.end_at) > new Date(sriLankaDay(day))) ? t('Unavailable') : t('Available')}</td>)}</tr></tbody>
        </table>
        <FlowActions><button type="button" disabled={busy} onClick={() => load()}>{t('Refresh')}</button><button type="submit" disabled={busy}>{busy ? t('Saving…') : t('Mark unavailable')}</button></FlowActions>
      </>}
    </form>
  </FlowShell>
}
