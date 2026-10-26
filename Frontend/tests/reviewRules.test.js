import test from 'node:test'
import assert from 'node:assert/strict'
import { roleActions, documentActions, needsReason, decisionPayload, mayReview } from '../src/reviewRules.js'

test('review navigation requires a currently eligible approved Admin', () => {
  assert.equal(mayReview({ account_status: 'PENDING_VERIFICATION', approved_roles: ['PASSENGER', 'ADMIN'] }), true)
  for (const user of [null, { account_status: 'ACTIVE', approved_roles: ['PASSENGER', 'OWNER', 'DRIVER'] }, { account_status: 'SUSPENDED', approved_roles: ['ADMIN'] }]) assert.equal(Boolean(mayReview(user)), false)
})
test('only documented role and correction transitions are offered', () => {
  assert.deepEqual(roleActions('PENDING'), ['APPROVED', 'REJECTED'])
  assert.deepEqual(roleActions('APPROVED'), ['SUSPENDED'])
  for (const s of ['REJECTED', 'SUSPENDED']) assert.deepEqual(roleActions(s), [])
  assert.deepEqual(documentActions('SUBMITTED'), ['UNDER_REVIEW'])
  assert.deepEqual(documentActions('UNDER_REVIEW'), ['APPROVED', 'REJECTED', 'NEEDS_CORRECTION'])
  for (const s of ['APPROVED', 'REJECTED', 'SUPERSEDED', 'NEEDS_CORRECTION']) assert.deepEqual(documentActions(s), [])
})
test('confirmation transports only decision, full trimmed reason and expected version', () => {
  assert.deepEqual(decisionPayload('REJECTED', 3, '  Complete applicant-visible reason.  '), { decision: 'REJECTED', version: 3, reason: 'Complete applicant-visible reason.' })
  assert.deepEqual(decisionPayload('APPROVED', 2), { decision: 'APPROVED', version: 2, reason: null })
  for (const decision of ['REJECTED', 'SUSPENDED', 'NEEDS_CORRECTION']) {
    assert.equal(needsReason(decision), true)
    assert.throws(() => decisionPayload(decision, 1, '   '))
    assert.throws(() => decisionPayload(decision, 1, 'a'.repeat(2001)))
  }
  for (const version of [true, '1', 0, 1.5]) assert.throws(() => decisionPayload('APPROVED', version))
})
