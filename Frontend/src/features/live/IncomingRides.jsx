import { t } from '../../i18n/language.js'
import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { api } from '../../services/api'
import { Icon } from '../../components/components'
import { tripLink } from '../trips/tripLinks'
import { useLive } from './liveSender'

const EVERY_MS = 5000

// A Book now request for a vehicle this person has online shows here on every page of the workspace (Dashboard included), with Accept and Decline,
// until it is answered or runs out. The Go online page lists the same requests itself, so the banner stays away from it.
export default function IncomingRides({ role }) {
  const live = useLive()
  const navigate = useNavigate()
  const place = useLocation()
  const [requests, setRequests] = useState([])
  const [problem, setProblem] = useState('')
  const key = (live.sendingIds || []).join(',')
  const onGoOnline = /\/go-online\/?$/.test(place.pathname)

  useEffect(() => {
    if (!key || onGoOnline) { setRequests([]); return undefined }
    let alive = true
    const read = async () => {
      try { const result = await api('/me/ride-requests', { cache: 'no-store' }); if (alive) setRequests(result?.items || []) } catch { /* the next poll tries again */ }
    }
    read()
    const timer = setInterval(() => { if (!document.hidden) read() }, EVERY_MS)
    return () => { alive = false; clearInterval(timer) }
  }, [key, onGoOnline])

  async function respond(request, what) {
    setProblem('')
    try {
      const result = await api(`/ride-now/requests/${request.id}/${what}`, { method: 'POST', body: '{}' })
      setRequests(current => current.filter(row => row.id !== request.id))
      if (what === 'accept' && result.trip_id) navigate(tripLink({ trip_id: result.trip_id, viewer_roles: ['DRIVER'] }, role))
    } catch (error) { setProblem(error?.message || t('The request could not be answered.')); setRequests(current => current.filter(row => row.id !== request.id)) }
  }

  if (!requests.length && !problem) return null
  return <div className="ride-banner" role="alert" aria-live="assertive">
    {requests.map(request => <div key={request.id} className="ride-banner-card">
      <div className="ride-banner-main">
        <strong className="ride-banner-title"><Icon name="pin" size={16}/>{t('New Book now request')}</strong>
        <div className="live-route"><strong>{request.pickup.label}</strong><Icon name="arrow" size={16}/><strong>{request.destination.label}</strong></div>
        <p>{request.passenger_first_name} · {request.passenger_count} {t('Passengers')} · {t('Fare')} {request.fare} {request.currency} · {t('{seconds} s left', { seconds: request.seconds_left })}</p>
      </div>
      <div className="live-actions"><button type="button" className="ui-button ui-button-primary" onClick={() => respond(request, 'accept')}>{t('Accept')}</button><button type="button" className="ui-button ui-button-secondary" onClick={() => respond(request, 'decline')}>{t('Decline')}</button></div>
    </div>)}
    {problem && <p className="live-alert">{problem}</p>}
  </div>
}
