import { getLocale } from '../../i18n/language.js'
import { t } from '../../i18n/language.js'
import {useCallback,useEffect,useRef,useState} from 'react'
import {Link,Navigate} from 'react-router-dom'
import {api,hasSession} from '../../services/api'
import {ErrorNotice,useSession} from '../../components/components'
import {eligibleWorkspaces} from '../../routes/workspaceRoutes'
import {evidenceMetadataErrors} from '../../services/applicationEvidence'
import {journeyLink} from './onboardingJourney'
import RoleApplicationForm,{readDocuments} from './RoleApplicationForm'
import DocumentUploadForm from '../../components/DocumentUploadForm'
import {FlowShell} from '../booking/flow/FlowParts'
import '../../styles/onboarding.css'
import {codeLabel} from '../../i18n/codeLabels.js'

export default function RoleOnboarding({role}) {
  const signedIn=useSession(),name=role==='OWNER'?'Owner':'Driver'
  const [data,setData]=useState(null),[error,setError]=useState(null),[corrections,setCorrections]=useState([]),[correction,setCorrection]=useState(null),[missing,setMissing]=useState(false),[showMissing,setShowMissing]=useState(false)
  const [refreshing,setRefreshing]=useState(false)
  const [invalidLicence,setInvalidLicence]=useState(null),[fixLicence,setFixLicence]=useState(false)
  const sequence=useRef(0),inFlight=useRef(false),action=useRef(false)
  const load=useCallback(async()=>{
    if(inFlight.current)return
    const id=++sequence.current;inFlight.current=true;setRefreshing(true)
    try {
      const options={cache:'no-store'}
      const [user,roles,status]=await Promise.all([api('/users/me',options),api('/users/me/roles',options),api(`/users/me/role-requests/${role}/status`,options)])
      if(id===sequence.current&&hasSession()){setData({user,roles:roles.items,status});setError(null)}
    } catch(e) {if(id===sequence.current){setData(null);setError(e)}}
    finally {if(id===sequence.current){inFlight.current=false;setRefreshing(false)}}
  },[role])
  useEffect(()=>{
    action.current=false;setFixLicence(false);setInvalidLicence(null)
    setData(null);setError(null);setCorrections([]);setCorrection(null);document.title=`${t(name)} application | Travelly`
    if(signedIn)load()
    return()=>{sequence.current++;inFlight.current=false}
  },[signedIn,role,load,name])
  const membership=data?.roles.find(r=>r.role_code===role)
  useEffect(()=>{
    if(!data||membership?.approval_status!=='PENDING')return
    let active=true
    const relevant=['NIC','PASSPORT',...(role==='OWNER'?['VEHICLE_REGISTRATION','OWNER_AUTHORISATION']:['DRIVING_LICENCE'])]
    readDocuments(data.user.id).then(items=>{if(active){if(role==='DRIVER'){const licence=items.find(item=>item.document_type==='DRIVING_LICENCE');setInvalidLicence(licence&&!['NEEDS_CORRECTION','REJECTED'].includes(licence.status)&&Object.keys(evidenceMetadataErrors(licence)).length?licence:null)}const needs=items.filter(item=>['NEEDS_CORRECTION','REJECTED'].includes(item.status)&&relevant.includes(item.document_type));setCorrections(needs);const current=items.filter(item=>['SUBMITTED','UNDER_REVIEW','APPROVED'].includes(item.status));setMissing(!current.some(item=>['NIC','PASSPORT'].includes(item.document_type))||!current.some(item=>(role==='OWNER'?['VEHICLE_REGISTRATION','OWNER_AUTHORISATION']:['DRIVING_LICENCE']).includes(item.document_type)))}}).catch(e=>{if(active)setError(e)})
    return()=>{active=false}
  },[data,membership?.approval_status,role])
  useEffect(()=>{
    if(!signedIn)return
    const refresh=()=>{if(document.visibilityState==='visible'&&!inFlight.current&&!action.current)load()}
    window.addEventListener('focus',refresh);document.addEventListener('visibilitychange',refresh)
    // Only this mounted waiting journey observes approval; never a global redirect.
    const timer=membership?.approval_status==='PENDING'?setInterval(refresh,5000):null
    return()=>{clearInterval(timer);window.removeEventListener('focus',refresh);document.removeEventListener('visibilitychange',refresh)}
  },[signedIn,membership?.approval_status,load])
  if(!signedIn)return <Navigate to={journeyLink('/login',role)} replace/>
  const allowed=data?eligibleWorkspaces(data.user,data.roles):[]
  if(allowed.includes(role))return <Navigate to={`/${role.toLowerCase()}/dashboard`} replace/>
  const eligible=allowed.includes('PASSENGER'),pending=membership?.approval_status==='PENDING'
  return <FlowShell heading={t("{value0} application", {value0: name})} icon="document"
    title={pending?t("{value0} application submitted — waiting for Admin approval", {value0: name}):membership?.approval_status==='REJECTED'?t('Update your documents and resubmit'):t('Your details and documents')}
    info={pending?t('Your application is with Admin for review.'):t("Use your existing Travelly account to complete your {value0} journey.", {value0: name})}>
    <ErrorNotice error={error}/>
    {!data?!error&&<p role="status">{t("Loading your application…")}</p>:!eligible?<section className="rate-preview"><h2>{t("Account access unavailable")}</h2><p>{t("Your current account and Passenger membership must permit this application. A journey link cannot grant access.")}</p></section>:<>
      {pending?<><div className="flow-actions"><button type="button" className="ui-button ui-button-secondary" onClick={load} disabled={refreshing}>{t("Refresh application status")}</button></div>{refreshing&&<p role="status">{t("Checking the latest saved application status?")}</p>}{data.status?.application?.approval_status==='PENDING'&&data.status.approval_readiness&&<section className="rate-preview" aria-label={t("Pending approval requirements")}><h2>{data.status.approval_readiness.ready?t('Documents verified ? final role approval pending'):t('What is still required')}</h2><p>{t("Your saved application status is PENDING. Document verification and final role approval are separate decisions.")}</p><ul>{data.status.approval_readiness.requirements.map(item=><li key={item.label}><strong>{t(item.label)}</strong><p>{t(item.message)}</p></li>)}</ul><p>{t("No new application is needed. Last checked: ")}{new Date(data.status.checked_at).toLocaleString(getLocale(), {timeZone:'Asia/Colombo'})}{t(" (Sri Lanka).")}</p></section>}{role==='DRIVER'&&invalidLicence&&<section className="rate-preview" aria-label={t("Correct driving licence details")}><h2>{t("Driving licence needs corrected details")}</h2><p>{t("The saved document is ")}{t(invalidLicence.status)}{t(", but its metadata cannot satisfy Driver approval. ")}{Object.values(evidenceMetadataErrors(invalidLicence)).map(message=>t(message)).join(' ')}</p><p>{t("Replace this licence on the same application. Your approved NIC and any Owner access stay unchanged; Super Admin must review the replacement.")}</p>{fixLicence?<DocumentUploadForm user={data.user} flow="DRIVER" correctionType="DRIVING_LICENCE" onUploaded={async()=>{action.current=false;setFixLicence(false);setInvalidLicence(null);await load()}}/>:<button className="button outline" onClick={()=>{action.current=true;setFixLicence(true)}}>{t("Correct driving licence")}</button>}{fixLicence&&<button type="button" className="button outline" onClick={()=>{action.current=false;setFixLicence(false)}}>{t("Cancel licence correction")}</button>}</section>}{missing&&corrections.length===0&&(showMissing?<RoleApplicationForm role={role} user={data.user} evidenceOnly onSubmitted={async()=>{setShowMissing(false);setMissing(false);await load()}}/>:<section className="rate-preview"><p>{t("This earlier application is missing evidence needed for review.")}</p><button type="button" className="button outline" onClick={()=>setShowMissing(true)}>{t("Provide missing evidence")}</button></section>)}{corrections.map(doc=><section className="rate-preview" key={doc.id}><h2>{t("Correction requested: ")}{codeLabel(doc.document_type)}</h2><p>{doc.rejection_reason}</p>{correction===doc.id?<DocumentUploadForm user={data.user} flow={role} correctionType={doc.document_type} onUploaded={async()=>{setCorrection(null);setCorrections(await readDocuments(data.user.id).then(items=>items.filter(item=>['NEEDS_CORRECTION','REJECTED'].includes(item.status)&&(['NIC','PASSPORT',...(role==='OWNER'?['VEHICLE_REGISTRATION','OWNER_AUTHORISATION']:['DRIVING_LICENCE'])].includes(item.document_type)))))}}/>:<button type="button" className="button outline" onClick={()=>setCorrection(doc.id)}>{t("Correct requested evidence")}</button>}</section>)}</>:membership?.approval_status==='SUSPENDED'?<section className="rate-preview"><h2>{t("Role suspended")}</h2><p>{membership.suspension_reason||t('An authorized review is required.')}</p></section>:membership?.approval_status==='APPROVED'?<p className="notice" role="status">{t("Approval and current account access are being checked.")}</p>:<><RoleApplicationForm key={`${data.user.id}-${role}`} role={role} user={data.user} resubmission={membership?.approval_status==='REJECTED'} rejection={membership?.rejection_reason} onSubmitted={load}/></>}
    </>}
    {!data&&error&&<button className="button" onClick={load}>{t("Try again")}</button>}
  </FlowShell>
}
