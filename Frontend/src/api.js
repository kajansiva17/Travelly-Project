const base = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')
let credentials = null
let refreshing = null
let generation = 0
let authFlow = null
export function setAuthFlow(value) { authFlow = value }
export function getAuthFlow() { return authFlow }

export function clearSession() { credentials = null; authFlow = null; generation += 1 }
export function hasSession() { return Boolean(credentials) }

async function send(path, options = {}, accessToken) {
  const response = await fetch(`${base}/api/v1${path}`, {
    ...options,
    headers: { ...(options.body && !(options.body instanceof FormData) ? { 'Content-Type': 'application/json' } : {}),
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}), ...options.headers },
  })
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
export function acceptAuthResult(result) {
  if (result.access_token && result.refresh_token) { credentials = result; generation += 1; authFlow = null }
  else { authFlow = result }
  return result
}

export async function login(data) {
  const tokens = await send('/auth/login', { method: 'POST', body: JSON.stringify(data) })
  return acceptAuthResult(tokens)
}

async function refreshSession() {
  if (!credentials) throw new Error('Please sign in again.')
  if (!refreshing) {
    const version = generation
    const token = credentials.refresh_token
    refreshing = send('/auth/refresh', { method: 'POST', body: JSON.stringify({ refresh_token: token }) })
      .then((tokens) => { if (generation === version) credentials = tokens; return tokens })
      .catch((error) => { if (generation === version) clearSession(); throw error })
      .finally(() => { refreshing = null })
  }
  return refreshing
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
  // Settle a concurrent refresh before selecting the matching access/refresh pair.
  if (refreshing) await refreshing
  if (!credentials) return
  try {
    await send('/auth/logout', { method: 'POST', body: JSON.stringify({ refresh_token: credentials.refresh_token }) }, credentials.access_token)
  } catch (error) {
    if (error.status !== 401) throw error
    await refreshSession()
    await send('/auth/logout', { method: 'POST', body: JSON.stringify({ refresh_token: credentials.refresh_token }) }, credentials.access_token)
  }
  clearSession()
}
