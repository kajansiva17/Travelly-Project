import React, { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, logout, hasSession, clearSession } from './api'
import { Icon, ErrorNotice } from './components'
import OwnDocuments from './OwnDocuments'
import ProfileAuth from './ProfileAuth'

export default function AccountPage() {
  const navigate = useNavigate()
  const [user, setUser] = useState(null)
  const [roles, setRoles] = useState([])
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState('')
  useEffect(()=>{
    let cancelled = false
    if (!hasSession()) { navigate('/login', {replace:true}); return }
    Promise.all([api('/users/me'), api('/users/me/roles')]).then(([u,r])=>{if(!cancelled){setUser(u);setRoles(r.items)}}).catch(err=>{if(!cancelled){if(err.status===401){clearSession();navigate('/login',{replace:true})}else setError(err)}})
    document.title = 'Your account | Travelly'
    return ()=>{cancelled=true}
  },[navigate])
  async function signOut() {
    setBusy('logout');setError(null)
    try {await logout();navigate('/login',{replace:true})}catch(err){setError(err)}finally{setBusy('')}
  }
  return <main className="account-main" id="main"><div className="account-heading"><div><div className="section-kicker"><span/> YOUR TRAVELLY ACCOUNT</div><h1>Hello{user ? `, ${user.full_name.split(' ')[0]}` : ''}.</h1><p className="intro">You’re in. Let’s make this account yours.</p></div><button className="secondary" onClick={signOut} disabled={Boolean(busy)}><Icon name="exit"/> Sign out</button></div><ErrorNotice error={error}/>{!user ? <div className="loading" role="status"><span className="spinner"/> Loading your account…</div> : <><div className="profile-card"><div className="avatar">{user.full_name[0]}</div><div><h2>{user.full_name}</h2><p>{user.email || user.phone_e164}</p></div><span className="badge">Passenger</span></div><div className="verification-note"><Icon name="shield" size={25}/><div><strong>{user.email_verified_at || user.phone_verified_at ? 'Contact verified' : 'Your contact is awaiting verification'}</strong><p>{user.email_verified_at || user.phone_verified_at ? 'Your contact verification is recorded separately from your roles.' : 'Your Passenger membership is active. Contact verification is a separate step before booking becomes available.'}</p></div></div><section className="roles-section"><div className="roles-heading"><h2>One account. More possibilities.</h2><p>Your Owner and Driver applications are reviewed separately.</p></div><div className="role-grid">{['OWNER','DRIVER'].map(code=>{const role=roles.find(r=>r.role_code===code);const mayApply=!role || role.approval_status==='REJECTED';return <article className="role-card" key={code}><span className="role-icon"><Icon name={code==='OWNER'?'shield':'user'} size={24}/></span><h3>{code==='OWNER'?'Become an Owner':'Become a Driver'}</h3><p>{code==='OWNER'?'Start your Owner application with this account.':'Apply for Driver membership using your shared profile.'}</p>{role && <span className={`status status-${role.approval_status.toLowerCase()}`}>{role.approval_status.replace('_',' ')}</span>}{role?.rejection_reason && <p>{role.rejection_reason}</p>}{role?.suspension_reason && <p>{role.suspension_reason}</p>}{mayApply ? <Link className="role-apply" to={`/dashboard#${code.toLowerCase()}-application`}>{role?'Apply again':'Start application'} <Icon name="arrow" size={17}/></Link> : <small>{role.approval_status==='PENDING'?'Application received. Approval is pending.':role.approval_status==='APPROVED'?'Role approved. Operational eligibility is checked separately.':'This role is currently suspended.'}</small>}</article>})}</div></section><ProfileAuth user={user}/><OwnDocuments user={user}/></>}</main>
}

