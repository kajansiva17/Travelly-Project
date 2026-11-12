const base = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')
export const mediaUrl=path=>`${base}${path}`
const sessionListeners = new Set()
export function subscribeSession(listener) { sessionListeners.add(listener); return () => sessionListeners.delete(listener) }
function sessionChanged() { sessionListeners.forEach(listener => listener()) }
let credentials = null
let refreshing = null
let generation = 0
let authFlow = null
export function setAuthFlow(value) { authFlow = value }
export function getAuthFlow() { return authFlow }

// Why the last session ended: 'logout' (the person chose to leave) or 'expired' (it could not be renewed).
let endReason = null
export function sessionEndReason() { return endReason }
export function clearSession(reason = 'expired') { credentials = null; authFlow = null; generation += 1; endReason = reason; sessionChanged() }
export function hasSession() { return Boolean(credentials) }

async function send(path, options = {}, accessToken) {
  const { timeoutMs = 20_000, signal: callerSignal, ...requestOptions } = options
  const controller = new AbortController()
  const abortForCaller = () => controller.abort(callerSignal?.reason)
  if (callerSignal?.aborted) abortForCaller()
  else callerSignal?.addEventListener('abort', abortForCaller, { once: true })
  const timeout = setTimeout(() => controller.abort('timeout'), timeoutMs)
  let response
  try {
    response = await fetch(`${base}/api/v1${path}`, {
      ...requestOptions,
      signal: controller.signal,
      headers: { ...(requestOptions.body && !(requestOptions.body instanceof FormData) ? { 'Content-Type': 'application/json' } : {}),
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}), ...requestOptions.headers },
    })
  } catch (error) {
    if (controller.signal.aborted && !callerSignal?.aborted) {
      const timeoutError = new Error('Travelly is taking too long to respond. Please try again.')
      timeoutError.code = 'API_TIMEOUT'
      throw timeoutError
    }
    throw error
  } finally {
    clearTimeout(timeout)
    callerSignal?.removeEventListener('abort', abortForCaller)
  }
  const data = response.ok && options.binary ? await response.blob() : response.status === 204 ? null : await response.json().catch(() => ({}))
  if (!response.ok) {
    const error = new Error(data.message || 'Unable to complete your request. Please try again.')
    error.status = response.status
    error.code = data.code
    error.fields = data.field_errors || []
    error.retryAfter = response.headers.get('Retry-After')
    throw error
  }
  return data
}

export const register = (data) => send('/auth/register', { method: 'POST', body: JSON.stringify(data) })
export const publicAuth = (path, data) => send('/auth/' + path, { method: 'POST', body: JSON.stringify(data) })
export const publicRead = path => send(path)
export const publicRequest = (path, data) => send(path, { method: 'POST', body: JSON.stringify(data) })
export function acceptAuthResult(result) {
  if (result.access_token && result.refresh_token) { credentials = result; generation += 1; authFlow = null; endReason = null; sessionChanged() }
  else { authFlow = result }
  return result
}

export async function login(data) {
  const tokens = await send('/auth/login', { method: 'POST', body: JSON.stringify(data) })
  return acceptAuthResult(tokens)
}

// The refresh token lives in an HttpOnly cookie that page scripts cannot read; it rotates on every use.
// Requests send an empty body so the newest cookie is always used, and a cross-tab lock makes tabs take turns,
// so two tabs never present the same token (which the server treats as a replay and ends the session).
function renew(timeoutMs) {
  const call = () => send('/auth/refresh', { method: 'POST', body: '{}', ...(timeoutMs ? { timeoutMs } : {}) })
  return navigator.locks?.request ? navigator.locks.request('travelly-session-refresh', call) : call()
}

async function refreshSession() {
  if (!credentials) throw new Error('Please sign in again.')
  if (!refreshing) {
    const version = generation
    refreshing = renew()
      .then((tokens) => { if (generation === version) credentials = tokens; return tokens })
      .catch((error) => { if (generation === version && [401, 403].includes(error.status)) clearSession(); throw error })
      .finally(() => { refreshing = null })
  }
  return refreshing
}

// On page load: sign back in from the session cookie if there is one. Never throws.
export async function restoreSession() {
  if (credentials) return true
  const version = generation
  try {
    const tokens = await renew(5_000)
    if (generation === version && !credentials) acceptAuthResult(tokens)
    return true
  } catch { return false }
}

export async function api(path, options = {}) {
  if (!credentials) { const error = new Error('Please sign in again.'); error.status = 401; throw error }
  try { return await send(path, options, credentials.access_token) }
  catch (error) {
    if (error.status !== 401) throw error
    await refreshSession()
    if (!credentials) throw error
    return send(path, options, credentials.access_token)
  }
}

export async function logout() {
  // Settle a concurrent refresh before ending the session.
  if (refreshing) await refreshing.catch(() => {})
  if (!credentials) return
  try {
    await send('/auth/logout', { method: 'POST', body: '{}' }, credentials.access_token)
  } catch (error) {
    if (error.status !== 401) throw error
    await refreshSession()
    await send('/auth/logout', { method: 'POST', body: '{}' }, credentials.access_token)
  }
  clearSession('logout')
}
