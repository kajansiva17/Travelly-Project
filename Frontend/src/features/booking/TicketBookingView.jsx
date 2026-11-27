import { t } from '../../i18n/language.js'
import { useState } from 'react'
import { Link } from '../passenger/travelRouter'
import TicketCancel, { CancelledTicket } from '../passenger/TicketCancel'
import { Header, Icon } from '../../components/components'
import { Chip } from '../../components/ui'
import { FlowShell } from './flow/FlowParts'
import { displayTime } from '../../hooks/workspaceData'
import { codeLabel } from '../../i18n/codeLabels.js'
import CallContact from '../trips/CallContact'
import TicketBoardingCode from '../passenger/TicketBoardingCode'
import { PassengerCard, Thumb, VehicleTripCard } from './BookingCardParts'
import ReplacementView from './ReplacementView'

/* A seat-ticket booking (TICKET_HIRE). It has no quote or itinerary of its own: the person sees what was booked,
   who travels in which seat, and the payment, with one clear way back to the list. */

export default function TicketBookingView({ booking, owner, passenger, backTo, backLabel, reload }) {
  const [result, setResult] = useState(null), [blocked, setBlocked] = useState(false)
  const hasChange = Boolean(passenger && !owner && booking.replacement)
  const [tab, setTab] = useState(hasChange && booking.replacement.status === 'PENDING' ? 'change' : 'trip')
  // The Passenger can cancel a confirmed (paid) ticket until the departure starts; the refund follows the 72 h / 24 h rule.
  const canCancel = Boolean(passenger && !owner && booking.status === 'CONFIRMED' && new Date(booking.start_at).getTime() > Date.now())
  // The Passenger shows this QR code / six digits to the Driver when getting on (paid online or cash on the bus).
  const showCode = Boolean(passenger && !owner && booking.status === 'CONFIRMED' && new Date(booking.end_at || booking.start_at).getTime() > Date.now())
  const forCancel = { ...booking, booking_reference: booking.booking_reference || booking.reference }
  const done = async res => { setResult(res); setTab('trip'); if (reload) await reload() }
  const route = booking.origin_text && booking.destination_text ? `${booking.origin_text} → ${booking.destination_text}` : booking.reference
  const people = booking.travellers || []
  const showCancel = canCancel && !blocked
  // One tab per job, so the page is not one long scroll: the trip, a vehicle change, the boarding code, and cancelling.
  const available = [{ key: 'trip', label: 'Trip', icon: 'pin' }, ...(hasChange ? [{ key: 'change', label: 'Vehicle change', icon: 'car' }] : []), ...(showCode ? [{ key: 'code', label: 'Boarding code', icon: 'ticket' }] : []), ...(showCancel ? [{ key: 'cancel', label: 'Cancel ticket', icon: 'close' }] : [])]
  const active = available.some(x => x.key === tab) ? tab : 'trip'
  const tabs = available.map(x => ({ label: t(x.label), icon: x.icon, active: active === x.key, onClick: () => setTab(x.key) }))
  return <><Header/><FlowShell heading={t('Ticket booking')} title={booking.reference} icon="ticket" tabs={tabs}
    info={t('A seat booking on a scheduled departure. The vehicle, route and price were fixed when the departure was published.')}>
    {active === 'trip' && <div className="tb-view">
      <VehicleTripCard booking={booking} route={route}/>
      {!passenger && <PassengerCard booking={booking}/>}
      <div className="tb-facts">
        <div><span>{t('Seats')}</span><strong>{booking.passenger_count}</strong></div>
        <div><span>{t('Total')}</span><strong>{booking.total_amount ? `${booking.currency || 'LKR'} ${booking.total_amount}` : '—'}</strong></div>
        <div><span>{t('Your part')}</span><strong>{owner ? t('Vehicle owner') : passenger ? t('Passenger') : t('Driver')}</strong></div>
      </div>
      <CallContact bookingId={booking.id} refreshKey={booking.status}/>
      <div className="tb-people">
        <h3>{t('Travellers')}</h3>
        {people.length ? <div className="tb-trav-grid">{people.map((p, i) => <article className="bc-card tb-trav" key={i}>
            <Thumb icon="user" name={p.full_name} round size={48}/>
            <div className="bc-body"><strong className="bc-name">{p.full_name}</strong>
              <span className="bc-sub">{p.is_primary ? t('Booked by') : codeLabel(p.traveller_status)}{p.is_primary ? ' · ' + codeLabel(p.traveller_status) : ''}</span></div>
            <span className="tb-seat"><small>{t('Seat')}</small><strong>{p.seat_code}</strong></span></article>)}</div>
          : <p className="tb-empty">{t('No travellers to show.')}</p>}
      </div>
      {booking.status === 'CANCELLED' && passenger && <CancelledTicket booking={forCancel} result={result}/>}
    </div>}
    {active === 'change' && hasChange && <div className="tb-view"><ReplacementView booking={booking} reload={reload}/></div>}
    {active === 'code' && showCode && <div className="tb-view">
      {booking.payment_status === 'CASH_AWAITING_CONFIRMATION' && <p className="tk-line" role="status">{t('Pay {value0} in cash to the Driver when you get on.', { value0: `${booking.currency || 'LKR'} ${booking.total_amount}` })}</p>}
      <TicketBoardingCode bookingId={booking.id}/>
    </div>}
    {active === 'cancel' && showCancel && <div className="tb-view"><div className="bc-card tb-cancel"><TicketCancel booking={forCancel} departureAt={booking.start_at} refresh={async () => { if (reload) await reload() }} onDone={done} onClose={() => setTab('trip')} onBlocked={() => { setBlocked(true); setTab('trip') }}/></div></div>}
    <div className="flow-actions">
      <Link className="ui-button ui-button-secondary" to={backTo}>{backLabel}</Link>
      {owner && booking.scheduled_trip_id ? <Link className="ui-button ui-button-primary" to="/owner/ticket?tab=departures">{t('Open departures')}</Link> : <span/>}
    </div>
  </FlowShell></>
}
