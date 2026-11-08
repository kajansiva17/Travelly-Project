import { t } from '../../i18n/language.js'
import React, { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, setAuthFlow } from '../../services/api'
import { ErrorNotice } from '../../components/components'
import GoogleSignIn from './GoogleSignIn'
import {useWorkspace} from '../../context/workspaceContext'
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
  return <section className="review-panel profile-auth"><h2>{t("Sign-in and email verification")}</h2><p>{t("Email: ")}{user.email_verified_at ? t('Verified') : t('Unverified')}{t(". Phone verification is separate.")}</p><ErrorNotice error={error}/>{message && <p role="status">{t(message)}</p>}{!user.email_verified_at && user.email && <><p>{t("Your existing account remains available while you verify your email.")}</p><button className="button" onClick={verify} disabled={busy}>{t("Verify my email")}</button></>}{!user.email && <p>{t("This account has no email address. Email verification and email recovery are unavailable.")}</p>}<p><Link to={journeyLink('/forgot-password',role)}>{t("Reset password using a verified email")}</Link></p>{methods && <><p>{t("Google: ")}{methods.google ? t('Connected to this Travelly account') : t('Not connected')}</p>{!methods.google && <><p>{t("Connect Google to this same account. Your roles and records stay together.")}</p>{methods.password && <label>{t("Current password")}<input type="password" autoComplete="current-password" value={password} onChange={event => setPassword(event.target.value)}/></label>}<label className="terms-check"><input type="checkbox" checked={confirm} onChange={event => setConfirm(event.target.checked)}/><span>{t("I confirm that I want to connect my Google sign-in to this account.")}</span></label>{confirm && (!methods.password || password) && <GoogleSignIn linking onCredential={connect}/>}</>}</>}</section>
}
