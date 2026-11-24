import { useEffect, useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { t } from '../../i18n/language.js'
import { api, hasSession } from '../../services/api'
import { Header, ErrorNotice, Icon } from '../../components/components'
import { FlowShell, usePaged, useRowCount } from '../booking/flow/FlowParts'
import VehiclePhoto from '../../components/VehiclePhoto'
import Chip from '../../components/ui/Chip'
import { startFavouriteHire } from '../passenger/PassengerBookingFlow'
import { reloadFavourites } from './favourites.jsx'

const name = v => v.display_name || [v.make, v.model].filter(Boolean).join(' ') || v.reference || t('Vehicle')

/* Sidebar > Favourite vehicles. Pick a favourite, give only the trip details, and see that vehicle's price: no searching through every vehicle again. */
export default function FavouriteVehicles() {
  const [items, setItems] = useState(null), [error, setError] = useState(null), navigate = useNavigate(), rows = useRowCount(88)
  const { slice, pager } = usePaged(items || [], Math.max(2, Math.min(rows, 4)))
  const load = () => api('/me/favourite-vehicles').then(r => setItems(r.items)).catch(setError)
  useEffect(() => { if (hasSession()) load() }, [])
  async function remove(id) {
    try { await api(`/me/favourite-vehicles/${id}`, { method: 'DELETE', body: '{}' }); setItems(list => list.filter(v => v.id !== id)); reloadFavourites() } catch (e) { setError(e) }
  }
  function hire(vehicle) { startFavouriteHire({ id: vehicle.id, label: name(vehicle) }); navigate('/travel/book/service', { state: { resume: true } }) }
  if (!hasSession()) return <Navigate to="/login" replace/>
  return <><Header/><FlowShell heading={t('Favourite vehicles')} title={t('Hire a vehicle you already like')} icon="heart" info={t('Save vehicles you hire often. Choose one here, give your trip details, and see that vehicle’s price without searching again.')}>
    <ErrorNotice error={error}/>
    {items === null && !error && <p role="status">{t('Loading…')}</p>}
    {items && !items.length && <p className="flow-note" role="status">{t('No favourite vehicles yet. Tap the heart on any vehicle to save it here.')} <Link to="/hire">{t('Browse vehicles')}</Link></p>}
    {items && items.length > 0 && <><div className="fav-list">{slice.map(v => <article key={v.id} className="fav-row ui-card">
      <div className="fav-photo">{v.profile_image_url ? <img src={v.profile_image_url} alt={name(v)} referrerPolicy="no-referrer"/> : v.photos?.[0] ? <VehiclePhoto photo={v.photos[0]} alt={name(v)}/> : <Icon name="car" size={32}/>}</div>
      <div className="fav-info"><h3>{name(v)}</h3>
        <p>{[v.manufacture_year, v.colour].filter(Boolean).join(' · ')}</p>
        <div className="status-chips">{v.available ? <><Chip tone="muted" icon="seat">{t('{value0} seats', { value0: v.passenger_seats })}</Chip>{v.owner_name && <Chip tone="muted" icon="user">{v.owner_name}</Chip>}</> : <Chip tone="warning">{t('Not available to hire now')}</Chip>}</div></div>
      <div className="fav-actions"><button type="button" className="ui-button ui-button-primary" disabled={!v.available} onClick={() => hire(v)}>{t('Hire this vehicle')}</button>
        <button type="button" className="ui-button ui-button-secondary" onClick={() => remove(v.id)}>{t('Remove')}</button></div>
    </article>)}</div>{pager}</>}
  </FlowShell></>
}
