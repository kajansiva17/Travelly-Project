import React, { useEffect, useId, useRef, useState, useSyncExternalStore } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { Brand, Icon, useNotice } from '../../components/components'
import { useNeedleEvents } from '../../components/NavbarBrand'
import { journeyLink } from '../auth/onboardingJourney'
import { hasSession } from '../../services/api'
import { getLanguage, languages, setLanguage, subscribeLanguage, t } from '../../i18n/language'
import { landingContent } from './landingContent'
import { heroArtwork, cardArtwork, artworkSources } from './landingAssets'
import './referenceLanding.css'
import './landingHero.css'
import './landingShared.css'

const brandAssets = '/images/travelly/branding/approved-2026-11-07/'
function LandingIcon({ name, size = 26, ...props }) {
  const paths = {
    car: <><path d="m5 9 2-6h10l2 6M4 9h16a2 2 0 0 1 2 2v7H2v-7a2 2 0 0 1 2-2ZM4 18v3m16-3v3M5 13h3m8 0h3"/></>,
    calendar: <><rect x="2" y="5" width="20" height="17" rx="2"/><path d="M7 2v6m10-6v6M2 11h20M7 15h.01m5 0h.01m5 0h.01M7 18h.01m5 0h.01m5 0h.01"/></>,
    steering: <><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/><path d="M3 8h18M9 12l-3 7m9-7 3 7M12 15v7"/></>,
    search: <><circle cx="10" cy="10" r="8"/><path d="m16 16 6 6"/></>,
    checkCircle: <><circle cx="12" cy="12" r="10"/><path d="m6 12 4 4 8-9"/></>,
    swap: <path d="M3 7h17l-4-4m5 14H4l4 4M20 7l-4 4M4 17l4-4"/>,
    road: <><path d="m7 2-6 20M17 2l6 20M12 2v3m0 3v4m0 4v6"/></>,
    luggage: <><rect x="3" y="6" width="18" height="15" rx="2"/><path d="M8 6V2h8v4M7 6v15M17 6v15"/></>,
    coins: <><ellipse cx="15" cy="5" rx="7" ry="3"/><path d="M8 5v4c0 4 14 4 14 0V5M22 9v4c0 3-7 4-11 2"/><ellipse cx="7" cy="15" rx="6" ry="3"/><path d="M1 15v5c0 4 12 4 12 0v-5"/></>,
    id: <><rect x="2" y="4" width="20" height="17" rx="2"/><circle cx="8" cy="10" r="2"/><path d="M4 18v-1a4 4 0 0 1 8 0v1m3-10h4m-4 4h4m-4 4h4"/></>,
    wrench: <path d="M14 3a6 6 0 0 0-6 8L1 18a3 3 0 0 0 5 4l8-9a6 6 0 0 0 7-8l-4 4-3-3 4-4Z"/>,
    layers: <><path d="m12 2 11 6-11 6L1 8ZM1 13l11 6 11-6M1 18l11 6 11-6"/></>,
    info: <><circle cx="12" cy="12" r="10"/><path d="M12 10v7m0-11h.01"/></>,
  }
  return paths[name] ? <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>{paths[name]}</svg> : <Icon name={name} size={size} {...props}/>
}

function Action({ to, children, className = '', onUnavailable, ...props }) {
  // go:/path opens a booking page; a signed-out visitor signs in first and comes back to it.
  if (to?.startsWith('go:')) { const target = to.slice(3), signedIn = hasSession(); return <Link to={signedIn ? target : '/login'} state={signedIn ? undefined : { returnTo: target }} className={className} {...props}>{children}</Link> }
  if (to?.startsWith('notice:')) return <button type="button" className={className} onClick={() => onUnavailable(to.slice(7))} {...props}>{children}</button>
  if (to?.startsWith('#')) return <a href={to} className={className} {...props}>{children}</a>
  return <Link to={to} className={className} {...props}>{children}</Link>
}

