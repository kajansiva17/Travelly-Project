import test from 'node:test'
import assert from 'node:assert/strict'
import { isTwoFactor, cleanCode, twoFactorBody, codeMinutes, returnTarget, twoFactorMessage, challengeExpired, enableBody, confirmBody, closeBody, blockerLines, canClose, BLOCKERS } from '../src/features/auth/loginFlow.js'

test('login answers two_factor_required with a challenge instead of tokens (email and Google alike)', () => {
  assert.equal(isTwoFactor({ status: 'two_factor_required', challenge: 'abc', expires_in: 300 }), true)
  assert.equal(isTwoFactor({ status: 'two_factor_required' }), false)
  assert.equal(isTwoFactor({ status: 'verification_required' }), false)
  assert.equal(isTwoFactor({ access_token: 'a', refresh_token: 'r' }), false)
  assert.equal(isTwoFactor(null), false)
})
test('POST /auth/2fa body: the challenge and the code with typed spaces removed, no format guessed', () => {
  assert.deepEqual(twoFactorBody('ch', '123 456'), { challenge: 'ch', code: '123456' })
  assert.deepEqual(twoFactorBody('ch', ' ABCDE-FGHJK '), { challenge: 'ch', code: 'ABCDE-FGHJK' })
  assert.equal(cleanCode(undefined), '')
  assert.equal(codeMinutes(300), 5); assert.equal(codeMinutes(undefined), 5); assert.equal(codeMinutes(20), 1)
})
test('error codes of the second step map to friendly text; an expired step goes back to sign-in', () => {
  assert.match(twoFactorMessage({ code: 'TWO_FACTOR_CODE_WRONG' }), /not correct/)
  assert.match(twoFactorMessage({ code: 'TWO_FACTOR_CHALLENGE_EXPIRED' }), /expired/)
  assert.match(twoFactorMessage({ code: 'RATE_LIMITED', status: 429 }), /Too many/)
  assert.match(twoFactorMessage({ status: 429 }), /Too many/)
  assert.equal(twoFactorMessage({ code: 'SOMETHING_ELSE' }), null)
  assert.equal(challengeExpired({ code: 'TWO_FACTOR_CHALLENGE_EXPIRED' }), true); assert.equal(challengeExpired({ code: 'X' }), false)
})
test('the return page of a landing card is kept (only the documented pages)', () => {
  assert.equal(returnTarget({ returnTo: '/travel/book/tickets' }), '/travel/book/tickets')
  assert.equal(returnTarget({ returnTo: '/owner/vehicles' }), '/owner/vehicles')
  assert.equal(returnTarget({ returnTo: 'https://evil.example' }), null)
  assert.equal(returnTarget(undefined), null)
})
test('request bodies: enable sends the code; password only when the account has one; code only when asked for', () => {
  assert.deepEqual(enableBody('123 456'), { code: '123456' })
  assert.deepEqual(confirmBody({ hasPassword: true, password: 'pw', code: '654321' }), { password: 'pw', code: '654321' })
  assert.deepEqual(confirmBody({ hasPassword: false, password: 'ignored', code: 'ABCDE-FGHJK' }), { code: 'ABCDE-FGHJK' })
  assert.deepEqual(closeBody({ hasPassword: true, password: 'pw', twoFactorOn: false, code: '' }), { confirm: true, password: 'pw' })
  assert.deepEqual(closeBody({ hasPassword: false, twoFactorOn: true, code: '123456' }), { confirm: true, code: '123456' })
  assert.deepEqual(closeBody({ hasPassword: true, password: 'pw', twoFactorOn: true, code: '1 2 3456' }), { confirm: true, password: 'pw', code: '123456' })
})
test('blockers: every documented code has its own text with the count; unknown codes use the server message; no page is invented', () => {
  const codes = ['OPEN_BOOKINGS_AS_PASSENGER', 'OPEN_BOOKINGS_AS_OWNER', 'OPEN_TRIPS_AS_DRIVER', 'OPEN_DEPARTURES', 'COMMISSION_DUE', 'OWNER_PAYOUT_PENDING', 'REFUND_PENDING']
  assert.deepEqual(Object.keys(BLOCKERS), codes)
  const lines = blockerLines([{ code: 'OPEN_BOOKINGS_AS_PASSENGER', message: 'x', count: 2 }, { code: 'REFUND_PENDING', count: 1 }, { code: 'NEW_ONE', message: 'Server words', count: 3 }])
  assert.deepEqual(lines[0].params, { value0: 2 }); assert.match(lines[0].key, /\{value0\}/); assert.equal(lines[0].path, null)
  assert.equal(lines[2].key, null); assert.equal(lines[2].text, 'Server words')
  assert.deepEqual(blockerLines(null), [])
})
test('the final buttons stay off while any blocker exists', () => {
  assert.equal(canClose({ can_close: true, blockers: [] }), true)
  assert.equal(canClose({ can_close: false, blockers: [{ code: 'COMMISSION_DUE', count: 1 }] }), false)
  assert.equal(canClose({ can_close: true, blockers: [{ code: 'COMMISSION_DUE', count: 1 }] }), false)
  assert.equal(canClose(null), false)
})
