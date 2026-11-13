import test from 'node:test'
import assert from 'node:assert/strict'
import {bannerKind,STAGE_CHIP} from '../src/features/settlements/commissionStanding.js'

test('one banner per stage; none when nothing is owed', () => {
  assert.equal(bannerKind(null),null)
  assert.equal(bannerKind({stage:'NONE',amount_due:'0.00',blocked:false}),null)
  assert.equal(bannerKind({stage:'FREE',amount_due:'0.00',blocked:false}),null)
  assert.equal(bannerKind({stage:'FREE',amount_due:'500.00',blocked:false}),'FREE')
  assert.equal(bannerKind({stage:'GRACE',amount_due:'500.00',blocked:false}),'GRACE')
  assert.equal(bannerKind({stage:'BLOCKED',amount_due:'500.00',blocked:true}),'BLOCKED')
})
test('blocked decides: an extension shows the grace warning, not the red banner', () => {
  assert.equal(bannerKind({stage:'BLOCKED',amount_due:'500.00',blocked:false,extended_until:'2026-12-01T00:00:00Z'}),'GRACE')
  assert.ok(STAGE_CHIP.BLOCKED&&STAGE_CHIP.GRACE&&STAGE_CHIP.FREE&&STAGE_CHIP.NONE)
})
