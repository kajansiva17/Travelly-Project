import React, { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Header, ErrorNotice, useNotice } from './components'
import { getAuthFlow, setAuthFlow, publicAuth, acceptAuthResult } from './api'
import { emailError, passwordErrors, passwordHint } from './authValidation'
import RegisterPhoneField from './RegisterPhoneField'
import { registrationPhone } from './registrationPhone'

function Shell({ children }) { return <><Header/><main className="auth-flow-panel" id="main">{children}</main></> }

export function CheckEmail() {
  const [flow, setFlow] = useState(getAuthFlow)
  const [error, setError] = useState(null), [busy, setBusy] = useState(false), [cooldown, setCooldown] = useState(0)
  useEffect(() => { if (!cooldown) return; const timer = setTimeout(() => setCooldown(cooldown - 1), 1000); return () => clearTimeout(timer) }, [cooldown])
  async function resend() {
    setBusy(true); setError(null)
    try { const result = await publicAuth('email/resend', { ticket: flow.verification_ticket }); const next = { ...flow, ...result }; setFlow(next); setAuthFlow(next); setCooldown(60) }
    catch (err) { setError(err); if (err.retryAfter) setCooldown(Number(err.retryAfter)) }
    finally { setBusy(false) }
  }
  return <Shell><h1>Check your email</h1><p>{flow?.legacy ? 'Your email is unverified. Open the Travelly verification link to confirm it; your existing account remains available.' : 'Your email is unverified. Open the Travelly verification link and confirm it before your first sign-in.'}</p><p role="status">{flow?.message || 'Sign in with your email and password, or Google, to request another verification link.'}</p><p>Links expire after 30 minutes and work once. A new link replaces the previous one.</p><ErrorNotice error={error}/>{flow?.verification_ticket && <button className="button" disabled={busy || cooldown > 0} onClick={resend}>{cooldown ? `Resend in ${cooldown}s` : busy ? 'Requesting email…' : 'Resend verification link'}</button>}<p><Link to="/login">Back to sign in</Link></p></Shell>
}

export function AuthLink({ reset = false }) {
  const [token, setToken] = useState(''), [error, setError] = useState(null), [message, setMessage] = useState(''), [busy, setBusy] = useState(false), [field, setField] = useState('')
  useEffect(() => {
    const value = new URLSearchParams(window.location.hash.slice(1)).get('token')
    if (value) { setToken(value); window.history.replaceState(null, '', window.location.pathname) }
  }, [])
  async function submit(event) {
    event.preventDefault(); setError(null); setField('')
    const password = new FormData(event.currentTarget).get('password')
    if (reset && passwordErrors(password).length) { setField(passwordErrors(password).join(' ')); return }
    setBusy(true)
    try { const result = await publicAuth(reset ? 'password/reset' : 'email/verify', reset ? { token, password } : { token }); setToken(''); setMessage(result.message); event.target?.reset?.() }
    catch (err) { setError(err); setField((err.fields || []).filter(f => f.field === 'password').map(f => f.message).join(' ')) }
    finally { setBusy(false) }
  }
  return <Shell><h1>{reset ? 'Choose a new password' : 'Verify your email'}</h1><ErrorNotice error={error}/>{message ? <p role="status">{message}</p> : token ? <form onSubmit={submit} noValidate>{reset ? <><label htmlFor="reset-password">New password</label><p id="reset-password-hint">{passwordHint}</p><input id="reset-password" name="password" type="password" autoComplete="new-password" aria-describedby="reset-password-hint reset-password-error" aria-invalid={Boolean(field)}/><p className="field-error" id="reset-password-error">{field}</p></> : <p>Confirm that you want to verify the email address for your Travelly account.</p>}<button className="button" disabled={busy}>{busy ? 'Please wait…' : reset ? 'Save new password' : 'Verify email'}</button></form> : <p>This page needs a valid link from your email. Request a new link if yours is missing, expired or already used.</p>}<p><Link to={reset ? '/forgot-password' : '/login'}>{reset ? 'Request a new reset link' : 'Sign in or request another verification link'}</Link></p>{reset && <Link to="/login">Back to sign in</Link>}</Shell>
}

export function ForgotPassword() {
  const [error, setError] = useState(null), [message, setMessage] = useState(''), [busy, setBusy] = useState(false), [field, setField] = useState('')
  async function submit(event) {
    event.preventDefault(); setError(null); const email = new FormData(event.currentTarget).get('email').trim(); const invalid = emailError(email); setField(invalid); if (invalid) return
    setBusy(true)
    try { setMessage((await publicAuth('password/forgot', { email })).message) }
    catch (err) { setError(err) }
    finally { setBusy(false) }
  }
  return <Shell><h1>Reset your password</h1><p>Recovery is available only through an email already verified on your Travelly account. Phone-only accounts and unverified email addresses cannot use this recovery method.</p><ErrorNotice error={error}/>{message && <p role="status">{message}</p>}<form noValidate onSubmit={submit}><label htmlFor="recovery-email">Email address</label><input id="recovery-email" name="email" type="email" autoComplete="email" aria-invalid={Boolean(field)} aria-describedby="recovery-error"/><p id="recovery-error" className="field-error">{field}</p><button className="button" disabled={busy}>{busy ? 'Requesting…' : 'Request reset link'}</button></form><p><Link to="/login">Back to sign in</Link></p></Shell>
}

export function GoogleCompletion() {
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
      const result = acceptAuthResult(await publicAuth('google/complete', { ticket: flow.ticket, full_name: data.full_name, phone_e164: number, preferred_language: 'en', accept_terms: true }))
      navigate(result.status === 'verification_required' ? '/check-email' : '/dashboard', { replace: true })
    } catch (err) { setError(err); setFields(Object.fromEntries((err.fields || []).map(f => [f.field, f.message]))) }
    finally { setBusy(false) }
  }
  if (!flow?.ticket || flow.status !== 'completion_required') return <Shell><h1>Complete your account</h1><p>Start Google sign-in again to continue.</p><Link to="/login">Sign in</Link></Shell>
  return <Shell><h1>Complete your Travelly account</h1><p>No Travelly account has been created yet. Confirm your details and terms to join as a Passenger.</p><p>Google email: {flow.email}</p><ErrorNotice error={error}/><form noValidate onSubmit={submit}><label htmlFor="google-full-name">Full name (Required)</label><input id="google-full-name" name="full_name" defaultValue={flow.full_name} maxLength={150} autoComplete="name" aria-invalid={Boolean(fields.full_name)}/>{fields.full_name && <p className="field-error">{fields.full_name}</p>}<RegisterPhoneField country={country} value={phone} onCountryChange={setCountry} onChange={setPhone} error={fields.phone_e164}/><p>Your mobile number is required. Google sign-in does not verify your phone.</p><label className="terms-check"><input name="accept_terms" type="checkbox"/><span>I agree to the <button type="button" className="inline-link" onClick={() => notice({ title: 'Terms and Privacy Policy', message: 'The official Terms and Privacy Policy documents have not yet been supplied for this preview.' })}>Terms and Privacy Policy</button></span></label>{fields.accept_terms && <p className="field-error">{fields.accept_terms}</p>}<button className="button" disabled={busy}>{busy ? 'Creating account…' : 'Create Passenger account'}</button></form></Shell>
}
