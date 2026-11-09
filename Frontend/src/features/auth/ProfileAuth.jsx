import { t } from '../../i18n/language.js'
import React, { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, setAuthFlow } from '../../services/api'
import { ErrorNotice } from '../../components/components'
import GoogleSignIn from './GoogleSignIn'
import {useWorkspace} from '../../context/workspaceContext'
import {Chip,FormField,Input} from '../../components/ui'
import {journeyLink} from './onboardingJourney'

export default function ProfileAuth({ user }) {
  const navigate = useNavigate()
  const role=useWorkspace()?.role
  const [methods, setMethods] = useState(null), [error, setError] = useState(null), [message, setMessage] = useState(''), [busy, setBusy] = useState(false), [password, setPassword] = useState(''), [confirm, setConfirm] = useState(false)
  useEffect(() => { let active = true; api('/users/me/auth-methods').then(result => { if (active) setMethods(result) }).catch(err => { if (active) setError(err) }); return () => { active = false } }, [])
  async function verify() {
    setBusy(true); setError(null)
    try {
      const result = await api('/users/me/email-verification', { method: 'POST', body: '{}' })
      if (result.status === 'verified') setMessage(result.message)
      else { setAuthFlow({ ...result, legacy: true, journey:role }); navigate(journeyLink('/check-email',role)) }
    } catch (err) { setError(err) }
    finally { setBusy(false) }
  }
  async function connect(value) {
    if (!confirm || (methods.password && !password)) throw new Error('Confirm your current password and the connection before continuing.')
    const result = await api('/users/me/google', { method: 'POST', body: JSON.stringify({ ...value, confirm: true, current_password: methods.password ? password : null }) })
    setPassword(''); setConfirm(false); setMethods({ ...methods, google: true }); setMessage(result.message)
  }
  const verified=Boolean(user.email_verified_at)
  return <section className="profile-auth auth-cards" aria-label={t("Account security")}>
    <article className="auth-card"><header><h3>{t("Sign-in & email")}</h3><Chip tone={verified?'success':'muted'}>{verified?t('Verified'):t('Unverified')}</Chip></header>
      <p>{user.email?<>{user.email} · {t("Phone verification is separate.")}</>:t("This account has no email address. Email verification and email recovery are unavailable.")}</p>
      <ErrorNotice error={error}/>{message && <p role="status" className="auth-status">{t(message)}</p>}
      {!verified && user.email && <p className="auth-hint">{t("Your existing account remains available while you verify your email.")}</p>}
      <div className="auth-row">{!verified && user.email && <button type="button" className="ui-button ui-button-primary" onClick={verify} disabled={busy}>{t("Verify my email")}</button>}<Link className="ui-button ui-button-secondary" to={journeyLink('/forgot-password',role)}>{t("Reset password using a verified email")}</Link></div>
    </article>
    <article className="auth-card"><header><h3>{t("Google connection")}</h3>{methods?<Chip tone={methods.google?'success':'muted'}>{methods.google?t('Connected'):t('Not connected')}</Chip>:<Chip tone="muted">{t("Checking…")}</Chip>}</header>
      {methods?.google?<p>{t("Connected to this Travelly account")}</p>:methods?<>
        <p className="auth-hint">{t("Connect Google to this same account. Your roles and records stay together.")}</p>
        <div className="auth-fields">{methods.password && <FormField label={t("Current password")}>{({id})=><Input id={id} type="password" autoComplete="current-password" value={password} onChange={event => setPassword(event.target.value)}/>}</FormField>}</div>
        <div className="auth-row"><label className="terms-check"><input type="checkbox" checked={confirm} onChange={event => setConfirm(event.target.checked)}/><span>{t("I confirm that I want to connect my Google sign-in to this account.")}</span></label>{confirm && (!methods.password || password) && <GoogleSignIn linking onCredential={connect}/>}</div></>:<p>{t("Checking…")}</p>}
    </article>
  </section>
}
