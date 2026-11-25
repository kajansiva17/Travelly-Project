import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { t } from '../../i18n/language.js'
import { api, hasSession } from '../../services/api'
import { fieldErrorMap } from '../../services/fieldErrors.js'
import { Header, ErrorNotice } from '../../components/components'
import { FlowShell } from '../booking/flow/FlowParts'
import { Field, PlaceSearch } from '../owner/OwnerRates'
import { Button } from '../../components/ui'

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

  const load = () => api('/me/saved-places', { cache: 'no-store' }).then(result => { setItems(result.items); setLimit(result.limit || 10) }).catch(setError)
  useEffect(() => { if (hasSession()) load() }, [])

  async function add(event) {
    event.preventDefault()
    setBusy(true); setError(null); setNotice('')
    try {
      await api('/me/saved-places', { method: 'POST', body: JSON.stringify({ name: name.trim(), place: place(found) }) })
      setName(''); setFound(null); setNotice(t('Saved.')); await load()
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
        <Field label="Name"><input name="name" maxLength={30} value={name} onChange={event => setName(event.target.value)} placeholder={t('Home')} aria-invalid={Boolean(fieldMsg.name)}/>{fieldMsg.name && <small className="field-error" role="alert">{fieldMsg.name}</small>}</Field>
        <PlaceSearch label="Place" value={found} onChange={setFound}/>
        <div className="flow-actions"><Button type="submit" disabled={busy || !name.trim() || !found}>{busy ? t('Saving…') : t('Save place')}</Button></div>
      </form>}
  </FlowShell></>
}
