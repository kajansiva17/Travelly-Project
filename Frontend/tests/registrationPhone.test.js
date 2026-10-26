import test from 'node:test'
import assert from 'node:assert/strict'
import { phoneCountries, registrationPhone } from '../src/registrationPhone.js'

test('country metadata supports Sri Lanka, foreign regions and shared calling codes', () => {
  assert.equal(phoneCountries.find(c => c.code === 'LK').callingCode, '94')
  assert.equal(phoneCountries.find(c => c.code === 'GB').callingCode, '44')
  assert.equal(phoneCountries.find(c => c.code === 'US').callingCode, '1')
  assert.equal(phoneCountries.find(c => c.code === 'CA').callingCode, '1')
})

for (const [country, national, expected] of [
  ['LK', '771234567', '+94771234567'],
  ['LK', '077 123-4567', '+94771234567'],
  ['GB', '7400123456', '+447400123456'],
  ['GB', '07400 123456', '+447400123456'],
  ['US', '(202) 555-0123', '+12025550123'],
  ['TK', '7290', '+6907290'],
]) test(`${country} national input normalizes correctly: ${national}`, () => assert.equal(registrationPhone(country, national), expected))

for (const [country, national] of [
  ['XX', '771234567'], ['LK', '77'], ['LK', '+94771234567'],
  ['LK', '94771234567'], ['LK', '0094771234567'], ['US', '12025550123'],
  ['GB', '447400123456'], ['LK', '0771234567 ext 1'], ['LK', '\n'],
]) test(`invalid/duplicated input is rejected: ${country} ${JSON.stringify(national)}`, () => assert.throws(() => registrationPhone(country, national)))

test('a selector alone is not a phone contact', () => assert.equal(registrationPhone('LK', ''), null))
