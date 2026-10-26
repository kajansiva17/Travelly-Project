import test from 'node:test'
import assert from 'node:assert/strict'
import { documentCountries, documentTypes, ownershipGuidance, validateDocumentUpload, MAX_DOCUMENT_BYTES } from '../src/documentUpload.js'

function body(kind = 'NIC', values = {}, file = new File(['image'], 'document.png', { type: 'image/png' })) {
  const form = new FormData()
  form.set('document_type', kind); form.set('file', file)
  for (const [key, value] of Object.entries(values)) form.set(key, value)
  return form
}

for (const kind of Object.keys(documentTypes)) test(`${kind}: upload accepts omitted metadata without guessing`, () => {
  assert.deepEqual(validateDocumentUpload(body(kind)), {})
})

test('ISO countries include Sri Lanka and regions outside telephone metadata', () => {
  assert.equal(documentCountries.length, 249)
  assert.equal(documentCountries.find(c => c.code === 'LK').name, 'Sri Lanka')
  assert.ok(documentCountries.some(c => c.code === 'AQ'))
  assert.equal(validateDocumentUpload(body('PASSPORT', { issuing_country: 'ZZ' })).issuing_country, 'Choose the country that issued the document, or leave it blank.')
})

test('date and number validation matches the upload contract', () => {
  assert.ok(validateDocumentUpload(body('NIC', { issue_date: '2026-02-30' })).issue_date)
  assert.ok(validateDocumentUpload(body('NIC', { issue_date: '0000-01-01' })).issue_date)
  assert.equal(validateDocumentUpload(body('PASSPORT', { issue_date: '2026-10-26', expiry_date: '2026-10-25' })).expiry_date, 'Expiry date must be on or after the issue date.')
  assert.deepEqual(validateDocumentUpload(body('DRIVING_LICENCE', { issuing_country: 'GB', issue_date: '2026-10-26', expiry_date: '2026-10-26' })), {})
  assert.ok(validateDocumentUpload(body('NIC', { number: 'x'.repeat(101) })).number)
  assert.equal(validateDocumentUpload(body('NIC', { number: 'x'.repeat(101) })).number, 'Enter 1–100 characters, or leave this optional field blank.')
  assert.equal(ownershipGuidance.INDIVIDUAL.title, 'Another individual’s name')
})

test('file type, empty file and exact size boundary', () => {
  assert.ok(validateDocumentUpload(body('NIC', {}, new File([], 'empty.pdf', { type: 'application/pdf' }))).file)
  assert.ok(validateDocumentUpload(body('NIC', {}, new File(['x'], 'bad.svg', { type: 'image/svg+xml' }))).file)
  assert.ok(validateDocumentUpload(body('NIC', {}, new File(['x'], 'bad.jpg', { type: 'image/png' }))).file)
  assert.deepEqual(validateDocumentUpload(body('NIC', {}, new File([new Uint8Array(MAX_DOCUMENT_BYTES)], 'max.pdf', { type: 'application/pdf' }))), {})
  assert.ok(validateDocumentUpload(body('NIC', {}, new File([new Uint8Array(MAX_DOCUMENT_BYTES + 1)], 'large.pdf', { type: 'application/pdf' }))).file)
})
