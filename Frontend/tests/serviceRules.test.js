import test from 'node:test'
import assert from 'node:assert/strict'
import { serviceRuleError, minimumKm } from '../src/features/booking/serviceRules.js'
import { checkAirports, checkMinKm } from '../src/features/admin/serviceRulesModel.js'

test('a trip that does not fit the service: the key and the values for t(), nothing guessed', () => {
  assert.equal(serviceRuleError({ code: 'AIRPORT_LOCATION_REQUIRED' }).key.startsWith('Airport hire is for trips'), true)
  const rule = serviceRuleError({ code: 'TRIP_TOO_SHORT_FOR_LONG_DISTANCE', fields: [{ field: 'distance_km', message: '8' }, { field: 'min_distance_km', message: '100' }] })
  assert.deepEqual(rule.params, { value0: '8', value1: '100' })
  assert.equal(rule.key, 'This trip is about {value0} km. Long distance is for trips of {value1} km or more. Choose Local hire.')
  // the numbers are missing: the server's own message is shown, never invented numbers
  const bare = serviceRuleError({ code: 'TRIP_TOO_SHORT_FOR_LONG_DISTANCE', message: 'Server text', fields: [] })
  assert.equal(bare.key, null); assert.equal(bare.text, 'Server text')
  assert.equal(serviceRuleError({ code: 'SOMETHING_ELSE' }), null); assert.equal(serviceRuleError(null), null)
  // field_errors (raw body) is read as well as fields (api client)
  assert.deepEqual(serviceRuleError({ code: 'TRIP_TOO_SHORT_FOR_LONG_DISTANCE', field_errors: [{ field: 'distance_km', message: '12' }, { field: 'min_distance_km', message: '50' }] }).params, { value0: '12', value1: '50' })
})

test('the Long distance card shows the minimum only when the service has one', () => {
  assert.equal(minimumKm({ min_distance_km: 100 }), 100)
  assert.equal(minimumKm({ min_distance_km: 0 }), null)
  assert.equal(minimumKm({}), null); assert.equal(minimumKm(undefined), null)
})

test('Admin minimum distance: a whole number from 0 to 2000', () => {
  for (const ok of ['0', '100', ' 2000 ', 60]) assert.equal(checkMinKm(ok), '')
  for (const bad of ['', '-1', '1.5', '2001', 'abc', '10000']) assert.notEqual(checkMinKm(bad), '')
})

test('Admin airport list: code, name, a position inside Sri Lanka, each code once', () => {
  const ok = { code: 'cmb', name: 'Bandaranaike International', latitude: '7.1808', longitude: '79.8841', is_active: true }
  assert.equal(checkAirports([ok]), ''); assert.equal(checkAirports([]), '')
  assert.match(checkAirports([{ ...ok, code: 'X' }]), /code/)
  assert.match(checkAirports([{ ...ok, name: ' a ' }]), /name/)
  assert.match(checkAirports([{ ...ok, latitude: '40' }]), /Sri Lanka/)
  assert.match(checkAirports([{ ...ok, longitude: 'x' }]), /Sri Lanka/)
  assert.match(checkAirports([ok, { ...ok, code: 'CMB' }]), /once/)
})
