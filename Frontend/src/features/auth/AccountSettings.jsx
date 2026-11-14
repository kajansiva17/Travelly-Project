import { t } from '../../i18n/language.js'
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, acceptAuthResult } from '../../services/api'
import { ErrorNotice } from '../../components/components'
import { Button, Chip, FormField, Input } from '../../components/ui'
import { useWorkspace } from '../../context/workspaceContext'
import { usePaged, useRowCount } from '../booking/flow/FlowParts'
import { fieldErrorMap, firstFieldMessage } from '../../services/fieldErrors.js'
import { codeLabel } from '../../i18n/codeLabels.js'
import { formatDateTime } from '../../i18n/dateTime.js'
import { journeyLink } from './onboardingJourney'
import { passwordErrors } from './authValidation'
import TwoFactorSettings from './TwoFactorSettings'
import CloseAccount from './CloseAccount'

/* Account security in Settings (contract 03ST): signed-in devices, change password, notification preferences. The same endpoints
   serve every role. A POST without fields sends {}. */
const when = value => (value ? formatDateTime(value) : '—')

// Whether the account has a password (GET /users/me/auth-methods) and whether two-step verification is on (GET /users/me/2fa).
function useAccountFacts() {
  const [facts, setFacts] = useState(null), [error, setError] = useState(null)
  useEffect(() => { Promise.all([api('/users/me/auth-methods', { cache: 'no-store' }), api('/users/me/2fa', { cache: 'no-store' })]).then(([methods, tf]) => setFacts({ hasPassword: methods?.password !== false, twoFactorOn: Boolean(tf?.enabled) })).catch(setError) }, [])
  return { facts, error }
}
export function TwoStepTab() {
  const { facts, error } = useAccountFacts()
  if (error) return <ErrorNotice error={error}/>
  return facts ? <TwoFactorSettings hasPassword={facts.hasPassword}/> : <p role="status">{t('Loading…')}</p>
}
export function CloseAccountTab() {
  const { facts, error } = useAccountFacts()
  if (error) return <ErrorNotice error={error}/>
  return facts ? <CloseAccount hasPassword={facts.hasPassword} twoFactorOn={facts.twoFactorOn}/> : <p role="status">{t('Loading…')}</p>
}

export function Sessions() {
  const [items, setItems] = useState(null), [error, setError] = useState(null), [notice, setNotice] = useState(''), [busy, setBusy] = useState(''), working = useRef(false)
  const rows = usePaged(items || [], useRowCount(58))
  const load = () => api('/users/me/sessions', { cache: 'no-store' }).then(r => { setItems(r.items || []); setError(null) }).catch(setError)
  useEffect(() => { load() }, [])
  async function run(key, action, done) {
    if (working.current) return
    working.current = true; setBusy(key); setError(null); setNotice('')
    try { const text = await action(); setNotice(text || done) }
    catch (err) { setError(err); if (err.code === 'SESSION_NOT_FOUND') load() }
    finally { working.current = false; setBusy(''); await load() }
  }
  const signOut = item => run(item.id, async () => { await api(`/users/me/sessions/${encodeURIComponent(item.id)}`, { method: 'DELETE' }) }, t('That device was signed out.'))
  const signOutOthers = () => run('others', async () => { const r = await api('/users/me/sessions/revoke-others', { method: 'POST', body: '{}' }); return t('{value0} devices signed out.', { value0: r?.signed_out ?? 0 }) }, '')
  const others = (items || []).filter(item => !item.current)
  return <section className="tk-pane" aria-label={t('Signed-in devices')}>
    <ErrorNotice error={error}/>{notice && <p className="tk-line" role="status"><Chip tone="success" icon="check">{notice}</Chip></p>}
    {items === null && !error ? <p role="status">{t('Loading…')}</p> : !items?.length ? <p className="tk-line">{t('No signed-in devices to show.')}</p>
      : <div className="tk-rows">{rows.slice.map(item => <article className="tk-row" key={item.id}>
        <div className="tk-row-main"><strong>{item.device || t('Unknown device')}{item.current && <> <Chip tone="success">{t('This device')}</Chip></>}</strong>
          <span>{t('Signed in')} {when(item.signed_in_at)} · {t('Last active')} {when(item.last_active_at)}{item.ip_hint ? ` · ${item.ip_hint}` : ''}</span></div>
        <div className="tk-row-actions">{!item.current && <Button variant="secondary" disabled={Boolean(busy)} onClick={() => signOut(item)}>{busy === item.id ? t('Please wait…') : t('Sign out')}</Button>}</div>
      </article>)}</div>}
    <p className="tk-line">{t('A device that was signed in before this update may not appear until the person signs in again there.')}</p>
    <div className="flow-actions">{rows.pager || <span/>}<Button variant="secondary" disabled={Boolean(busy) || !others.length} onClick={signOutOthers}>{busy === 'others' ? t('Please wait…') : t('Sign out all other devices')}</Button></div>
  </section>
}

