import { t } from '../../i18n/language.js'
import { useEffect, useRef, useState } from 'react'
import { api } from '../../services/api'
import { ErrorNotice } from '../../components/components'
import QrCode from '../../components/QrCode'
import { Button, Chip, FormField, Input } from '../../components/ui'
import { formatDateTime } from '../../i18n/dateTime.js'
import { fieldErrorMap, firstFieldMessage } from '../../services/fieldErrors.js'
import { confirmBody, enableBody, twoFactorMessage } from './loginFlow'

/* Two-step verification in Settings (contract 03SV, section 1). Backup codes live only in this component's state: shown once after
   they are made, with Copy and Download, and gone when the person is done. Never stored, never logged. */
const JSON_POST = (body = {}) => ({ method: 'POST', body: JSON.stringify(body) })

// Password (when the account has one) and a code, asked before a sensitive step. onSubmit(body) throws the server error.
export function ConfirmForm({ hasPassword, needCode = true, intro, submitLabel, onSubmit, onCancel, danger = false }) {
  const [password, setPassword] = useState(''), [code, setCode] = useState(''), [errors, setErrors] = useState({}), [error, setError] = useState(null), [busy, setBusy] = useState(false), sending = useRef(false)
  async function submit(event) {
    event.preventDefault()
    if (sending.current) return
    const invalid = {}
    if (hasPassword && !password) invalid.password = t('Enter your current password.')
    if (needCode && !code.trim()) invalid.code = t('Enter your authenticator code.')
    setErrors(invalid); setError(null)
    if (Object.keys(invalid).length) return
    sending.current = true; setBusy(true)
    try { await onSubmit(confirmBody({ hasPassword, password, code: needCode ? code : '' })) }
    catch (err) {
      const map = fieldErrorMap(err), friendly = twoFactorMessage(err)
      if (err.code === 'CURRENT_PASSWORD_WRONG') setErrors({ password: firstFieldMessage(err) || err.message })
      else if (err.code === 'TWO_FACTOR_CODE_WRONG' || err.code === 'TWO_FACTOR_CODE_REQUIRED') setErrors({ code: t(friendly) })
      else if (err.code === 'VALIDATION_ERROR' && (map.password || map.code)) setErrors({ password: map.password, code: map.code })
      else setError(friendly ? Object.assign(new Error(t(friendly)), { retryAfter: err.retryAfter, code: err.code }) : err)
      setCode('')
    } finally { sending.current = false; setBusy(false) }
  }
  return <form className="tk-pane" onSubmit={submit} noValidate>
    <ErrorNotice error={error}/>
    {intro && <p className="tk-line">{intro}</p>}
    <div className="tk-grid" style={{ '--cols': hasPassword && needCode ? 2 : 1 }}>
      {hasPassword && <FormField label={t('Current password')} required error={errors.password}>{({ id }) => <Input id={id} type="password" autoComplete="current-password" value={password} onChange={e => setPassword(e.target.value)}/>}</FormField>}
      {needCode && <FormField label={t('Code (app code or backup code)')} required error={errors.code}>{({ id }) => <Input id={id} name="code" autoComplete="one-time-code" autoCapitalize="characters" spellCheck="false" maxLength={20} value={code} onChange={e => setCode(e.target.value)}/>}</FormField>}
    </div>
    <div className="flow-actions"><Button type="button" variant="secondary" disabled={busy} onClick={onCancel}>{t('Cancel')}</Button><Button type="submit" variant={danger ? 'primary' : 'primary'} disabled={busy}>{busy ? t('Please wait…') : submitLabel}</Button></div>
  </form>
}

function BackupCodes({ codes, onDone }) {
  const [copied, setCopied] = useState(false), [saved, setSaved] = useState(false), [failed, setFailed] = useState(false)
  const text = codes.join('\n')
  async function copy() { try { await navigator.clipboard.writeText(text); setCopied(true); setFailed(false) } catch { setFailed(true) } }
  function download() {
    const url = URL.createObjectURL(new Blob([`${t('Travelly backup codes')}\n${t('Each code works once.')}\n\n${text}\n`], { type: 'text/plain' }))
    const link = Object.assign(document.createElement('a'), { href: url, download: 'travelly-backup-codes.txt' })
    document.body.appendChild(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 0)
    setSaved(true)
  }
  return <section className="tk-pane" aria-label={t('Backup codes')}>
    <p className="tk-line"><strong>{t('Save your backup codes now. They are shown only once.')}</strong> {t('Each code works once, instead of an app code.')}</p>
    <ul className="backup-codes" aria-label={t('Backup codes')}>{codes.map(code => <li key={code}><code>{code}</code></li>)}</ul>
    {failed && <p className="tk-line is-warn" role="alert">{t('The codes could not be copied. Select them and copy by hand, or download them.')}</p>}
    <div className="flow-actions"><span className="status-chips">{copied && <Chip tone="success" icon="check">{t('Copied')}</Chip>}</span>
      <span className="tk-bar"><Button type="button" variant="secondary" onClick={copy}>{t('Copy')}</Button><Button type="button" variant="secondary" onClick={download}>{t('Download')}</Button></span></div>
    <label className="terms-check"><input type="checkbox" checked={saved} onChange={e => setSaved(e.target.checked)}/><span>{t('I have saved my backup codes.')}</span></label>
    <div className="flow-actions"><span/><Button type="button" disabled={!saved} onClick={onDone}>{t('Done')}</Button></div>
  </section>
}

