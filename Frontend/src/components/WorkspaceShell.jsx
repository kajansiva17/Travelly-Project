import { t } from '../i18n/language.js'
import {useCallback,useEffect,useRef,useState} from 'react'
import {Link,Navigate,Outlet,useLocation,useNavigate} from 'react-router-dom'
import {api,logout} from '../services/api'
import {Header,ErrorNotice,useSession} from './components'
import {NavbarBell,NavbarProfile,NavbarReels} from './AppNavbar'
import AppSidebar from './AppSidebar'
import {WorkspaceContext} from '../context/workspaceContext'
import {accountPath,eligibleWorkspaces,travelPath,requestedWorkspace,workspaceMenu,workspaceRoles} from '../routes/workspaceRoutes'
import {journeyLink} from '../features/auth/onboardingJourney'
import {StateCard} from '../features/booking/flow/FlowParts'
import {NOTIFICATION_POLL_MS} from '../features/notifications/unread.js'
import LiveLocationSender from '../features/live/LiveLocationSender'
import IncomingRides from '../features/live/IncomingRides'
import ChatHost from '../features/trips/ChatHost'
import NotificationPanel from '../features/notifications/NotificationPanel'
import {bellOpened} from '../features/trips/chatEvents'

export default function WorkspaceShell({role:fixedRole}){
 const location=useLocation(),navigate=useNavigate(),signedIn=useSession()
 const role=fixedRole||requestedWorkspace(location.search)
 const [access,setAccess]=useState({loading:true,user:null,roles:[],error:null})
 const [busy,setBusy]=useState(false),[logoutError,setLogoutError]=useState(null)
 const [unreadCount,setUnreadCount]=useState(0),[panelOpen,setPanelOpen]=useState(false)
 const stamp=useRef(0),dialog=useRef(null),trigger=useRef(null),header=useRef(null),shell=useRef(null)
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
 useEffect(()=>{dialog.current?.close()},[location.key])
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
 useEffect(()=>{
  if(!signedIn||!authorized||!access.user){setUnreadCount(0);return}
  let active=true
  const refresh=()=>api('/notifications/unread-count').then(result=>{if(active)setUnreadCount(Number(result.unread_count)||0)}).catch(()=>{})
  const visible=()=>{if(document.visibilityState==='visible')refresh()}
  refresh()
  const timer=window.setInterval(refresh,NOTIFICATION_POLL_MS)
  window.addEventListener('focus',refresh);document.addEventListener('visibilitychange',visible)
  return()=>{active=false;window.clearInterval(timer);window.removeEventListener('focus',refresh);document.removeEventListener('visibilitychange',visible)}
 },[signedIn,authorized,access.user?.id])
 async function signOut(){
  if(busy)return
  setBusy(true);setLogoutError(null)
  try{await logout();navigate('/login',{replace:true})}catch(error){setLogoutError(error)}finally{setBusy(false)}
 }
 function openSidebar(){dialog.current?.showModal()}
 function openNotifications(event){
  // The bell opens the list of notifications right here (it no longer leaves the page); a waiting chat message opens its chat instead.
  if(event&&event.preventDefault)event.preventDefault()
  const chatOpened=bellOpened()
  if(!chatOpened)setPanelOpen(open=>!open)
  setUnreadCount(0)
  api('/notifications/read-all',{method:'POST',body:'{}'}).catch(()=>api('/notifications/unread-count').then(result=>setUnreadCount(Number(result.unread_count)||0)).catch(()=>{}))
 }
 if(!signedIn)return <Navigate to={journeyLink('/login',role)} replace/>
 const sidebar=mobile=><AppSidebar role={role} info={info} authorized={authorized} pathname={location.pathname} search={location.search} mobile={mobile} busy={busy} onSignOut={signOut} logoutError={logoutError} onClose={()=>dialog.current?.close()}/>
 const updateProfile=user=>setAccess(current=>({...current,user}))
 const value={role,updateProfile,user:access.user,roles:access.roles,allowed,refreshAccess,openSidebar,sidebarTrigger:trigger,signOut,busy}
 const notificationPath=role==='ADMIN'?'/admin/manual-fulfilment':role==='OWNER'?'/owner/bookings':role==='DRIVER'?'/driver/assignments':'/bookings'
 const notificationLabel=role==='ADMIN'?'View support notifications':role==='OWNER'?'View customer bookings':role==='DRIVER'?'View assigned trips':'View my trips'
 return <WorkspaceContext.Provider value={value}>
  <div className="workspace-shell" data-workspace={role.toLowerCase()} style={{'--workspace-nav-count':workspaceMenu(role).length+(role==='OWNER'?0:2)+(role==='PASSENGER'?0:1)}} ref={shell}>
   <LiveLocationSender enabled={Boolean(access.user)&&authorized&&(allowed.includes('OWNER')||allowed.includes('DRIVER'))}/>
   <IncomingRides role={role}/>
   <ChatHost enabled={Boolean(access.user)&&authorized}/>
   {panelOpen&&<NotificationPanel role={role} seeAll={notificationPath} onClose={()=>setPanelOpen(false)}/>}
   <div className="workspace-topbar" ref={header}>
    <Header dashboard workspaceHeader>
     {authorized? <>
      <NavbarReels to={travelPath(role,'/reels')}/>
      <NavbarBell to={notificationPath} label={t(notificationLabel)} unreadCount={unreadCount} onOpen={openNotifications}/>
      <NavbarProfile user={access.user} roleLabel={t(info.label)} profileTo={accountPath(role)}/>
     </>:<Link to="/">{t('Travel & booking')}</Link>}
    </Header>
   </div>
   <div className="workspace-layout">
    <aside className="app-sidebar" aria-label={t('{value0} navigation',{value0:t(info.label)})}>{sidebar(false)}</aside>
    <div className="workspace-content"><ErrorNotice error={logoutError}/>{access.loading?<StateCard busy title={<>{t(' Loading your ')}{t(info.label)}{t(' workspace...')}</>}/>:access.error?<StateCard icon="alert" title={t('Workspace unavailable')} actions={<button type="button" className="ui-button ui-button-primary" onClick={refreshAccess}>{t('Try again')}</button>}><ErrorNotice error={access.error}/></StateCard>:!authorized?<StateCard title={t('Workspace access denied')} actions={<Link className="ui-button ui-button-primary" to="/">{t('Return to booking home')}</Link>}><p>{t('A current approved ')}{t(info.label)}{t(' membership is required. Navigation does not grant access.')}</p></StateCard>:<Outlet key={role+access.user.id}/>}</div>
   </div>
   <dialog id="workspace-navigation-drawer" ref={dialog} className="workspace-drawer" aria-label={t('{value0} navigation drawer',{value0:t(info.label)})} onClick={event=>{if(event.target===dialog.current)dialog.current.close()}} onClose={()=>trigger.current?.focus()}><div className="workspace-drawer-panel">{sidebar(true)}</div></dialog>
  </div>
 </WorkspaceContext.Provider>
}
