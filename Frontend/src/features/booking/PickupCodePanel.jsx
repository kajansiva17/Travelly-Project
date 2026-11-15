import { useState, useEffect, useRef } from 'react'
import { api } from '../../services/api'
import { t } from '../../i18n/language.js'
import { Icon } from '../../components/components'
import qrcode from 'qrcode-generator'

/**
 * Shown to the Passenger on the Trip tab when pickup verification is required.
 * Fetches the 6-digit PIN and QR token from GET /trips/{id}/pickup-code and
 * displays them so the Passenger can read them out to the Driver/Owner.
 */
function QRImage({ token }) {
  const ref = useRef(null)
  useEffect(() => {
    if (!ref.current || !token) return
    const qr = qrcode(0, 'M')
    qr.addData(token)
    qr.make()
    ref.current.innerHTML = qr.createSvgTag(4, 0)
    const svg = ref.current.querySelector('svg')
    if (svg) { svg.setAttribute('width','160'); svg.setAttribute('height','160') }
  }, [token])
  return <div ref={ref} className="pickup-qr" aria-label={t('QR code')}/>
}

export default function PickupCodePanel({ tripId }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [shown, setShown] = useState(false)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const res = await api(`/trips/${tripId}/pickup-code`)
      setData(res)
      setShown(true)
    } catch (e) {
      setError(e.message || t('Could not load pickup code.'))
    } finally {
      setLoading(false)
    }
  }

  if (data?.verified_at) {
    return (
      <section className="rate-preview">
        <h2>{t('Pickup verified')}</h2>
        <p><Icon name="check" size={16}/> {t('The Driver has checked your pickup code. Your trip is ready to start.')}</p>
      </section>
    )
  }

  return (
    <section className="rate-preview pickup-code-section">
      <h2>{t('Your pickup code')}</h2>
      <p>{t('The Driver will ask for this code before starting the trip. Show the six digits or the QR code.')}</p>
      {!shown && (
        <button className="button" disabled={loading} onClick={load}>
          {loading ? t('Loading…') : t('Show pickup code')}
        </button>
      )}
      {error && <p className="field-error" role="alert">{error}</p>}
      {shown && data && (
        <div className="pickup-code-display">
          <QRImage token={data.qr_token}/>
          <p className="pickup-pin" aria-label={t('Six digit PIN')}>{data.pin}</p>
          {data.attempts_left < 5 && (
            <p className="field-error" role="status">
              {t('{value0} attempt(s) remaining.', { value0: data.attempts_left })}
            </p>
          )}
          <button className="button outline" onClick={load}>{t('Refresh code')}</button>
        </div>
      )}
    </section>
  )
}
