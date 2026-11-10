import { t, getLanguage } from '../../i18n/language.js'
import React, { useEffect, useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { Header, ErrorNotice, Icon, useNotice } from '../../components/components'
import { AuthLayout, Field } from './AuthLayout'
import { api, hasSession, getAuthFlow, setAuthFlow, publicAuth, acceptAuthResult } from '../../services/api'
import {authJourney as journeyRole,journeyLink} from './onboardingJourney'
import { emailError, passwordErrors, passwordHint } from './authValidation'
import RegisterPhoneField from './RegisterPhoneField'
import { registrationPhone } from './registrationPhone'
import {loginDestination} from '../../routes/workspaceRoutes'

function Shell({ children }) { return <><Header auth/><main className="auth-flow-panel" id="main">{children}</main></> }

export function CheckEmail() {
  const journey=journeyRole(useLocation().search)
  const [flow, setFlow] = useState(getAuthFlow)
  const [error, setError] = useState(null), [busy, setBusy] = useState(false), [cooldown, setCooldown] = useState(0)
  useEffect(() => { if (!cooldown) return; const timer = setTimeout(() => setCooldown(cooldown - 1), 1000); return () => clearTimeout(timer) }, [cooldown])
  async function resend() {
    setBusy(true); setError(null)
    try { const result = await publicAuth('email/resend', { ticket: flow.verification_ticket }); const next = { ...flow, ...result }; setFlow(next); setAuthFlow(next); setCooldown(60) }
    catch (err) { setError(err); if (err.retryAfter) setCooldown(Number(err.retryAfter)) }
    finally { setBusy(false) }
  }
  return <Shell><h1>{t("Check your email")}</h1><p>{flow?.legacy ? t('Your email is unverified. Open the Travelly verification link to confirm it; your existing account remains available.') : t('Open your Travelly verification link to verify your email and continue.')}</p><p role="status">{t(flow?.message) || t('Sign in with your email and password, or Google, to request another verification link.')}</p><p>{t("Links expire after 30 minutes and work once. A new link replaces the previous one.")}</p><ErrorNotice error={error}/>{flow?.verification_ticket && <button className="button" disabled={busy || cooldown > 0} onClick={resend}>{cooldown ? t("Resend in {value0}s", {value0: cooldown}) : busy ? t('Requesting email…') : t('Resend verification link')}</button>}<p><Link to={journeyLink('/login',journey)}>{t("Back to sign in")}</Link></p></Shell>
}

export function AuthLink({ reset = false }) {
  const location=useLocation(),navigate=useNavigate(),journey=reset?(journeyRole(location.search)||getAuthFlow()?.journey):(['OWNER','DRIVER'].includes(getAuthFlow()?.journey)?getAuthFlow().journey:null)
  const [token, setToken] = useState(''), [error, setError] = useState(null), [message, setMessage] = useState(''), [busy, setBusy] = useState(false), [field, setField] = useState('')
  useEffect(() => {
    const value = new URLSearchParams(window.location.hash.slice(1)).get('token')
    if (value) { setToken(value); window.history.replaceState(null, '', window.location.pathname+window.location.search) }
  }, [])
  async function submit(event) {
    event.preventDefault(); setError(null); setField('')
    const password = new FormData(event.currentTarget).get('password')
    if (reset && passwordErrors(password).length) { setField(passwordErrors(password).join(' ')); return }
    setBusy(true)
    try {
      const activeUser=!reset&&hasSession()?await api('/users/me'):null
      const result = await publicAuth(reset ? 'password/reset' : 'email/verify', reset ? { token, password } : { token })
      setToken('');event.target?.reset?.()
      if(!reset&&result.access_token){
        if(activeUser&&activeUser.id!==result.verified_user_id){setMessage('Email verified. You are signed in to another account; sign out before continuing with this account.');return}
        acceptAuthResult(result);const [user,roles]=await Promise.all([api('/users/me'),api('/users/me/roles')]);navigate(loginDestination(user,roles.items||[],result.journey),{replace:true});return
      }
      setMessage(result.message)
    }
    catch (err) { setError(err); setField((err.fields || []).filter(f => f.field === 'password').map(f => f.message).join(' ')) }
    finally { setBusy(false) }
  }
  return <Shell><h1>{reset ? t('Choose a new password') : t('Verify your email')}</h1><ErrorNotice error={error}/>{message ? <p role="status">{t(message)}</p> : token ? <form onSubmit={submit} noValidate>{reset ? <><label htmlFor="reset-password">{t("New password")}</label><p id="reset-password-hint">{t(passwordHint)}</p><input id="reset-password" name="password" type="password" autoComplete="new-password" aria-describedby="reset-password-hint reset-password-error" aria-invalid={Boolean(field)}/><p className="field-error" id="reset-password-error">{t(field)}</p></> : <p>{t("Confirm that you want to verify the email address for your Travelly account.")}</p>}<button className="button" disabled={busy}>{busy ? t('Please wait…') : reset ? t('Save new password') : t('Verify email')}</button></form> : <p>{t("This page needs a valid link from your email. Request a new link if yours is missing, expired or already used.")}</p>}<p><Link to={journeyLink(reset ? '/forgot-password' : '/login',journey)}>{reset ? t('Request a new reset link') : t('Sign in or request another verification link')}</Link></p>{reset && <Link to={journeyLink('/login',journey)}>{t("Back to sign in")}</Link>}</Shell>
}

export function ForgotPassword() {
  const journey=journeyRole(useLocation().search)
  const [error, setError] = useState(null), [message, setMessage] = useState(''), [busy, setBusy] = useState(false), [field, setField] = useState('')
  async function submit(event) {
    event.preventDefault(); setError(null); const email = new FormData(event.currentTarget).get('email').trim(); const invalid = emailError(email); setField(invalid); if (invalid) return
    setBusy(true)
    try { setAuthFlow({journey}); setMessage((await publicAuth('password/forgot', { email })).message) }
    catch (err) { setError(err) }
    finally { setBusy(false) }
  }
  return <AuthLayout variant="login" title={t("Reset your password")} subtitle={t("We will email you a link to choose a new one.")} tip={t("Recovery is available only through an email already verified on your Travelly account. Phone-only accounts and unverified email addresses cannot use this recovery method.")}>
    <ErrorNotice error={error}/>{message && <p className="auth-status" role="status">{t(message)}</p>}
    <form className="auth-credentials-form" noValidate onSubmit={submit} aria-label={t("Reset your password")}>
      <Field name="email" label="Email address" icon="mail" type="email" placeholder="Email address" autoComplete="email" error={field || undefined}/>
      <button type="submit" className="ui-button ui-button-primary auth-submit" disabled={busy}>{busy ? t('Requesting…') : <>{t('Request reset link')}<Icon name="arrow" size={20}/></>}</button>
    </form>
    <p className="auth-switch login-switch"><Link to={journeyLink('/login',journey)}>{t("Back to sign in")}</Link></p>
  </AuthLayout>
}

export function GoogleCompletion() {
  const journey=journeyRole(useLocation().search)
  const navigate = useNavigate(), notice = useNotice(), flow = getAuthFlow()
  const [country, setCountry] = useState('LK'), [phone, setPhone] = useState(''), [fields, setFields] = useState({}), [error, setError] = useState(null), [busy, setBusy] = useState(false)
  async function submit(event) {
    event.preventDefault(); setFields({}); setError(null)
    const data = Object.fromEntries(new FormData(event.currentTarget))
    let number
    try { number = registrationPhone(country, phone); if (!number) throw new Error('Enter your mobile number.') }
    catch (err) { setFields({ phone_e164: err.message }); return }
    if (!data.full_name.trim()) { setFields({ full_name: 'Enter your full name.' }); return }
    if (!data.accept_terms) { setFields({ accept_terms: 'Agree to the Terms and Privacy Policy to continue.' }); return }
    setBusy(true)
    try {
      const result = acceptAuthResult(await publicAuth('google/complete', { ticket: flow.ticket, full_name: data.full_name, phone_e164: number, preferred_language: getLanguage(), accept_terms: true, ...(['OWNER','DRIVER'].includes(journey)?{journey}:{}) }))
      if(!result.access_token)setAuthFlow({...result,journey})
      if(result.status==='verification_required')navigate(journeyLink('/check-email',journey),{replace:true})
      else {const [user,roles]=await Promise.all([api('/users/me'),api('/users/me/roles')]);navigate(loginDestination(user,roles.items||[],journey),{replace:true})}
    } catch (err) { setError(err); setFields(Object.fromEntries((err.fields || []).map(f => [f.field, f.message]))) }
    finally { setBusy(false) }
  }
  if(journey==='ADMIN')return <Shell><h1>{t("Admin sign-in")}</h1><p>{t("Use your existing approved Admin account.")}</p><Link to={journeyLink('/login',journey)}>{t("Sign in")}</Link></Shell>
  if (!flow?.ticket || flow.status !== 'completion_required') return <Shell><h1>{t("Complete your account")}</h1><p>{t("Start Google sign-in again to continue.")}</p><Link to={journeyLink('/login',journey)}>{t("Sign in")}</Link></Shell>
  return <Shell><h1>{t("Complete your Travelly account")}</h1><p>{t("No Travelly account has been created yet. Confirm your details and terms to join as a Passenger.")}</p><p>{t("Google email: ")}{flow.email}</p><ErrorNotice error={error}/><form noValidate onSubmit={submit}><label htmlFor="google-full-name">{t("Full name (Required)")}</label><input id="google-full-name" name="full_name" defaultValue={flow.full_name} maxLength={150} autoComplete="name" aria-invalid={Boolean(fields.full_name)}/>{fields.full_name && <p className="field-error">{fields.full_name}</p>}<RegisterPhoneField country={country} value={phone} onCountryChange={setCountry} onChange={setPhone} error={fields.phone_e164}/><p>{t("Your mobile number is required. Google sign-in does not verify your phone.")}</p><label className="terms-check"><input name="accept_terms" type="checkbox"/><span>{t("I agree to the ")}<button type="button" className="inline-link" onClick={() => notice({ title: 'Terms and Privacy Policy', message: 'The official Terms and Privacy Policy documents have not yet been supplied for this preview.' })}>{t("Terms and Privacy Policy")}</button></span></label>{fields.accept_terms && <p className="field-error">{t(fields.accept_terms)}</p>}<button className="button" disabled={busy}>{busy ? t('Creating account…') : t('Create Passenger account')}</button></form></Shell>
}
