import { t } from '../../i18n/language.js'
import React,{useEffect,useRef,useState} from 'react'
import {api} from '../../services/api'
import {ErrorNotice} from '../../components/components'
import {evidenceMetadataErrors,reusableApplicationEvidence,validateApplicationEvidence} from '../../services/applicationEvidence'
import {documentCountries,documentTypes} from '../../services/documentUpload'
import {fieldErrors} from '../../services/fieldErrors.js'

async function readDocuments(userId){
  let page=1,items=[],result
  do {result=await api(`/documents?user_id=${userId}&page=${page}&page_size=100`,{cache:'no-store'});items.push(...result.items);page++} while(result.has_next)
  const replaced=new Set(items.map(item=>item.superseded_document_id).filter(Boolean))
  return items.filter(item=>!replaced.has(item.id)&&item.status!=='SUPERSEDED')
}
export {readDocuments}

export default function RoleApplicationForm({role,user,onSubmitted,evidenceOnly=false,resubmission=false}){
  const owner=role==='OWNER',name=owner?'Owner':'Driver'
  const [identity,setIdentity]=useState('NIC'),[ownership,setOwnership]=useState(''),[docs,setDocs]=useState(null),[values,setValues]=useState({}),[errors,setErrors]=useState({}),[error,setError]=useState(null),[busy,setBusy]=useState(false),[uncertain,setUncertain]=useState(false),[retry,setRetry]=useState(0)
  const sent=useRef({}),sending=useRef(false)
  useEffect(()=>{let active=true;readDocuments(user.id).then(d=>{if(active){setDocs(d);setError(null)}}).catch(e=>{if(active)setError(e)});return()=>{active=false}},[user.id,retry])
  const other=owner?(ownership==='SELF'?'VEHICLE_REGISTRATION':ownership?'OWNER_AUTHORISATION':null):'DRIVING_LICENCE'
  const types=[identity,...(other?[other]:[])]
  function existing(type){return docs?.find(d=>d.document_type===type&&reusableApplicationEvidence(d))}
  function update(type,key,value){setValues(current=>({...current,[type]:{...current[type],[key]:value}}));setErrors(current=>({...current,[`${type}.${key}`]:null}))}
  function bodyFor(type){const body=new FormData();body.set('owner_type','USER');body.set('owner_id',user.id);body.set('document_type',type);const v=values[type]||{};for(const key of ['number','issuing_country','issue_date','expiry_date','file'])if(v[key])body.set(key,v[key]);if(type==='DRIVING_LICENCE'&&v.issuing_country===undefined)body.set('issuing_country','LK');return body}
  async function submit(event){
    event.preventDefault();if(sending.current||uncertain||!docs)return
    const invalid={};if(owner&&!ownership)invalid.ownership='Choose whose name appears on the registration.'
    for(const type of types){if(sent.current[type]||(existing(type)&&!values[type]?.replace))continue;const check=validateApplicationEvidence(bodyFor(type));for(const [key,message] of Object.entries(check))invalid[`${type}.${key}`]=message}
    setErrors(invalid);setError(null);if(Object.keys(invalid).length)return
    sending.current=true;setBusy(true)
    try{
      for(const type of types){if(sent.current[type]||(existing(type)&&!values[type]?.replace))continue
        try{const uploaded=await api('/documents',{method:'POST',body:bodyFor(type)});sent.current[type]=uploaded.id}
        catch(e){const inline=Object.fromEntries(fieldErrors(e).filter(f=>['file','number','issuing_country','issue_date','expiry_date'].includes(f.field)).map(f=>[`${type}.${f.field}`,f.message]));setErrors(current=>({...current,...inline}));if(!e.status||e.status>=500)setUncertain(true);throw e}
      }
      if(!evidenceOnly)await api('/users/me/role-requests',{method:'POST',body:JSON.stringify({role_code:role})})
      await onSubmitted()
    }catch(e){setError(e);if(e.code==='ROLE_ALREADY_REQUESTED')await onSubmitted()}
    finally{sending.current=false;setBusy(false)}
  }
  return <form className="workspace-card single-application" onSubmit={submit} noValidate aria-label={t("{value0} application form", {value0: name})}>
    <h2>{t(name)}{t(" application")}</h2><p>{t("Your account: ")}{user.full_name}{user.email?` · ${user.email}`:''}{user.phone_e164?` · ${user.phone_e164}`:''}</p>
    {resubmission&&<p>{t("Your previous rejection is retained. Correct the evidence below and resubmit this same application for a new review.")}</p>}
    <p>{t("Upload the required evidence once. Super Admin reviews your details and documents with this application.")}</p>
    {docs===null&&!error&&<p role="status">{t("Checking your retained evidence…")}</p>}
    <ErrorNotice error={error}/>{!docs&&error&&<button type="button" className="button outline" onClick={()=>setRetry(retry+1)}>{t("Retry evidence check")}</button>}{uncertain&&<p role="alert">{t("The upload outcome is uncertain. Do not resubmit the file yet. Reload this page and check your retained documents before continuing.")}</p>}
    <fieldset disabled={busy||!docs||uncertain}>
      <label htmlFor="identity-kind">{t("Identity document ")}<span>{t("(Required)")}</span></label><select id="identity-kind" value={identity} onChange={e=>setIdentity(e.target.value)}><option value="NIC">{t("National identity card (NIC)")}</option><option value="PASSPORT">{t("Passport")}</option></select>
      {owner&&<><label htmlFor="registration-owner">{t("Whose name is on the vehicle registration? ")}<span>{t("(Required)")}</span></label><select id="registration-owner" value={ownership} onChange={e=>setOwnership(e.target.value)} aria-invalid={Boolean(errors.ownership)}><option value="">{t("Choose one")}</option><option value="SELF">{t("My name")}</option><option value="INDIVIDUAL">{t("Another individual’s name")}</option><option value="COMPANY">{t("A company’s name")}</option></select>{errors.ownership&&<p className="upload-field-error" role="alert">{t(errors.ownership)}</p>}<p>{t("Vehicle registration and vehicle verification remain separate from role approval.")}</p></>}
      {types.map(type=>{const info=documentTypes[type],v=values[type]||{},old=existing(type),retained=docs?.find(d=>d.document_type===type),reused=old&&!v.replace,done=sent.current[type];return <section className="single-application-evidence" key={type}>
        <h3>{t(info.label)}</h3><p>{t(info.helper)}</p>{retained&&!old&&<p className="notice">{t("The previous ")}{t(info.label)} ({t(retained.status.replaceAll('_',' '))}{t(") cannot be reused. ")}{Object.values(evidenceMetadataErrors(retained)).map(message=>t(message)).join(' ')}{t(" Upload replacement evidence below; the previous document and review history will be retained.")}</p>}
        {done?<p role="status">{t("Document uploaded for review.")}</p>:<>{old&&<label className="single-application-replace"><input type="checkbox" checked={Boolean(v.replace)} onChange={e=>update(type,'replace',e.target.checked)}/>{t(" Replace existing ")}{t(info.label)} ({t(old.status.replaceAll('_',' '))})</label>}{reused?<p>{t("Your existing document will be used. A replacement supersedes the previous document.")}</p>:<>
          <label htmlFor={`${type}-file`}>{t("Document file (Required)")}</label><input id={`${type}-file`} type="file" accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png" onChange={e=>update(type,'file',e.target.files[0])} aria-invalid={Boolean(errors[`${type}.file`])}/>{errors[`${type}.file`]&&<p className="upload-field-error" role="alert">{t(errors[`${type}.file`])}</p>}<small>{t("PDF, JPG or PNG; maximum 10 MiB.")}</small>
          <label htmlFor={`${type}-number`}>{t(info.number)}{t(" (Optional)")}</label><input id={`${type}-number`} maxLength={100} value={v.number||''} onChange={e=>update(type,'number',e.target.value)}/>{errors[`${type}.number`]&&<p className="upload-field-error">{t(errors[`${type}.number`])}</p>}
          {info.country&&<><label htmlFor={`${type}-country`}>{t("Issuing country (Optional)")}</label><select id={`${type}-country`} value={v.issuing_country??(type==='DRIVING_LICENCE'?'LK':'')} onChange={e=>update(type,'issuing_country',e.target.value)}><option value="">{t("Select country if known")}</option>{documentCountries.map(c=><option key={c.code} value={c.code}>{c.name}</option>)}</select>{errors[`${type}.issuing_country`]&&<p className="upload-field-error">{t(errors[`${type}.issuing_country`])}</p>}</>}
          {type==='DRIVING_LICENCE'&&<p>{t("Driver approval requires a Sri Lanka-issued licence with a valid expiry date.")}</p>}
          {['issue_date','expiry_date'].map(key=><React.Fragment key={key}><label htmlFor={`${type}-${key}`}>{key==='issue_date'?t('Issue date (Optional)'):info.expiry?t('Expiry date (Required for role approval)'):t('Expiry date (Optional)')}</label><input id={`${type}-${key}`} type="date" value={v[key]||''} onChange={e=>update(type,key,e.target.value)}/>{errors[`${type}.${key}`]&&<p className="upload-field-error">{t(errors[`${type}.${key}`])}</p>}</React.Fragment>)}
        </>}</>}
      </section>})}
      <button type="submit" className="button">{busy?t('Submitting…'):evidenceOnly?t('Submit missing evidence'):t("{value0} {value1} application", {value0: resubmission?'Resubmit':'Submit', value1: name})}</button>
    </fieldset>
  </form>
}