export function ChangePassword() {
  const role = useWorkspace()?.role
  const [current, setCurrent] = useState(''), [next, setNext] = useState(''), [again, setAgain] = useState('')
  const [errors, setErrors] = useState({}), [error, setError] = useState(null), [message, setMessage] = useState(''), [busy, setBusy] = useState(false), sending = useRef(false)
  async function save(event) {
    event.preventDefault()
    if (sending.current) return
    setError(null); setMessage('')
    const invalid = {}
    if (!current) invalid.current_password = t('Enter your current password.')
    const weak = passwordErrors(next)
    if (weak.length) invalid.new_password = weak.map(x => t(x)).join(' ')
    else if (next !== again) invalid.confirm_password = t('Your passwords do not match.')
    setErrors(invalid)
    if (Object.keys(invalid).length) return
    sending.current = true; setBusy(true)
    try {
      const result = await api('/users/me/password', { method: 'POST', body: JSON.stringify({ current_password: current, new_password: next }) })
      acceptAuthResult(result)   // new tokens: the old ones stop working, this device stays signed in
      setCurrent(''); setNext(''); setAgain(''); setMessage(result.message || t('Your password was changed.'))
    } catch (err) {
      const map = fieldErrorMap(err)
      if (err.code === 'CURRENT_PASSWORD_WRONG') setErrors({ current_password: firstFieldMessage(err) || err.message })
      else if (err.code === 'PASSWORD_UNCHANGED') setErrors({ new_password: firstFieldMessage(err) || err.message })
      else if (err.code === 'VALIDATION_ERROR' && Object.keys(map).length) setErrors({ current_password: map.current_password, new_password: map.new_password })
      else setError(err)
    } finally { sending.current = false; setBusy(false) }
  }
  return <form className="tk-pane" onSubmit={save} noValidate aria-label={t('Change password')}>
    <ErrorNotice error={error}/>
    {error?.code === 'NO_PASSWORD_SET' && <p className="tk-line"><Link to={journeyLink('/forgot-password', role)}>{t('Reset password using a verified email')}</Link></p>}
    <div className="tk-grid" style={{ '--cols': 3 }}>
      <FormField label={t('Current password')} required error={errors.current_password}>{({ id }) => <Input id={id} type="password" autoComplete="current-password" value={current} onChange={e => setCurrent(e.target.value)}/>}</FormField>
      <FormField label={t('New password')} required error={errors.new_password}>{({ id }) => <Input id={id} type="password" autoComplete="new-password" value={next} onChange={e => setNext(e.target.value)}/>}</FormField>
      <FormField label={t('Confirm new password')} required error={errors.confirm_password}>{({ id }) => <Input id={id} type="password" autoComplete="new-password" value={again} onChange={e => setAgain(e.target.value)}/>}</FormField>
    </div>
    <p className="tk-line">{t('Other devices are signed out when you change your password. This device stays signed in.')}</p>
    <div className="flow-actions"><span>{message && <Chip tone="success" icon="check">{message}</Chip>}</span><Button type="submit" disabled={busy}>{busy ? t('Saving…') : t('Change password')}</Button></div>
  </form>
}

export function NotificationPreferences() {
  const role = useWorkspace()?.role
  const [items, setItems] = useState(null), [error, setError] = useState(null), [busy, setBusy] = useState(false), working = useRef(false)
  useEffect(() => { api('/users/me/notification-preferences', { cache: 'no-store' }).then(r => setItems(r.items || [])).catch(setError) }, [])
  async function toggle(type, enabled) {
    if (working.current) return
    working.current = true; setBusy(true); setError(null)
    // The list of turned-off types is replaced as a whole: the ones already off, plus or minus this one.
    const muted = (items || []).filter(item => item.can_turn_off && (item.notification_type === type ? !enabled : !item.enabled)).map(item => item.notification_type)
    try { const r = await api('/users/me/notification-preferences', { method: 'PUT', body: JSON.stringify({ muted }) }); setItems(r.items || []) }
    catch (err) { setError(err) }
    finally { working.current = false; setBusy(false) }
  }
  // A Passenger never receives maintenance reminders, so that type is not listed for them.
  const shown = (items || []).filter(item => !(role === 'PASSENGER' && item.notification_type === 'MAINTENANCE_DUE'))
  return <section className="tk-pane" aria-label={t('Notification preferences')}>
    <ErrorNotice error={error}/>
    {items === null && !error ? <p role="status">{t('Loading…')}</p> : <div className="tk-rows">{shown.map(item => <article className="tk-row" key={item.notification_type}>
      <div className="tk-row-main"><strong>{codeLabel(item.notification_type)}</strong></div>
      <div className="tk-row-actions">{item.can_turn_off
        ? <label className="ui-switch"><input type="checkbox" role="switch" checked={item.enabled} disabled={busy} onChange={e => toggle(item.notification_type, e.target.checked)}/><span className="ui-switch-track" aria-hidden="true"/><span>{item.enabled ? t('On') : t('Off')}</span></label>
        : <Chip tone="muted">{t('Always on')}</Chip>}</div>
    </article>)}</div>}
    <p className="tk-line">{t('Only road alerts and maintenance reminders can be turned off. Bookings, payments, refunds, trips and other important notices always arrive.')}</p>
  </section>
}
