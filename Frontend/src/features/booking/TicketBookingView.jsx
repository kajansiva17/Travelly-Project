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

/* A seat-ticket booking (TICKET_HIRE). It has no quote or itinerary of its own: the person sees what was booked,
   who travels in which seat, and the payment, with one clear way back to the list. */
const TONE = { CONFIRMED: 'success', COMPLETED: 'success', REQUESTED: 'warning' }

export default function TicketBookingView({ booking, owner, passenger, backTo, backLabel, reload }) {
  const [cancelOpen, setCancelOpen] = useState(false), [result, setResult] = useState(null)
  // The Passenger can cancel a confirmed (paid) ticket until the departure starts; the refund follows the 72 h / 24 h rule.
  const canCancel = Boolean(passenger && !owner && booking.status === 'CONFIRMED' && new Date(booking.start_at).getTime() > Date.now())
  // The Passenger shows this QR code / six digits to the Driver when getting on (paid online or cash on the bus).
  const showCode = Boolean(passenger && !owner && booking.status === 'CONFIRMED' && new Date(booking.end_at || booking.start_at).getTime() > Date.now())
  const forCancel = { ...booking, booking_reference: booking.booking_reference || booking.reference }
  const done = async res => { setResult(res); setCancelOpen(false); if (reload) await reload() }
  const route = booking.origin_text && booking.destination_text ? `${booking.origin_text} → ${booking.destination_text}` : booking.reference
  const people = booking.travellers || []
  return <><Header/><FlowShell heading={t('Ticket booking')} title={booking.reference} icon="ticket"
    info={t('A seat booking on a scheduled departure. The vehicle, route and price were fixed when the departure was published.')}>
    <div className="tb-view">
      <div className="tb-hero">
        <div><strong className="tb-route">{route}</strong>
          <span className="tb-when"><Icon name="clock" size={15}/>{displayTime(booking.start_at)}{t(' to ')}{displayTime(booking.end_at)}</span></div>
        <Chip tone={TONE[booking.status] || 'default'}>{codeLabel(booking.status)}</Chip>
      </div>
      <div className="tb-facts">
        <div><span>{t('Seats')}</span><strong>{booking.passenger_count}</strong></div>
        <div><span>{t('Total')}</span><strong>{booking.total_amount ? `${booking.currency || 'LKR'} ${booking.total_amount}` : '—'}</strong></div>
        <div><span>{t('Your part')}</span><strong>{owner ? t('Vehicle owner') : passenger ? t('Passenger') : t('Driver')}</strong></div>
      </div>
      <CallContact bookingId={booking.id} refreshKey={booking.status}/>
      {showCode && <>
        {booking.payment_status === 'CASH_AWAITING_CONFIRMATION' && <p className="tk-line" role="status">{t('Pay {value0} in cash to the Driver when you get on.', { value0: `${booking.currency || 'LKR'} ${booking.total_amount}` })}</p>}
        <TicketBoardingCode bookingId={booking.id}/>
      </>}
      <div className="tb-people">
        <h3>{t('Travellers')}</h3>
        {people.length ? <ul>{people.map((p, i) => <li key={i}><Icon name="user" size={16}/><span>{p.full_name}{p.is_primary && <em> · {t('Booked by')}</em>}</span><Chip>{t('Seat')} {p.seat_code}</Chip><span className="tb-state">{codeLabel(p.traveller_status)}</span></li>)}</ul>
          : <p className="tb-empty">{t('No travellers to show.')}</p>}
      </div>
    </div>
    {booking.status === 'CANCELLED' && passenger && <CancelledTicket booking={forCancel} result={result}/>}
    {cancelOpen && canCancel && <TicketCancel booking={forCancel} departureAt={booking.start_at} refresh={async () => { if (reload) await reload() }} onDone={done} onClose={() => setCancelOpen(false)}/>}
    <div className="flow-actions">
      <Link className="ui-button ui-button-secondary" to={backTo}>{backLabel}</Link>
      {canCancel && !cancelOpen && <button type="button" className="ui-button ui-button-secondary" onClick={() => setCancelOpen(true)}>{t('Cancel ticket')}</button>}
      {owner && booking.scheduled_trip_id ? <Link className="ui-button ui-button-primary" to="/owner/ticket?tab=departures">{t('Open departures')}</Link> : <span/>}
    </div>
  </FlowShell></>
}
