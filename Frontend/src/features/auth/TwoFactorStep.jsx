import { t } from '../../i18n/language.js'
import { useRef, useState } from 'react'
import { ErrorNotice } from '../../components/components'
import { Button, FormField, Input } from '../../components/ui'
import { challengeExpired, codeMinutes, twoFactorMessage } from './loginFlow'

/* "Enter your code" (contract 03SV): the second step of signing in (email or Google). The code is an app code or a backup code, so the
   field accepts text; it is never stored or logged. onSubmit(code) throws the server error; an expired step goes back to sign-in. */
export default function TwoFactorStep({ expiresIn, message, onSubmit, onBack, onExpired }) {
  const [code, setCode] = useState(''), [error, setError] = useState(null), [busy, setBusy] = useState(false), sending = useRef(false)
  async function submit(event) {
    event.preventDefault()
    if (sending.current) return
    if (!code.trim()) { setError(new Error('Enter your authenticator code.')); return }
    sending.current = true; setBusy(true); setError(null)
    try { await onSubmit(code) }
    catch (err) {
      if (challengeExpired(err)) { onExpired(err); return }
      setError(err); setCode('')
    } finally { sending.current = false; setBusy(false) }
  }
  const friendly = error && twoFactorMessage(error)
  return <form className="auth-credentials-form" onSubmit={submit} noValidate aria-label={t('Enter your code')}>
    {friendly ? <div className="notice error" role="alert">{t(friendly)}{error.retryAfter && <span>{t(' Try again in ')}{error.retryAfter}{t(' seconds.')}</span>}</div> : <ErrorNotice error={error}/>}
    <p className="auth-hint">{t('Open your authenticator app and enter the 6-digit code, or enter one of your backup codes.')} {t('You have {value0} minutes to enter it.', { value0: codeMinutes(expiresIn) })}</p>
    <FormField label={t('Code')} required>{({ id }) => <Input id={id} name="code" autoFocus autoComplete="one-time-code" autoCapitalize="characters" spellCheck="false" maxLength={20} value={code} onChange={e => setCode(e.target.value)}/>}</FormField>
    <button type="submit" className="ui-button ui-button-primary auth-submit" disabled={busy}>{busy ? t('Checking…') : t('Continue')}</button>
    <Button type="button" variant="secondary" disabled={busy} onClick={onBack}>{t('Back to sign in')}</Button>
  </form>
}
