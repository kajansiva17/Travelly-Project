import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { t } from '../../i18n/language.js'
import { api, hasSession } from '../../services/api'
import { Header, ErrorNotice } from '../../components/components'
import { FlowShell, usePaged, useRowCount } from '../booking/flow/FlowParts'
import { Field, Compact } from '../owner/OwnerRates'
import Chip from '../../components/ui/Chip'
import '../../styles/rates.css'

const post = (path, body) => api(path, { method: 'POST', body: JSON.stringify(body || {}) })

/* Driver: sidebar > My owners. Ask an Owner to list you (using the Owner's Travelly reference), or answer an Owner's invitation.
   Being listed gives you nothing by itself: a trip still needs the licence check and your own acceptance. */
export default function MyOwners() {
  const [items, setItems] = useState(null), [mine, setMine] = useState(''), [error, setError] = useState(null), [tab, setTab] = useState(0), [busy, setBusy] = useState(false)
  const [query, setQuery] = useState(''), [results, setResults] = useState(null), [notice, setNotice] = useState('')
  const rows = useRowCount(66)
  const invites = (items || []).filter(o => o.status === 'OWNER_INVITED')
  const list = (items || []).filter(o => o.status !== 'DECLINED')
  const { slice, pager } = usePaged(list, Math.max(2, Math.min(rows, 5)))
  const load = () => api('/drivers/me/owner-links').then(r => { setItems(r.items); setMine(r.my_reference || '') }).catch(setError)
  useEffect(() => { if (hasSession()) load() }, [])
  async function run(fn, message) {
    setBusy(true); setError(null); setNotice('')
    try { await fn(); await load(); if (message) setNotice(message) } catch (err) { setError(err) } finally { setBusy(false) }
  }
  const search = e => { e.preventDefault(); setBusy(true); setError(null); setNotice(''); setResults(null)
    api('/drivers/me/owner-search?q=' + encodeURIComponent(query.trim())).then(r => setResults(r.items)).catch(setError).finally(() => setBusy(false)) }
  const ask = o => run(async () => { await post('/drivers/me/owner-links', { owner_reference: o.reference }); setResults(list => list.map(x => x.reference === o.reference ? { ...x, link_status: 'DRIVER_REQUESTED' } : x)) }, t('Request sent. The Owner will see it in My drivers.'))
  const decide = (o, accept) => run(() => post(`/drivers/me/owner-links/${o.id}/${accept ? 'accept' : 'decline'}`), accept ? t('You joined this Owner’s drivers.') : '')
  const leave = o => run(() => api(`/drivers/me/owner-links/${o.id}`, { method: 'DELETE', body: '{}' }))
  const label = { ACTIVE: t('Listed by this Owner'), DRIVER_REQUESTED: t('Waiting for the Owner') }
  if (!hasSession()) return <Navigate to="/login" replace/>
  return <><Header/><FlowShell heading={t('My owners')} title={tab === 0 ? t('Owners who can offer you trips') : t('Ask an Owner')} icon="user"
    info={t('Ask an Owner to list you by typing their Travelly reference. Once they accept, they can offer you their trips. Every trip still needs your licence check and your own acceptance.')}
    tabs={[{ label: invites.length ? `${t('My owners')} (${invites.length})` : t('My owners'), icon: 'user', active: tab === 0, onClick: () => setTab(0) }, { label: t('Ask an Owner'), icon: 'plus', active: tab === 1, onClick: () => setTab(1) }]}>
    <Compact.Provider value={true}>
      {notice && <p className="flow-note" role="status">{notice}</p>}
      <ErrorNotice error={error}/>
      {tab === 0 && <>
        {mine && <p className="flow-note">{t('Your Travelly reference')}: <strong>{mine}</strong></p>}
        {items === null && !error && <p role="status">{t('Loading…')}</p>}
        {items && !list.length && <p className="flow-note" role="status">{t('No Owners yet. Ask an Owner with their Travelly reference.')}</p>}
        <div className="vehicle-rows">{slice.map(o => <article className="trip-vehicle-card" key={o.id}>
          <h2>{o.name}</h2>
          <p>{o.reference} {o.status === 'OWNER_INVITED' ? <Chip tone="info">{t('Invited you')}</Chip> : <Chip tone="muted">{label[o.status]}</Chip>}</p>
          <span className="vehicle-row-actions">{o.status === 'OWNER_INVITED' ? <>
            <button type="button" className="ui-button ui-button-primary" disabled={busy} onClick={() => decide(o, true)}>{t('Accept')}</button>
            <button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={() => decide(o, false)}>{t('Decline')}</button></>
            : <button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={() => leave(o)}>{o.status === 'ACTIVE' ? t('Leave') : t('Cancel request')}</button>}</span>
        </article>)}</div>{list.length > 0 && pager}
      </>}
      {tab === 1 && <div style={{display:'grid',gap:8,alignContent:'start'}}>
        <form onSubmit={search}><fieldset disabled={busy} style={{display:'flex',gap:10,alignItems:'flex-end',border:0,padding:0,margin:0}}>
          <div style={{flex:1,minWidth:0}}><Field label="Find an Owner" help="Type the Owner's name (at least 3 letters), the full number plate of one of their vehicles, or their Travelly reference (USR-…). Phone, email and plate are never shown."><input required minLength={3} maxLength={60} value={query} onChange={e => setQuery(e.target.value)}/></Field></div>
          <button className="ui-button ui-button-primary" style={{flex:'none',width:'auto',paddingInline:28}}>{t('Search')}</button>
        </fieldset></form>
        {results && !results.length && <p className="flow-note" role="status">{t('No Owner found. Check the spelling, or ask the Owner for their Travelly reference.')}</p>}
        <div className="vehicle-rows" style={{marginTop:10}}>{(results || []).map(o => <article className="trip-vehicle-card" key={o.reference}>
          <h2>{o.name}</h2>
          <p>{o.vehicles.length ? o.vehicles.join(' · ') : t('Vehicle Owner')}</p>
          <span className="vehicle-row-actions">{o.link_status === 'ACTIVE' ? <Chip tone="success">{t('Listed by this Owner')}</Chip> : o.link_status === 'DRIVER_REQUESTED' ? <Chip tone="muted">{t('Waiting for the Owner')}</Chip> : o.link_status === 'OWNER_INVITED' ? <Chip tone="info">{t('Invited you')}</Chip>
            : <button type="button" className="ui-button ui-button-primary" disabled={busy} onClick={() => ask(o)}>{t('Send request')}</button>}</span>
        </article>)}</div>
      </div>}
    </Compact.Provider>
  </FlowShell></>
}
