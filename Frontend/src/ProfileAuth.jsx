import React, { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, setAuthFlow } from './api'
import { ErrorNotice } from './components'
import GoogleSignIn from './GoogleSignIn'

export default function ProfileAuth({ user }) {
  const navigate = useNavigate()
  const [methods, setMethods] = useState(null), [error, setError] = useState(null), [message, setMessage] = useState(''), [busy, setBusy] = useState(false), [password, setPassword] = useState(''), [confirm, setConfirm] = useState(false)
  useEffect(() => { let active = true; api('/users/me/auth-methods').then(result => { if (active) setMethods(result) }).catch(err => { if (active) setError(err) }); return () => { active = false } }, [])
  async function verify() {
    setBusy(true); setError(null)
    try {
      const result = await api('/users/me/email-verification', { method: 'POST', body: '{}' })
      if (result.status === 'verified') setMessage(result.message)
      else { setAuthFlow({ ...result, legacy: true }); navigate('/check-email') }
    } catch (err) { setError(err) }
    finally { setBusy(false) }
  }
  async function connect(value) {
    if (!confirm || (methods.password && !password)) throw new Error('Confirm your current password and the connection before continuing.')
    const result = await api('/users/me/google', { method: 'POST', body: JSON.stringify({ ...value, confirm: true, current_password: methods.password ? password : null }) })
    setPassword(''); setConfirm(false); setMethods({ ...methods, google: true }); setMessage(result.message)
  }
  return <section className="review-panel profile-auth"><h2>Sign-in and email verification</h2><p>Email: {user.email_verified_at ? 'Verified' : 'Unverified'}. Phone verification is separate.</p><ErrorNotice error={error}/>{message && <p role="status">{message}</p>}{!user.email_verified_at && user.email && <><p>Your existing account remains available while you verify your email.</p><button className="button" onClick={verify} disabled={busy}>Verify my email</button></>}{!user.email && <p>This account has no email address. Email verification and email recovery are unavailable.</p>}<p><Link to="/forgot-password">Reset password using a verified email</Link></p>{methods && <><p>Google: {methods.google ? 'Connected to this Travelly account' : 'Not connected'}</p>{!methods.google && <><p>Connect Google to this same account. Your roles and records stay together.</p>{methods.password && <label>Current password<input type="password" autoComplete="current-password" value={password} onChange={event => setPassword(event.target.value)}/></label>}<label className="terms-check"><input type="checkbox" checked={confirm} onChange={event => setConfirm(event.target.checked)}/><span>I confirm that I want to connect my Google sign-in to this account.</span></label>{confirm && (!methods.password || password) && <GoogleSignIn linking onCredential={connect}/>}</>}</>}</section>
}
