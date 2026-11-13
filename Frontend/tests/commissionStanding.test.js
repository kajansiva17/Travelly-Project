import test from 'node:test'
import assert from 'node:assert/strict'
import {bannerKind,daysOpenMessage,isExtended,nothingTakenOut,owesCommission,stageChip} from '../src/features/settlements/commissionStanding.js'

test('one banner per stage; none when nothing is owed', () => {
  assert.equal(bannerKind(null),null)
  assert.equal(bannerKind({stage:'NONE',amount_due:'0.00',blocked:false}),null)
  assert.equal(bannerKind({stage:'FREE',amount_due:'0.00',blocked:false}),null)
  assert.equal(bannerKind({stage:'FREE',amount_due:'500.00',blocked:false}),'FREE')
  assert.equal(bannerKind({stage:'GRACE',amount_due:'500.00',blocked:false}),'GRACE')
  assert.equal(bannerKind({stage:'BLOCKED',amount_due:'500.00',blocked:true}),'BLOCKED')
})
test('BLOCKED stage with blocked false is the extended state', () => {
  const extended={stage:'BLOCKED',amount_due:'500.00',blocked:false,extended_until:'2026-12-01T00:00:00Z'}
  assert.equal(isExtended(extended),true);assert.equal(bannerKind(extended),'EXTENDED')
  assert.equal(isExtended({stage:'GRACE',blocked:false}),false)
})
test('stage chips', () => {
  assert.deepEqual(stageChip({stage:'NONE'}),['muted','No commission'])
  assert.deepEqual(stageChip({stage:'FREE'}),['info','Free period'])
  assert.deepEqual(stageChip({stage:'GRACE'}),['warning','Grace period'])
  assert.deepEqual(stageChip({stage:'BLOCKED',blocked:true}),['danger','Blocked'])
  assert.deepEqual(stageChip({stage:'BLOCKED',blocked:false}),['warning','Extended'])
})
test('days open: today, one day, many', () => {
  assert.deepEqual(daysOpenMessage(0),['Opened today',{}])
  assert.deepEqual(daysOpenMessage(1),['1 day open',{}])
  assert.deepEqual(daysOpenMessage(15),['{value0} days open',{value0:15}])
})
test('payout tick only while commission is owed; zero set-off reads "no commission"', () => {
  assert.equal(owesCommission({amount_due:'3370.00'}),true);assert.equal(owesCommission({amount_due:'0.00'}),false);assert.equal(owesCommission(undefined),false)
  assert.equal(nothingTakenOut('0.00'),true);assert.equal(nothingTakenOut('1685.00'),false)
})
