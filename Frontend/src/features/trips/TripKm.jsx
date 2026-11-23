import { useEffect, useState } from 'react'
import { t } from '../../i18n/language.js'
import { api } from '../../services/api'

// Owner only, finished trip: the kilometres the Passenger was charged for next to the kilometres the vehicle really covered.
// The difference shows detours or private use. It never changes the Passenger's fare.
export default function TripKm({ tripId }) {
  const [km, setKm] = useState(null)
  useEffect(() => { api(`/trips/${encodeURIComponent(tripId)}/km-summary`, { cache: 'no-store' }).then(setKm).catch(() => setKm(null)) }, [tripId])
  if (!km || !km.finished || km.odometer_km == null) return null
  return <section className="flow-wizard-form" aria-label={t('Kilometres of this trip')}>
    <strong>{t('Kilometres of this trip')}</strong>
    <dl className="booking-facts">
      <div><dt>{t('Billed km (route estimate)')}</dt><dd>{km.billed_km ?? '—'}</dd></div>
      <div><dt>{t('Odometer km (really driven)')}</dt><dd>{km.odometer_km}</dd></div>
      {km.extra_km != null && <div><dt>{t('Extra km')}</dt><dd>{km.extra_km}</dd></div>}
    </dl>
    <p className="flow-note">{t('Extra km are not charged to the Passenger. They show detours or private use.')}</p>
  </section>
}
