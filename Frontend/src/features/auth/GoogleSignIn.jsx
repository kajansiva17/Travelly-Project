import { t, getLanguage } from '../../i18n/language.js'
import { useEffect, useId, useRef, useState } from 'react'
import { api, publicAuth } from '../../services/api'

let library
let referrerLease
function acquireGoogleOriginReferrer() {
  if (!referrerLease) {
    const existing = document.querySelector('meta[name="referrer"]')
    const meta = existing || document.createElement('meta')
    const previous = meta.getAttribute('content')
    meta.name = 'referrer'
    // GIS needs the public origin for its allowlist check. Never disclose a
    // page path, query, verification fragment or private document reference.
    meta.content = 'strict-origin'
    if (!existing) document.head.appendChild(meta)
    referrerLease = { meta, previous, created: !existing, count: 0 }
  }
  const lease = referrerLease
  lease.count++
  return () => {
    if (--lease.count) return
    if (lease.meta.content === 'strict-origin') {
      if (lease.created) lease.meta.remove()
      else if (lease.previous === null) lease.meta.removeAttribute('content')
      else lease.meta.content = lease.previous
    }
    referrerLease = null
  }
}
function loadGIS() {
  if (window.google?.accounts?.id) return Promise.resolve()
  if (!library) library = new Promise((resolve, reject) => {
    const script = document.createElement('script')
    const fail = () => {
      clearTimeout(timeout); script.remove(); library = null
      reject(new Error('Google sign-in could not load. Try again or use email and password.'))
    }
    const timeout = setTimeout(fail, 12000)
    script.src = 'https://accounts.google.com/gsi/client'; script.async = true
    script.referrerPolicy = 'strict-origin'
    script.onload = () => {
      if (!window.google?.accounts?.id) { fail(); return }
      clearTimeout(timeout); resolve()
    }
    script.onerror = fail
    document.head.appendChild(script)
  })
  return library
}

// Inline SVG from Google's official HTML button configurator; no image request.
// https://developers.google.com/identity/branding-guidelines#render-html-button-element
function GoogleIcon() {
  return <svg className="google-button-icon" viewBox="0 0 48 48" aria-hidden="true" focusable="false">
    <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
    <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
    <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
    <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
  </svg>
}

export default function GoogleSignIn({ onResult, linking = false, onCredential, journey = null }) {
  const language = getLanguage()
  const host = useRef(null), handler = useRef({ onResult, onCredential })
  const helperId = useId()
  handler.current = { onResult, onCredential }
  const [message, setMessage] = useState('Preparing Google sign-in…')
  const [unconfigured, setUnconfigured] = useState(false)
  const [canRetry, setCanRetry] = useState(false)
  const [retry, setRetry] = useState(0)
  const [ready, setReady] = useState(false)
  const [checking, setChecking] = useState(false)
  const inFlight = useRef(false)
  useEffect(acquireGoogleOriginReferrer, [])
  useEffect(() => {
    let active = true
    async function prepare() {
      setReady(false); setChecking(false); setUnconfigured(false); setCanRetry(false); setMessage('Preparing Google sign-in…')
      host.current?.replaceChildren()
      try {
        const config = linking ? await api('/users/me/google/challenge', { method: 'POST', body: '{}' }) : await publicAuth('google/challenge', {})
        await loadGIS()
        if (!active || !host.current) return
        window.google.accounts.id.initialize({ client_id: config.client_id, nonce: config.nonce, auto_select: false,
          callback: async ({ credential }) => {
            if (!active || inFlight.current) return
            inFlight.current = true
            setChecking(true)
            setMessage('Checking Google sign-in…')
            try {
              if (linking) await handler.current.onCredential({ credential, challenge: config.challenge })
              else await handler.current.onResult(await publicAuth('google', { credential, challenge: config.challenge, ...(['OWNER','DRIVER'].includes(journey)?{journey}:{}) }))
              // A completed callback may leave this page open (for example an
              // existing-email conflict). Its one-time challenge is now used.
              if (active) setRetry(value => value + 1)
            } catch (err) {
              if (active) {
                setReady(false); host.current?.replaceChildren()
                setMessage(err instanceof TypeError ? 'We could not reach Travelly. Please try again.' : err.message); setCanRetry(true)
              }
            } finally {
              inFlight.current = false
              if (active) setChecking(false)
            }
          } })
        host.current.replaceChildren()
        window.google.accounts.id.renderButton(host.current, { theme: 'outline', size: 'large', text: 'continue_with', locale: language, width: Math.min(350, host.current.parentElement.clientWidth || 250) })
        setReady(true)
        setMessage('')
      } catch (err) {
        if (!active) return
        const unavailable = err.code === 'GOOGLE_NOT_CONFIGURED'
        setUnconfigured(unavailable)
        setMessage(unavailable ? 'Google sign-in will be available soon.' : err instanceof TypeError ? 'We could not reach Travelly. Please try again.' : err.message)
        setCanRetry(!unavailable)
      }
    }
    prepare()
    return () => { active = false }
  }, [linking, retry, journey, language])
  return <div className="google-sign-in" aria-busy={checking}><div ref={host} inert={checking || !ready}/>{!ready && <button type="button" className="google-button-unavailable" disabled aria-describedby={message ? helperId : undefined}><GoogleIcon/><span>{t("Continue with Google")}</span></button>}{message && <p id={helperId} className={unconfigured ? 'google-availability-hint' : undefined} role="status">{t(message)}</p>}{canRetry && <button type="button" className="inline-link" onClick={() => setRetry(value => value + 1)}>{t("Retry Google sign-in")}</button>}</div>
}
