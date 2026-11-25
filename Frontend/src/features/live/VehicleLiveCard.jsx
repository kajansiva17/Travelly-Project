import { t } from '../../i18n/language.js'
import { Icon } from '../../components/components'
import { Chip } from '../../components/ui'

// One vehicle in the Go online page and in the Live tab: status, where the vehicle is (the last position this phone sent), and the two switches.
const when = iso => { try { return new Date(iso).toLocaleString('en-GB', { timeZone: 'Asia/Colombo', dateStyle: 'short', timeStyle: 'short' }) } catch { return '' } }

export default function VehicleLiveCard({ item, busy, onToggle, onBookNow, showName = true }) {
  const online = Boolean(item.sending)
  const hasPosition = item.latitude != null && item.longitude != null
  const map = hasPosition ? `https://www.openstreetmap.org/?mlat=${item.latitude}&mlon=${item.longitude}#map=16/${item.latitude}/${item.longitude}` : null
  const label = item.name || item.registration_number
  const blocked = !online && (!item.ready || item.taken_by_someone_else)
  const bookNowOn = Boolean(item.instant_booking)
  return <article className={'live-card' + (online ? ' is-online' : '')}>
    <header className="live-card-head">
      {showName ? <div className="live-id"><strong>{label}</strong><span>{item.registration_number}{item.owner_name ? ' · ' + item.owner_name : ''}</span></div> : <span/>}
      <Chip tone={online ? 'success' : 'default'}>{online ? t('Online') : item.taken_by_someone_else ? t('Online with someone else') : t('Offline')}</Chip>
    </header>
    <ul className="live-facts">
      <li><Icon name="pin" size={16}/><span><b>{online ? t('Live position') : t('Last known position')}</b>{hasPosition
        ? <> · {when(item.last_seen_at)} · <a href={map} target="_blank" rel="noreferrer">{t('Open map')}</a></>
        : <> · {t("No position yet. Go online to share this phone's location.")}</>}</span></li>
      {item.base_location_label && <li><Icon name="home" size={16}/><span><b>{t('Base')}</b> · {item.base_location_label}</span></li>}
      {!online && !item.ready && item.not_ready_reason && <li className="is-warn"><Icon name="alert" size={16}/><span>{item.not_ready_reason}</span></li>}
    </ul>
    <footer className="live-actions">
      {!item.owner_name && <button type="button" role="switch" aria-checked={bookNowOn} className={'ui-button ui-button-secondary live-switch' + (bookNowOn ? ' is-on' : '')} onClick={onBookNow}><span className="live-knob" aria-hidden="true"/>{bookNowOn ? t('Book now is on') : t('Book now is off')}</button>}
      <button type="button" className={'ui-button ' + (online ? 'ui-button-secondary' : 'ui-button-primary')} disabled={busy || blocked} onClick={onToggle}>{online ? t('Go offline') : t('Go online')}</button>
    </footer>
  </article>
}
