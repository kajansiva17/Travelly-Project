import test from 'node:test'
import assert from 'node:assert/strict'
import { extraKeys, modeOf, withExtraPolicy, extraLine, extraLines, searchEntries, headingsBefore, distanceValue, orderNearFirst } from '../src/features/booking/extraPolicy.js'

test('each method offers only its own extras (03XP)', () => {
  assert.deepEqual(extraKeys('DISTANCE'), ['WAITING', 'EXTRA_KM'])
  assert.deepEqual(extraKeys('DAY_HIRE'), ['WAITING', 'EXTRA_KM', 'EXTRA_HOURS', 'OVERNIGHT'])
  assert.deepEqual(extraKeys('FIXED_ROUTE'), ['WAITING'])
})
test('a rule without extra_policy loads as CHARGED', () => {
  assert.equal(modeOf({ method: 'DISTANCE' }, 'EXTRA_KM'), 'CHARGED')
  assert.equal(modeOf({ extra_policy: { EXTRA_KM: 'FREE' } }, 'EXTRA_KM'), 'FREE')
  assert.equal(modeOf({ extra_policy: { EXTRA_KM: 'bogus' } }, 'EXTRA_KM'), 'CHARGED')
})
test('saving sends "0" for rates of an extra that is not charged and drops keys the method does not use', () => {
  const rule = { method: 'DISTANCE', extra_km_rate: '90', free_wait_minutes: '10', waiting_hour_rate: '500', extra_policy: { EXTRA_KM: 'FREE', WAITING: 'NOT_OFFERED', OVERNIGHT: 'CHARGED', EXTRA_HOURS: 'FREE' } }
  const out = withExtraPolicy(rule)
  assert.deepEqual(out.extra_policy, { WAITING: 'NOT_OFFERED', EXTRA_KM: 'FREE' })
  assert.equal(out.extra_km_rate, '0'); assert.equal(out.free_wait_minutes, '0'); assert.equal(out.waiting_hour_rate, '0')
  const charged = withExtraPolicy({ method: 'FIXED_ROUTE', fixed_fare: '5000', free_wait_minutes: '15', waiting_hour_rate: '400' })
  assert.deepEqual(charged.extra_policy, { WAITING: 'CHARGED' }); assert.equal(charged.waiting_hour_rate, '400')
  assert.equal(rule.extra_km_rate, '90')   // the form state is not changed
})
test('Passenger lines: Not available, No extra charge, or the rate with its unit', () => {
  assert.equal(extraLine({ code: 'WAITING', mode: 'NOT_OFFERED' }).key, 'Not available')
  assert.equal(extraLine({ code: 'EXTRA_KM', mode: 'FREE' }).key, 'No extra charge')
  assert.deepEqual(extraLine({ code: 'EXTRA_KM', mode: 'CHARGED', km_rate: '100' }).params, { value0: 'LKR 100.00' })
  const wait = extraLine({ code: 'WAITING', mode: 'CHARGED', free_minutes: '30', hour_rate: '1500' })
  assert.deepEqual(wait.params, { value0: 30, value1: 'LKR 1,500.00' })
  assert.equal(extraLine({ code: 'OVERNIGHT', mode: 'CHARGED', cost: '3000' }).key, '{value0} per overnight stay')
  assert.equal(extraLines({ calculation: { extra_policies: [{ code: 'EXTRA_HOURS', mode: 'CHARGED', hour_rate: '800' }] } }).length, 1)
  assert.deepEqual(extraLines({ total: '1' }), [])
})
test('nearby order: server order kept, near first, nothing hidden, no distance when null', () => {
  const list = [{ id: 'a', near: false, distance_km: 120.5 }, { id: 'b', near: true, distance_km: 4.2 }, { id: 'c', near: false, distance_km: null }, { id: 'd', near: true, distance_km: 49.9 }]
  assert.deepEqual(orderNearFirst(list).map(x => x.id), ['b', 'd', 'a', 'c'])
  assert.equal(distanceValue(list[0]), '120.5'); assert.equal(distanceValue(list[2]), null); assert.equal(distanceValue({ distance_km: 12 }), '12')
  const all = searchEntries({ items: list, quote_on_request: [{ id: 'q', near: true }, { id: 'r', near: false }] })
  assert.deepEqual(all.map(x => x.id), ['b', 'd', 'a', 'c', 'q', 'r'])
  assert.deepEqual(all.map(x => x.quote_required), [false, false, false, false, true, true])
})
test('headings: Farther away before the first far entry, Ask the Owner before the first unpriced one', () => {
  const all = searchEntries({ items: [{ id: 'b', near: true }, { id: 'a', near: false }], quote_on_request: [{ id: 'q', near: true }, { id: 'r', near: false }] })
  assert.deepEqual(all.map((e, i) => headingsBefore(e, all[i - 1])), [[], ['FAR'], ['ASK'], ['FAR']])
  assert.deepEqual(headingsBefore(all[3], undefined), ['ASK', 'FAR'])   // a page that starts in the far unpriced part
  assert.deepEqual(headingsBefore(all[0], undefined), [])
})

test('owner-confirmation entries form their own clearly labelled search section', () => {
  const all = searchEntries({ items: [{ id: 'available' }], quote_on_request: [
    { id: 'price', near: true }, { id: 'confirm', near: true, owner_confirmation_required: true },
  ] })
  assert.deepEqual(all.map(entry => entry.id), ['available', 'confirm', 'price'])
  assert.deepEqual(all.map((entry, index) => headingsBefore(entry, all[index - 1])), [[], ['CONFIRM'], ['ASK']])
})
