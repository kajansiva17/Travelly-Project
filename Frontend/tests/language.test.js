import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, readdirSync } from 'node:fs'
import { createRequire } from 'node:module'
import { messages } from '../src/i18n/messages.js'
import { getLanguage, getLocale, languageKey, setLanguage, subscribeLanguage, translate } from '../src/i18n/language.js'

const require = createRequire(import.meta.url)
const { parse } = require('@babel/parser')
const traverse = require('@babel/traverse').default

test('both bundled dictionaries cover every marked static interface string and preserve placeholders', () => {
  const missing = []
  for (const file of readdirSync(new URL('../src', import.meta.url), { recursive: true }).filter(file => /\.(jsx|js)$/.test(file) && !file.startsWith('i18n'))) {
    const source = readFileSync(new URL('../src/' + file.replaceAll('\\', '/'), import.meta.url), 'utf8')
    traverse(parse(source, { sourceType: 'module', plugins: ['jsx'] }), {
      CallExpression(path) {
        if (path.node.callee.name === 't' && path.node.arguments[0]?.type === 'StringLiteral') {
          const key = path.node.arguments[0].value.trim().replace(/\s+/g, ' ')
          if (/[A-Za-z]{2}/.test(key) && !messages[key]) missing.push(`${file}: ${key}`)
        }
      },
      JSXText(path) {
        if (/[A-Za-z]{2}/.test(path.node.value)) missing.push(`${file}: unmarked JSX text`)
      },
    })
  }
  assert.deepEqual(missing, [])
  for (const [key, value] of Object.entries(messages)) {
    for (const code of ['ta', 'si']) {
      assert.equal(typeof value[code], 'string', `${code}: ${key}`)
      assert.ok(value[code].trim(), `${code}: ${key}`)
      assert.deepEqual([...value[code].matchAll(/\{\w+\}/g)].map(match => match[0]).sort(), [...key.matchAll(/\{\w+\}/g)].map(match => match[0]).sort(), `${code}: ${key}`)
    }
  }
})

test('selection persists only its language code and notifies without accepting unknown languages', () => {
  const writes = []
  globalThis.localStorage = { setItem: (...args) => writes.push(args) }
  let updates = 0
  const stop = subscribeLanguage(() => updates++)
  setLanguage('ta')
  assert.equal(getLanguage(), 'ta')
  assert.equal(getLocale(), 'ta-LK')
  assert.deepEqual(writes, [[languageKey, 'ta']])
  setLanguage('xx'); setLanguage('ta')
  assert.equal(updates, 1)
  stop(); setLanguage('en')
  delete globalThis.localStorage
})

test('catalogue preserves the Travelly brand and uses the correct script without broken Unicode', () => {
  for (const [key,value] of Object.entries(messages)) {
    assert.doesNotMatch(value.ta, /[\u0D80-\u0DFF]/u, `Sinhala glyph in Tamil: ${key}`)
    assert.doesNotMatch(value.si, /[\u0B80-\u0BFF]/u, `Tamil glyph in Sinhala: ${key}`)
    for (const code of ['ta','si']) {
      assert.ok(value[code].isWellFormed(), `${code}: ${key}`)
      assert.ok(!value[code].includes('\uFFFD'), `${code}: ${key}`)
      if(key.includes('Travelly')) assert.ok(value[code].includes('Travelly'), `${code} brand: ${key}`)
    }
  }
})

test('switching still works with blocked browser storage', () => {
  globalThis.localStorage = { setItem: () => { throw new Error('Blocked') } }
  setLanguage('si')
  assert.equal(getLanguage(), 'si')
  setLanguage('en')
  delete globalThis.localStorage
})

test('translation preserves values, inline whitespace and safe fallbacks', () => {
  assert.equal(translate('Home', 'ta'), 'முகப்பு')
  assert.equal(translate('Home', 'si'), 'මුල් පිටුව')
  assert.equal(translate(' Home ', 'ta'), ' முகப்பு ')
  assert.equal(translate('Uncatalogued user-supplied text', 'si'), 'Uncatalogued user-supplied text')
  assert.equal(translate('Home', 'unknown'), 'Home')
  assert.equal(translate(null, 'ta'), null)
  const translated = translate('Country code: {value0} (+{value1})', 'si', { value0: 'Sri Lanka', value1: '94' })
  assert.ok(translated.includes('Sri Lanka'))
  assert.ok(translated.includes('94'))
  assert.ok(!translated.includes('{value'))
})
