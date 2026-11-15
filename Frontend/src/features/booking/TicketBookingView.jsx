import { t } from '../../i18n/language.js'
import { Link } from '../passenger/travelRouter'
import { Header, Icon } from '../../components/components'
import { Chip } from '../../components/ui'
import { FlowShell } from './flow/FlowParts'
import { displayTime } from '../../hooks/workspaceData'
import { codeLabel } from '../../i18n/codeLabels.js'

/* A seat-ticket booking (TICKET_HIRE). It has no quote or itinerary of its own: the person sees what was booked,
   who travels in which seat, and the payment, with one clear way back to the list. */
const TONE = { CONFIRMED: 'success', COMPLETED: 'success', REQUESTED: 'warning' }

export default function TicketBookingView({ booking, owner, passenger, backTo, backLabel }) {
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
      <div className="tb-people">
        <h3>{t('Travellers')}</h3>
        {people.length ? <ul>{people.map((p, i) => <li key={i}><Icon name="user" size={16}/><span>{p.full_name}{p.is_primary && <em> · {t('Booked by')}</em>}</span><Chip>{t('Seat')} {p.seat_code}</Chip><span className="tb-state">{codeLabel(p.traveller_status)}</span></li>)}</ul>
          : <p className="tb-empty">{t('No travellers to show.')}</p>}
      </div>
    </div>
    <div className="flow-actions">
      <Link className="ui-button ui-button-secondary" to={backTo}>{backLabel}</Link>
      {owner && booking.scheduled_trip_id ? <Link className="ui-button ui-button-primary" to="/owner/ticket?tab=departures">{t('Open departures')}</Link> : <span/>}
    </div>
  </FlowShell></>
}
