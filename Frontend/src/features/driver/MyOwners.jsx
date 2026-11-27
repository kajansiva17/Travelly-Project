import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { t } from '../../i18n/language.js'
import { api, hasSession } from '../../services/api'
import { Header, ErrorNotice, Icon } from '../../components/components'
import { FlowShell } from '../booking/flow/FlowParts'
import { Field, Compact } from '../owner/OwnerRates'
import Chip from '../../components/ui/Chip'
import { EmptyCard, PersonCard, ReferenceCard } from '../people/PeopleParts'
import '../../styles/rates.css'

const post = (path, body) => api(path, { method: 'POST', body: JSON.stringify(body || {}) })

/* Driver: sidebar > My owners. Ask an Owner to list you (using the Owner's Travelly reference), or answer an Owner's invitation.
   Being listed gives you nothing by itself: a trip still needs the licence check and your own acceptance. */
export default function MyOwners() {
  const [items, setItems] = useState(null), [mine, setMine] = useState(''), [error, setError] = useState(null), [tab, setTab] = useState(0), [busy, setBusy] = useState(false)
  const [query, setQuery] = useState(''), [results, setResults] = useState(null), [notice, setNotice] = useState(''), [group, setGroup] = useState(0)
  const invites = (items || []).filter(o => o.status === 'OWNER_INVITED')
  const listed = (items || []).filter(o => o.status === 'ACTIVE')
  const waiting = (items || []).filter(o => o.status === 'DRIVER_REQUESTED')
  const groups = [['Listed by this Owner', listed], ['Invited you', invites], ['Waiting for the Owner', waiting]]
  // The Driver lands on the group that needs an answer first.
  const [picked, setPicked] = useState(false)
  const first = Math.max(0, groups.findIndex(([, g]) => g.length)), active = picked ? group : (invites.length ? 1 : first)
  const list = groups[active][1]
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
  if (!hasSession()) return <Navigate to="/login" replace/>
  return <><Header/><FlowShell heading={t('My owners')} title={tab === 0 ? t('Owners who can offer you trips') : t('Ask an Owner')} icon="user"
    info={t('Ask an Owner to list you by typing their Travelly reference. Once they accept, they can offer you their trips. Every trip still needs your licence check and your own acceptance.')}
    tabs={[{ label: invites.length ? `${t('My owners')} (${invites.length})` : t('My owners'), icon: 'user', active: tab === 0, onClick: () => setTab(0) }, { label: t('Ask an Owner'), icon: 'plus', active: tab === 1, onClick: () => setTab(1) }]}>
    <Compact.Provider value={true}>
      {tab === 0 && <div className="flow-wizard-form booking-pane">
        {notice && <p className="flow-note" role="status">{notice}</p>}
        <ErrorNotice error={error}/>
        {mine && <ReferenceCard reference={mine} hint={t('Share it with an Owner so they can invite you.')}/>}
        <div className="bk-groups" role="tablist">{groups.map(([label, g], i) => <Chip key={label} selected={active === i} onClick={() => { setGroup(i); setPicked(true) }}>{t(label)} ({g.length})</Chip>)}</div>
        {items === null && !error && <p role="status">{t('Loading…')}</p>}
        {items && !list.length && <EmptyCard icon="user" title={t('No Owners here yet.')}>{t('No Owners yet. Ask an Owner with their Travelly reference.')}</EmptyCard>}
        {list.length > 0 && <div className="bk-list pl-list">{list.map(o => <PersonCard key={o.id} name={o.name} lines={[o.reference]} photo={o.profile_image_url} live={o.status === 'ACTIVE'}
          chips={o.status === 'OWNER_INVITED' ? <Chip tone="info">{t('Invited you')}</Chip> : o.status === 'ACTIVE' ? <Chip tone="success">{t('Listed by this Owner')}</Chip> : <Chip tone="muted">{t('Waiting for the Owner')}</Chip>}
          actions={o.status === 'OWNER_INVITED' ? <>
            <button type="button" className="ui-button ui-button-primary" disabled={busy} onClick={() => decide(o, true)}>{t('Accept')}</button>
            <button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={() => decide(o, false)}>{t('Decline')}</button></>
            : <button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={() => leave(o)}>{o.status === 'ACTIVE' ? t('Leave') : t('Cancel request')}</button>}/>)}</div>}
      </div>}
      {tab === 1 && <div className="flow-wizard-form booking-pane">
        {notice && <p className="flow-note" role="status">{notice}</p>}
        <ErrorNotice error={error}/>
        <form onSubmit={search}><fieldset disabled={busy} className="pl-fieldset">
          <section className="bc-card pl-search"><span className="pl-ico"><Icon name="user" size={22}/></span>
            <div className="pl-search-field"><Field label="Find an Owner" help="Type the Owner's name (at least 3 letters), the full number plate of one of their vehicles, or their Travelly reference (USR-…). Phone, email and plate are never shown."><input required minLength={3} maxLength={60} value={query} onChange={e => setQuery(e.target.value)}/></Field></div>
            <button className="ui-button ui-button-primary pl-search-go">{t('Search')}</button></section>
        </fieldset></form>
        {results && !results.length && <EmptyCard icon="user" title={t('No Owner found.')}>{t('No Owner found. Check the spelling, or ask the Owner for their Travelly reference.')}</EmptyCard>}
        {results && results.length > 0 && <div className="bk-list pl-list">{results.map(o => <PersonCard key={o.reference} name={o.name} lines={[o.vehicles.length ? o.vehicles.join(' · ') : t('Vehicle Owner')]} photo={o.profile_image_url}
          actions={o.link_status === 'ACTIVE' ? <Chip tone="success">{t('Listed by this Owner')}</Chip> : o.link_status === 'DRIVER_REQUESTED' ? <Chip tone="muted">{t('Waiting for the Owner')}</Chip> : o.link_status === 'OWNER_INVITED' ? <Chip tone="info">{t('Invited you')}</Chip>
            : <button type="button" className="ui-button ui-button-primary" disabled={busy} onClick={() => ask(o)}>{t('Send request')}</button>}/>)}</div>}
      </div>}
    </Compact.Provider>
  </FlowShell></>
}
