import { t } from '../../i18n/language.js'
import React,{useEffect,useRef,useState} from 'react'
import {api} from '../../services/api'
import {ErrorNotice} from '../../components/components'
import {evidenceMetadataErrors,reusableApplicationEvidence,validateApplicationEvidence} from '../../services/applicationEvidence'
import {documentCountries,documentTypes} from '../../services/documentUpload'
import {fieldErrors} from '../../services/fieldErrors.js'
import {codeLabel} from '../../i18n/codeLabels.js'
import {Field,Compact} from '../owner/OwnerRates'
import {WizardPane,WizardNav,useWizard} from '../booking/flow/FlowParts'

async function readDocuments(userId){
  let page=1,items=[],result
  do {result=await api(`/documents?user_id=${userId}&page=${page}&page_size=100`,{cache:'no-store'});items.push(...result.items);page++} while(result.has_next)
  const replaced=new Set(items.map(item=>item.superseded_document_id).filter(Boolean))
  return items.filter(item=>!replaced.has(item.id)&&item.status!=='SUPERSEDED')
}
export {readDocuments}

export default function RoleApplicationForm({role,user,onSubmitted,evidenceOnly=false,resubmission=false,rejection=''}){
  const owner=role==='OWNER',name=owner?'Owner':'Driver'
  const [identity,setIdentity]=useState('NIC'),[ownership,setOwnership]=useState(''),[docs,setDocs]=useState(null),[values,setValues]=useState({}),[errors,setErrors]=useState({}),[error,setError]=useState(null),[busy,setBusy]=useState(false),[uncertain,setUncertain]=useState(false),[retry,setRetry]=useState(0)
  const sent=useRef({}),sending=useRef(false),w=useWizard(3),labels=[owner?['Identity','Vehicle registration','Review']:['Identity','Driving licence','Review']][0]
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
  function next(){
    const invalid={},step=[[identity],[...(other?[other]:[])]][w.step]||[]
    if(w.step===1&&owner&&!ownership)invalid.ownership='Choose whose name appears on the registration.'
    for(const type of step){if(sent.current[type]||(existing(type)&&!values[type]?.replace))continue;const check=validateApplicationEvidence(bodyFor(type));for(const [key,message] of Object.entries(check))invalid[`${type}.${key}`]=message}
    setErrors(current=>({...current,...invalid}));if(Object.keys(invalid).length)return
    w.forward()
  }
  const evidence=type=>{const info=documentTypes[type],v=values[type]||{},old=existing(type),retained=docs?.find(d=>d.document_type===type),reused=old&&!v.replace,done=sent.current[type]
    return <section className="app-evidence" key={type}>
      <p className="app-hint"><strong>{t(info.label)}</strong> · {t(info.helper)}</p>
      {retained&&!old&&<p className="notice">{t("The previous ")}{t(info.label)} ({codeLabel(retained.status)}{t(") cannot be reused. ")}{Object.values(evidenceMetadataErrors(retained)).map(message=>t(message)).join(' ')}{t(" Upload replacement evidence below; the previous document and review history will be retained.")}</p>}
      {done?<p role="status">{t("Document uploaded for review.")}</p>:<>
        {old&&<label className="single-application-replace"><input type="checkbox" checked={Boolean(v.replace)} onChange={e=>update(type,'replace',e.target.checked)}/>{t(" Replace existing ")}{t(info.label)} ({codeLabel(old.status)})</label>}
        {reused?<p className="app-hint">{t("Your existing document will be used. A replacement supersedes the previous document.")}</p>:<div className="app-grid">
          <Field label="Document file" help="PDF, JPG or PNG"><input name={`${type}-file`} type="file" accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png" onChange={e=>update(type,'file',e.target.files[0])} aria-invalid={Boolean(errors[`${type}.file`])}/></Field>
          <Field label={info.number} optional><input name={`${type}-number`} maxLength={100} value={v.number||''} onChange={e=>update(type,'number',e.target.value)}/></Field>
          {info.country&&<Field label="Issuing country" optional><select name={`${type}-country`} value={v.issuing_country??(type==='DRIVING_LICENCE'?'LK':'')} onChange={e=>update(type,'issuing_country',e.target.value)}><option value="">{t("Select country if known")}</option>{documentCountries.map(c=><option key={c.code} value={c.code}>{c.name}</option>)}</select></Field>}
          <Field label="Issue date" optional><input name={`${type}-issue`} type="date" value={v.issue_date||''} onChange={e=>update(type,'issue_date',e.target.value)}/></Field>
          <Field label={info.expiry?'Expiry date (needed for approval)':'Expiry date'} optional={!info.expiry}><input name={`${type}-expiry`} type="date" value={v.expiry_date||''} onChange={e=>update(type,'expiry_date',e.target.value)}/></Field>
        </div>}
        {Object.entries(errors).filter(([key,message])=>message&&key.startsWith(type+'.')).map(([key,message])=><p key={key} className="upload-field-error" role="alert">{t(message)}</p>)}
        {type==='DRIVING_LICENCE'&&<p className="app-hint">{t("Driver approval requires a Sri Lanka-issued licence with a valid expiry date.")}</p>}
      </>}
    </section>}
  const fileName=type=>sent.current[type]?t('Uploaded'):values[type]?.file?.name||(existing(type)&&!values[type]?.replace?t('Your existing document'):t('Not added yet'))
  return <form className="single-application app-wizard" onSubmit={submit} noValidate aria-label={t("{value0} application form", {value0: name})}>
    <p className="tk-stepline"><strong>{user.full_name}</strong>{user.email?` · ${user.email}`:''} · {t('Step {value0} of {value1}',{value0:w.step+1,value1:3})} · {t(labels[w.step])}</p>
    {resubmission&&w.step===0&&<p className="app-hint app-reject" role="status"><strong>{t("Application rejected: ")}</strong>{rejection} {t("Your previous rejection is retained. Correct the evidence below and resubmit this same application for a new review.")}</p>}
    {docs===null&&!error&&<p role="status">{t("Checking your retained evidence…")}</p>}
    <ErrorNotice error={error}/>{!docs&&error&&<button type="button" className="button outline" onClick={()=>setRetry(retry+1)}>{t("Retry evidence check")}</button>}{uncertain&&<p role="alert">{t("The upload outcome is uncertain. Do not resubmit the file yet. Reload this page and check your retained documents before continuing.")}</p>}
    <Compact.Provider value={true}><fieldset disabled={busy||!docs||uncertain}>
      <WizardPane w={w} index={0}>
        <Field label="Identity document"><select name="identity-kind" value={identity} onChange={e=>setIdentity(e.target.value)}><option value="NIC">{t("National identity card (NIC)")}</option><option value="PASSPORT">{t("Passport")}</option></select></Field>
        {evidence(identity)}
      </WizardPane>
      <WizardPane w={w} index={1}>
        {owner&&<Field label="Whose name is on the vehicle registration?"><select name="registration-owner" value={ownership} onChange={e=>{setOwnership(e.target.value);setErrors(c=>({...c,ownership:null}))}} aria-invalid={Boolean(errors.ownership)}><option value="">{t("Choose one")}</option><option value="SELF">{t("My name")}</option><option value="INDIVIDUAL">{t("Another individual’s name")}</option><option value="COMPANY">{t("A company’s name")}</option></select></Field>}
        {errors.ownership&&<p className="upload-field-error" role="alert">{t(errors.ownership)}</p>}
        {other?evidence(other):<p className="app-hint">{t("Choose whose name is on the registration to see what to upload.")}</p>}
      </WizardPane>
      <WizardPane w={w} index={2}>
        <dl className="app-review">{types.map(type=><div key={type}><dt>{t(documentTypes[type].label)}</dt><dd>{fileName(type)}</dd></div>)}</dl>
        <p className="app-hint">{t("Upload the required evidence once. Super Admin reviews your details and documents with this application.")}</p>
        {errors.ownership&&<p className="upload-field-error" role="alert">{t(errors.ownership)}</p>}
        <button type="submit" className="ui-button ui-button-primary">{busy?t('Submitting…'):evidenceOnly?t('Submit missing evidence'):t("{value0} {value1} application", {value0: resubmission?'Resubmit':'Submit', value1: name})}</button>
      </WizardPane>
    </fieldset></Compact.Provider>
    <WizardNav w={w} onNext={next}/>
  </form>
}
