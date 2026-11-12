import { t } from '../i18n/language.js'
import React, { useCallback, useEffect, useRef, useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { api, logout, hasSession, clearSession } from '../services/api'
import { Icon, ErrorNotice, useSession } from '../components/components'
import OwnDocuments from '../components/OwnDocuments'
import MyRoles from '../features/auth/MyRoles'
import ProfileAuth from '../features/auth/ProfileAuth'
import AdminProfile from '../features/admin/AdminProfile'
import {FlowShell} from '../features/booking/flow/FlowParts'
import Chip from '../components/ui/Chip'
import ProfileDetails,{PROFILE_FORM_ID} from '../features/auth/ProfileDetails'
import {useWorkspace} from '../context/workspaceContext'
import {accountPath,personalBookingsPath,workspaceRoles} from '../routes/workspaceRoutes'
import {onboardingPath,journeyLink} from '../features/auth/onboardingJourney'

export default function AccountPage() {
  const navigate=useNavigate(),signedIn=useSession(),{hash}=useLocation(),workspace=useWorkspace(),role=workspace.role
  const documentFlow=['OWNER','DRIVER'].includes(role)?role:'SHARED',roleName=role==='OWNER'?'Owner':role==='DRIVER'?'Driver':'Admin'
  const home=role==='PASSENGER'?'/':workspaceRoles[role].home,trips=['OWNER','DRIVER'].includes(role)?personalBookingsPath(role):'/bookings'
  const [user,setUser]=useState(null),[roles,setRoles]=useState([]),[error,setError]=useState(null),[busy,setBusy]=useState('')
  const request=useRef(0),[tab,setTab]=useState(()=>hash==='#own-documents-heading'?2:0),[form,setForm]=useState({busy:false,changed:false,message:''})
  const load=useCallback(async()=>{
    const version=++request.current
    try{const [u,r]=await Promise.all([api('/users/me'),api('/users/me/roles')]);if(version===request.current&&hasSession()){setUser(u);setRoles(r.items);setError(null)}}
    catch(err){if(version!==request.current)return;if(err.status===401){clearSession();navigate(journeyLink('/login',role),{replace:true})}else setError(err)}
  },[navigate,role])
  useEffect(()=>{if(signedIn)load();document.title='Your account | Travelly';return()=>{request.current++}},[signedIn,load])
  useEffect(()=>{if(user&&hash)requestAnimationFrame(()=>document.getElementById(hash.slice(1))?.scrollIntoView({block:'start'}))},[user,hash])
  async function signOut(){setBusy('logout');try{await logout();navigate('/login',{replace:true})}catch(err){setError(err)}finally{setBusy('')}}
  if(!signedIn)return <Navigate to={journeyLink('/login',role)} replace/>
  if(role==='ADMIN')return <AdminProfile user={user} onSaved={setUser} error={error}/>
  const tabs=[{label:t('Account security'),active:tab===0,onClick:()=>setTab(0),icon:'shield'},{label:t('Profile details'),active:tab===1,onClick:()=>setTab(1),icon:'user'},{label:t('Documents'),active:tab===2,onClick:()=>setTab(2),icon:'document'},{label:t('My roles'),active:tab===3,onClick:()=>setTab(3),icon:'users'}]
  const approved=user?['OWNER','DRIVER','ADMIN'].filter(code=>user.approved_roles.includes(code)&&roles.some(r=>r.role_code===code&&r.approval_status==='APPROVED')):[]
  return <FlowShell heading={t('Your account')} title={[t('Account security'),t('Profile details'),t('Documents'),t('My roles')][tab]} icon="user" tabs={tabs}
    info={tab===3?t("Your Owner and Driver applications. Each is reviewed separately, and the buttons open the same application form."):tab===0?t("Contact verification and role approval are checked separately."):tab===1?t("Update your name and mobile number. Your email address is changed through account recovery."):t("Correct a reviewed file by submitting a new document of the same type in its matching evidence flow. Earlier files and reasons are retained; replacing a file does not reinstate a suspended role.")}>
    <ErrorNotice error={error}/>
    {!user?!error&&<p role="status">{t("Loading your account…")}</p>:<>
      <div className="flow-wizard-form account-pane" hidden={tab!==0}><ProfileAuth user={user}/>
        <div className="flow-actions"><button type="button" className="ui-button ui-button-secondary" onClick={signOut} disabled={Boolean(busy)}><Icon name="exit"/>{t("Sign out")}</button>
          <span className="status-chips">{role==='PASSENGER'&&approved.map(code=><Link className="ui-button ui-button-secondary" key={code} to={`/${code.toLowerCase()}/dashboard`}>{code==='ADMIN'?t('Admin'):code==='OWNER'?t('Owner'):t('Driver')}<Icon name="arrow" size={16}/></Link>)}<Link className="ui-button ui-button-secondary" to={role==='PASSENGER'?trips:home}>{role==='PASSENGER'?t('My Trips'):t('Back to {value0} dashboard',{value0:t(roleName)})}<Icon name="arrow" size={16}/></Link></span></div></div>
      <div className="flow-wizard-form account-pane" hidden={tab!==1}><ProfileDetails user={user} onState={setForm}/>
        <div className="flow-actions"><span className="status-chips">{form.message&&<Chip tone="success">{t(form.message)}</Chip>}</span><button type="submit" form={PROFILE_FORM_ID} className="ui-button ui-button-primary" disabled={form.busy||!form.changed}>{form.busy?t('Saving…'):t('Save Changes')}</button></div></div>
      {tab===2&&<div className="flow-wizard-form account-pane account-docs"><OwnDocuments key={`${user.id}-${documentFlow}`} user={user} flow={documentFlow} evidencePath={code=>workspace.allowed.includes(code)?accountPath(code):onboardingPath(code)}/></div>}
      {tab===3&&<div className="flow-wizard-form account-pane"><MyRoles key={user.id}/></div>}
    </>}
  </FlowShell>
}
