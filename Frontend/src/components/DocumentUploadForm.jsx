import { t } from '../i18n/language.js'
import React, { useEffect, useRef, useState } from 'react'
import {validateApplicationEvidence} from '../services/applicationEvidence'
import { api } from '../services/api'
import { ErrorNotice } from './components'
import { documentCountries, documentTypes, documentRequirement, ownershipGuidance, validateDocumentUpload } from '../services/documentUpload'

function Field({ name, label, helper, error, required = false, children }) {
  const id = `upload-${name}`
  return <div className="upload-field">
    <label htmlFor={id}>{t(label)} <span className="field-optionality">({required ? t('Required') : t('Optional')})</span></label>
    <p className="upload-helper" id={`${id}-hint`}>{t(helper)}</p>
    {React.cloneElement(children, { id, name, required, 'aria-invalid': Boolean(error), 'aria-describedby': `${id}-hint${error ? ` ${id}-error` : ''}` })}
    {error && <p className="upload-field-error" id={`${id}-error`}>{t(error)}</p>}
  </div>
}

export default function DocumentUploadForm({ user, onUploaded, flow = 'SHARED', correctionType = null }) {
  const [type, setType] = useState(correctionType || 'NIC')
  const [ownership, setOwnership] = useState('')
  const [printedExpiry, setPrintedExpiry] = useState(false)
  const [fields, setFields] = useState({})
  const [error, setError] = useState(null)
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const sending = useRef(false)
  const formRef = useRef(null)
  const owner = flow === 'OWNER', driver = flow === 'DRIVER'
  const availableTypes = correctionType ? [correctionType] : owner ? ['NIC','PASSPORT','VEHICLE_REGISTRATION','OWNER_AUTHORISATION'] : driver ? ['NIC','PASSPORT','DRIVING_LICENCE'] : ['NIC','PASSPORT']
  const info = documentTypes[type]
  const driverLicence = driver && type === 'DRIVING_LICENCE'
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
    const invalid = driverLicence ? validateApplicationEvidence(body) : validateDocumentUpload(body)
    setFields(invalid); setError(null); setNotice('')
    if (Object.keys(invalid).length) { setError(new Error('Check the highlighted fields.')); return }
    sending.current = true; setBusy(true)
    try {
      await api('/documents', { method: 'POST', body })
      form.reset(); setType(correctionType || 'NIC'); setPrintedExpiry(false)
      setNotice('Your private document was submitted for review. Document review, role approval and contact verification are separate.')
      await onUploaded()
    } catch (err) {
      const inline = Object.fromEntries((err.fields || []).filter(f => ['number', 'issuing_country', 'issue_date', 'expiry_date', 'file', 'document_type'].includes(f.field)).map(f => [f.field, f.message]))
      setFields(inline); setError(err)
    } finally { sending.current = false; setBusy(false) }
  }
  return <>
    {!correctionType&&<div className="document-checklist">
      <h3>{owner ? t('What you need for Owner approval') : driver ? t('What you need for Driver approval') : t('Shared identity documents')}</h3>
      <ul>
        <li><strong>{owner || driver ? t('Identity: Required.') : t('Identity: Optional for your Passenger profile.')}</strong>{t(" For a role application, upload one NIC or Passport; the second identity document is optional. Shared identity evidence can support either application.")}</li>
        {owner && <><li><strong>{t("Vehicle registration — Required for your case.")}</strong>{t(" Required for Owner approval when you are the registered owner.")}</li>
        <li><strong>{t("Owner/company authorization — Required for your case.")}</strong>{t(" Required for Owner approval when another individual or a company is the registered owner.")}</li></>}
        {driver && <li><strong>{t("Sri Lanka-issued driving licence — Required for your case.")}</strong>{t(" Required for Driver approval, including an Owner who also applies to drive.")}</li>}
      </ul>
      {owner && <><label htmlFor="ownership-guidance">{t("Whose name is on the vehicle registration? ")}<span className="field-optionality">{t("(Optional guidance)")}</span></label>
      <select id="ownership-guidance" value={ownership} onChange={event => setOwnership(event.target.value)} aria-describedby="ownership-help">
        <option value="">{t("Choose to see your Owner checklist")}</option>
        {Object.entries(ownershipGuidance).map(([value, guide]) => <option key={value} value={value}>{t(guide.title)}</option>)}
      </select>
      <p id="ownership-help" className="upload-helper">{t("Select the registered owner to see which evidence supports your application.")}</p>
      {ownership && <p className="ownership-case" role="status">{t(ownershipGuidance[ownership].text)}</p>}
      <p className="vehicle-registration-note">{t("Authorization proves your permission to manage a vehicle; it does not replace its registration. Vehicle registration and vehicle verification remain separate from role approval, including for another individual’s or a company’s vehicle.")}</p>
      </>}
      <p>{t("Required evidence must be reviewed and approved before role approval. You can submit documents individually; uploading a file does not approve your role.")}</p>
    </div>}
    <form ref={formRef} className="private-upload" onSubmit={submit} noValidate aria-label={t("Private document upload")}>
      <ErrorNotice error={error}/>
      {notice && <p className="notice success" role="status">{t(notice)}</p>}
      <fieldset disabled={busy}>
        <legend>{correctionType?t('Correct requested evidence'):t('Upload one document')}</legend>
        <Field name="document_type" label="Document type" required helper="Choose the kind of document you are uploading." error={fields.document_type}>
          <select value={type} onChange={event => { setType(event.target.value); setPrintedExpiry(false); setFields({}); setError(null); setNotice('') }}>
            {availableTypes.map(value => <option key={value} value={value}>{t(documentTypes[value].label)}</option>)}
          </select>
        </Field>
        <div className="document-type-guidance" aria-live="polite">
          <span className="document-requirement">{owner || driver ? documentRequirement(type, ownership) : t('Optional for your Passenger profile')}</span>
          <p>{t(info.helper)}</p>
          {['NIC', 'PASSPORT'].includes(type) && <p>{t("One identity document is required for role approval; this upload is optional if you already provided the other valid identity document.")}</p>}
          {type === 'VEHICLE_REGISTRATION' && ownership && ownership !== 'SELF' && <p>{t("For this Owner application, provide the registered owner’s authorization. Keep the vehicle registration available for separate vehicle verification; authorization does not waive registration.")}</p>}
          {type === 'OWNER_AUTHORISATION' && ownership === 'SELF' && <p>{t("Your own vehicle registration is the required ownership evidence for this case.")}</p>}
        </div>
        <p className="upload-metadata-note">{driverLicence ? t('Copy the licence details exactly as printed. A current expiry date and Sri Lanka issuing country are required. Upload corrected evidence; its verification must be completed again before Driver approval.') : t('The details below are optional for uploading. Copy only what is printed on the document; leave missing numbers or dates blank. Missing approval evidence may still need correction during review.')}</p>
        <div className="upload-metadata" key={type}>
          <Field name="number" label={t(info.number)} helper="Copy the printed document or reference number, up to 100 characters; leave blank if none is printed." error={fields.number}>
            <input maxLength={100} autoComplete="off"/>
          </Field>
          {info.country && <Field name="issuing_country" label="Issuing country" required={driverLicence} helper="Choose the country that issued this document, not your nationality or phone country." error={fields.issuing_country}>
            <select defaultValue={type === 'DRIVING_LICENCE' ? 'LK' : ''}>
              <option value="">{t("Select country if known")}</option>
              {documentCountries.map(country => <option key={country.code} value={country.code}>{country.name}</option>)}
            </select>
          </Field>}
          {type === 'DRIVING_LICENCE' && <p className="upload-approval-note">{t("Driver approval requires a licence issued by Sri Lanka with a valid expiry date. A foreign-issued licence cannot satisfy this requirement.")}</p>}
          <Field name="issue_date" label="Issue date" helper="Enter the date marked as the issue date; leave blank if it is not printed." error={fields.issue_date}>
            <input type="date"/>
          </Field>
          {!info.expiry && <label className="printed-expiry"><input type="checkbox" checked={printedExpiry} onChange={event => { setPrintedExpiry(event.target.checked); setFields(previous => ({ ...previous, expiry_date: undefined })) }}/><span>{t("This document has a printed expiry date (Optional)")}</span></label>}
          {(info.expiry || printedExpiry) && <Field name="expiry_date" label="Expiry date" required={driverLicence} helper={driverLicence ? 'Enter the valid expiry date printed on the replacement driving licence.' : info.expiry ? 'Copy the printed expiry date; it is needed before role approval, but leave blank if missing rather than guessing.' : 'Copy the printed expiry date; leave blank if the document does not state one.'} error={fields.expiry_date}>
            <input type="date"/>
          </Field>}
        </div>
        <Field key={`file-${type}`} name="file" label="Document file" required helper="Choose one PDF, JPG/JPEG or PNG, up to 10 MiB (10,485,760 bytes); include the readable document details in that file." error={fields.file}>
          <input type="file" accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"/>
        </Field>
        <button className="button" disabled={busy}>{busy ? t('Submitting private document…') : t('Submit private document')}</button>
      </fieldset>
    </form>
  </>
}
