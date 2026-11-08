import { t } from '../i18n/language.js'
import React, { useCallback, useEffect, useRef, useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { api, logout, hasSession, clearSession } from '../services/api'
import { Icon, ErrorNotice, useSession } from '../components/components'
import OwnDocuments from '../components/OwnDocuments'
import ProfileAuth from '../features/auth/ProfileAuth'
import AdminProfile from '../features/admin/AdminProfile'
import {useWorkspace} from '../context/workspaceContext'
import {accountPath,workspaceRoles} from '../routes/workspaceRoutes'
import {onboardingPath,journeyLink} from '../features/auth/onboardingJourney'

export default function AccountPage() {
  const navigate=useNavigate(),signedIn=useSession(),{hash}=useLocation(),workspace=useWorkspace(),role=workspace.role
  const documentFlow=['OWNER','DRIVER'].includes(role)?role:'SHARED',roleName=role==='OWNER'?'Owner':role==='DRIVER'?'Driver':'Admin'
  const home=role==='PASSENGER'?'/':workspaceRoles[role].home,trips=['OWNER','DRIVER'].includes(role)?workspaceRoles[role].prefix+'/personal/bookings':'/bookings'
  const [user,setUser]=useState(null),[roles,setRoles]=useState([]),[error,setError]=useState(null),[busy,setBusy]=useState('')
  const request=useRef(0)
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
  return <main className="account-main" id="main"><Link className="inline-link" to={home}>{role==='PASSENGER'?t('Back to booking home'):t("Back to {value0} dashboard", {value0: t(roleName)})}</Link>
    <div className="account-heading"><div><div className="section-kicker">{t("YOUR TRAVELLY ACCOUNT")}</div><h1>{t("Hello")}{user?`, ${user.full_name.split(' ')[0]}`:''}.</h1><p className="intro">{t("Your details and private documents. All in one place.")}</p></div><button className="button outline" onClick={signOut} disabled={Boolean(busy)}><Icon name="exit"/>{t(" Sign out")}</button></div><ErrorNotice error={error}/>
    {!user?!error&&<p role="status">{t("Loading your account?")}</p>:<>
      <div className="profile-card"><div className="avatar">{user.full_name[0]}</div><div><h2>{user.full_name}</h2><p>{user.email||user.phone_e164}</p></div><Link className="button outline" to={role==='ADMIN'?home:trips}>{role==='ADMIN'?t('Admin dashboard'):t('My Trips')}<Icon name="arrow"/></Link></div>
      <div className="verification-note"><Icon name="shield" size={25}/><div><strong>{user.email_verified_at||user.phone_verified_at?t('Contact verified'):t('Your contact is awaiting verification')}</strong><p>{t("Contact verification and role approval are checked separately.")}</p></div></div>
      {role==='PASSENGER'&&<nav className="approved-workspace-links" aria-label={t("Your approved workspaces")}>{['OWNER','DRIVER','ADMIN'].filter(code=>user.approved_roles.includes(code)&&roles.some(r=>r.role_code===code&&r.approval_status==='APPROVED')).map(code=><Link className="button outline" key={code} to={`/${code.toLowerCase()}/dashboard`}>{t("Open ")}{code==='ADMIN'?t('Admin'):code==='OWNER'?t('Owner'):t('Driver')}{t(" workspace")}<Icon name="arrow" size={16}/></Link>)}</nav>}<ProfileAuth user={user}/><OwnDocuments key={`${user.id}-${documentFlow}`} user={user} flow={documentFlow} evidencePath={code=>workspace.allowed.includes(code)?accountPath(code):onboardingPath(code)}/>
    </>}
  </main>
}
