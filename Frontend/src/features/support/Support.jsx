import { useCallback, useEffect, useRef, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { t } from '../../i18n/language.js'
import { api, hasSession } from '../../services/api'
import { fieldErrorMap } from '../../services/fieldErrors.js'
import { Header, ErrorNotice, Icon } from '../../components/components'
import { FlowShell } from '../booking/flow/FlowParts'
import { Thumb } from '../booking/BookingCardParts'
import { Button, Chip, FormField, Input } from '../../components/ui'
import { useWorkspace } from '../../context/workspaceContext'
import { displayTime } from '../../hooks/workspaceData'

const CATEGORIES = [['PAYMENT', 'Payment'], ['BOOKING', 'Booking'], ['VEHICLE', 'Vehicle'], ['DRIVER', 'Driver'], ['REFUND', 'Refund'], ['ACCOUNT', 'Account'], ['APP', 'App problem'], ['OTHER', 'Other']]
const STATUS = { OPEN: 'Open', IN_PROGRESS: 'In progress', RESOLVED: 'Resolved', CLOSED: 'Closed' }
const CATEGORY_ICON = { PAYMENT: 'wallet', BOOKING: 'calendar', VEHICLE: 'car', DRIVER: 'user', REFUND: 'wallet', ACCOUNT: 'user', APP: 'alert', OTHER: 'help' }
const STATUS_TONE = { OPEN: 'warning', IN_PROGRESS: 'info', RESOLVED: 'success', CLOSED: 'muted' }
const label = (list, code) => t((list.find(item => item[0] === code) || [code, code])[1])

/* One conversation. The page reads it again every 5 seconds while it is open (there is no push connection). */
function Thread({ id, admin, onBack, onChanged }) {
  const [ticket, setTicket] = useState(null)
  const [error, setError] = useState(null)
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const end = useRef(null)
  const load = useCallback(() => api(`/support/tickets/${id}`, { cache: 'no-store' }).then(result => { setTicket(result); setError(null) }).catch(setError), [id])
  useEffect(() => {
    load()
    const timer = setInterval(() => { if (!document.hidden) load() }, 5000)
    return () => clearInterval(timer)
  }, [load])
  const count = ticket?.messages?.length || 0
  useEffect(() => { end.current?.scrollIntoView?.({ block: 'nearest' }) }, [count])

  async function send(event) {
    event.preventDefault()
    setBusy(true); setError(null)
    try {
      await api(`/support/tickets/${id}/messages`, { method: 'POST', body: JSON.stringify({ body: text.trim() }) })
      setText(''); await load(); onChanged()
    } catch (failure) { setError(failure) }
    finally { setBusy(false) }
  }

  async function change(path, body) {
    setError(null)
    try { await api(`/support/tickets/${id}/${path}`, { method: 'POST', body: JSON.stringify(body) }); await load(); onChanged() } catch (failure) { setError(failure) }
  }

  const closed = ticket?.status === 'CLOSED'
  return <div className="flow-wizard-form su-pane">
    <div className="su-top"><Button variant="secondary" onClick={onBack}>{t('Back to tickets')}</Button></div>
    <ErrorNotice error={error}/>
    {!ticket && !error && <p role="status">{t('Loading…')}</p>}
    {ticket && <>
      <section className={'bc-card su-head is-' + ticket.status.toLowerCase()}>
        <Thumb icon={CATEGORY_ICON[ticket.category] || 'help'} round size={48}/>
        <div className="bc-body"><strong className="bc-name">{ticket.subject}</strong>
          {admin && ticket.person && <span className="bc-sub">{ticket.person.name}{' · '}{ticket.person.reference}{' · '}{t(words(ticket.workspace_role))}</span>}</div>
        <div className="bc-side su-chips"><Chip tone={STATUS_TONE[ticket.status] || 'muted'}>{t(STATUS[ticket.status])}</Chip><Chip tone="muted">{label(CATEGORIES, ticket.category)}</Chip></div>
      </section>
      <div role="log" aria-live="polite" className="su-log">
        {ticket.messages.map(message => <div key={message.id} className={'su-msg' + (message.mine ? ' is-mine' : '')}>
          <div className="su-meta">{message.from_admin ? t('Support team') : (admin ? ticket.person?.name : t('You'))}{' · '}{displayTime(message.created_at)}</div>
          <div className="su-text">{message.body}</div>
        </div>)}
        <div ref={end}/>
      </div>
      {closed ? <p className="flow-note" role="status">{t('This ticket is closed.')}</p>
        : <form className="bc-card su-composer" onSubmit={send}>
          <FormField label={t('Message')}>
            {({ id: fieldId }) => <textarea id={fieldId} rows={2} maxLength={2000} value={text} onChange={event => setText(event.target.value)} placeholder={t('Type your message')}/>}
          </FormField>
          <div className="su-actions">
            <Button type="submit" disabled={busy || !text.trim()}>{busy ? t('Sending…') : t('Send')}</Button>
            {admin && ticket.status === 'OPEN' && <Button type="button" variant="secondary" onClick={() => change('status', { status: 'IN_PROGRESS' })}>{t('Mark in progress')}</Button>}
            {admin && ticket.status !== 'RESOLVED' && <Button type="button" variant="secondary" onClick={() => change('status', { status: 'RESOLVED' })}>{t('Mark resolved')}</Button>}
            {admin ? <Button type="button" variant="secondary" onClick={() => change('status', { status: 'CLOSED' })}>{t('Close ticket')}</Button>
              : <Button type="button" variant="secondary" onClick={() => change('close', {})}>{t('Close ticket')}</Button>}
          </div>
        </form>}
    </>}
  </div>
}

const words = value => String(value || '').toLowerCase().replace(/^./, letter => letter.toUpperCase())

/* Sidebar > Support (Passenger, Owner, Driver) and the Admin inbox: every ticket is a chat thread with the Travelly team. */
export default function Support({ admin = false }) {
  const { role } = useWorkspace()
  const [items, setItems] = useState(null)
  const [error, setError] = useState(null)
  const [selected, setSelected] = useState(null)
  const [composing, setComposing] = useState(false)
  const [filter, setFilter] = useState('ALL')
  const [form, setForm] = useState({ category: 'OTHER', subject: '', message: '' })
  const [busy, setBusy] = useState(false)
  const path = admin ? '/admin/support/tickets' : '/me/support/tickets'
  const load = useCallback(() => api(path, { cache: 'no-store' }).then(result => { setItems(result.items); setError(null) }).catch(setError), [path])
  useEffect(() => {
    if (!hasSession()) return undefined
    load()
    const timer = setInterval(() => { if (!document.hidden) load() }, 15000)
    return () => clearInterval(timer)
  }, [load])

  async function create(event) {
    event.preventDefault()
    setBusy(true); setError(null)
    try {
      const made = await api('/support/tickets', { method: 'POST', body: JSON.stringify({ role, category: form.category, subject: form.subject.trim(), message: form.message.trim() }) })
      setForm({ category: 'OTHER', subject: '', message: '' }); setComposing(false); setSelected(made.id); await load()
    } catch (failure) { setError(failure) }
    finally { setBusy(false) }
  }

  if (!hasSession()) return <Navigate to="/login" replace/>
  const fieldMsg = fieldErrorMap(error)
  const set = name => event => setForm(current => ({ ...current, [name]: event.target.value }))
  return <><Header/><FlowShell heading={admin ? t('Support inbox') : t('Support')} title={admin ? t('Messages from people who need help') : t('Talk to the Travelly team')} icon="help"
    info={admin ? t('Open a ticket to read it and reply. People get a notification when you reply.') : t('Open a ticket and chat with our team. We reply here, and you also get a notification.')}>
    {selected ? <Thread id={selected} admin={admin} onBack={() => { setSelected(null); load() }} onChanged={load}/>
      : composing ? <div className="flow-wizard-form su-pane"><form className="bc-card su-form" onSubmit={create}>
        <ErrorNotice error={error}/>
        <div className="su-pair">
          <FormField label={t('Category')}>
            {({ id }) => <select id={id} value={form.category} onChange={set('category')}>{CATEGORIES.map(([code, name]) => <option key={code} value={code}>{t(name)}</option>)}</select>}
          </FormField>
          <FormField label={t('Subject')} error={fieldMsg.subject}>
            {({ id }) => <Input id={id} maxLength={120} value={form.subject} onChange={set('subject')}/>}
          </FormField>
        </div>
        <FormField label={t('Message')} error={fieldMsg.message}>
          {({ id }) => <textarea id={id} rows={4} maxLength={2000} value={form.message} onChange={set('message')} placeholder={t('Type your message')}/>}
        </FormField>
        <div className="su-actions">
          <Button type="submit" disabled={busy || !form.subject.trim() || !form.message.trim()}>{busy ? t('Creating…') : t('Create ticket')}</Button>
          <Button type="button" variant="secondary" onClick={() => setComposing(false)}>{t('Cancel')}</Button>
        </div>
      </form></div>
        : <div className="flow-wizard-form su-pane">
          <ErrorNotice error={error}/>
          {!admin && <section className="bc-card su-hero">
            <span className="su-hero-icon"><Icon name="help" size={26}/></span>
            <div className="bc-body"><strong className="bc-name">{t('Talk to the Travelly team')}</strong><span className="bc-sub">{t('Open a ticket and chat with our team. We reply here, and you also get a notification.')}</span></div>
            <div className="bc-side"><Button onClick={() => setComposing(true)}>{t('New ticket')}</Button></div>
          </section>}
          {items === null && !error && <p role="status">{t('Loading…')}</p>}
          {items && <div className="bk-groups" role="tablist">{[['ALL', 'All'], ...Object.entries(STATUS)].map(([code, name]) => <Chip key={code} selected={filter === code} onClick={() => setFilter(code)}>{t(name)} ({code === 'ALL' ? items.length : items.filter(i => i.status === code).length})</Chip>)}</div>}
          {items && !items.length && <p className="flow-note" role="status">{admin ? t('No tickets yet.') : t('No tickets yet. Start a new one if you need help.')}</p>}
          {items && items.length > 0 && <div className="bk-list su-list">{items.filter(i => filter === 'ALL' || i.status === filter).map(item => <button type="button" key={item.id} className={'bc-card su-card is-' + item.status.toLowerCase()} onClick={() => setSelected(item.id)}>
            <Thumb icon={CATEGORY_ICON[item.category] || 'help'} round size={48}/>
            <div className="bc-body">
              <strong className="bc-name">{item.subject}</strong>
              <span className="su-last">{admin && item.person ? item.person.name + ' · ' : ''}{item.last_message}</span>
              <span className="bc-sub">{label(CATEGORIES, item.category)}{' · '}{displayTime(item.last_message_at)}</span>
            </div>
            <div className="bc-side su-chips">{item.unread && <Chip tone="danger">{t('New')}</Chip>}<Chip tone={STATUS_TONE[item.status] || 'muted'}>{t(STATUS[item.status])}</Chip></div>
          </button>)}</div>}
        </div>}
  </FlowShell></>
}