export default function TwoFactorSettings({ hasPassword }) {
  const [status, setStatus] = useState(null), [error, setError] = useState(null), [view, setView] = useState('status')   // status | setup | codes | off | newcodes
  const [setup, setSetup] = useState(null), [code, setCode] = useState(''), [codeError, setCodeError] = useState(''), [codes, setCodes] = useState(null), [busy, setBusy] = useState(false), working = useRef(false)
  const load = () => api('/users/me/2fa', { cache: 'no-store' }).then(setStatus).catch(setError)
  useEffect(() => { load() }, [])
  useEffect(() => () => setCodes(null), [])
  async function run(action) {
    if (working.current) return
    working.current = true; setBusy(true); setError(null)
    try { await action() } catch (err) { setError(err); if (err.code === 'TWO_FACTOR_ALREADY_ON' || err.code === 'TWO_FACTOR_NOT_ON') { setView('status'); load() } }
    finally { working.current = false; setBusy(false) }
  }
  const start = () => run(async () => { setSetup(await api('/users/me/2fa/setup', JSON_POST())); setCode(''); setCodeError(''); setView('setup') })
  async function enable(event) {
    event.preventDefault()
    if (!code.trim()) { setCodeError(t('Enter your authenticator code.')); return }
    if (working.current) return
    working.current = true; setBusy(true); setError(null); setCodeError('')
    try { const result = await api('/users/me/2fa/enable', JSON_POST(enableBody(code))); setStatus({ enabled: result.enabled, enabled_at: result.enabled_at, backup_codes_left: result.backup_codes_left }); setCodes(result.backup_codes || []); setSetup(null); setCode(''); setView('codes') }
    catch (err) {
      if (err.code === 'TWO_FACTOR_CODE_WRONG') setCodeError(firstFieldMessage(err) || t(twoFactorMessage(err)))
      else { setError(err); if (err.code === 'TWO_FACTOR_SETUP_REQUIRED') setView('status') }
      setCode('')
    } finally { working.current = false; setBusy(false) }
  }
  const turnOff = async body => { const result = await api('/users/me/2fa/disable', JSON_POST(body)); setStatus(result); setView('status') }
  const newCodes = async body => { const result = await api('/users/me/2fa/backup-codes', JSON_POST(body)); setStatus({ enabled: result.enabled, enabled_at: result.enabled_at, backup_codes_left: result.backup_codes_left }); setCodes(result.backup_codes || []); setView('codes') }
  if (!status && !error) return <p role="status">{t('Loading…')}</p>
  return <section className="tk-pane" aria-label={t('Two-step verification')}>
    <ErrorNotice error={error}/>
    {view === 'codes' && codes && <BackupCodes codes={codes} onDone={() => { setCodes(null); setView('status') }}/>}
    {view === 'setup' && setup && <form onSubmit={enable} noValidate className="two-factor-setup">
      <div className="two-factor-qr"><QrCode value={setup.otpauth_uri} size={150} label={t('Two-step verification QR code')}/></div>
      <div className="two-factor-steps">
        <p className="tk-line">{t('1. In your authenticator app, scan the QR code, or enter this key by hand:')}</p>
        <p className="tk-line"><code className="two-factor-secret">{setup.secret}</code></p>
        <p className="tk-line">{t('2. Enter the 6-digit code the app shows.')}</p>
        <FormField label={t('Code')} required error={codeError}>{({ id }) => <Input id={id} name="code" inputMode="numeric" autoComplete="one-time-code" maxLength={6} value={code} onChange={e => setCode(e.target.value)}/>}</FormField>
        <div className="flow-actions"><Button type="button" variant="secondary" disabled={busy} onClick={() => { setSetup(null); setView('status') }}>{t('Cancel')}</Button><Button type="submit" disabled={busy}>{busy ? t('Please wait…') : t('Turn on')}</Button></div>
      </div>
    </form>}
    {view === 'off' && <ConfirmForm hasPassword={hasPassword} intro={t('Enter your password and a code to turn two-step verification off.')} submitLabel={t('Turn off')} onSubmit={turnOff} onCancel={() => setView('status')}/>}
    {view === 'newcodes' && <ConfirmForm hasPassword={hasPassword} intro={t('Making new backup codes stops the old ones from working.')} submitLabel={t('Make new backup codes')} onSubmit={newCodes} onCancel={() => setView('status')}/>}
    {view === 'status' && status && <>
      <div className="tk-row"><div className="tk-row-main"><strong>{status.enabled ? t('Two-step verification is on') : t('Two-step verification is off')}</strong>
        <span>{status.enabled ? `${status.enabled_at ? formatDateTime(status.enabled_at) + ' · ' : ''}${t('Backup codes left: {value0}', { value0: status.backup_codes_left ?? 0 })}` : t('When it is on, signing in on a new device asks for a code from your authenticator app.')}</span></div>
        <div className="tk-row-actions">{status.enabled ? <Chip tone="success">{t('On')}</Chip> : <Chip tone="muted">{t('Off')}</Chip>}</div></div>
      <div className="flow-actions"><span/>{status.enabled
        ? <span className="tk-bar"><Button variant="secondary" disabled={busy} onClick={() => setView('newcodes')}>{t('Get new backup codes')}</Button><Button variant="secondary" disabled={busy} onClick={() => setView('off')}>{t('Turn off')}</Button></span>
        : <Button disabled={busy} onClick={start}>{busy ? t('Please wait…') : t('Turn on')}</Button>}</div>
    </>}
  </section>
}
