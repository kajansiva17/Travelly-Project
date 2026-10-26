import test from 'node:test'
import assert from 'node:assert/strict'
import { emailError, passwordErrors } from '../src/authValidation.js'

for (const value of ['1john@gmail.com', 'john+travel@gmail.com', ' First.Last@Example.COM ']) test(`email accepts ${value}`, () => assert.equal(emailError(value), ''))
for (const value of ['.john@example.com', 'john.@example.com', 'jo..hn@example.com', 'john@localhost', 'john @example.com', 'john@example.invalid', 'john@@example.com', 'john@']) test(`email rejects ${value}`, () => assert.ok(emailError(value)))
test('password requirements are specific and preserve valid long Unicode passwords', () => {
  for (const value of ['TravellyStrong1!', 'Aa1!' + 'é'.repeat(60), 'Aa1!' + '😀'.repeat(100)]) assert.deepEqual(passwordErrors(value), [])
  assert.ok(passwordErrors('lowercase123!').includes('Add an uppercase letter.'))
  assert.ok(passwordErrors('UPPERCASE123!').includes('Add a lowercase letter.'))
  assert.ok(passwordErrors('SomePassword!').includes('Add a number.'))
  assert.ok(passwordErrors('SomePassword1').includes('Add a symbol.'))
  assert.ok(passwordErrors('SomePassword1! ').includes('Remove all whitespace.'))
  assert.ok(passwordErrors('Aa1!' + 'x'.repeat(125)).includes('Use at most 128 characters.'))
})
