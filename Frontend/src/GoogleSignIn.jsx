import React, { useEffect, useRef, useState } from 'react'
import { api, publicAuth } from './api'

let library
function loadGIS() {
  if (window.google?.accounts?.id) return Promise.resolve()
  if (!library) library = new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = 'https://accounts.google.com/gsi/client'; script.async = true
    script.onload = resolve; script.onerror = () => { script.remove(); library = null; reject(new Error('Google sign-in could not load. Try again or use email and password.')) }
    document.head.appendChild(script)
  })
  return library
}

export default function GoogleSignIn({ onResult, linking = false, onCredential }) {
  const host = useRef(null), handler = useRef({ onResult, onCredential })
  handler.current = { onResult, onCredential }
  const [message, setMessage] = useState('Preparing Google sign-in…')
  const [retry, setRetry] = useState(0)
  useEffect(() => {
    let active = true
    async function prepare() {
      try {
        const config = linking ? await api('/users/me/google/challenge', { method: 'POST', body: '{}' }) : await publicAuth('google/challenge', {})
        await loadGIS()
        if (!active || !host.current) return
        window.google.accounts.id.initialize({ client_id: config.client_id, nonce: config.nonce, auto_select: false,
          callback: async ({ credential }) => {
            if (!active) return
            setMessage('Checking Google sign-in…')
            try {
              if (linking) await handler.current.onCredential({ credential, challenge: config.challenge })
              else handler.current.onResult(await publicAuth('google', { credential, challenge: config.challenge }))
            } catch (err) { if (active) setMessage(err.message) }
          } })
        host.current.replaceChildren()
        window.google.accounts.id.renderButton(host.current, { theme: 'outline', size: 'large', text: 'continue_with', width: Math.min(350, host.current.clientWidth || 250) })
        setMessage('')
      } catch (err) { if (active) setMessage(err.message) }
    }
    prepare()
    return () => { active = false }
  }, [linking, retry])
  return <div className="google-sign-in"><div ref={host}/>{message && <p role="status">{message}</p>}<button type="button" className="inline-link" onClick={() => setRetry(retry + 1)}>Retry Google sign-in</button></div>
}
