import { useCallback, useEffect, useState } from 'react'
import { api } from '../../services/api'
import { liveChanged } from './liveSender'

// The vehicles this person can take online (GET /me/live-vehicles) and the two switches: Go online / Go offline and Book now.
// Shared by the Go online page and the Live tab of a vehicle in My vehicles.
export function useLiveVehicles() {
  const [items, setItems] = useState(null)
  const [error, setError] = useState(null)
  const [busyId, setBusyId] = useState('')

  const load = useCallback(async () => {
    try {
      const result = await api('/me/live-vehicles', { cache: 'no-store' })
      setItems(result?.items || [])
      setError(null)
    } catch (problem) { setError(problem) }
  }, [])

  useEffect(() => { load() }, [load])
  // While a vehicle is online its last position moves; read it again now and then so the place and time stay current.
  const sending = (items || []).some(item => item.sending)
  useEffect(() => { if (!sending) return undefined; const timer = setInterval(load, 15000); return () => clearInterval(timer) }, [sending, load])

  async function toggle(item) {
    if (busyId) return
    setBusyId(item.vehicle_id); setError(null)
    try {
      await api(`/vehicles/${item.vehicle_id}/live/${item.sending ? 'offline' : 'online'}`, { method: 'POST', body: '{}' })
      await load()
    } catch (problem) { setError(problem); load() }
    finally { setBusyId(''); liveChanged() }
  }

  async function bookNow(item) {
    setError(null)
    try { await api(`/vehicles/${item.vehicle_id}/live/instant-booking`, { method: 'PATCH', body: JSON.stringify({ enabled: !item.instant_booking }) }); await load() }
    catch (problem) { setError(problem) }
  }

  return { items, error, setError, busyId, load, toggle, bookNow }
}
