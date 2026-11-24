import { t } from '../../i18n/language.js'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../services/api'
import { ErrorNotice } from '../../components/components'
import { FlowShell } from '../booking/flow/FlowParts'
import { PlaceSearch } from '../owner/OwnerRates'
import { TravellyField } from '../../components/TravellyVisualFoundation'
import { travelPath } from '../../routes/workspaceRoutes'

const POLL_MS = 3000
const place = value => value && ({ label: value.label, latitude: value.latitude, longitude: value.longitude, token: value.token })

// Passenger "Book now": stand at the pickup, choose where to go, see the online vehicles close by with their fare, pick one.
// Every ticked vehicle is asked at once; the first one to accept within 2 minutes takes the trip and the other requests are cancelled.
export default function NearbyNow() {
  const navigate = useNavigate()
  const [here, setHere] = useState(null)
  const [problem, setProblem] = useState('')
  const [destination, setDestination] = useState(null)
  const [passengers, setPassengers] = useState('1')
  const [journey, setJourney] = useState('ONE_WAY')
  const [saved, setSaved] = useState([])
  const [items, setItems] = useState(null)
  const [ticked, setTicked] = useState({})
  const [asked, setAsked] = useState(null)
  const [message, setMessage] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const stillHere = useRef(true)

  useEffect(() => () => { stillHere.current = false }, [])
  useEffect(() => { api('/me/saved-places', { cache: 'no-store' }).then(result => { if (stillHere.current) setSaved(result?.items || []) }).catch(() => {}) }, [])
  useEffect(() => {
    if (!navigator.geolocation) { setProblem(t('This device cannot share a location.')); return }
    navigator.geolocation.getCurrentPosition(result => setHere({ latitude: result.coords.latitude, longitude: result.coords.longitude }), failure => {
      setProblem(failure.code === 1
        ? t('Location is blocked. Allow location for this site in your browser, then try again.')
        : t('Your device could not find its location. Check that location is switched on.'))
    }, { enableHighAccuracy: true, timeout: 20000, maximumAge: 30000 })
  }, [])

  const find = useCallback(async () => {
    if (!here || !destination) return
    setBusy(true); setError(null)
    try {
      const result = await api('/ride-now/options', { method: 'POST', body: JSON.stringify({ pickup: here, destination: place(destination), passenger_count: Number(passengers), radius_km: 5, round_trip: journey === 'RETURN' }) })
      if (stillHere.current) { setItems(result?.items || []); setTicked(Object.fromEntries((result?.items || []).map(item => [item.vehicle_id, true]))) }
    } catch (failure) { setError(failure) }
    finally { setBusy(false) }
  }, [here, destination, passengers, journey])

  const chosen = (items || []).filter(item => ticked[item.vehicle_id])
  async function book() {
    if (!chosen.length) { setMessage(t('Choose at least one vehicle.')); return }
    setBusy(true); setError(null); setMessage('')
    try {
      const result = await api('/ride-now/requests/broadcast', { method: 'POST', body: JSON.stringify({ pickup: here, destination: place(destination), passenger_count: Number(passengers), round_trip: journey === 'RETURN', vehicles: chosen.map(item => ({ vehicle_id: item.vehicle_id, fare: item.fare })) }) })
      setAsked({ group_id: result.group_id, status: 'OPEN', asked: result.items.length, seconds_left: Math.max(0, ...result.items.map(row => row.seconds_left)), round_trip: journey === 'RETURN' })
    } catch (failure) { setError(failure); find() }
    finally { setBusy(false) }
  }

  useEffect(() => {
    if (!asked || asked.status !== 'OPEN') return undefined
    const timer = setInterval(async () => {
      try {
        const next = await api(`/ride-now/groups/${asked.group_id}`)
        if (!stillHere.current) return
        if (next.status === 'ACCEPTED' && next.accepted?.trip_id) { navigate(travelPath('PASSENGER', `/trips/${next.accepted.trip_id}/map`)); return }
        if (next.status === 'ENDED') {
          setMessage(next.ended_because === 'DECLINED' ? t('Every vehicle declined your request. Search again.')
            : next.ended_because === 'EXPIRED' ? t('No vehicle accepted in time. Search again.') : t('Your request was cancelled.'))
          setAsked(null); find()
        } else setAsked({ ...asked, status: 'OPEN', asked: next.asked, still_waiting: next.still_waiting, seconds_left: next.seconds_left })
      } catch (failure) { setError(failure) }
    }, POLL_MS)
    return () => clearInterval(timer)
  }, [asked?.group_id, asked?.status, navigate, find])

  async function cancel() {
    try { await api(`/ride-now/groups/${asked.group_id}/cancel`, { method: 'POST', body: '{}' }) } catch (failure) { setError(failure) }
    setAsked(null); find()
  }

  return <FlowShell title="Book now" icon="pin" heading="Travel & Booking"
    info={t('Choose where you are going. Vehicles shown are online close to you now, each with its own fare. Keep the ones you accept ticked; the first to accept takes your trip. Distances and minutes are approximate.')}>
    <div className="booking-pane">
      {error && <ErrorNotice error={error}/>}
      {problem && <p role="alert">{problem}</p>}
      {message && <p role="status">{message}</p>}
      {asked ? <section role="status">
        <strong>{t('Waiting for a vehicle to accept')}</strong>
        <div>{t('{count} vehicles asked. The first to accept takes your trip.', { count: asked.still_waiting ?? asked.asked })}</div>
        {asked.round_trip && <div>{t('Return trip')}</div>}
        <div>{t('{seconds} s left', { seconds: asked.seconds_left })}</div>
        <div className="flow-actions"><button type="button" onClick={cancel}>{t('Cancel request')}</button></div>
      </section> : <>
        {saved.length > 0 && <div className="flow-actions" role="group" aria-label={t('Saved Places')}>
          {saved.map(item => <button key={item.id} type="button" className="ui-button ui-button-secondary" onClick={() => { setDestination(item.place); setItems(null) }}>{item.name}</button>)}
        </div>}
        <PlaceSearch label="Destination" value={destination} onChange={value => { setDestination(value); setItems(null) }}/>
        <div className="flow-grid-2">
          <TravellyField label={t('Passengers')}>
            <select value={passengers} onChange={event => { setPassengers(event.target.value); setItems(null) }}>{Array.from({ length: 20 }, (_, index) => index + 1).map(count => <option key={count} value={count}>{count}</option>)}</select>
          </TravellyField>
          <TravellyField label={t('Journey')}>
            <select value={journey} onChange={event => { setJourney(event.target.value); setItems(null) }}>
              <option value="ONE_WAY">{t('One way')}</option>
              <option value="RETURN">{t('Return')}</option>
            </select>
          </TravellyField>
        </div>
        <div className="flow-actions"><button type="button" className="ui-button ui-button-primary" disabled={busy || !here || !destination} onClick={find}>{busy ? t('Searching…') : t('Find vehicles')}</button></div>
        {items && (items.length === 0 ? <p>{t('No vehicle is online near you right now.')}</p> : items.map(item => <section key={item.vehicle_id} className="dash-row" style={{ display: 'flex', gap: 12, justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', padding: '12px 0' }}>
          <div>
            <strong>{item.name || item.reference}</strong>
            <div>{item.seats} {t('seats')} · {item.distance_km}{' km · '}{t('{minutes} min away', { minutes: item.minutes_away })}</div>
            <div>{t('Fare')} {item.fare} {item.currency}</div>
            {item.rating && <div title={t('Passenger rating')}><span style={{ color: '#f5a623' }}>★</span> {item.rating.average} ({item.rating.count})</div>}
            {item.waiting && <div>{t('Free waiting: {free} min. After that LKR {hour} per hour (LKR {minute} per minute), for the time actually waited.', { free: item.waiting.free_minutes, hour: Number(item.waiting.hour_rate).toFixed(2), minute: (Number(item.waiting.hour_rate) / 60).toFixed(2) })}</div>}
          </div>
          <label><input type="checkbox" checked={Boolean(ticked[item.vehicle_id])} onChange={event => setTicked({ ...ticked, [item.vehicle_id]: event.target.checked })}/> {t('Ask this vehicle')}</label>
        </section>))}
        {items && items.length > 0 && <div className="flow-actions"><button type="button" className="ui-button ui-button-primary" disabled={busy || !chosen.length} onClick={book}>{t('Book now')}</button></div>}
      </>}
    </div>
  </FlowShell>
}