function LandingHeader({ role }) {
  const [open, setOpen] = useState(false)
  const headerRef = useRef(null)
  useNeedleEvents(headerRef)
  const lang = useSyncExternalStore(subscribeLanguage, getLanguage, () => 'en')
  useEffect(() => {
    const header = headerRef.current
    const page = header.closest('.lr-page')
    const measure = () => page.style.setProperty('--lr-header-bottom', `${header.offsetTop + header.offsetHeight}px`)
    measure()
    const observer = new ResizeObserver(measure)
    observer.observe(header)
    return () => observer.disconnect()
  }, [])
  return <header ref={headerRef} className="lr-header site-header app-navbar">
    <Brand/>
    <button className="lr-menu" type="button" aria-expanded={open} aria-controls="landing-navigation" aria-label={t('Navigation menu')} onClick={() => setOpen(!open)}><LandingIcon name={open ? 'close' : 'menu'}/></button>
    <nav id="landing-navigation" className={`lr-nav ${open ? 'lr-nav-open' : ''}`} aria-label={t('Main navigation')}>
      {[['/', 'home', 'Home'], ['/drive-with-us', 'steering', 'For Drivers'], ['/for-owners', 'car', 'For Owners']].map(([to, icon, label]) => <NavLink end to={to} key={to} onClick={() => setOpen(false)} className={({ isActive }) => `lr-nav-link ${isActive ? 'lr-active' : ''}`}>{['steering','car'].includes(icon) ? <span className={`lr-role-icon lr-role-icon-${icon}`} style={{ '--lr-role-icon': `url(${brandAssets}${icon === 'steering' ? 'drivers' : 'owners'}-icon.png)` }} aria-hidden="true"/> : <LandingIcon name={icon} size={20}/>}<span>{t(label)}</span></NavLink>)}
      <label className="lr-language"><LandingIcon name="globe" size={22}/><span className="lr-sr-only">{t('Language')}</span><select value={lang} onChange={event => setLanguage(event.target.value)} aria-label={t('Language')}>{languages.map(language => <option key={language.code} value={language.code}>{language.code === 'en' ? 'EN' : language.name}</option>)}</select></label>
      <Link className="lr-pill lr-login" to={journeyLink('/login', role.toUpperCase())}>{t('Log in')}</Link>
      <Link className="lr-pill lr-red lr-signup" to={journeyLink('/register', role.toUpperCase())}>{t('Sign up')}</Link>
    </nav>
  </header>
}

