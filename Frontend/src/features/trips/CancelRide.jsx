import { t } from '../../i18n/language.js'
import { useState } from 'react'
import { api } from '../../services/api'
import { Button } from '../../components/ui'
import { ErrorNotice } from '../../components/components'

// Book now: until the trip starts, the Passenger or the person sending the vehicle's location can cancel. No fee: private hire is paid after the trip.
// Two taps (ask, then confirm) so a ride is never cancelled by a slip. The newest trip version is read just before the request.
export default function CancelRide({ tripId, operator = false, onDone }) {
  const [asking, setAsking] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  async function cancel() {
    setBusy(true); setError(null)
    try {
      const fresh = await api(`/trips/${encodeURIComponent(tripId)}`, { cache: 'no-store' })
      await api(`/trips/${encodeURIComponent(tripId)}/cancel-ride`, { method: 'POST', body: JSON.stringify({ expected_version: fresh.version }) })
      onDone()
    } catch (failure) { setError(failure); setAsking(false) }
    finally { setBusy(false) }
  }

  return <div className="flow-actions">
    {error && <ErrorNotice error={error}/>}
    {asking ? <>
      <p role="alert">{operator ? t('Cancel this ride? The Passenger will be told to book another vehicle.') : t('Cancel this ride? No charge applies.')}</p>
      <Button disabled={busy} onClick={cancel}>{t('Yes, cancel the ride')}</Button>
      <Button variant="secondary" disabled={busy} onClick={() => setAsking(false)}>{t('Keep the ride')}</Button>
    </> : <Button variant="secondary" onClick={() => setAsking(true)}>{t('Cancel this ride')}</Button>}
  </div>
}
