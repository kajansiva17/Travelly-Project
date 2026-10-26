import React, { useEffect, useRef, useState } from 'react'
import { api } from './api'
import { ErrorNotice } from './components'
import { documentCountries, documentTypes, documentRequirement, ownershipGuidance, validateDocumentUpload } from './documentUpload'

function Field({ name, label, helper, error, required = false, children }) {
  const id = `upload-${name}`
  return <div className="upload-field">
    <label htmlFor={id}>{label} <span className="field-optionality">({required ? 'Required' : 'Optional'})</span></label>
    <p className="upload-helper" id={`${id}-hint`}>{helper}</p>
    {React.cloneElement(children, { id, name, required, 'aria-invalid': Boolean(error), 'aria-describedby': `${id}-hint${error ? ` ${id}-error` : ''}` })}
    {error && <p className="upload-field-error" id={`${id}-error`}>{error}</p>}
  </div>
}

export default function DocumentUploadForm({ user, onUploaded }) {
  const [type, setType] = useState('NIC')
  const [ownership, setOwnership] = useState('')
  const [printedExpiry, setPrintedExpiry] = useState(false)
  const [fields, setFields] = useState({})
  const [error, setError] = useState(null)
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const sending = useRef(false)
  const formRef = useRef(null)
  const info = documentTypes[type]
  function focusError(form, errors) {
    const first = Object.keys(errors).find(name => form.elements.namedItem(name))
    if (first) form.elements.namedItem(first).focus()
  }
  useEffect(() => {
    if (!busy && formRef.current) focusError(formRef.current, fields)
  }, [fields, busy])
  async function submit(event) {
    event.preventDefault()
    if (sending.current) return
    const form = event.currentTarget
    const body = new FormData(form)
    for (const [key, value] of [...body]) if (value === '' || (key === 'number' && !value.trim())) body.delete(key)
    body.set('owner_type', 'USER'); body.set('owner_id', user.id)
    const invalid = validateDocumentUpload(body)
    setFields(invalid); setError(null); setNotice('')
    if (Object.keys(invalid).length) { setError(new Error('Check the highlighted fields.')); return }
    sending.current = true; setBusy(true)
    try {
      await api('/documents', { method: 'POST', body })
      form.reset(); setType('NIC'); setPrintedExpiry(false)
      setNotice('Your private document was submitted for review. Document review, role approval and contact verification are separate.')
      await onUploaded()
    } catch (err) {
      const inline = Object.fromEntries((err.fields || []).filter(f => ['number', 'issuing_country', 'issue_date', 'expiry_date', 'file', 'document_type'].includes(f.field)).map(f => [f.field, f.message]))
      setFields(inline); setError(err)
    } finally { sending.current = false; setBusy(false) }
  }
  return <>
    <div className="document-checklist">
      <h3>What you need for role approval</h3>
      <ul>
        <li><strong>Identity — Required.</strong> Upload one NIC or Passport for either role; the second identity document is optional.</li>
        <li><strong>Vehicle registration — Required for your case.</strong> Required for Owner approval when you are the registered owner.</li>
        <li><strong>Owner/company authorization — Required for your case.</strong> Required for Owner approval when another individual or a company is the registered owner.</li>
        <li><strong>Sri Lanka-issued driving licence — Required for your case.</strong> Required for Driver approval, including an Owner who also applies to drive.</li>
      </ul>
      <label htmlFor="ownership-guidance">Whose name is on the vehicle registration? <span className="field-optionality">(Optional guidance)</span></label>
      <select id="ownership-guidance" value={ownership} onChange={event => setOwnership(event.target.value)} aria-describedby="ownership-help">
        <option value="">Choose to see your Owner checklist</option>
        {Object.entries(ownershipGuidance).map(([value, guide]) => <option key={value} value={value}>{guide.title}</option>)}
      </select>
      <p id="ownership-help" className="upload-helper">Select the registered owner to see which evidence supports your application.</p>
      {ownership && <p className="ownership-case" role="status">{ownershipGuidance[ownership].text}</p>}
      <p className="vehicle-registration-note">Authorization proves your permission to manage a vehicle; it does not replace its registration. Vehicle registration and vehicle verification remain separate from role approval, including for another individual’s or a company’s vehicle.</p>
      <p>Required evidence must be reviewed and approved before role approval. You can submit documents individually; uploading a file does not approve your role.</p>
    </div>
    <form ref={formRef} className="private-upload" onSubmit={submit} noValidate aria-label="Private document upload">
      <ErrorNotice error={error}/>
      {notice && <p className="notice success" role="status">{notice}</p>}
      <fieldset disabled={busy}>
        <legend>Upload one document</legend>
        <Field name="document_type" label="Document type" required helper="Choose the kind of document you are uploading." error={fields.document_type}>
          <select value={type} onChange={event => { setType(event.target.value); setPrintedExpiry(false); setFields({}); setError(null); setNotice('') }}>
            {Object.entries(documentTypes).map(([value, doc]) => <option key={value} value={value}>{doc.label}</option>)}
          </select>
        </Field>
        <div className="document-type-guidance" aria-live="polite">
          <span className="document-requirement">{documentRequirement(type, ownership)}</span>
          <p>{info.helper}</p>
          {['NIC', 'PASSPORT'].includes(type) && <p>One identity document is required; this upload is optional if you already provided the other valid identity document.</p>}
          {type === 'VEHICLE_REGISTRATION' && ownership && ownership !== 'SELF' && <p>For this Owner application, provide the registered owner’s authorization. Keep the vehicle registration available for separate vehicle verification; authorization does not waive registration.</p>}
          {type === 'OWNER_AUTHORISATION' && ownership === 'SELF' && <p>Your own vehicle registration is the required ownership evidence for this case.</p>}
        </div>
        <p className="upload-metadata-note">The details below are optional for uploading. Copy only what is printed on the document; leave missing numbers or dates blank. Missing approval evidence may still need correction during review.</p>
        <div className="upload-metadata" key={type}>
          <Field name="number" label={info.number} helper="Copy the printed document or reference number, up to 100 characters; leave blank if none is printed." error={fields.number}>
            <input maxLength={100} autoComplete="off"/>
          </Field>
          {info.country && <Field name="issuing_country" label="Issuing country" helper="Choose the country that issued this document, not your nationality or phone country." error={fields.issuing_country}>
            <select defaultValue={type === 'DRIVING_LICENCE' ? 'LK' : ''}>
              <option value="">Select country if known</option>
              {documentCountries.map(country => <option key={country.code} value={country.code}>{country.name}</option>)}
            </select>
          </Field>}
          {type === 'DRIVING_LICENCE' && <p className="upload-approval-note">Driver approval requires a licence issued by Sri Lanka with a valid expiry date. A foreign-issued licence cannot satisfy this requirement.</p>}
          <Field name="issue_date" label="Issue date" helper="Enter the date marked as the issue date; leave blank if it is not printed." error={fields.issue_date}>
            <input type="date"/>
          </Field>
          {!info.expiry && <label className="printed-expiry"><input type="checkbox" checked={printedExpiry} onChange={event => { setPrintedExpiry(event.target.checked); setFields(previous => ({ ...previous, expiry_date: undefined })) }}/><span>This document has a printed expiry date (Optional)</span></label>}
          {(info.expiry || printedExpiry) && <Field name="expiry_date" label="Expiry date" helper={info.expiry ? 'Copy the printed expiry date; it is needed before role approval, but leave blank if missing rather than guessing.' : 'Copy the printed expiry date; leave blank if the document does not state one.'} error={fields.expiry_date}>
            <input type="date"/>
          </Field>}
        </div>
        <Field key={`file-${type}`} name="file" label="Document file" required helper="Choose one PDF, JPG/JPEG or PNG, up to 10 MiB (10,485,760 bytes); include the readable document details in that file." error={fields.file}>
          <input type="file" accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"/>
        </Field>
        <button className="button" disabled={busy}>{busy ? 'Submitting private document…' : 'Submit private document'}</button>
      </fieldset>
    </form>
  </>
}
