import { t } from '../../i18n/language.js'
import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { api } from '../../services/api'
import { Icon } from '../../components/components'
import { Chip } from '../../components/ui'
import VehiclePhoto from '../../components/VehiclePhoto'
import { codeLabel } from '../../i18n/codeLabels.js'
import { Thumb } from './BookingCardParts'
import SeatMap from '../../components/SeatMap'

/* A Passenger's view of a replacement vehicle on a ticket booking: the new vehicle with its photos, the Owner who runs it, the seat
   each Traveller now has (same or changed, with the seat layout), and, while the change waits, the choice to travel or to reject it
   for a full refund. Rejecting asks to confirm first; doing nothing means the Passenger travels. */
const facts = v => [codeLabel(v.vehicle_type_code), v.colour, v.air_conditioned ? 'AC' : null, v.seat_capacity != null ? t('{value0} seats', { value0: v.seat_capacity }) : null].filter(Boolean).join(' · ')

function VehicleCard({ label, vehicle, owner, strong }) {
  return <section className={'bc-card rv-vehicle' + (strong ? ' is-new' : '')}>
    <Thumb src={vehicle.profile_image_url} icon="car" size={strong ? 84 : 64}/>
    <div className="bc-body"><span className="bc-sub">{label}</span><strong className="bc-name">{vehicle.name}</strong>
      <span className="bc-sub">{vehicle.registration}</span><span className="bc-line">{facts(vehicle)}</span>
      {owner && <span className="bc-line"><Icon name="user" size={15}/>{owner.name}</span>}</div>
  </section>
}

function explain(error) {
  if (error instanceof TypeError || error.code === 'API_TIMEOUT') return t('We could not reach Travelly. Please try again.')
  if (error.code === 'VERSION_CONFLICT') return t('Your booking changed while you were looking. It was refreshed, so check it and answer again.')
  return error.message || t('Your answer could not be sent. Please try again.')
}

export default function ReplacementView({ booking, reload }) {
  const view = booking.replacement, pending = view?.status === 'PENDING' && booking.status === 'CONFIRMED'
  const [mode, setMode] = useState(null), [busy, setBusy] = useState(false), [message, setMessage] = useState(''), [big, setBig] = useState(null)
  useEffect(() => { if (!big) return; const key = e => { if (e.key === 'Escape') setBig(null) }; window.addEventListener('keydown', key); return () => window.removeEventListener('keydown', key) }, [big])
  if (!view) return null
  async function answer(decision) {
    setBusy(true); setMessage('')
    try { await api(`/bookings/${booking.id}/replacement-decision`, { method: 'POST', body: JSON.stringify({ expected_version: booking.version, decision }) }); setMode(null); await reload() }
    catch (error) { setMessage(explain(error)); setMode(null); reload && reload().catch(() => {}) }
    finally { setBusy(false) }
  }
  const photos = view.vehicle.photos || []
  return <div className="rv-view" role="group" aria-label={t('Your vehicle has changed')}>
    <p className="tk-line">{pending ? <Chip tone="info" icon="route">{t('Action needed')}</Chip> : <Chip tone={view.status === 'ACCEPTED' ? 'success' : 'muted'}>{view.status === 'ACCEPTED' ? t('Vehicle change accepted') : t('Your vehicle has changed')}</Chip>} <strong>{t('Your vehicle has changed')}</strong></p>
    {pending && <p className="bc-sub">{t('Check the new vehicle and your seats. If it suits you, travel in it. If not, reject it and get a full refund.')}</p>}
    <div className="rv-pair">
      {view.previous_vehicle && <VehicleCard label={t('Was')} vehicle={view.previous_vehicle} owner={view.previous_owner}/>}
      <VehicleCard label={t('Now')} vehicle={view.vehicle} owner={view.owner} strong/>
    </div>
    {view.operator_changed && view.owner && <section className="bc-card bc-person" aria-label={t('New operator')}>
      <Thumb src={view.owner.profile_image_url} icon="user" name={view.owner.name} round size={56}/>
      <div className="bc-body"><span className="bc-sub">{t('New operator')}</span><strong className="bc-name">{view.owner.name}</strong><span className="bc-line">{t('Vehicle Owner')}</span></div></section>}
    {photos.length > 0 && <section className="rv-photos"><strong className="tk-line">{t('Photos of the new vehicle')}</strong>
      <div className="rv-strip">{photos.map(p => <button type="button" key={p.id} className="rv-photo" onClick={() => setBig(p)}><VehiclePhoto photo={p} alt={t('Photos of the new vehicle')}/></button>)}</div></section>}
    {big && createPortal(<div className="rv-lightbox" role="dialog" aria-modal="true" onClick={() => setBig(null)}><div onClick={e => e.stopPropagation()}><button type="button" className="rv-close" aria-label={t('Close')} onClick={() => setBig(null)}><Icon name="close" size={22}/></button><VehiclePhoto photo={big} alt={t('Photos of the new vehicle')}/></div></div>, document.body)}
    <section className="rv-seats"><strong className="tk-line">{t('Your seats')}</strong>
      {view.seats.map((s, i) => <div className="bc-card rv-seat-row" key={i}><span className="bc-name">{s.full_name}</span>
        {s.from_seat === s.to_seat ? <Chip tone="success">{t('Same seat')}: {s.to_seat}</Chip> : <Chip tone="warning">{s.from_seat} → {s.to_seat}</Chip>}</div>)}
      {view.layout.length > 0 && <><span className="bc-sub">{t('Seat layout')} · {t('Your seat')}</span>
        <div className="rv-map"><SeatMap seats={view.layout} selected={view.layout.filter(x => x.mine).map(x => x.code)} label={t('Seat layout')}/></div></>}</section>
    {message && <p className="tk-line is-warn" role="status">{message}</p>}
    {pending && (mode === 'reject'
      ? <><p className="tk-line is-warn"><strong>{t('Reject the new vehicle?')}</strong> {t('Your booking is cancelled, your seats go back on sale, and you get a full refund ({value0}%) after Admin approval.', { value0: view.refund_if_rejected_percent ?? 100 })}</p>
        <div className="tk-bar"><button type="button" className="ui-button ui-button-primary" disabled={busy} onClick={() => answer('REJECT')}>{busy ? t('Please wait…') : t('Yes, reject and get a full refund')}</button><button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={() => setMode(null)}>{t('Back')}</button></div></>
      : <div className="tk-bar"><button type="button" className="ui-button ui-button-primary" disabled={busy} onClick={() => answer('ACCEPT')}>{busy ? t('Please wait…') : t('Travel in the new vehicle')}</button><button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={() => setMode('reject')}>{t('Reject and get a full refund')}</button></div>)}
  </div>
}
