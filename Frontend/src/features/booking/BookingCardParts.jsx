import { t } from '../../i18n/language.js'
import { Icon } from '../../components/components'
import { Chip } from '../../components/ui'
import { codeLabel } from '../../i18n/codeLabels.js'
import { displayTime } from '../../hooks/workspaceData'

/* Pieces shared by the booking cards and the booking pages: a vehicle or person photo that falls back to an icon / the first letter. */
export function Thumb({ src, icon = 'car', name = '', round = false, size = 56 }) {
  const letter = (name || '').trim().charAt(0).toUpperCase()
  return <span className={'bc-thumb' + (round ? ' is-round' : '')} style={{ width: size, height: size }}>
    {src ? <img src={src} alt="" loading="lazy"/> : round && letter ? <b>{letter}</b> : <Icon name={icon} size={Math.round(size / 2.2)}/>}
  </span>
}

const TONE = { CONFIRMED: 'success', COMPLETED: 'success', REQUESTED: 'warning', OWNER_ACTION_REQUIRED: 'warning', AWAITING_DRIVER: 'warning' }
const price = b => b.total_amount ? `${b.currency || 'LKR'} ${b.total_amount}` : null

/* The booked vehicle as one card: photo, name, route, time and price. */
export function VehicleTripCard({ booking, route }) {
  const v = booking.vehicle || {}, amount = price(booking)
  return <section className="bc-card bc-vehicle">
    <Thumb src={v.profile_image_url} icon="car" size={84}/>
    <div className="bc-body">
      <strong className="bc-name">{v.name || route}</strong>
      {v.registration && <span className="bc-sub">{v.registration}</span>}
      <span className="bc-line"><Icon name="route" size={15}/>{route}</span>
      <span className="bc-line"><Icon name="clock" size={15}/>{displayTime(booking.start_at)}{t(' to ')}{displayTime(booking.end_at)}</span>
    </div>
    <div className="bc-side">{amount && <strong className="bc-price">{amount}</strong>}<Chip tone={TONE[booking.status] || 'default'}>{codeLabel(booking.status)}</Chip></div>
  </section>
}

/* Who booked it, for the Owner and the Driver. */
export function PassengerCard({ booking }) {
  const p = booking.passenger
  if (!p) return null
  return <section className="bc-card bc-person" aria-label={t('Passenger')}>
    <Thumb src={p.profile_image_url} icon="user" name={p.name} round size={56}/>
    <div className="bc-body"><span className="bc-sub">{t('Passenger')}</span><strong className="bc-name">{p.name}</strong>
      <span className="bc-line"><Icon name="users" size={15}/>{t('{value0} passengers', { value0: booking.passenger_count })}</span></div>
  </section>
}
