import React, { createContext, useContext, useEffect, useRef, useState } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import NavbarBrand from './NavbarBrand'

export function Icon({ name, size = 22, ...props }) {
  const paths = {
    arrow: <path d="M4 12h15m-6-6 6 6-6 6" />,
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
    signal: <><circle cx="12" cy="12" r="2" /><path d="M7 7a7 7 0 0 0 0 10m10-10a7 7 0 0 1 0 10M3 3a13 13 0 0 0 0 18M21 3a13 13 0 0 1 0 18" /></>,
  }
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.65" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>{paths[name] || paths.arrow}</svg>
}

// Dimensions are the supplied PNG dimensions, not a cropped rendition.
const dimensions = {
  'Speedometer vehicle logo with deep red accents.png': [1536, 1024],
  'White Toyota Hiace by the lake.png': [1983, 793],
  'owner-hero-fleet.png': [802, 321], 'driver-hero.png': [526, 315],
  'vehicle-car-owner.png': [278,145], 'vehicle-van-owner.png': [278,145],
  'vehicle-bus-owner.png': [278,145], 'vehicle-three-wheeler-owner.png': [278,145],
  'vehicle-three-wheeler-passenger.png': [220,163],
  'driver-assigned-vehicle-trips.png': [255,142], 'driver-owner-support.png': [255,142],
  'driver-workspace-context.png': [255,142],
  'destination-coast-passenger.png': [297,160], 'destination-hills-passenger.png': [297,160],
  'destination-city-passenger.png': [297,160],
  'passenger-footer-scenery.png': [1020,133], 'owner-footer-scenery.png': [910,62],
  'service-icon-vehicle-hire.png': [71,71], 'service-icon-tickets.png': [71,71],
  'service-icon-rentals.png': [71,71],
  'auth/Screenshot 2026-10-25 011557.png': [516,418],
  'auth/Screenshot 2026-10-25 011752.png': [384,376],
  'auth/Quiet ivory canvas with peach curves.png': [1394,1128],
}

export function Asset({ file, alt = '', immediate = false, className = '', ...props }) {
  const [width, height] = dimensions[file] || []
  return <img src={`/images/${file}`} alt={alt} width={width} height={height} className={className}
    loading={immediate ? 'eager' : 'lazy'} fetchPriority={immediate ? 'high' : 'auto'} decoding="async" {...props}/>
}

export function Brand() {
  return <NavbarBrand/>
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
      {notice && <><button className="dialog-close" onClick={()=>dialog.current.close()} aria-label="Close dialog"><Icon name="close"/></button><h2 id="dialog-title">{notice.title}</h2><p>{notice.message}</p>{notice.content}<button className="button outline" onClick={()=>dialog.current.close()}>Close</button></>}
    </dialog>
  </NoticeContext.Provider>
}

export function Header({ auth = false, signup = false, dashboard = false, children }) {
  const { pathname, hash } = useLocation()
  const [open, setOpen] = useState(false)
  const notice = useNotice()
  useEffect(()=>setOpen(false),[pathname,hash])
  const owner = pathname === '/for-owners'
  const driver = pathname === '/drive-with-us'
  return <header className={`site-header ${auth ? 'auth-header' : ''}`}><div className="header-inner"><Brand/>
    <button className="menu-toggle" onClick={()=>setOpen(!open)} aria-label={open ? 'Close navigation' : 'Open navigation'} aria-expanded={open} aria-controls="site-navigation"><Icon name={open ? 'close' : 'menu'}/></button>
    <nav id="site-navigation" aria-label="Main navigation" className={open ? 'navigation open' : 'navigation'}>
      {dashboard ? children : <>{auth ? <><Link to="/" className="nav-icon"><Icon name="home"/> Back to home</Link><button className="text-button nav-icon" onClick={()=>notice({title:'Travelly help',message:'Use one Travelly account for Passenger, Owner and Driver membership. Create an account, then sign in to view your profile and role applications.'})}><Icon name="help"/> Help</button></> : <><NavLink to="/" end>Home</NavLink><Link to="/#rides">Vehicles</Link><Link to="/#services">Tickets</Link><NavLink to="/for-owners">For Owners</NavLink><NavLink to="/drive-with-us">Drive with us</NavLink></>}
      <span className="language"><Icon name="globe" size={19}/><span>EN</span></span>
      <span className="nav-divider"/>
      {auth ? <><span className="member-prompt">{signup ? 'Already a member?' : 'New to Travelly?'}</span><Link className="button nav-cta" to={signup ? '/login' : '/register'}>{signup ? 'Log in' : 'Create account'}</Link></> : <><Link className="login-link" to="/login">Log in</Link><Link className="button nav-cta" to={owner || driver ? '/register' : '/#search'}>{owner ? 'List your vehicle' : driver ? 'Drive with Travelly' : 'Find a ride'}</Link></>}</>}
    </nav>
  </div></header>
}

export function ButtonLink({ to = '/register', children, outline = false, arrow = false, className = '', ...props }) {
  return <Link to={to} className={`button ${outline ? 'outline' : ''} ${className}`} {...props}>{children}{arrow && <Icon name="arrow" size={20}/>}</Link>
}

export function SectionHeading({ title, subtitle, link, to = '/register', id }) {
  return <div className="section-heading" id={id}><div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>{link && <Link className="section-link" to={to}>{link}<Icon name="arrow"/></Link>}</div>
}

export function Footer() {
  return <footer className="site-footer"><Link to="/" className="footer-brand">Travelly</Link><span>Every ride. Every destination. One place.</span></footer>
}

export function ErrorNotice({ error }) {
  return error ? <div className="notice error" role="alert">{error.message}{error.retryAfter && <span> Try again in {error.retryAfter} seconds.</span>}</div> : null
}

export function ScrollToPage() {
  const {pathname,hash} = useLocation()
  useEffect(()=>{
    if(hash) requestAnimationFrame(()=>document.getElementById(hash.slice(1))?.scrollIntoView())
    else window.scrollTo(0,0)
  },[pathname,hash])
  return null
}
