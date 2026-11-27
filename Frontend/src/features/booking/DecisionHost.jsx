import { t } from '../../i18n/language.js'
import { useCallback, useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { Link } from 'react-router-dom'
import { api } from '../../services/api'
import { Icon } from '../../components/components'
import { useWorkspace } from '../../context/workspaceContext'
import { personalBookingPath, withWorkspace } from '../../routes/workspaceRoutes'
import { pendingBooking, tripRoute } from '../../hooks/workspaceData'
import { VehicleTripCard } from './BookingCardParts'

/* A pop-up on top of any page for a Passenger who has something to decide, so it is not missed in the bell:
     * a trip quote from the Owner waits for the price to be accepted (Accept price / Not for me / Decide later);
     * a replacement vehicle waits for the Passenger's answer (opens the booking to review the vehicle and seats).
     * a Driver is asked to take a trip: the assignment waits for Accept trip / Decline (the Driver never has to hunt for it in the bell).
   "Decide later" hides it for a while on this device; the decision itself stays on the booking and in the bell. */
const EVERY_MS = 30000, SNOOZE_MS = 10 * 60000, STORE = 'travelly-decision-later'

const quoteOf = b => b.status === 'REQUESTED' && !b.accepted_quote_digest && b.proposal?.kind === 'QUOTE' ? b.proposal.quote : null
const replacementOf = b => b.status === 'CONFIRMED' && b.proposal?.kind === 'REPLACEMENT_VEHICLE' && b.proposal.status === 'PENDING'
const assignmentOf = (b, userId) => b.trip?.driver_user_id === userId && b.trip.assignment_status === 'PENDING' && b.trip.status !== 'CANCELLED' && pendingBooking(b)
const keyOf = b => `${b.id}:${b.kind === 'assign' ? 'a' + b.trip.version : b.version}`
function snoozed() { try { return JSON.parse(sessionStorage.getItem(STORE) || '{}') } catch { return {} } }
function snooze(key) { try { sessionStorage.setItem(STORE, JSON.stringify({ ...snoozed(), [key]: Date.now() + SNOOZE_MS })) } catch { /* private mode: it simply shows again */ } }

export default function DecisionHost({ enabled }) {
  const { role, user } = useWorkspace()
  const [items, setItems] = useState([]), [, tick] = useState(0)
  const [mode, setMode] = useState(null), [busy, setBusy] = useState(false), [message, setMessage] = useState('')

  const read = useCallback(async () => {
    try {
      const result = await api('/bookings?as=passenger', { cache: 'no-store' })
      const vehicles = result?.vehicles || {}
      const mine = (result?.items || []).filter(b => quoteOf(b) || replacementOf(b)).map(b => ({ ...b, vehicle: vehicles[b.vehicle_id] || null }))
      let asked = []
      if (role === 'DRIVER' && user?.id) {
        // The list does not carry the trip, so each open booking is read (a few at a time) to find assignments that wait for this Driver.
        const driving = await api('/bookings?as=driver', { cache: 'no-store' }), open = (driving?.items || []).filter(pendingBooking), found = []
        let next = 0
        await Promise.all(Array.from({ length: Math.min(4, open.length) }, async () => {
          while (next < open.length) {
            const b = open[next++]
            try { const d = await api('/bookings/' + b.id, { cache: 'no-store' }); if (assignmentOf(d, user.id)) found.push({ ...d, kind: 'assign', vehicle: driving.vehicles?.[d.vehicle_id] || d.vehicle || null }) } catch { /* skipped until the next poll */ }
          }
        }))
        asked = found.sort((a, b) => new Date(a.start_at) - new Date(b.start_at))
      }
      setItems([...asked, ...mine])
    } catch { /* the next poll tries again */ }
  }, [role, user?.id])
  useEffect(() => {
    if (!enabled) return undefined
    read()
    const timer = setInterval(() => { if (!document.hidden) read() }, EVERY_MS)
    const visible = () => { if (!document.hidden) read() }
    document.addEventListener('visibilitychange', visible)
    return () => { clearInterval(timer); document.removeEventListener('visibilitychange', visible) }
  }, [enabled, read])

  const hidden = snoozed(), now = Date.now()
  const current = items.find(b => !(hidden[keyOf(b)] > now))
  useEffect(() => { setMode(null); setMessage('') }, [current && keyOf(current)])
  if (!enabled || !current) return null

  const isAssign = current.kind === 'assign', quote = isAssign ? null : quoteOf(current), isQuote = Boolean(quote)
  const link = isAssign ? withWorkspace('/bookings/' + current.id, role) : role === 'PASSENGER' ? withWorkspace('/bookings/' + current.id, role) : personalBookingPath(role, current.id)
  const later = () => { snooze(keyOf(current)); tick(n => n + 1) }
  async function send(path, body) {
    setBusy(true); setMessage('')
    const url = isAssign ? `/trips/${current.trip.id}/${path}` : `/bookings/${current.id}/${path}`
    try { await api(url, { method: 'POST', body: JSON.stringify({ expected_version: isAssign ? current.trip.version : current.version, ...body }) }); setMode(null); await read() }
    catch (error) {
      setMode(null)
      setMessage(error.code === 'QUOTE_CHANGED' || error.code === 'VERSION_CONFLICT' ? (isAssign ? t('This trip changed. Please open it to review.') : t('The quote changed. Please open the booking to review it.')) : error.message || t('Your answer could not be sent. Please try again.'))
      read()
    } finally { setBusy(false) }
  }
  // The card shows what the Passenger is about to accept: the vehicle, the route, the time the Owner offers and the price.
  const shown = isQuote ? { ...current, total_amount: quote.calculation?.total, start_at: quote.itinerary?.start_at || current.start_at, end_at: quote.reserved_end_at || current.end_at } : current
  const otherTime = isQuote && quote.itinerary?.start_at && new Date(quote.itinerary.start_at).getTime() !== new Date(current.start_at).getTime()

  const title = isAssign ? t('A trip is waiting for your answer') : isQuote ? t('Your trip quote is ready') : t('Your vehicle has changed')
  const hint = isAssign ? t('Accept the trip, or decline it so the Owner can find another Driver.') : isQuote ? t('Review the price and the time, then accept or decline.') : t('Open the booking to see the new vehicle and your seats, then travel or reject it.')
  const ask = isAssign ? 'Decline this trip?' : 'Cancel this request?'
  return createPortal(<div className="dh-backdrop" role="presentation">
    <section className="dh-modal" role="alertdialog" aria-modal="true" aria-label={title}>
      <header className="dh-head"><Icon name={isAssign ? 'car' : isQuote ? 'wallet' : 'route'} size={22}/><strong>{title}</strong>
        {items.length > 1 && <span className="dh-count">{items.length}</span>}</header>
      <p className="bc-sub">{hint}</p>
      <VehicleTripCard booking={shown} route={tripRoute(current)}/>
      {otherTime && <p className="tk-line is-warn" role="status">{t('The Owner offers a different time')}</p>}
      {message && <p className="tk-line is-warn" role="status">{message}</p>}
      {(isQuote || isAssign) && mode === 'decline'
        ? <><p className="tk-line is-warn"><strong>{t(ask)}</strong> {isAssign ? t('The Owner is told and will look for another Driver.') : t('The Owner is told and the vehicle is released. Nothing is charged.')}</p>
          <div className="dh-actions"><button type="button" className="ui-button ui-button-primary" disabled={busy} onClick={() => isAssign ? send('assignment-decline', {}) : send('cancel', { reason: 'The Passenger declined the quote.' })}>{busy ? t('Please wait…') : isAssign ? t('Yes, decline the trip') : t('Yes, cancel the request')}</button>
            <button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={() => setMode(null)}>{t('Back')}</button></div></>
        : <div className="dh-actions">
          {isAssign
            ? <><button type="button" className="ui-button ui-button-primary" disabled={busy} onClick={() => send('assignment-accept', {})}>{busy ? t('Please wait…') : t('Accept trip')}</button>
              <button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={() => setMode('decline')}>{t('Decline')}</button></>
            : isQuote
            ? <><button type="button" className="ui-button ui-button-primary" disabled={busy} onClick={() => send('price-acceptance', { digest: quote.digest })}>{busy ? t('Please wait…') : t('Accept price')}</button>
              <button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={() => setMode('decline')}>{t('Not for me')}</button></>
            : <Link className="ui-button ui-button-primary" to={link} onClick={later}>{t('Review the change')}</Link>}
          <button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={later}>{t('Decide later')}</button>
          {(isQuote || isAssign) && <Link className="dh-link" to={link} onClick={later}>{t('View details')}</Link>}
        </div>}
    </section>
  </div>, document.body)
}
