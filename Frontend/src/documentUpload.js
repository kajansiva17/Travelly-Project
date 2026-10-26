import countryCodes from './documentCountryCodes.js'

// Upload optionality is frozen in 03D section 4. Approval is a separate gate.
const names = new Intl.DisplayNames(['en'], { type: 'region' })
export const documentCountries = countryCodes.map(code => ({ code, name: names.of(code) })).sort((a, b) => a.name.localeCompare(b.name))
export const MAX_DOCUMENT_BYTES = 10485760
export const documentTypes = {
  NIC: { label: 'National identity card (NIC)', number: 'Identity card number', country: true,
    helper: 'Upload your readable identity card; choose either NIC or Passport for identity evidence.' },
  PASSPORT: { label: 'Passport', number: 'Passport number', country: true, expiry: true,
    helper: 'Upload the passport page showing your identity and document details; choose either Passport or NIC.' },
  DRIVING_LICENCE: { label: 'Driving licence', number: 'Driving licence number', country: true, expiry: true,
    helper: 'Upload your Sri Lanka-issued driving licence for Driver approval; Owner-only applications do not require it.' },
  VEHICLE_REGISTRATION: { label: 'Vehicle registration', number: 'Registration document number', country: true,
    helper: 'Upload the vehicle registration document showing the vehicle and its registered owner.' },
  OWNER_AUTHORISATION: { label: 'Owner/company authorization', number: 'Authorization reference number', country: false,
    helper: 'Upload authorization from the registered owner or company identifying you, the vehicle and your authority to manage it.' },
}

export const ownershipGuidance = {
  SELF: { title: 'My name', text: 'For Owner approval, upload your vehicle registration showing you as the registered owner, plus your NIC or Passport.' },
  INDIVIDUAL: { title: 'Another individual’s name', text: 'For Owner approval, upload authorization from that registered individual identifying you and the relevant vehicle, plus your NIC or Passport.' },
  COMPANY: { title: 'A company’s name', text: 'For Owner approval, upload authorization from the registered company establishing its authority and your permission to manage the vehicle, plus your NIC or Passport. Apply as an individual; no company account is needed.' },
}

export function documentRequirement(type, ownership) {
  if (type === 'OWNER_AUTHORISATION' && ownership === 'SELF') return 'Optional'
  return 'Required for your case'
}

export function validateDocumentUpload(body) {
  const errors = {}
  if (!documentTypes[body.get('document_type')]) errors.document_type = 'Choose a document type.'
  const number = body.get('number')
  if (number != null && (!number.trim() || [...number.trim()].length > 100)) errors.number = 'Enter 1–100 characters, or leave this optional field blank.'
  const country = body.get('issuing_country')
  if (country != null && !countryCodes.includes(country)) errors.issuing_country = 'Choose the country that issued the document, or leave it blank.'
  for (const field of ['issue_date', 'expiry_date']) {
    const value = body.get(field)
    if (value && (!/^\d{4}-\d{2}-\d{2}$/.test(value) || value.startsWith('0000') || !Number.isFinite(Date.parse(value)) || new Date(value).toISOString().slice(0, 10) !== value)) {
      errors[field] = 'Enter a valid date, or leave this optional field blank.'
    }
  }
  if (!errors.issue_date && !errors.expiry_date && body.get('issue_date') && body.get('expiry_date') && body.get('expiry_date') < body.get('issue_date')) errors.expiry_date = 'Expiry date must be on or after the issue date.'
  const file = body.get('file')
  if (!file?.size) errors.file = 'Choose a non-empty PDF, JPG or PNG file.'
  else if (file.size > MAX_DOCUMENT_BYTES) errors.file = 'Choose a file no larger than 10 MiB (10,485,760 bytes).'
  else {
    const mime = { pdf: 'application/pdf', jpg: 'image/jpeg', jpeg: 'image/jpeg', png: 'image/png' }[file.name.split('.').pop().toLowerCase()]
    if (!mime || (file.type && file.type !== mime)) errors.file = 'Choose a PDF, JPG or PNG file with a matching file extension.'
  }
  return errors
}
