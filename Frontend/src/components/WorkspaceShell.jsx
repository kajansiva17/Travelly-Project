import { t } from '../i18n/language.js'
import React,{useCallback,useEffect,useRef,useState} from 'react'
import {Link,Navigate,Outlet,useLocation,useNavigate} from 'react-router-dom'
import {api,logout} from '../services/api'
import {Header,Icon,ErrorNotice,useSession} from './components'
import DashboardAvatar from './DashboardAvatar'
import {WorkspaceContext} from '../context/workspaceContext'
import {accountPath,personalHirePath,eligibleWorkspaces,menuActive,requestedWorkspace,workspaceMenu,workspaceRoles} from '../routes/workspaceRoutes'
import {journeyLink} from '../features/auth/onboardingJourney'

export default function WorkspaceShell({role:fixedRole}){
 const location=useLocation(),navigate=useNavigate(),signedIn=useSession()
 const role=fixedRole||requestedWorkspace(location.search)
 const [access,setAccess]=useState({loading:true,user:null,roles:[],error:null})
 const [busy,setBusy]=useState(false),[logoutError,setLogoutError]=useState(null)
 const stamp=useRef(0),dialog=useRef(null),trigger=useRef(null),header=useRef(null),shell=useRef(null),account=useRef(null)
 const refreshAccess=useCallback(async({quiet=false}={})=>{
  const id=++stamp.current
  if(!quiet)setAccess({loading:true,user:null,roles:[],error:null})
  try{
   const [user,roles]=await Promise.all([api('/users/me'),api('/users/me/roles')])
   if(id===stamp.current)setAccess({loading:false,user,roles:roles.items,error:null})
  }catch(error){
   if(id===stamp.current)setAccess({loading:false,user:null,roles:[],error})
  }
 },[])
 useEffect(()=>{if(signedIn)refreshAccess();return()=>{stamp.current++}},[signedIn,role,location.pathname,refreshAccess])
 useEffect(()=>{
  if(!signedIn)return
  const refresh=()=>{if(document.visibilityState==='visible')refreshAccess({quiet:true})}
  window.addEventListener('focus',refresh);document.addEventListener('visibilitychange',refresh)
  return()=>{window.removeEventListener('focus',refresh);document.removeEventListener('visibilitychange',refresh)}
 },[signedIn,refreshAccess])
 useEffect(()=>{dialog.current?.close();account.current?.removeAttribute('open')},[location.key])
 useEffect(()=>{
  if(!header.current)return
  const observer=new ResizeObserver(()=>shell.current?.style.setProperty('--workspace-header-height',header.current.getBoundingClientRect().height+'px'))
  observer.observe(header.current)
  return()=>observer.disconnect()
 },[])
 useEffect(()=>{
  const media=matchMedia('(min-width:768px)')
  const close=()=>{if(media.matches)dialog.current?.close()}
  media.addEventListener('change',close)
  return()=>media.removeEventListener('change',close)
 },[])
 const allowed=eligibleWorkspaces(access.user,access.roles)
 const authorized=allowed.includes(role)
 const info=workspaceRoles[role]
 async function signOut(){
  if(busy)return
  setBusy(true);setLogoutError(null)
  try{await logout();navigate('/login',{replace:true})}catch(error){setLogoutError(error)}finally{setBusy(false)}
 }
 function openSidebar(){dialog.current?.showModal()}
 if(!signedIn)return <Navigate to={journeyLink('/login',role)} replace/>
 function Sidebar({mobile=false}){
  return <>
   <div className="workspace-sidebar-title">
    <div><span className="section-kicker">{t('YOUR WORKSPACE')}</span><strong>{t(info.label)}</strong></div>
    {mobile&&<button className="workspace-icon-button" aria-label={t('Close workspace navigation')} onClick={()=>dialog.current.close()}><Icon name="close"/></button>}
   </div>
   <nav aria-label={t('{value0} sidebar',{value0:t(info.label)})} className="workspace-sidebar-links">
    {[false,true].map(bottom=><div className={bottom?'workspace-sidebar-bottom':'workspace-sidebar-main'} key={String(bottom)}>
     {authorized&&workspaceMenu(role).filter(item=>Boolean(item.bottom)===bottom).map(item=><Link key={item.label} to={item.path} className={menuActive(item,location.pathname,location.search)?'workspace-sidebar-link active':'workspace-sidebar-link'} aria-current={menuActive(item,location.pathname,location.search)?'page':undefined}><Icon name={item.icon} size={20}/><span>{t(item.label)}</span></Link>)}
     {bottom&&role!=='OWNER'&&<Link className={'workspace-sidebar-link'+(location.pathname.startsWith(info.prefix+'/personal/')?' active':'')} aria-current={location.pathname.startsWith(info.prefix+'/personal/')?'page':undefined} to={personalHirePath(role)}><Icon name="home" size={20}/><span>{t('Travel & Booking')}</span></Link>}
     {bottom&&role!=='OWNER'&&<button className="workspace-sidebar-link" disabled={busy} onClick={signOut}><Icon name="exit" size={20}/><span>{busy?t('Signing out...'):t('Logout')}</span></button>}
     {bottom&&role!=='OWNER'&&mobile&&<ErrorNotice error={logoutError}/>}</div>)}
   </nav>
  </>
 }
 const updateProfile=user=>setAccess(current=>({...current,user}))
 const value={role,updateProfile,user:access.user,roles:access.roles,allowed,refreshAccess,openSidebar,sidebarTrigger:trigger,signOut,busy}
 const notificationPath=role==='ADMIN'?'/admin/manual-fulfilment':role==='OWNER'?'/owner/bookings':role==='DRIVER'?'/driver/assignments':'/bookings'
 const notificationLabel=role==='ADMIN'?'View support notifications':role==='OWNER'?'View customer bookings':role==='DRIVER'?'View assigned trips':'View my trips'
 return <WorkspaceContext.Provider value={value}>
  <div className="workspace-shell" data-workspace={role.toLowerCase()} style={{'--workspace-nav-count':workspaceMenu(role).length+(role==='OWNER'?0:2)}} ref={shell}>
   <div className="workspace-topbar" ref={header}>
    <Header dashboard workspaceHeader>
     {authorized? <>
      <span className="workspace-reels" aria-label={t('Travel Reels unavailable')}><Icon name="video" size={22}/><span>{t('Travel Reels')}</span></span>
      <Link className="admin-notifications" to={notificationPath} aria-label={t(notificationLabel)}><Icon name="bell" size={25}/></Link>
      {role==='ADMIN'?<Link className="workspace-profile admin-profile-link" to={accountPath(role)} aria-label={t('{name}, Super Admin profile',{name:access.user.full_name})}><DashboardAvatar name={access.user.full_name} url={access.user.profile_image_url}/><span className="workspace-profile-name"><strong>{access.user.full_name}</strong><small>{t('Super Admin')}</small></span></Link>:<details className="dashboard-profile-menu workspace-profile" ref={account} onKeyDown={event=>{if(event.key==='Escape'){account.current.open=false;account.current.querySelector('summary').focus()}}}><summary aria-label={t('{value0}, {value1} workspace',{value0:access.user.display_name||access.user.full_name,value1:t(info.label)})}><DashboardAvatar name={access.user.display_name||access.user.full_name} url={access.user.profile_image_url}/><span className="workspace-profile-name"><strong>{access.user.display_name||access.user.full_name}</strong><small>{t(info.label)}</small></span><Icon name="chevron" size={17}/></summary><div className="dashboard-profile-dropdown"><Link to={accountPath(role)}><Icon name="user" size={18}/>{t(' Your profile')}</Link><Link to={workspaceRoles[role].prefix+'/settings'}><Icon name="settings" size={18}/>{t(' Account settings')}</Link><button className="inline-link" disabled={busy} onClick={signOut}>{t('Sign out')}</button></div></details>}
      {role!=='ADMIN'&&<button className="button outline dashboard-signout" disabled={busy} onClick={signOut}><Icon name="exit" size={18}/>{t(' Sign out')}</button>}
     </>:<Link to="/">{t('Travel & booking')}</Link>}
    </Header>
   </div>
   <div className="workspace-layout">
    <aside className="workspace-sidebar"><Sidebar/></aside>
    <div className="workspace-content"><ErrorNotice error={logoutError}/>{access.loading?<main id="main" className="workspace-state" role="status"><span className="spinner"/>{t(' Loading your ')}{t(info.label)}{t(' workspace...')}</main>:access.error?<main id="main" className="workspace-state"><h1>{t('Workspace unavailable')}</h1><ErrorNotice error={access.error}/><button className="button" onClick={refreshAccess}>{t('Try again')}</button></main>:!authorized?<main id="main" className="workspace-state"><Icon name="shield" size={36}/><h1>{t('Workspace access denied')}</h1><p>{t('A current approved ')}{t(info.label)}{t(' membership is required. Navigation does not grant access.')}</p><Link className="button" to="/">{t('Return to booking home')}</Link></main>:<Outlet key={role+access.user.id}/>}</div>
   </div>
   <dialog id="workspace-navigation-drawer" ref={dialog} className="workspace-drawer" aria-label={t('{value0} navigation drawer',{value0:t(info.label)})} onClick={event=>{if(event.target===dialog.current)dialog.current.close()}} onClose={()=>trigger.current?.focus()}><div className="workspace-drawer-panel"><Sidebar mobile/></div></dialog>
  </div>
 </WorkspaceContext.Provider>
}
