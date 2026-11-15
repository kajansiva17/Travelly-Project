import { useEffect, useState } from 'react'
import { t } from '../../i18n/language.js'
import { api, hasSession } from '../../services/api'
import { Icon } from '../../components/components'

/* A Passenger's favourite vehicles: one shared list for the page, so every heart on screen agrees. */
let ids = null, loading = null
const listeners = new Set()
const publish = () => listeners.forEach(fn => fn())
export function reloadFavourites() {
  if (!hasSession()) { ids = []; publish(); return Promise.resolve() }
  loading = api('/me/favourite-vehicles').then(r => { ids = r.ids || [] }).catch(() => { ids = ids || [] }).finally(() => { loading = null; publish() })
  return loading
}
export function useFavourites() {
  const [, tick] = useState(0)
  useEffect(() => { const fn = () => tick(n => n + 1); listeners.add(fn); if (ids === null && !loading) reloadFavourites(); return () => listeners.delete(fn) }, [])
  const has = id => (ids || []).includes(id)
  async function toggle(id) {
    const on = has(id)
    ids = on ? ids.filter(x => x !== id) : [...(ids || []), id]; publish()
    try { await api(`/me/favourite-vehicles/${id}`, { method: on ? 'DELETE' : 'PUT', body: '{}' }) } catch (e) { ids = on ? [...ids, id] : ids.filter(x => x !== id); publish(); throw e }
  }
  return { has, toggle, ready: ids !== null }
}

export function FavouriteHeart({ vehicleId, className = '' }) {
  const { has, toggle } = useFavourites(), [error, setError] = useState('')
  if (!vehicleId || !hasSession()) return null
  const on = has(vehicleId)
  return <button type="button" className={'fav-heart' + (on ? ' is-on' : '') + (className ? ' ' + className : '')} aria-pressed={on} title={error || (on ? t('Remove from favourite vehicles') : t('Save as a favourite vehicle'))}
    aria-label={on ? t('Remove from favourite vehicles') : t('Save as a favourite vehicle')} onClick={e => { e.preventDefault(); e.stopPropagation(); setError(''); toggle(vehicleId).catch(err => setError(err?.message || t('Could not save this favourite.'))) }}>
    <Icon name="heart" size={20}/>
  </button>
}
