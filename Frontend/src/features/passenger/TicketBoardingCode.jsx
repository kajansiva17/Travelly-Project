import { useEffect, useRef, useState } from 'react'
import qrcode from 'qrcode-generator'
import { t } from '../../i18n/language.js'
import { api } from '../../services/api'
import { ErrorNotice } from '../../components/components'
import { Button } from '../../components/ui'

function QRImage({ token }) {
  const ref = useRef(null)
  useEffect(() => {
    if (!ref.current || !token) return
    const qr = qrcode(0, 'M')
    qr.addData(token)
    qr.make()
    ref.current.innerHTML = qr.createSvgTag(4, 0)
    const svg = ref.current.querySelector('svg')
    if (svg) { svg.setAttribute('width', '100%'); svg.setAttribute('height', '100%') }
  }, [token])
  return <div ref={ref} className="pickup-qr" aria-label={t('QR code')}/>
}

// Paid ticket booking: the QR code and the six digits the Driver checks at boarding. If the camera does not work, the Driver types the six digits.
export default function TicketBoardingCode({ bookingId }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  async function show() {
    setBusy(true); setError(null)
    try { setData(await api(`/bookings/${encodeURIComponent(bookingId)}/boarding-code`, { cache: 'no-store' })) }
    catch (failure) { setError(failure) }
    finally { setBusy(false) }
  }
  return <section className="rate-preview pickup-code-section" aria-label={t('Your boarding code')}>
    <h2>{t('Your boarding code')}</h2>
    <ErrorNotice error={error}/>
    {!data && <Button type="button" disabled={busy} onClick={show}>{busy ? t('Loading…') : t('Show boarding code')}</Button>}
    {data && <div className="pickup-code-display">
      <QRImage token={data.qr_token}/>
      <div className="pickup-code-side">
        <p className="pickup-pin" aria-label={t('Six digit PIN')}>{data.pin}</p>
        <p className="flow-note">{t('Show the QR code to the Driver. If it will not scan, read out the six digits.')}</p>
        <p className="flow-note">{t('Boarded: {value0} of {value1}', { value0: data.boarded, value1: data.travellers })}</p>
      </div>
    </div>}
  </section>
}