function JourneySearch({ unavailable }) {
  const [active, setActive] = useState(0)
  const [pickup, setPickup] = useState('')
  const [destination, setDestination] = useState('')
  const [departure, setDeparture] = useState('')
  const dateRef = useRef(null)
  const navigate = useNavigate()
  const earliestDeparture = new Date().toLocaleString('sv-SE', { timeZone: 'Asia/Colombo', hour12: false }).slice(0, 16).replace(' ', 'T')
  const tabs = [['Hire', 'car'], ['Tickets', 'ticket'], ['Rentals', 'car']]
  function search(event) {
    event.preventDefault()
    if (active) { const target = active === 1 ? '/travel/book/tickets' : '/travel/book/rental'; navigate(hasSession() ? target : '/login', hasSession() ? undefined : { state: { returnTo: target } }); return }
    if (!departure || !dateRef.current.checkValidity()) { requestAnimationFrame(() => { dateRef.current.focus(); dateRef.current.reportValidity() }); return }
    navigate('/hire', { state: { seed: { pickup, destination, departure } } })
  }
  return <section id="search" className="lr-search lr-glass" aria-label={t('Plan your journey')}>
    <div className="lr-tabs" role="tablist" aria-label={t('Travel service')}>{tabs.map(([label, icon], index) => <button key={label} type="button" role="tab" id={`lr-tab-${index}`} aria-selected={active === index} aria-controls="lr-search-fields" tabIndex={active === index ? 0 : -1} className={active === index ? 'lr-red' : ''} onClick={() => setActive(index)} onKeyDown={event => { if (['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) { event.preventDefault(); const next = event.key === 'Home' ? 0 : event.key === 'End' ? 2 : (index + (event.key === 'ArrowRight' ? 1 : 2)) % 3; setActive(next); event.currentTarget.parentElement.children[next].focus() } }}><LandingIcon name={icon}/><span>{t(label)}</span></button>)}</div>
    <form id="lr-search-fields" role="tabpanel" aria-labelledby={`lr-tab-${active}`} onSubmit={search}>
      <label className="lr-field"><span>{t('Pickup location')}</span><span className="lr-field-input"><LandingIcon name="pin" size={22}/><input name="pickup" value={pickup} onChange={event => setPickup(event.target.value)} placeholder={t('e.g. Jaffna')} maxLength={100} required={!active} autoComplete="off"/><button type="button" aria-label={t('Swap pickup and destination')} onClick={() => { setPickup(destination); setDestination(pickup) }}><LandingIcon name="swap" size={16}/></button></span></label>
      <label className="lr-field"><span>{t('Destination')}</span><span className="lr-field-input"><LandingIcon name="pin" size={22}/><input name="destination" value={destination} onChange={event => setDestination(event.target.value)} placeholder={t('e.g. Colombo')} maxLength={100} required={!active} autoComplete="off"/></span></label>
      <div className="lr-field lr-date"><span id="lr-date-label">{t('Journey date')}</span><div className="lr-date-trigger"><LandingIcon name="calendar" size={21}/><span id="lr-date-value" className={departure ? '' : 'lr-placeholder'}><span>{departure ? `${new Date(departure).toLocaleDateString(getLanguage() === 'en' ? 'en-GB' : `${getLanguage()}-LK`, { day: 'numeric', month: 'short', year: 'numeric' })} · ${departure.slice(11, 16)}` : t('Select date & time')}</span><LandingIcon name="chevron" size={18}/></span>
        <input ref={dateRef} className="lr-date-native" form="lr-date-selection" name="departure" type="datetime-local" min={earliestDeparture} required value={departure} aria-labelledby="lr-date-label lr-date-value" disabled={!!active}
          onClick={event => { try { event.currentTarget.showPicker?.() } catch { /* the native picker is optional */ } }}
          onChange={event => { setDeparture(event.target.value); const input = event.currentTarget; if (event.target.value) requestAnimationFrame(() => input.blur()) }}/></div></div>
      <button type="submit" className="lr-pill lr-red lr-search-submit"><LandingIcon name="search"/>{t('Search')}<LandingIcon name="arrow"/></button>
    </form>
  </section>
}

function Cards({ items, kind, unavailable }) {
  return <div className={`lr-cards lr-cards-${kind}`}>{items.map(([photo, icon, title, description, to]) => <Action key={title} to={to} onUnavailable={unavailable} className="lr-card lr-glass"><img className="lr-card-photo" {...artworkSources(cardArtwork[photo])} data-artwork={photo} sizes="(max-width: 760px) 90vw, (max-width: 1099px) 33vw, 440px" alt="" loading="lazy"/><div className="lr-card-body"><span className="lr-icon-well"><LandingIcon name={icon} size={31}/></span><div><h3>{t(title)}</h3>{description && <p>{t(description)}</p>}</div><LandingIcon name="chevron" size={24} className="lr-card-arrow"/></div></Action>)}</div>
}

function Steps({ data, role }) {
  return <section className="lr-steps-section"><h2>{t(data.stepsHeading)}</h2><div className={`lr-step-box ${role !== 'driver' ? 'lr-glass' : ''}`}><ol className="lr-steps">{data.steps.map(([icon, title, description], index) => <li key={title}><span className="lr-step-number">{String(index + 1).padStart(2, '0')}</span><LandingIcon name={icon} size={34}/><div><h3>{t(title)}</h3>{description && <p>{t(description)}</p>}</div>{index < data.steps.length - 1 && <LandingIcon name="arrow" className="lr-step-arrow" size={28}/>}</li>)}</ol>{data.info && <p className="lr-step-info"><LandingIcon name="info" size={19}/>{t(data.info)}</p>}</div></section>
}

function Features({ data, unavailable }) {
  return <section className="lr-features-section">{data.featureHeading && <h2>{t(data.featureHeading)}</h2>}<div className="lr-features lr-glass">{data.features.map(([icon, label, to]) => <Action key={label} to={to} onUnavailable={unavailable}><LandingIcon name={icon} size={31}/><span>{t(label)}</span></Action>)}</div></section>
}

function FaqItem({ question, answer }) {
  const [open, setOpen] = useState(true)
  const id = useId()
  return <article className={`lr-faq-item lr-glass ${open ? 'lr-faq-open' : ''}`}><span className="lr-faq-icon"><LandingIcon name="help" size={25}/></span><div><h3><button type="button" id={`${id}-q`} aria-expanded={open} aria-controls={`${id}-a`} onClick={() => setOpen(!open)} onKeyDown={event => { if (['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) { event.preventDefault(); const buttons = [...event.currentTarget.closest('.lr-faq-list').querySelectorAll('h3 button')]; const index = buttons.indexOf(event.currentTarget); buttons[event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1 : (index + (event.key === 'ArrowDown' ? 1 : buttons.length - 1)) % buttons.length].focus() } }}><span>{t(question)}</span><LandingIcon name="chevron" size={24}/></button></h3><div id={`${id}-a`} role="region" aria-labelledby={`${id}-q`} hidden={!open}><p>{t(answer)}</p></div></div></article>
}

function LandingPage({ role }) {
  const data = landingContent[role]
  const notice = useNotice()
  useSyncExternalStore(subscribeLanguage, getLanguage, () => 'en')
  useEffect(() => { document.title = `${t(data.title)} | Travelly` }, [data.title, getLanguage()])
  const register = journeyLink('/register', role.toUpperCase())
  const login = journeyLink('/login', role.toUpperCase())
  function unavailable(kind) {
    const messages = {
      'hire-type': 'Only Long-distance private hire is currently available. Other journey types are not available yet.',
      reels: 'Travel Reels are not available yet.',
      expenses: 'Trip expense recording is not available yet.',
      maintenance: 'Maintenance record keeping is not available yet. Existing vehicle details and documents remain available in your Owner workspace.',
      policy: 'This information has not been published yet.',
    }
    notice({ title: 'Travelly', message: messages[kind] || messages.policy })
  }
  return <div className={`lr-page lr-${role}`}>
    <LandingHeader role={role}/>
    <main id="main">
      <section className="lr-hero"><div className="lr-hero-art" aria-hidden="true"><img className="lr-hero-scene" {...artworkSources(heroArtwork[role])} sizes="100vw" alt="" fetchPriority="high"/></div><div className="lr-hero-copy"><h1>{role === 'owner' && getLanguage() === 'en' ? ['Your fleet.', 'More possibilities.'].map((line, index) => <React.Fragment key={line}>{index > 0 && ' '}<span className="lr-title-line">{line}</span></React.Fragment>) : t(data.title)}</h1><p className="lr-description">{t(data.description)}</p><div className="lr-hero-actions"><Action to={role === 'home' ? '#search' : register} className="lr-pill lr-red">{t(data.primary)}<LandingIcon name="arrow"/></Action><Link to={role === 'home' ? register : login} className="lr-pill lr-light"><LandingIcon name="user"/>{t(data.secondary)}</Link></div>{role === 'home' ? <p className="lr-hero-helper">{t('Already have an account?')} <Link to={login}>{t('Sign in')}</Link></p> : <p className="lr-hero-helper">{t(data.helper)}</p>}</div>{role === 'home' && <JourneySearch unavailable={unavailable}/>}</section>
      <div className="lr-content">
        <section className="lr-first-section"><h2>{t(data.firstHeading)}</h2><Cards items={data.firstCards} kind="first" unavailable={unavailable}/></section>
        <section className="lr-second-section"><h2>{t(data.secondHeading)}</h2><Cards items={data.secondCards} kind="second" unavailable={unavailable}/></section>
        {role === 'owner' && <Features data={data} unavailable={unavailable}/>}
        <Steps data={data} role={role}/>
        {role !== 'owner' && <Features data={data} unavailable={unavailable}/>}
        <section className="lr-faq" id="faq"><h2>{t(data.faqHeading)}</h2><div className="lr-faq-list">{data.faq.map(([question, answer]) => <FaqItem key={question} question={question} answer={answer}/>)}</div></section>
        <section className="lr-cta lr-glass"><h2>{t(data.cta)}</h2><div><Link className="lr-pill lr-red" to={register}><LandingIcon name={role === 'driver' ? 'steering' : role === 'owner' ? 'car' : 'users'}/>{t(data.ctaPrimary)}<LandingIcon name="arrow"/></Link><Link className="lr-pill lr-light" to={login}><LandingIcon name="user"/>{t(data.ctaSecondary)}</Link></div></section>
      </div>
    </main>
    <footer className="lr-footer"><div className="site-header lr-footer-brand"><Brand/></div><nav aria-label={t('Footer navigation')}>{['Help', 'Terms', 'Privacy', 'Contact'].map(label => <Action key={label} to={label === 'Help' ? '#faq' : 'notice:policy'} onUnavailable={unavailable}>{t(label)}</Action>)}</nav></footer>
  </div>
}

export function PassengerPage() { return <LandingPage role="home"/> }
export function DriverPage() { return <LandingPage role="driver"/> }
export function OwnerPage() { return <LandingPage role="owner"/> }
