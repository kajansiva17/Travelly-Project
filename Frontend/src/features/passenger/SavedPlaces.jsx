import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { t } from '../../i18n/language.js'
import { api, hasSession, publicRead } from '../../services/api'
import { fieldErrorMap } from '../../services/fieldErrors.js'
import { Header, ErrorNotice } from '../../components/components'
import { FlowShell } from '../booking/flow/FlowParts'
import { Field, PlaceSearch } from '../owner/OwnerRates'
import { Button } from '../../components/ui'
import PlaceMapPicker from './PlaceMapPicker'

const place = value => value && ({ label: value.label, latitude: value.latitude, longitude: value.longitude, token: value.token })

/* Sidebar > Saved Places. A few named places (Home, Work ...) saved once; Book now offers them as one-tap destinations. */
export default function SavedPlaces() {
  const [items, setItems] = useState(null)
  const [limit, setLimit] = useState(10)
  const [error, setError] = useState(null)
  const [name, setName] = useState('')
  const [found, setFound] = useState(null)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')
  const [mapOpen, setMapOpen] = useState(false)
  const [locating, setLocating] = useState(false)
  const [hint, setHint] = useState('')
  const [suggestions, setSuggestions] = useState([])

  const load = () => api('/me/saved-places', { cache: 'no-store' }).then(result => { setItems(result.items); setLimit(result.limit || 10) }).catch(setError)
  useEffect(() => { if (hasSession()) load() }, [])
  const loadSuggestions = () => api('/me/saved-places/suggestions', { cache: 'no-store' }).then(result => setSuggestions(result.items || [])).catch(() => setSuggestions([]))
  useEffect(() => { if (hasSession()) loadSuggestions() }, [])

  // The phone's position becomes the place (the server names it and signs it); nothing is saved until the Passenger names it and presses Save.
  function useHere() {
    setHint('')
    if (!navigator.geolocation) { setHint(t('Your location is not available. Allow location access or pick on the map.')); return }
    setLocating(true)
    navigator.geolocation.getCurrentPosition(async position => {
      try { const result = await publicRead(`/locations/reverse?lat=${position.coords.latitude.toFixed(6)}&lng=${position.coords.longitude.toFixed(6)}`); setFound(result.items[0]) }
      catch (failure) { setHint(failure.message || t('Location search is temporarily unavailable. Please try again.')) }
      finally { setLocating(false) }
    }, () => { setLocating(false); setHint(t('Your location is not available. Allow location access or pick on the map.')) }, { enableHighAccuracy: true, timeout: 15000 })
  }

  async function add(event) {
    event.preventDefault()
    setBusy(true); setError(null); setNotice('')
    try {
      await api('/me/saved-places', { method: 'POST', body: JSON.stringify({ name: name.trim(), place: place(found) }) })
      setName(''); setFound(null); setMapOpen(false); setNotice(t('Saved.')); await load(); loadSuggestions()
    } catch (failure) { setError(failure) }
    finally { setBusy(false) }
  }

  async function remove(id) {
    setError(null)
    try { await api(`/me/saved-places/${id}`, { method: 'DELETE', body: '{}' }); setItems(list => list.filter(item => item.id !== id)) } catch (failure) { setError(failure) }
  }

  if (!hasSession()) return <Navigate to="/login" replace/>
  const fieldMsg = fieldErrorMap(error)
  const full = items && items.length >= limit
  return <><Header/><FlowShell heading={t('Saved Places')} title={t('Places you go to often')} icon="pin"
    info={t('Save places such as Home or Work once. When you book, pick them with one tap instead of searching again.')}>
    <ErrorNotice error={error}/>
    {notice && <p role="status">{notice}</p>}
    {items === null && !error && <p role="status">{t('Loading…')}</p>}
    {items && !items.length && <p className="flow-note" role="status">{t('No saved places yet.')}</p>}
    {items && items.map(item => <section key={item.id} className="dash-row" style={{ display: 'flex', gap: 12, justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', padding: '10px 0' }}>
      <div><strong>{item.name}</strong><div>{item.place.label}</div></div>
      <Button variant="secondary" onClick={() => remove(item.id)}>{t('Remove')}</Button>
    </section>)}
    {full ? <p className="flow-note" role="status">{t('You can keep up to {limit} saved places. Remove one to add another.', { limit })}</p>
      : <form className="flow-fields" onSubmit={add}>
        <Field label="Name"><input name="name" maxLength={30} value={name} onChange={event => setName(event.target.value)} placeholder={t('Home')} aria-invalid={Boolean(fieldMsg.name)}/></Field>
        {fieldMsg.name && <small className="field-error" role="alert">{fieldMsg.name}</small>}
        <PlaceSearch label="Place" value={found} onChange={setFound}/>
        <div className="sp-quick">
          <Button type="button" variant="secondary" disabled={locating} onClick={useHere}>{locating ? t('Locating you…') : t('Use my current location')}</Button>
          <Button type="button" variant="secondary" onClick={() => setMapOpen(open => !open)}>{mapOpen ? t('Hide map') : t('Pick on map')}</Button>
        </div>
        {hint && <p className="field-error" role="alert">{hint}</p>}
        {mapOpen && <PlaceMapPicker onPick={setFound} start={found}/>}
        {suggestions.length > 0 && <div className="sp-suggest"><span>{t('Recent places you went to')}</span><div>{suggestions.map(item => <button key={item.token} type="button" className="sp-chip" onClick={() => setFound(item)} title={item.label}>{item.label}</button>)}</div></div>}
        <div className="flow-actions"><Button type="submit" disabled={busy || !name.trim() || !found}>{busy ? t('Saving…') : t('Save place')}</Button></div>
      </form>}
  </FlowShell></>
}
