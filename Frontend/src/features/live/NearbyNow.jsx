import { t } from '../../i18n/language.js'
import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../services/api'
import { ErrorNotice } from '../../components/components'
import { FlowShell, StateCard } from '../booking/flow/FlowParts'

// Passenger: vehicles that are online right now near the phone, nearest first.
// Booking itself stays the normal hire flow.
export default function NearbyNow() {
  const [radius, setRadius] = useState('5')
  const [items, setItems] = useState(null)
  const [error, setError] = useState(null)
  const [problem, setProblem] = useState('')
  const [busy, setBusy] = useState(true)

  const find = useCallback(() => {
    setBusy(true); setError(null); setProblem('')
    if (!navigator.geolocation) { setProblem(t('This device cannot share a location.')); setBusy(false); return }
    navigator.geolocation.getCurrentPosition(async result => {
      try {
        const query = new URLSearchParams({ latitude: String(result.coords.latitude), longitude: String(result.coords.longitude), radius_km: radius })
        const found = await api(`/hire/nearby-now?${query}`)
        setItems(found?.items || [])
      } catch (failure) { setError(failure) }
      finally { setBusy(false) }
    }, failure => {
      setProblem(failure.code === 1
        ? t('Location is blocked. Allow location for this site in your browser, then try again.')
        : t('Your device could not find its location. Check that location is switched on.'))
      setBusy(false)
    }, { enableHighAccuracy: true, timeout: 20000, maximumAge: 30000 })
  }, [radius])

  useEffect(() => { find() }, [find])

  if (busy && !items) return <StateCard busy title={t('Looking for vehicles near you')}/>

  return <FlowShell title="Nearby now" icon="pin" heading="Travel & Booking"
    info={t('Vehicles shown here are online and have sent their location in the last few minutes. Distances and minutes are approximate.')}>
    <div className="booking-pane">
      {error && <ErrorNotice error={error}/>}
      {problem && <p role="alert">{problem}</p>}
      <label>{t('Search distance')}
        <select value={radius} onChange={event => setRadius(event.target.value)}>
          {['3', '5', '10', '20'].map(km => <option key={km} value={km}>{km} km</option>)}
        </select>
      </label>
      {items && (items.length === 0 ? <p>{t('No vehicle is online near you right now.')}</p> : items.map(item => <section key={item.vehicle_id} className="dash-row" style={{ display: 'flex', gap: 12, justifyContent: 'space-between', flexWrap: 'wrap', padding: '12px 0' }}>
        <div>
          <strong>{item.name || item.reference}</strong>
          <div>{item.seats} {t('seats')} · {item.distance_km} km · {t('{minutes} min away', { minutes: item.minutes_away })}</div>
        </div>
      </section>))}
      <div className="flow-actions">
        <button type="button" disabled={busy} onClick={find}>{busy ? t('Searching…') : t('Refresh')}</button>
        <Link className="ui-button ui-button-primary" to="/hire">{t('Hire a vehicle')}</Link>
      </div>
    </div>
  </FlowShell>
}
