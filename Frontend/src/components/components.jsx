import { t } from '../i18n/language.js'
import LanguageSelector from './LanguageSelector'
import { createContext, useContext, useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { Link, useLocation } from 'react-router-dom'
import TravellyBrand, { useNeedleEvents } from './NavbarBrand'
import { hasSession, subscribeSession } from '../services/api'
import { useWorkspace } from '../context/workspaceContext'
import { LandingHeader } from '../features/landing/ReferenceLandingPages'

export const useSession = () => useSyncExternalStore(subscribeSession, hasSession, () => false)

export function Icon({ name, size = 22, ...props }) {
  const paths = {
    grid: <><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></>,
    settings: <><circle cx="12" cy="12" r="4"/><path d="m9 3 1-1h4l1 3 3 1 3 3-1 3 1 3-3 3-3 1-1 3h-4l-1-3-3-1-3-3 1-3-1-3 3-3 3-1Z"/></>,
    spark: <path d="m12 2 3 7 7 3-7 3-3 7-3-7-7-3 7-3Z"/>,
    video: <><rect x="2" y="4" width="20" height="16" rx="3"/><path d="m10 8 6 4-6 4Z"/></>,
    star: <path d="m12 2 3 6 7 1-5 5 1 8-6-4-6 4 1-8-5-5 7-1Z"/>,
    heart: <path d="M12 21S2 15 2 8a5 5 0 0 1 10-1 5 5 0 0 1 10 1c0 7-10 13-10 13Z"/>,
    seat: <><path d="M6 3v11h12v5H4V3ZM8 19v3m9-3v3M9 10h8v4"/><path d="M4 7h2"/></>,
    chart: <><path d="M3 21h19M5 17V9h3v8m3 0V3h3v14m3 0v-6h3v6"/></>,
    route: <><circle cx="5" cy="5" r="3"/><circle cx="19" cy="19" r="3"/><path d="M8 5h7a4 4 0 0 1 0 8H9a4 4 0 0 0 0 8h7"/></>,
    alert: <><path d="m12 2 11 20H1ZM12 8v6m0 4h.01"/></>,
    clock: <><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 3"/></>,
    arrow: <path d="M4 12h15m-6-6 6 6-6 6" />,
    search: <><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></>,
    plane: <path d="M21 3 3 10l7 3 3 7ZM10 13l11-10"/>,
    chevron: <path d="m7 10 5 5 5-5" />,
    mail: <><rect x="3" y="5" width="18" height="14" rx="2" /><path d="m4 7 8 6 8-6" /></>,
    lock: <><rect x="5" y="10" width="14" height="11" rx="2" /><path d="M8 10V7a4 4 0 0 1 8 0v3m-4 5v2" /></>,
    user: <><circle cx="12" cy="7" r="4" /><path d="M4 21v-2a8 8 0 0 1 16 0v2" /></>,
    users: <><circle cx="12" cy="7" r="3" /><circle cx="4" cy="10" r="2" /><circle cx="20" cy="10" r="2" /><path d="M6 22v-3a6 6 0 0 1 12 0v3M1 21v-3a4 4 0 0 1 4-4m18 7v-3a4 4 0 0 0-4-4" /></>,
    eye: <><path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z" /><circle cx="12" cy="12" r="3" /></>,
    eyeOff: <><path d="m3 3 18 18M9 5a13 13 0 0 1 13 7 17 17 0 0 1-4 5M6 6a17 17 0 0 0-4 6s4 7 10 7a13 13 0 0 0 5-1" /></>,
    check: <path d="m5 12 4 4L19 6" />,
    pin: <><path d="M19 10c0 6-7 11-7 11S5 16 5 10a7 7 0 0 1 14 0Z" /><circle cx="12" cy="10" r="2" /></>,
    phone: <path d="m7 3 3 5-3 3a15 15 0 0 0 6 6l3-3 5 3-2 4C10 23 1 14 3 5Z" />,
    mobile: <><rect x="6" y="2" width="12" height="20" rx="2" /><path d="M7 6h10M7 18h10" /></>,
    shield: <><path d="m12 2 8 4v6c0 5-8 10-8 10S4 17 4 12V6Z" /><path d="m8 12 3 3 5-6" /></>,
    exit: <path d="M9 4H4v16h5m4-12 4 4-4 4m-5-4h13" />,
    home: <><path d="m2 11 10-9 10 9M5 9v13h14V9M10 22v-8h4v8" /></>,
    help: <><circle cx="12" cy="12" r="10" /><path d="M9 8a3 3 0 1 1 5 2c-2 1-2 2-2 3m0 4h.01" /></>,
    globe: <><circle cx="12" cy="12" r="10" /><ellipse cx="12" cy="12" rx="4" ry="10" /><path d="M2 12h20M4 6h16M4 18h16" /></>,
    menu: <path d="M3 6h18M3 12h18M3 18h18" />,
    close: <path d="m6 6 12 12M6 18 18 6" />,
    car: <><path d="m4 10 2-6h12l2 6M3 10h18v9H3ZM5 19v3m14-3v3M3 14h3m12 0h3" /></>,
    ticket: <path d="m3 13 10-10 3 3a3 3 0 0 0 4 4l2 3-10 10-3-3a3 3 0 0 0-4-4Zm9-4 1 1m2 2 1 1" />,
    key: <><circle cx="16" cy="8" r="6" /><circle cx="16" cy="8" r="2" /><path d="m12 12-10 10v-5l3-1v-3l3-1" /></>,
    calendar: <><rect x="3" y="5" width="18" height="17" rx="2" /><path d="M7 2v6m10-6v6M3 11h18m-14 5 3 3 6-6" /></>,
    document: <><path d="M5 2h10l5 5v15H5ZM15 2v6h5M9 12h7m-7 4h7m-7 3h4" /></>,
    headset: <><path d="M3 14v-3a9 9 0 0 1 18 0v3m-1 5c0 3-5 3-8 3" /><rect x="2" y="11" width="5" height="9" rx="2" /><rect x="17" y="11" width="5" height="9" rx="2" /></>,
    wallet: <><path d="M20 7H4V3h14v4M3 7h18v15H3Z" /><path d="M21 12h-7v5h7m-5-2.5h.01" /></>,
    bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4M12 2V1"/></>,
    watch: <><circle cx="6" cy="16" r="4"/><circle cx="18" cy="16" r="4"/><path d="m2 15 2-10h4l2 10m4 0 2-10h4l2 10M8 8h8M10 12h4"/></>,
    signal: <><circle cx="12" cy="12" r="2" /><path d="M7 7a7 7 0 0 0 0 10m10-10a7 7 0 0 1 0 10M3 3a13 13 0 0 0 0 18M21 3a13 13 0 0 1 0 18" /></>,
    chat: <><path d="M4 4h16a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H9l-5 4v-4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Z"/><path d="M7 9h10M7 13h6"/></>,
    mic: <><rect x="8" y="2" width="8" height="13" rx="4"/><path d="M5 11a7 7 0 0 0 14 0M12 18v4M8 22h8"/></>,
    bookmark: <path d="M6 3h12v18l-6-4-6 4Z"/>,
    share: <><circle cx="18" cy="5" r="2.5"/><circle cx="6" cy="12" r="2.5"/><circle cx="18" cy="19" r="2.5"/><path d="m8.2 10.8 7.6-4.6M8.2 13.2l7.6 4.6"/></>,
    expand: <><path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/></>,
    shrink: <><path d="M9 4v5H4M15 4v5h5M9 20v-5H4M15 20v-5h5"/></>,
    more: <><circle cx="5" cy="12" r="1.4"/><circle cx="12" cy="12" r="1.4"/><circle cx="19" cy="12" r="1.4"/></>,
    volume: <><path d="M4 9v6h4l5 4V5L8 9Z"/><path d="M16 9a4 4 0 0 1 0 6M18.5 6.5a8 8 0 0 1 0 11"/></>,
    mute: <><path d="M4 9v6h4l5 4V5L8 9Z"/><path d="m17 9 5 6m0-6-5 6"/></>,
    play: <path d="m8 5 11 7-11 7Z"/>,
    pause: <><path d="M9 5v14M15 5v14"/></>,
    plus: <path d="M12 5v14M5 12h14"/>,
  }
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.65" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>{paths[name] || paths.arrow}</svg>
}

export function Brand() {
  return <TravellyBrand/>
}

const NoticeContext = createContext(null)
export const useNotice = () => useContext(NoticeContext)

export function NoticeProvider({ children }) {
  const { pathname } = useLocation()
  const [notice, setNotice] = useState(null)
  const dialog = useRef(null)
  useEffect(() => { if (notice && !dialog.current.open) dialog.current.showModal() }, [notice])
  useEffect(() => { dialog.current?.close(); setNotice(null) }, [pathname])
  return <NoticeContext.Provider value={setNotice}>{children}
    <dialog className="preview-dialog" ref={dialog} onClose={()=>setNotice(null)} onClick={event=>{if(event.target===dialog.current)dialog.current.close()}} aria-labelledby="dialog-title">
      {notice && <><button className="dialog-close" onClick={()=>dialog.current.close()} aria-label={t("Close dialog")}><Icon name="close"/></button><h2 id="dialog-title">{t(notice.title)}</h2><p>{t(notice.message)}</p>{notice.content}<button className="button outline" onClick={()=>dialog.current.close()}>{t("Close")}</button></>}
    </dialog>
  </NoticeContext.Provider>
}

export function Header({ auth = false, signup = false, dashboard = false, workspaceHeader = false, customerHeader = false, children }) {
  const { pathname, search, key: navigationKey } = useLocation()
  const signedIn = useSession()
  const [openAt, setOpenAt] = useState(null)
  const open = openAt === navigationKey
  const menuTrigger=useRef(null)
  useEffect(()=>{
    if(!open)return
    const dismiss=event=>{if(event.key==='Escape'){setOpenAt(null);menuTrigger.current?.focus()}}
    document.addEventListener('keydown',dismiss)
    return()=>document.removeEventListener('keydown',dismiss)
  },[open])
  const notice = useNotice()
  const workspace = useWorkspace()
  const navbarRef=useRef(null)
  useNeedleEvents(navbarRef)
  if(workspace && !workspaceHeader && !customerHeader)return null
  // One navbar outside the workspace too: the landing navbar (guests see Log in / Sign up, a signed-in person sees Dashboard).
  if(!auth && !dashboard && !workspaceHeader)return <div className="lr-page lr-bare"><LandingHeader role="home" signedIn={signedIn}/></div>
  return <header ref={navbarRef}
    className={`site-header app-navbar ${auth ? 'auth-header' : ''} ${workspaceHeader ? 'workspace-header' : ''}`}
  ><div className="header-inner">
    {workspaceHeader && <button ref={workspace.sidebarTrigger} className="workspace-menu-toggle" onClick={workspace.openSidebar} aria-label={t("Open workspace navigation")} aria-haspopup="dialog" aria-controls="workspace-navigation-drawer"><Icon name="menu"/></button>}
    <Brand/>
    {!workspaceHeader && <button ref={menuTrigger} className="menu-toggle" onClick={()=>setOpenAt(open ? null : navigationKey)} aria-label={open ? t('Close navigation') : t('Open navigation')} aria-expanded={open} aria-controls="site-navigation"><Icon name={open ? 'close' : 'menu'}/></button>}
    <nav id="site-navigation" aria-label={t("Main navigation")} className={open ? 'navigation open' : 'navigation'}>
      {dashboard ? <><LanguageSelector/>{children}</> : <><Link to="/" className="nav-icon"><Icon name="home"/>{t(" Back to home")}</Link><button className="text-button nav-icon" onClick={()=>notice({title:'Travelly help',message:'Use one Travelly account for Passenger, Owner and Driver membership. Create an account, then sign in to view your profile and role applications.'})}><Icon name="help"/>{t(" Help")}</button><LanguageSelector/></>}
    </nav>
  </div></header>
}

export function ButtonLink({ to, children, outline = false, arrow = false, className = '', ...props }) {
  const {pathname}=useLocation()
  const destination=to||(pathname==='/for-owners'?'/owner/onboarding':pathname==='/drive-with-us'?'/driver/onboarding':'/register')
  return <Link to={destination} className={`button ${outline ? 'outline' : ''} ${className}`} {...props}>{children}{arrow && <Icon name="arrow" size={20}/>}</Link>
}

export function ErrorNotice({ error }) {
  const [gone, setGone] = useState(false)
  useEffect(() => {
    setGone(false)
    if (!error) return undefined
    const timer = setTimeout(() => setGone(true), 6000)
    return () => clearTimeout(timer)
  }, [error])
  return error && !gone ? <div className="notice error" role="alert">{t(error.message)}{error.retryAfter && <span>{t(" Try again in ")}{error.retryAfter}{t(" seconds.")}</span>}</div> : null
}

export function ScrollToPage() {
  const {pathname,hash} = useLocation()
  useEffect(()=>{
    if(hash) requestAnimationFrame(()=>document.getElementById(hash.slice(1))?.scrollIntoView())
    else window.scrollTo(0,0)
  },[pathname,hash])
  return null
}
