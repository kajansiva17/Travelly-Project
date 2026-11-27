import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { t } from '../../i18n/language.js'
import { api, hasSession } from '../../services/api'
import { Header, ErrorNotice, Icon } from '../../components/components'
import { FlowShell } from '../booking/flow/FlowParts'
import { Field, Compact } from './OwnerRates'
import Chip from '../../components/ui/Chip'
import { EmptyCard, PersonCard, ReferenceCard } from '../people/PeopleParts'
import { PayDriversPane } from '../driverPayments/DriverPayments'
import '../../styles/rates.css'

const post = (path, body) => api(path, { method: 'POST', body: JSON.stringify(body || {}) })

/* Owner: sidebar > My drivers. Drivers ask the Owner by the Owner's Travelly reference (they find it here), or the Owner invites a Driver by reference.
   The other side accepts. Only accepted Drivers can be offered a trip, and every trip still needs the licence check and the Driver's own acceptance.
   Pay Drivers is a tab of this page, so the tab bar stays where it is. */
export default function MyDrivers({ initialTab = 0 }) {
  const [findable, setFindable] = useState(true), [items, setItems] = useState(null), [mine, setMine] = useState(''), [error, setError] = useState(null), [tab, setTab] = useState(initialTab), [busy, setBusy] = useState(false)
  const [reference, setReference] = useState(''), [nickname, setNickname] = useState(''), [notice, setNotice] = useState(''), [group, setGroup] = useState(0)
  const active = (items || []).filter(d => d.status === 'ACTIVE'), asking = (items || []).filter(d => d.status === 'DRIVER_REQUESTED'), invited = (items || []).filter(d => d.status === 'OWNER_INVITED')
  const list = group === 0 ? active : invited
  const [photo, setPhoto] = useState(null)
  useEffect(() => { if (!photo) return undefined; const onKey = e => { if (e.key === 'Escape') setPhoto(null) }; window.addEventListener('keydown', onKey); return () => window.removeEventListener('keydown', onKey) }, [photo])
  const load = () => api('/owners/me/saved-drivers').then(r => { setItems(r.items); setMine(r.my_reference || ''); setFindable(r.findable !== false) }).catch(setError)
  useEffect(() => { if (hasSession()) load() }, [])
  async function run(fn, message) {
    setBusy(true); setError(null); setNotice('')
    try { await fn(); await load(); if (message) setNotice(message) } catch (err) { setError(err) } finally { setBusy(false) }
  }
  const invite = e => { e.preventDefault(); run(async () => { await post('/owners/me/saved-drivers', { driver_reference: reference.trim().toUpperCase(), nickname: nickname.trim() || null }); setReference(''); setNickname(''); setTab(0); setGroup(1) }, t('Invitation sent. The Driver must accept it.')) }
  const decide = (d, accept) => run(() => post(`/owners/me/saved-drivers/${d.id}/${accept ? 'accept' : 'decline'}`), accept ? t('Driver added to your list.') : '')
  const toggleFindable = on => run(async () => { await api('/owners/me/findable', { method: 'PUT', body: JSON.stringify({ findable: on }) }) })
  const remove = d => run(() => api(`/owners/me/saved-drivers/${d.id}`, { method: 'DELETE', body: '{}' }))
  if (!hasSession()) return <Navigate to="/login" replace/>
  const labelOf = d => d.nickname ? `${d.nickname} · ${d.name}` : d.name
  const card = d => {
    const live = d.status === 'ACTIVE' && d.online
    return <PersonCard key={d.id} name={labelOf(d)} lines={[d.reference]} photo={d.profile_image_url} live={live} onPhoto={() => setPhoto({ url: d.profile_image_url, name: labelOf(d) })}
      chips={<>
        {d.status === 'OWNER_INVITED' && <Chip tone="info">{t('Waiting for the Driver')}</Chip>}
        {d.status === 'DRIVER_REQUESTED' && <Chip tone="info">{t('Asked to join')}</Chip>}
        {d.status === 'ACTIVE' && <Chip tone={d.online ? 'success' : 'muted'}>{d.online ? t('Online') : t('Offline')}</Chip>}
        {d.status === 'ACTIVE' && d.is_driver && (d.on_trip ? <Chip tone="warning">{t('On a trip')}</Chip> : d.online && <Chip tone="success">{t('Available')}</Chip>)}
        {!d.is_driver && <Chip tone="danger">{t('Not an approved Driver now')}</Chip>}</>}
      actions={d.status === 'DRIVER_REQUESTED' ? <>
        <button type="button" className="ui-button ui-button-primary" disabled={busy} onClick={() => decide(d, true)}>{t('Accept')}</button>
        <button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={() => decide(d, false)}>{t('Decline')}</button></>
        : <button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={() => remove(d)}>{d.status === 'OWNER_INVITED' ? t('Cancel invitation') : t('Remove')}</button>}/>
  }
  return <><Header/><FlowShell heading={t('My drivers')} title={[t('Drivers you can offer a trip'), t('Driver requests'), t('Invite a Driver'), t('Pay Drivers')][tab]} icon={tab === 3 ? 'wallet' : 'user'}
    info={tab === 3 ? t('Completed trips that had a separate Driver. Pay the Driver now or days later, then record it here. Cash counts after the Driver confirms it.') : t('Drivers ask you with your Travelly reference, or you invite a Driver with theirs. Only accepted Drivers appear when you accept a hire. Every trip still needs the licence check and the Driver’s own acceptance.')}
    tabs={[{ label: t('My drivers'), icon: 'user', active: tab === 0, onClick: () => setTab(0) },
      { label: asking.length ? `${t('Requests')} (${asking.length})` : t('Requests'), icon: 'mail', active: tab === 1, onClick: () => setTab(1) },
      { label: t('Invite a Driver'), icon: 'plus', active: tab === 2, onClick: () => setTab(2) },
      { label: t('Pay Drivers'), icon: 'wallet', active: tab === 3, onClick: () => setTab(3) }]}>
    <Compact.Provider value={true}>
      {tab === 0 && <div className="flow-wizard-form booking-pane">
        {notice && <p className="flow-note" role="status">{notice}</p>}
        <ErrorNotice error={error}/>
        {mine && <ReferenceCard reference={mine} hint={t('Share it with a Driver so they can ask you.')}/>}
        <label className="bc-card pl-find"><input type="checkbox" checked={findable} disabled={busy} onChange={e => toggleFindable(e.target.checked)}/><span>{t('Drivers can find me by name or number plate')}</span></label>
        <div className="bk-groups" role="tablist"><Chip selected={group === 0} onClick={() => setGroup(0)}>{t('My drivers')} ({active.length})</Chip><Chip selected={group === 1} onClick={() => setGroup(1)}>{t('Waiting for the Driver')} ({invited.length})</Chip></div>
        {items === null && !error && <p role="status">{t('Loading…')}</p>}
        {items && !list.length && <EmptyCard icon="user" title={group === 0 ? t('No Drivers yet.') : t('No invitations waiting.')}>{group === 0 ? t('Ask a Driver to send you a request with your reference, or invite one.') : t('Invitations you send appear here until the Driver accepts.')}</EmptyCard>}
        {list.length > 0 && <div className="bk-list pl-list">{list.map(card)}</div>}
      </div>}
      {tab === 1 && <div className="flow-wizard-form booking-pane">
        {notice && <p className="flow-note" role="status">{notice}</p>}
        <ErrorNotice error={error}/>
        {items && !asking.length && <EmptyCard icon="mail" title={t('No requests waiting.')}>{t('When a Driver asks to join you with your reference, it shows up here.')}</EmptyCard>}
        {asking.length > 0 && <div className="bk-list pl-list">{asking.map(card)}</div>}
      </div>}
      {tab === 2 && <form className="flow-wizard-form booking-pane" onSubmit={invite}><ErrorNotice error={error}/><fieldset disabled={busy} className="pl-fieldset">
        <section className="bc-card pl-formcard"><span className="pl-ico"><Icon name="mail" size={24}/></span>
          <div className="pl-formbody">
            <Field label="Driver public reference" help="Ask the Driver for their exact Travelly public reference (USR-…). The Driver gets an invitation and must accept. Private phone and licence details are never shown."><input required pattern="USR-[0-9A-Fa-f]{16}" placeholder="USR-…" value={reference} onChange={e => setReference(e.target.value)}/></Field>
            <Field label="Name you use for them" optional><input maxLength={60} value={nickname} onChange={e => setNickname(e.target.value)}/></Field>
            <div className="pl-formactions"><button className="ui-button ui-button-primary">{t('Send invitation')}</button></div>
          </div></section>
      </fieldset></form>}
      {tab === 3 && <div className="flow-wizard-form booking-pane"><PayDriversPane/></div>}
    </Compact.Provider>
  {photo && <div className="md-lightbox" role="dialog" aria-modal="true" aria-label={photo.name} onClick={() => setPhoto(null)}><figure><img src={photo.url} alt={photo.name} referrerPolicy="no-referrer"/><figcaption>{photo.name}</figcaption><button type="button" className="ui-button ui-button-secondary" onClick={() => setPhoto(null)}>{t('Close')}</button></figure></div>}
  </FlowShell></>
}
