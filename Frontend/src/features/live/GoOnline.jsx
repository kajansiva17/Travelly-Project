import { t } from '../../i18n/language.js'
import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../services/api'
import { useWorkspace } from '../../context/workspaceContext'
import { ErrorNotice } from '../../components/components'
import { Chip } from '../../components/ui'
import { FlowShell, StateCard } from '../booking/flow/FlowParts'
import TripInProgressCard from '../trips/TripInProgressCard'
import { useActiveTrips } from '../trips/tripHooks'
import { tripLink } from '../trips/tripLinks'
import { liveChanged, useLive } from './liveSender'

const REQUESTS_EVERY_MS = 4000

// Go online: the person's phone supplies the vehicle location (LiveLocationSender in the workspace sends it on every page).
// Used by a Driver (assigned vehicles) and by an Owner (own vehicles, self-drive). Ride requests from Book now arrive here.
export default function GoOnline() {
  const { role } = useWorkspace()
  const navigate = useNavigate()
  const live = useLive()
  const active = useActiveTrips()
  const [items, setItems] = useState(null)
  const [requests, setRequests] = useState([])
  const [error, setError] = useState(null)
  const [busyId, setBusyId] = useState('')

  const load = useCallback(async () => {
    try {
      const result = await api('/me/live-vehicles')
      setItems(result?.items || [])
      setError(null)
    } catch (problem) { setError(problem) }
  }, [])

  useEffect(() => { load() }, [load])

  const sending = (items || []).filter(item => item.sending)
  const sendingKey = sending.map(item => item.vehicle_id).join(',')

  useEffect(() => {
    if (!sendingKey) { setRequests([]); return undefined }
    let alive = true
    const read = async () => {
      try { const result = await api('/me/ride-requests'); if (alive) setRequests(result?.items || []) } catch { /* the next poll tries again */ }
    }
    read()
    const timer = setInterval(read, REQUESTS_EVERY_MS)
    return () => { alive = false; clearInterval(timer) }
  }, [sendingKey])

  async function respond(request, what) {
    setError(null)
    try {
      const result = await api(`/ride-now/requests/${request.id}/${what}`, { method: 'POST', body: '{}' })
      setRequests(current => current.filter(row => row.id !== request.id))
      // The trip opens on its pickup map at once; the dashboard card and this page bring the person back to it.
      if (what === 'accept' && result.trip_id) navigate(tripLink({ trip_id: result.trip_id, viewer_roles: ['DRIVER'] }, role))
    } catch (problem) { setError(problem); setRequests(current => current.filter(row => row.id !== request.id)) }
  }

  async function bookNowSwitch(item) {
    setError(null)
    try { await api(`/vehicles/${item.vehicle_id}/live/instant-booking`, { method: 'PATCH', body: JSON.stringify({ enabled: !item.instant_booking }) }); await load() }
    catch (problem) { setError(problem) }
  }

  async function toggle(item) {
    if (busyId) return
    setBusyId(item.vehicle_id); setError(null)
    try {
      await api(`/vehicles/${item.vehicle_id}/live/${item.sending ? 'offline' : 'online'}`, { method: 'POST', body: '{}' })
      await load()
    } catch (problem) { setError(problem); load() }
    finally { setBusyId(''); liveChanged() }
  }

  if (!items && !error) return <StateCard busy title={t('Loading vehicles')}/>
  if (!items) return <StateCard icon="alert" title={t('Vehicles unavailable')}><ErrorNotice error={error}/></StateCard>

  return <FlowShell title="Go online" icon="pin" heading="Live location"
    info={t('While you are online, your phone location is sent so nearby Passengers can find the vehicle. Keep Travelly open on your phone. The location is sent only while the app is open.')}>
    <div className="booking-pane">
      <TripInProgressCard items={active.items}/>
      {error && <ErrorNotice error={error}/>}
      {live.problem && sending.length > 0 && <p role="alert">{live.problem}</p>}
      {sending.length > 0 && <section aria-live="polite">
        <h3>{t('Ride requests')}</h3>
        {requests.length === 0 ? <p>{t('No ride requests right now.')}</p> : requests.map(request => <div key={request.id} className="dash-row" style={{ padding: '10px 0' }}>
          <div><strong>{request.pickup.label}</strong> → <strong>{request.destination.label}</strong></div>
          <div>{request.passenger_first_name} · {request.passenger_count} {t('Passengers')} · {t('Fare')} {request.fare} {request.currency} · {t('{seconds} s left', { seconds: request.seconds_left })}</div>
          <div className="flow-actions"><button type="button" onClick={() => respond(request, 'accept')}>{t('Accept')}</button><button type="button" onClick={() => respond(request, 'decline')}>{t('Decline')}</button></div>
        </div>)}
      </section>}
      {items.length === 0 ? <p>{t('No vehicle is available for you to take online.')}</p> : items.map(item => {
        const label = item.name || item.registration_number
        const last = live.sentAt[item.vehicle_id]
        return <section key={item.vehicle_id} className="dash-row" style={{ display: 'flex', gap: 12, alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', padding: '12px 0' }}>
          <div>
            <strong>{label}</strong> <span>{item.registration_number}</span>
            {item.owner_name && <div>{item.owner_name}</div>}
            <div><Chip tone={item.sending ? 'success' : 'default'}>{item.sending ? t('Online') : item.taken_by_someone_else ? t('Online with someone else') : t('Offline')}</Chip></div>
            {item.sending && last && <div>{t('Last location sent {time}', { time: last.toLocaleTimeString() })}</div>}
            {!item.ready && !item.sending && item.not_ready_reason && <div>{item.not_ready_reason}</div>}
          </div>
          {!item.owner_name && <button type="button" onClick={() => bookNowSwitch(item)}>{item.instant_booking ? t('Book now is on') : t('Book now is off')}</button>}
          <button type="button" disabled={busyId === item.vehicle_id || (!item.sending && (!item.ready || item.taken_by_someone_else))} onClick={() => toggle(item)}>
            {item.sending ? t('Go offline') : t('Go online')}
          </button>
        </section>
      })}
    </div>
  </FlowShell>
}
