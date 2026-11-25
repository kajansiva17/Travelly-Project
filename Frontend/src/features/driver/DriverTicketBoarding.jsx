import { useCallback, useEffect, useRef, useState } from 'react'
import { t } from '../../i18n/language.js'
import { api } from '../../services/api'
import { Header, ErrorNotice } from '../../components/components'
import { Button, FormField } from '../../components/ui'
import Chip from '../../components/ui/Chip'
import EmptyState from '../../components/ui/EmptyState'
import { FlowShell } from '../booking/flow/FlowParts'
import { formatDateTime } from '../../i18n/dateTime.js'
import CallContact from '../trips/CallContact'

const post = (path, body) => api(path, { method: 'POST', body: JSON.stringify(body) })
const canScan = () => typeof window !== 'undefined' && 'BarcodeDetector' in window && Boolean(navigator.mediaDevices?.getUserMedia)
const done = status => ['BOARDED', 'COMPLETED'].includes(status)

// The Driver of a ticket departure checks each ticket: scan the Passenger's QR code, or type the six digits when the camera does not work,
// then mark the travellers boarded. A traveller can also be marked from the list below.
export default function DriverTicketBoarding() {
  const [departures, setDepartures] = useState(null)
  const [selected, setSelected] = useState('')
  const [list, setList] = useState(null)
  const [found, setFound] = useState(null)
  const [pin, setPin] = useState('')
  const [scanning, setScanning] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [notice, setNotice] = useState('')
  const video = useRef(null)

  useEffect(() => {
    api('/scheduled-trips?driving=true&limit=100').then(result => {
      const items = (result.items || []).filter(item => item.status !== 'CANCELLED').sort((a, b) => new Date(a.departure_at) - new Date(b.departure_at))
      setDepartures(items)
      const now = Date.now() - 6 * 3600000
      const next = items.find(item => new Date(item.departure_at).getTime() >= now) || items[items.length - 1]
      if (next) setSelected(next.id)
    }).catch(failure => { setError(failure); setDepartures([]) })
  }, [])

  const reload = useCallback(async () => {
    if (!selected) { setList(null); return }
    try { setList(await api(`/scheduled-trips/${encodeURIComponent(selected)}/travellers`, { cache: 'no-store' })) }
    catch (failure) { setError(failure) }
  }, [selected])
  useEffect(() => { setFound(null); setNotice(''); reload() }, [reload])

  const check = useCallback(async body => {
    setBusy(true); setError(null); setNotice('')
    try { const result = await post(`/scheduled-trips/${encodeURIComponent(selected)}/boarding-checks`, body); setFound(result.matches); setPin(''); return true }
    catch (failure) { setError(failure); return false }
    finally { setBusy(false) }
  }, [selected])

  useEffect(() => {
    if (!scanning) return undefined
    if (!canScan()) { setError(new Error(t('This browser cannot scan a code. Ask the Passenger to read out the six digits.'))); setScanning(false); return undefined }
    let stream = null, stopped = false, timer = null
    const detector = new window.BarcodeDetector({ formats: ['qr_code'] })
    const read = async () => {
      if (stopped) return
      try {
        const codes = video.current ? await detector.detect(video.current) : []
        if (codes.length && codes[0].rawValue && await check({ qr_token: codes[0].rawValue })) { setScanning(false); return }
      } catch { /* a frame that cannot be read is normal; try the next one */ }
      timer = setTimeout(read, 500)
    }
    navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } }).then(async media => {
      stream = media
      if (video.current) { video.current.srcObject = media; await video.current.play().catch(() => {}) }
      read()
    }).catch(() => { setError(new Error(t('Allow the camera, or ask the Passenger to read out the six digits.'))); setScanning(false) })
    return () => { stopped = true; clearTimeout(timer); stream?.getTracks().forEach(track => track.stop()) }
  }, [scanning, check])

  async function board(ids) {
    setBusy(true); setError(null)
    try {
      for (const id of ids) await post(`/scheduled-trips/${encodeURIComponent(selected)}/boardings`, { traveller_id: id })
      setFound(null); setNotice(t('Boarded.')); await reload()
    } catch (failure) { setError(failure); await reload() }
    finally { setBusy(false) }
  }

  const departure = (departures || []).find(item => item.id === selected)
  return <><Header/><FlowShell heading={t('Ticket boarding')} title={t('Check tickets')} icon="ticket"
    info={t('Only the assigned Driver or Owner-driver checks Passenger tickets here.')}>
    <ErrorNotice error={error}/>
    {departures === null && <p role="status">{t('Loading…')}</p>}
    {departures !== null && !departures.length && <EmptyState icon="ticket" title={t('Departures you drive appear here.')}/>}
    {departures !== null && departures.length > 0 && <div className="tk-pane">
      <FormField label={t('Departure')}>
        {({ id }) => <select id={id} value={selected} onChange={event => setSelected(event.target.value)}>
          {departures.map(item => <option key={item.id} value={item.id}>{(item.route?.origin_name || '') + ' → ' + (item.route?.destination_name || '') + ' · ' + formatDateTime(item.departure_at)}</option>)}
        </select>}
      </FormField>
      {notice && <p role="status" className="flow-note">{notice}</p>}
      <section className="flow-wizard-form" aria-label={t('Check a ticket')}>
        <strong>{t('Check a ticket')}</strong>
        <div className="flow-actions">
          <Button type="button" disabled={busy || !selected} onClick={() => { setError(null); setScanning(value => !value) }}>{scanning ? t('Stop scanning') : t('Scan QR code')}</Button>
        </div>
        {scanning && <video ref={video} playsInline muted style={{ width: '100%', maxWidth: 360, borderRadius: 8 }}/>}
        <form onSubmit={event => { event.preventDefault(); check({ pin: pin.trim() }) }}>
          <FormField label={t('Or type the six digits')}>
            {({ id }) => <input id={id} inputMode="numeric" autoComplete="off" maxLength={6} value={pin} onChange={event => setPin(event.target.value.replace(/\D/g, ''))}/>}
          </FormField>
          <div className="flow-actions"><Button type="submit" disabled={busy || pin.length !== 6}>{t('Check')}</Button></div>
        </form>
        {found && found.map(match => <div key={match.booking_reference} className="rate-preview">
          <strong>{match.booking_reference}</strong>{match.booking_id && <CallContact lazy bookingId={match.booking_id}/>}
          {match.travellers.map(traveller => <div key={traveller.traveller_id} className="tk-row">
            <div className="tk-row-main"><strong>{traveller.full_name}</strong><span>{t('Seat')}{' '}{traveller.seat_code}</span></div>
            <div className="tk-row-actions">{done(traveller.status) ? <Chip tone="success">{t('Boarded')}</Chip> : traveller.can_board ? <Button type="button" disabled={busy} onClick={() => board([traveller.traveller_id])}>{t('Board')}</Button> : <Chip tone="muted">{t('Not paid')}</Chip>}</div>
          </div>)}
          {match.travellers.filter(traveller => traveller.can_board).length > 1 && <div className="flow-actions"><Button type="button" disabled={busy} onClick={() => board(match.travellers.filter(traveller => traveller.can_board).map(traveller => traveller.traveller_id))}>{t('Board all')}</Button></div>}
        </div>)}
      </section>
      {list && <section aria-label={t('Travellers')}>
        <strong>{t('Travellers')}{': '}{list.boarded}{' / '}{list.items.length}{' '}{t('boarded')}</strong>
        <div className="tk-rows">
          {list.items.map(item => <article className="tk-row" key={item.traveller_id}>
            <div className="tk-row-main"><strong>{item.full_name}</strong><span>{t('Seat')}{' '}{item.seat_code}{item.gets_on ? ' · ' + item.gets_on + ' → ' + (item.gets_off || '') : ''}</span></div>
            <div className="tk-row-actions">{item.is_primary && item.booking_id && <CallContact lazy bookingId={item.booking_id}/>}{done(item.status) ? <Chip tone="success">{t('Boarded')}</Chip> : item.can_board ? <Button type="button" variant="secondary" disabled={busy} onClick={() => board([item.traveller_id])}>{t('Board')}</Button> : <Chip tone="muted">{t('Not paid')}</Chip>}</div>
          </article>)}
          {!list.items.length && <p className="flow-note">{t('No travellers on this departure yet.')}</p>}
        </div>
      </section>}
      {departure && <p className="flow-note">{departure.status}</p>}
    </div>}
  </FlowShell></>
}
