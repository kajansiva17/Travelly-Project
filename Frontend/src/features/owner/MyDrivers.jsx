import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { t } from '../../i18n/language.js'
import { api, hasSession } from '../../services/api'
import { Header, ErrorNotice } from '../../components/components'
import { FlowShell, usePaged, useRowCount } from '../booking/flow/FlowParts'
import { Field, Compact } from './OwnerRates'
import Chip from '../../components/ui/Chip'
import '../../styles/rates.css'

const post = (path, body) => api(path, { method: 'POST', body: JSON.stringify(body || {}) })

/* Owner: sidebar > My drivers. Drivers ask the Owner by the Owner's Travelly reference (they find it here), or the Owner invites a Driver by reference.
   The other side accepts. Only accepted Drivers can be offered a trip, and every trip still needs the licence check and the Driver's own acceptance. */
export default function MyDrivers() {
  const [findable, setFindable] = useState(true), [items, setItems] = useState(null), [mine, setMine] = useState(''), [error, setError] = useState(null), [tab, setTab] = useState(0), [busy, setBusy] = useState(false)
  const [reference, setReference] = useState(''), [nickname, setNickname] = useState(''), [notice, setNotice] = useState('')
  const rows = useRowCount(66)
  const active = (items || []).filter(d => d.status === 'ACTIVE'), asking = (items || []).filter(d => d.status === 'DRIVER_REQUESTED'), invited = (items || []).filter(d => d.status === 'OWNER_INVITED')
  const list = tab === 0 ? [...active, ...invited] : asking
  const { slice, pager } = usePaged(list, Math.max(2, Math.min(rows, 5)))
  const load = () => api('/owners/me/saved-drivers').then(r => { setItems(r.items); setMine(r.my_reference || ''); setFindable(r.findable !== false) }).catch(setError)
  useEffect(() => { if (hasSession()) load() }, [])
  async function run(fn, message) {
    setBusy(true); setError(null); setNotice('')
    try { await fn(); await load(); if (message) setNotice(message) } catch (err) { setError(err) } finally { setBusy(false) }
  }
  const invite = e => { e.preventDefault(); run(async () => { await post('/owners/me/saved-drivers', { driver_reference: reference.trim().toUpperCase(), nickname: nickname.trim() || null }); setReference(''); setNickname(''); setTab(0) }, t('Invitation sent. The Driver must accept it.')) }
  const decide = (d, accept) => run(() => post(`/owners/me/saved-drivers/${d.id}/${accept ? 'accept' : 'decline'}`), accept ? t('Driver added to your list.') : '')
  const toggleFindable = on => run(async () => { await api('/owners/me/findable', { method: 'PUT', body: JSON.stringify({ findable: on }) }) })
  const remove = d => run(() => api(`/owners/me/saved-drivers/${d.id}`, { method: 'DELETE', body: '{}' }))
  if (!hasSession()) return <Navigate to="/login" replace/>
  return <><Header/><FlowShell heading={t('My drivers')} title={[t('Drivers you can offer a trip'), t('Driver requests'), t('Invite a Driver')][tab]} icon="user"
    info={t('Drivers ask you with your Travelly reference, or you invite a Driver with theirs. Only accepted Drivers appear when you accept a hire. Every trip still needs the licence check and the Driver’s own acceptance.')}
    tabs={[{ label: t('My drivers'), icon: 'user', active: tab === 0, onClick: () => setTab(0) },
      { label: asking.length ? `${t('Requests')} (${asking.length})` : t('Requests'), icon: 'mail', active: tab === 1, onClick: () => setTab(1) },
      { label: t('Invite a Driver'), icon: 'plus', active: tab === 2, onClick: () => setTab(2) }]}>
    <Compact.Provider value={true}>
      {notice && <p className="flow-note" role="status">{notice}</p>}
      <ErrorNotice error={error}/>
      {tab < 2 && <>
        {mine && <p className="flow-note">{t('Your Travelly reference')}: <strong>{mine}</strong> · {t('Share it with a Driver so they can ask you.')}</p>}
        <label className="terms-check"><input type="checkbox" checked={findable} disabled={busy} onChange={e => toggleFindable(e.target.checked)}/><span>{t('Drivers can find me by name or number plate')}</span></label>
        {items === null && !error && <p role="status">{t('Loading…')}</p>}
        {items && !list.length && <p className="flow-note" role="status">{tab === 0 ? t('No Drivers yet. Ask a Driver to send you a request with your reference, or invite one.') : t('No requests waiting.')}</p>}
        <div className="vehicle-rows">{slice.map(d => <article className="trip-vehicle-card" key={d.id}>
          <h2>{d.nickname ? `${d.nickname} · ${d.name}` : d.name}</h2>
          <p>{d.reference} {d.status === 'OWNER_INVITED' && <Chip tone="muted">{t('Waiting for the Driver')}</Chip>}{!d.is_driver && <Chip tone="warning">{t('Not an approved Driver now')}</Chip>}</p>
          <span className="vehicle-row-actions">{d.status === 'DRIVER_REQUESTED' ? <>
            <button type="button" className="ui-button ui-button-primary" disabled={busy} onClick={() => decide(d, true)}>{t('Accept')}</button>
            <button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={() => decide(d, false)}>{t('Decline')}</button></>
            : <button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={() => remove(d)}>{d.status === 'OWNER_INVITED' ? t('Cancel invitation') : t('Remove')}</button>}</span>
        </article>)}</div>{list.length > 0 && pager}
      </>}
      {tab === 2 && <form className="flow-wizard-form" onSubmit={invite}><fieldset disabled={busy}>
        <Field label="Driver public reference" help="Ask the Driver for their exact Travelly public reference (USR-…). The Driver gets an invitation and must accept. Private phone and licence details are never shown."><input required pattern="USR-[0-9A-Fa-f]{16}" value={reference} onChange={e => setReference(e.target.value)}/></Field>
        <Field label="Name you use for them" optional><input maxLength={60} value={nickname} onChange={e => setNickname(e.target.value)}/></Field>
        <button className="ui-button ui-button-primary">{t('Send invitation')}</button>
      </fieldset></form>}
    </Compact.Provider>
  </FlowShell></>
}
