import { t } from '../../i18n/language.js'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../services/api'
import { useWorkspace } from '../../context/workspaceContext'
import { ErrorNotice, Icon } from '../../components/components'
import { FlowShell, StateCard } from '../booking/flow/FlowParts'
import TripInProgressCard from '../trips/TripInProgressCard'
import { useActiveTrips } from '../trips/tripHooks'
import { tripLink } from '../trips/tripLinks'
import { useLive } from './liveSender'
import { useLiveVehicles } from './liveVehicles'
import VehicleLiveCard from './VehicleLiveCard'

const REQUESTS_EVERY_MS = 4000

// Go online: the person's phone supplies the vehicle location (LiveLocationSender in the workspace sends it on every page).
// Used by a Driver (assigned vehicles) and by an Owner (own vehicles, self-drive). Ride requests from Book now arrive here.
// An Owner also finds each vehicle's Live tab under My vehicles.
export default function GoOnline() {
  const { role } = useWorkspace()
  const navigate = useNavigate()
  const live = useLive()
  const active = useActiveTrips()
  const { items, error, setError, busyId, toggle, bookNow } = useLiveVehicles()
  const [requests, setRequests] = useState([])

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

  if (!items && !error) return <StateCard busy title={t('Loading vehicles')}/>
  if (!items) return <StateCard icon="alert" title={t('Vehicles unavailable')}><ErrorNotice error={error}/></StateCard>

  return <FlowShell title="Go online" icon="pin" heading="Live location"
    info={t('While you are online, your phone location is sent so nearby Passengers can find the vehicle. Keep Travelly open on your phone. The location is sent only while the app is open.')}>
    <div className="booking-pane live-page">
      <TripInProgressCard items={active.items}/>
      {error && <ErrorNotice error={error}/>}
      {live.problem && sending.length > 0 && <p className="live-alert" role="alert"><Icon name="alert" size={16}/><span>{live.problem}</span></p>}
      {sending.length > 0 && <section className="live-requests" aria-live="polite">
        <h3>{t('Ride requests')}</h3>
        {requests.length === 0 ? <p className="live-empty">{t('No ride requests right now.')}</p> : requests.map(request => <div key={request.id} className="live-request">
          <div className="live-request-main">
            <div className="live-route"><strong>{request.pickup.label}</strong><Icon name="arrow" size={16}/><strong>{request.destination.label}</strong></div>
            <p>{request.passenger_first_name} · {request.passenger_count} {t('Passengers')} · {t('Fare')} {request.fare} {request.currency} · {t('{seconds} s left', { seconds: request.seconds_left })}</p>
          </div>
          <div className="live-actions"><button type="button" className="ui-button ui-button-primary" onClick={() => respond(request, 'accept')}>{t('Accept')}</button><button type="button" className="ui-button ui-button-secondary" onClick={() => respond(request, 'decline')}>{t('Decline')}</button></div>
        </div>)}
      </section>}
      {items.length === 0 ? <p className="live-empty">{t('No vehicle is available for you to take online.')}</p>
        : <div className="live-list">{items.map(item => <VehicleLiveCard key={item.vehicle_id} item={item} busy={busyId === item.vehicle_id} onToggle={() => toggle(item)} onBookNow={() => bookNow(item)}/>)}</div>}
    </div>
  </FlowShell>
}
