import { t } from '../../i18n/language.js'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../services/api'
import { ErrorNotice } from '../../components/components'
import { FlowShell } from '../booking/flow/FlowParts'
import { PlaceSearch } from '../owner/OwnerRates'
import { travelPath } from '../../routes/workspaceRoutes'

const POLL_MS = 3000
const place = value => value && ({ label: value.label, latitude: value.latitude, longitude: value.longitude, token: value.token })

// Passenger "Book now": stand at the pickup, choose where to go, see the online vehicles close by with their fare, pick one.
// The person sending that vehicle's location accepts within 90 seconds; then the booking is confirmed.
export default function NearbyNow() {
  const navigate = useNavigate()
  const [here, setHere] = useState(null)
  const [problem, setProblem] = useState('')
  const [destination, setDestination] = useState(null)
  const [passengers, setPassengers] = useState('1')
  const [journey, setJourney] = useState('ONE_WAY')
  const [saved, setSaved] = useState([])
  const [items, setItems] = useState(null)
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
      if (stillHere.current) setItems(result?.items || [])
    } catch (failure) { setError(failure) }
    finally { setBusy(false) }
  }, [here, destination, passengers, journey])

  async function book(item) {
    setBusy(true); setError(null); setMessage('')
    try {
      const result = await api('/ride-now/requests', { method: 'POST', body: JSON.stringify({ vehicle_id: item.vehicle_id, pickup: here, destination: place(destination), passenger_count: Number(passengers), fare: item.fare, round_trip: journey === 'RETURN' }) })
      setAsked(result)
    } catch (failure) { setError(failure); find() }
    finally { setBusy(false) }
  }

  useEffect(() => {
    if (!asked || asked.status !== 'OFFERED') return undefined
    const timer = setInterval(async () => {
      try {
        const next = await api(`/ride-now/requests/${asked.id}`)
        if (!stillHere.current) return
        if (next.status === 'ACCEPTED' && next.trip_id) { navigate(travelPath('PASSENGER', `/trips/${next.trip_id}/map`)); return }
        if (next.status !== 'OFFERED') {
          setMessage(next.status === 'DECLINED' ? t('The vehicle declined your request. Choose another one.')
            : next.status === 'EXPIRED' ? t('The vehicle did not accept in time. Choose another one.') : t('Your request was cancelled.'))
          setAsked(null); find()
        } else setAsked(next)
      } catch (failure) { setError(failure) }
    }, POLL_MS)
    return () => clearInterval(timer)
  }, [asked?.id, asked?.status, navigate, find])

  async function cancel() {
    try { await api(`/ride-now/requests/${asked.id}/cancel`, { method: 'POST', body: '{}' }) } catch (failure) { setError(failure) }
    setAsked(null); find()
  }

  return <FlowShell title="Book now" icon="pin" heading="Travel & Booking"
    info={t('Choose where you are going. Vehicles shown are online close to you now, each with its own fare. Pick one and wait for the driver to accept. Distances and minutes are approximate.')}>
    <div className="booking-pane">
      {error && <ErrorNotice error={error}/>}
      {problem && <p role="alert">{problem}</p>}
      {message && <p role="status">{message}</p>}
      {asked ? <section role="status">
        <strong>{t('Waiting for the vehicle to accept')}</strong>
        <div>{asked.vehicle?.name || asked.vehicle?.registration_number} · {t('Fare')} {asked.fare} {asked.currency}</div>
        {asked.round_trip && <div>{t('Return trip')}</div>}
        <div>{t('{seconds} s left', { seconds: asked.seconds_left })}</div>
        <div className="flow-actions"><button type="button" onClick={cancel}>{t('Cancel request')}</button></div>
      </section> : <>
        {saved.length > 0 && <div className="flow-actions" role="group" aria-label={t('Saved Places')}>
          {saved.map(item => <button key={item.id} type="button" className="ui-button ui-button-secondary" onClick={() => { setDestination(item.place); setItems(null) }}>{item.name}</button>)}
        </div>}
        <PlaceSearch label="Destination" value={destination} onChange={value => { setDestination(value); setItems(null) }}/>
        <label>{t('Passengers')}
          <select value={passengers} onChange={event => { setPassengers(event.target.value); setItems(null) }}>{[1, 2, 3, 4, 5, 6].map(count => <option key={count} value={count}>{count}</option>)}</select>
        </label>
        <label>{t('Journey')}
          <select value={journey} onChange={event => { setJourney(event.target.value); setItems(null) }}>
            <option value="ONE_WAY">{t('One way')}</option>
            <option value="RETURN">{t('Return')}</option>
          </select>
        </label>
        <div className="flow-actions"><button type="button" disabled={busy || !here || !destination} onClick={find}>{busy ? t('Searching…') : t('Find vehicles')}</button></div>
        {items && (items.length === 0 ? <p>{t('No vehicle is online near you right now.')}</p> : items.map(item => <section key={item.vehicle_id} className="dash-row" style={{ display: 'flex', gap: 12, justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', padding: '12px 0' }}>
          <div>
            <strong>{item.name || item.reference}</strong>
            <div>{item.seats} {t('seats')} · {item.distance_km}{' km · '}{t('{minutes} min away', { minutes: item.minutes_away })}</div>
            <div>{t('Fare')} {item.fare} {item.currency}</div>
            {item.rating && <div title={t('Passenger rating')}><span style={{ color: '#f5a623' }}>★</span> {item.rating.average} ({item.rating.count})</div>}
            {item.waiting && <div>{t('Free waiting: {free} min. After that LKR {hour} per hour (LKR {minute} per minute), for the time actually waited.', { free: item.waiting.free_minutes, hour: Number(item.waiting.hour_rate).toFixed(2), minute: (Number(item.waiting.hour_rate) / 60).toFixed(2) })}</div>}
          </div>
          <button type="button" disabled={busy} onClick={() => book(item)}>{t('Book now')}</button>
        </section>))}
      </>}
    </div>
  </FlowShell>
}
