import { t } from '../../i18n/language.js'
import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../../services/api'
import { ErrorNotice } from '../../components/components'
import { Chip } from '../../components/ui'
import { FlowShell, StateCard } from '../booking/flow/FlowParts'

const SEND_EVERY_MS = 30000

// Go online: the person's phone supplies the vehicle location while this page is open.
// Used by a Driver (assigned vehicles) and by an Owner (own vehicles, self-drive).
export default function GoOnline() {
  const [items, setItems] = useState(null)
  const [error, setError] = useState(null)
  const [geoProblem, setGeoProblem] = useState('')
  const [busyId, setBusyId] = useState('')
  const [sentAt, setSentAt] = useState({})
  const position = useRef(null)
  const sendingIds = useRef([])

  const load = useCallback(async () => {
    try {
      const result = await api('/me/live-vehicles')
      setItems(result?.items || [])
      setError(null)
    } catch (problem) { setError(problem) }
  }, [])

  useEffect(() => { load() }, [load])

  const sending = (items || []).filter(item => item.sending)
  sendingIds.current = sending.map(item => item.vehicle_id)
  const sendingKey = sendingIds.current.join(',')

  const push = useCallback(async () => {
    const fix = position.current
    if (!fix || !sendingIds.current.length) return
    for (const id of sendingIds.current) {
      try {
        await api(`/vehicles/${id}/live/location`, { method: 'PUT', body: JSON.stringify(fix) })
        setSentAt(current => ({ ...current, [id]: new Date() }))
      } catch (problem) {
        setError(problem)
        load()
      }
    }
  }, [load])

  useEffect(() => {
    if (!sendingKey) { position.current = null; return undefined }
    if (!navigator.geolocation) { setGeoProblem(t('This device cannot share a location.')); return undefined }
    setGeoProblem('')
    let first = true
    const watch = navigator.geolocation.watchPosition(result => {
      position.current = {
        latitude: result.coords.latitude,
        longitude: result.coords.longitude,
        accuracy_m: Math.min(1000, Math.round(result.coords.accuracy || 0))
      }
      if (first) { first = false; push() }
    }, problem => {
      setGeoProblem(problem.code === 1
        ? t('Location is blocked. Allow location for this site in your browser, then try again.')
        : t('Your device could not find its location. Check that location is switched on.'))
    }, { enableHighAccuracy: true, maximumAge: 10000, timeout: 30000 })
    const timer = setInterval(push, SEND_EVERY_MS)
    return () => { navigator.geolocation.clearWatch(watch); clearInterval(timer) }
  }, [sendingKey, push])

  async function toggle(item) {
    if (busyId) return
    setBusyId(item.vehicle_id); setError(null)
    try {
      await api(`/vehicles/${item.vehicle_id}/live/${item.sending ? 'offline' : 'online'}`, { method: 'POST', body: '{}' })
      await load()
    } catch (problem) { setError(problem); load() }
    finally { setBusyId('') }
  }

  if (!items && !error) return <StateCard busy title={t('Loading vehicles')}/>
  if (!items) return <StateCard icon="alert" title={t('Vehicles unavailable')}><ErrorNotice error={error}/></StateCard>

  return <FlowShell title="Go online" icon="pin" heading="Live location"
    info={t('While you are online, this page sends your phone location so nearby Passengers can find the vehicle. Keep this page open. The location is sent only while the page is open.')}>
    <div className="booking-pane">
      {error && <ErrorNotice error={error}/>}
      {geoProblem && <p role="alert">{geoProblem}</p>}
      {items.length === 0 ? <p>{t('No vehicle is available for you to take online.')}</p> : items.map(item => {
        const label = item.name || item.registration_number
        const last = sentAt[item.vehicle_id]
        return <section key={item.vehicle_id} className="dash-row" style={{ display: 'flex', gap: 12, alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', padding: '12px 0' }}>
          <div>
            <strong>{label}</strong> <span>{item.registration_number}</span>
            {item.owner_name && <div>{item.owner_name}</div>}
            <div><Chip tone={item.sending ? 'success' : 'default'}>{item.sending ? t('Online') : item.taken_by_someone_else ? t('Online with someone else') : t('Offline')}</Chip></div>
            {item.sending && last && <div>{t('Last location sent {time}', { time: last.toLocaleTimeString() })}</div>}
            {!item.ready && !item.sending && item.not_ready_reason && <div>{item.not_ready_reason}</div>}
          </div>
          <button type="button" disabled={busyId === item.vehicle_id || (!item.sending && (!item.ready || item.taken_by_someone_else))} onClick={() => toggle(item)}>
            {item.sending ? t('Go offline') : t('Go online')}
          </button>
        </section>
      })}
    </div>
  </FlowShell>
}
