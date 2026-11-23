import { useCallback, useEffect, useRef, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { t } from '../../i18n/language.js'
import { api, hasSession } from '../../services/api'
import { fieldErrorMap } from '../../services/fieldErrors.js'
import { Header, ErrorNotice } from '../../components/components'
import { FlowShell } from '../booking/flow/FlowParts'
import { Button, Chip, FormField, Input } from '../../components/ui'
import { useWorkspace } from '../../context/workspaceContext'
import { displayTime } from '../../hooks/workspaceData'

const CATEGORIES = [['PAYMENT', 'Payment'], ['BOOKING', 'Booking'], ['VEHICLE', 'Vehicle'], ['DRIVER', 'Driver'], ['REFUND', 'Refund'], ['ACCOUNT', 'Account'], ['APP', 'App problem'], ['OTHER', 'Other']]
const STATUS = { OPEN: 'Open', IN_PROGRESS: 'In progress', RESOLVED: 'Resolved', CLOSED: 'Closed' }
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
  return <>
    <div className="flow-actions"><Button variant="secondary" onClick={onBack}>{t('Back to tickets')}</Button></div>
    <ErrorNotice error={error}/>
    {!ticket && !error && <p role="status">{t('Loading…')}</p>}
    {ticket && <>
      <p><strong>{ticket.subject}</strong>{' '}<Chip tone="muted">{t(STATUS[ticket.status])}</Chip>{' '}<Chip tone="muted">{label(CATEGORIES, ticket.category)}</Chip></p>
      {admin && ticket.person && <p className="flow-note">{ticket.person.name}{' · '}{ticket.person.reference}{' · '}{t(words(ticket.workspace_role))}</p>}
      <div role="log" aria-live="polite" style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 420, overflowY: 'auto', padding: '8px 0' }}>
        {ticket.messages.map(message => <div key={message.id} style={{ alignSelf: message.mine ? 'flex-end' : 'flex-start', maxWidth: '80%', padding: '8px 12px', borderRadius: 12, background: message.mine ? 'rgba(46,111,230,.12)' : 'rgba(128,128,128,.14)' }}>
          <div style={{ fontSize: 12, opacity: .7 }}>{message.from_admin ? t('Support team') : (admin ? ticket.person?.name : t('You'))}{' · '}{displayTime(message.created_at)}</div>
          <div style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{message.body}</div>
        </div>)}
        <div ref={end}/>
      </div>
      {closed ? <p className="flow-note" role="status">{t('This ticket is closed.')}</p>
        : <form className="flow-fields" onSubmit={send}>
          <FormField label={t('Message')}>
            {({ id: fieldId }) => <textarea id={fieldId} rows={3} maxLength={2000} value={text} onChange={event => setText(event.target.value)} placeholder={t('Type your message')}/>}
          </FormField>
          <div className="flow-actions">
            <Button type="submit" disabled={busy || !text.trim()}>{busy ? t('Sending…') : t('Send')}</Button>
            {admin && ticket.status === 'OPEN' && <Button type="button" variant="secondary" onClick={() => change('status', { status: 'IN_PROGRESS' })}>{t('Mark in progress')}</Button>}
            {admin && ticket.status !== 'RESOLVED' && <Button type="button" variant="secondary" onClick={() => change('status', { status: 'RESOLVED' })}>{t('Mark resolved')}</Button>}
            {admin ? <Button type="button" variant="secondary" onClick={() => change('status', { status: 'CLOSED' })}>{t('Close ticket')}</Button>
              : <Button type="button" variant="secondary" onClick={() => change('close', {})}>{t('Close ticket')}</Button>}
          </div>
        </form>}
    </>}
  </>
}

const words = value => String(value || '').toLowerCase().replace(/^./, letter => letter.toUpperCase())

/* Sidebar > Support (Passenger, Owner, Driver) and the Admin inbox: every ticket is a chat thread with the Travelly team. */
export default function Support({ admin = false }) {
  const { role } = useWorkspace()
  const [items, setItems] = useState(null)
  const [error, setError] = useState(null)
  const [selected, setSelected] = useState(null)
  const [composing, setComposing] = useState(false)
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
      : composing ? <form className="flow-fields" onSubmit={create}>
        <ErrorNotice error={error}/>
        <FormField label={t('Category')}>
          {({ id }) => <select id={id} value={form.category} onChange={set('category')}>{CATEGORIES.map(([code, name]) => <option key={code} value={code}>{t(name)}</option>)}</select>}
        </FormField>
        <FormField label={t('Subject')} error={fieldMsg.subject}>
          {({ id }) => <Input id={id} maxLength={120} value={form.subject} onChange={set('subject')}/>}
        </FormField>
        <FormField label={t('Message')} error={fieldMsg.message}>
          {({ id }) => <textarea id={id} rows={4} maxLength={2000} value={form.message} onChange={set('message')} placeholder={t('Type your message')}/>}
        </FormField>
        <div className="flow-actions">
          <Button type="submit" disabled={busy || !form.subject.trim() || !form.message.trim()}>{busy ? t('Creating…') : t('Create ticket')}</Button>
          <Button type="button" variant="secondary" onClick={() => setComposing(false)}>{t('Cancel')}</Button>
        </div>
      </form>
        : <>
          <ErrorNotice error={error}/>
          {!admin && <div className="flow-actions"><Button onClick={() => setComposing(true)}>{t('New ticket')}</Button></div>}
          {items === null && !error && <p role="status">{t('Loading…')}</p>}
          {items && !items.length && <p className="flow-note" role="status">{admin ? t('No tickets yet.') : t('No tickets yet. Start a new one if you need help.')}</p>}
          {items && items.map(item => <button type="button" key={item.id} className="dash-row" onClick={() => setSelected(item.id)}
            style={{ display: 'flex', width: '100%', gap: 12, justifyContent: 'space-between', alignItems: 'center', textAlign: 'left', padding: '10px 0', background: 'none', border: 0, cursor: 'pointer', color: 'inherit' }}>
            <div style={{ minWidth: 0 }}>
              <strong>{item.subject}</strong>
              <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{admin && item.person ? item.person.name + ' · ' : ''}{item.last_message}</div>
              <div style={{ fontSize: 12, opacity: .7 }}>{label(CATEGORIES, item.category)}{' · '}{displayTime(item.last_message_at)}</div>
            </div>
            <div>{item.unread && <Chip tone="muted">{t('New')}</Chip>}{' '}<Chip tone="muted">{t(STATUS[item.status])}</Chip></div>
          </button>)}
        </>}
  </FlowShell></>
}
