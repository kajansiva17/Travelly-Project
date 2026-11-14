/* Sign-in and account settings rules (contract 03SV): the two-step branch of login, request bodies and the account-closure blockers.
   Pure functions, no network and no storage. Codes are never logged or stored. */

// POST /auth/login and Google sign-in answer {status:'two_factor_required', challenge, expires_in} instead of tokens.
export const isTwoFactor = result => result?.status === 'two_factor_required' && typeof result?.challenge === 'string' && result.challenge !== ''
// An app code or a backup code: no format is guessed, only the spaces people type between groups are dropped.
export const cleanCode = value => String(value ?? '').replace(/\s+/g, '')
export const twoFactorBody = (challenge, code) => ({ challenge, code: cleanCode(code) })
export const codeMinutes = expiresIn => Math.max(1, Math.round(Number(expiresIn || 300) / 60))

// Landing cards send a signed-out visitor to sign-in with a return target; only these pages are accepted.
export const RETURN_PAGES = ['/travel/book/tickets', '/travel/book/rental', '/owner/vehicles']
export const returnTarget = state => (RETURN_PAGES.includes(state?.returnTo) ? state.returnTo : null)

// Friendly text (English key for t()) for the errors of the second step; null means "show the server message".
export function twoFactorMessage(error) {
  if (error?.code === 'TWO_FACTOR_CODE_WRONG') return 'That code is not correct, or it was already used. Check the code in your app, or use a backup code.'
  if (error?.code === 'TWO_FACTOR_CHALLENGE_EXPIRED') return 'This sign-in step expired. Sign in again.'
  if (error?.code === 'TWO_FACTOR_CODE_REQUIRED') return 'Enter your authenticator code.'
  if (error?.code === 'RATE_LIMITED' || error?.status === 429) return 'Too many wrong codes. Try again later.'
  return null
}
export const challengeExpired = error => error?.code === 'TWO_FACTOR_CHALLENGE_EXPIRED'

// Request bodies. The password is sent only when the account has one, the code only when asked for; POSTs without fields send {}.
export const enableBody = code => ({ code: cleanCode(code) })
export function confirmBody({ hasPassword, password, code }) {
  const body = {}
  if (hasPassword) body.password = password
  if (cleanCode(code)) body.code = cleanCode(code)
  return body
}
export const closeBody = ({ hasPassword, password, twoFactorOn, code }) => ({ confirm: true, ...(hasPassword ? { password } : {}), ...(twoFactorOn ? { code: cleanCode(code) } : {}) })

/* Account closure blockers: the UI's own text per code (the server message is only the fallback). The contract gives no page for
   a blocker, so none is linked; `path` is where a link would go when one is documented. */
export const BLOCKERS = {
  OPEN_BOOKINGS_AS_PASSENGER: { key: 'Your bookings that are not finished: {value0}', path: null },
  OPEN_BOOKINGS_AS_OWNER: { key: 'Bookings for your vehicles that are not finished: {value0}', path: null },
  OPEN_TRIPS_AS_DRIVER: { key: 'Trips you still have to drive or run: {value0}', path: null },
  OPEN_DEPARTURES: { key: 'Ticket departures that are not finished: {value0}', path: null },
  COMMISSION_DUE: { key: 'Commission payments you still owe: {value0}', path: null },
  OWNER_PAYOUT_PENDING: { key: 'Payouts to you that are not paid out yet: {value0}', path: null },
  REFUND_PENDING: { key: 'Refunds that are still being paid back to you: {value0}', path: null },
}
export const blockerLines = blockers => (Array.isArray(blockers) ? blockers : []).filter(item => item?.code).map(item => {
  const known = BLOCKERS[item.code]
  return known
    ? { code: item.code, key: known.key, params: { value0: Number(item.count ?? 0) }, path: known.path }
    : { code: item.code, key: null, text: item.message || item.code, path: null }
})
export const canClose = status => status?.can_close === true && !(status?.blockers || []).length
