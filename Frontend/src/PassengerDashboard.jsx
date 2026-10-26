import React, { useCallback, useEffect, useRef, useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { api, clearSession, hasSession, logout } from './api'
import { Asset, ButtonLink, ErrorNotice, Footer, Header, Icon, useNotice } from './components'
import RoleApplicationCard from './RoleApplicationCard'

const services = [
  { title: 'Hire a vehicle', image: 'service-icon-vehicle-hire.png', copy: 'Find your kind of ride, from everyday trips to family getaways.', to: '/#rides', action: 'Explore vehicles' },
  { title: 'Book tickets', image: 'service-icon-tickets.png', copy: 'More places to go. More ways to share the journey.', to: '/#services', action: 'Explore services' },
  { title: 'Rentals', image: 'service-icon-rentals.png', copy: 'Discover a little more freedom for your next adventure.', to: '/#services', action: 'Explore rentals' },
]

const destinations = [
  { image: 'destination-coast-passenger.png', title: 'Follow the coast', copy: 'Sea breezes, heritage streets and unhurried days.' },
  { image: 'destination-hills-passenger.png', title: 'Head for the hills', copy: 'Tea country, winding roads and a change of pace.' },
  { image: 'destination-city-passenger.png', title: 'See a different side', copy: 'City discoveries and local journeys worth making.' },
]

function workspaceUnavailable(code, notice) {
  notice({ title: `${code === 'OWNER' ? 'Owner' : 'Driver'} workspace`, message: 'Your role is approved. This workspace is not available yet. Documents and operational eligibility will be checked separately when it becomes available.' })
}

function DashboardNavigation({ user, roles, signOut, busy, notice }) {
  const menu = useRef(null)
  const approved = roles.filter(role => ['OWNER', 'DRIVER'].includes(role.role_code) && role.approval_status === 'APPROVED' && user.approved_roles.includes(role.role_code))
  return <>
    <Link to="/dashboard" aria-current="page">Overview</Link>
    <a href="#journeys">My journeys</a>
    <a href="#explore">Explore Sri Lanka</a>
    {user.approved_roles.includes('ADMIN') && <Link to="/admin/applications">Application review</Link>}
    <details className="dashboard-profile-menu" ref={menu} onKeyDown={event => {
      if (event.key === 'Escape') { menu.current.open = false; menu.current.querySelector('summary').focus() }
    }}>
      <summary><span className="dashboard-avatar">{Array.from(user.display_name || user.full_name)[0]}</span><span><strong>{user.display_name || user.full_name}</strong><small>Passenger workspace</small></span><Icon name="chevron" size={17}/></summary>
      <div className="dashboard-profile-dropdown">
        <p>Your workspace</p>
        <Link to="/dashboard" aria-current="page" onClick={() => { menu.current.open = false }}><Icon name="check" size={18}/> Passenger <small>Default</small></Link>
        {approved.map(role => <button key={role.role_code} type="button" onClick={() => { menu.current.open = false; workspaceUnavailable(role.role_code, notice) }}>{role.role_code === 'OWNER' ? 'Owner' : 'Driver'}<small>Workspace coming soon</small></button>)}
        <Link to="/account"><Icon name="user" size={18}/> Your profile</Link>
      </div>
    </details>
    <button className="button outline dashboard-signout" onClick={signOut} disabled={busy}><Icon name="exit" size={18}/> Sign out</button>
  </>
}

export default function PassengerDashboard() {
  const navigate = useNavigate()
  const { hash } = useLocation()
  const notice = useNotice()
  const request = useRef(0)
  const action = useRef(false)
  const [account, setAccount] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const [confirmation, setConfirmation] = useState('')
  const [applicationError, setApplicationError] = useState(null)

  const loadAccount = useCallback(async () => {
    const version = ++request.current
    setLoading(true); setAccount(null); setError(null)
    try {
      const [user, result] = await Promise.all([api('/users/me'), api('/users/me/roles')])
      if (version !== request.current || !hasSession()) return
      const passenger = result.items.some(role => role.role_code === 'PASSENGER' && role.approval_status === 'APPROVED')
      if (!['PENDING_VERIFICATION', 'ACTIVE'].includes(user.account_status) || !passenger || !user.approved_roles.includes('PASSENGER')) {
        throw new Error('Your Passenger workspace is unavailable. Please contact Travelly support.')
      }
      setAccount({ user, roles: result.items })
    } catch (err) {
      if (version !== request.current) return
      if (err.status === 401 || !hasSession()) { clearSession(); navigate('/login', { replace: true }) }
      else setError(err)
    } finally { if (version === request.current) setLoading(false) }
  }, [navigate])

  useEffect(() => {
    document.title = 'Your Passenger dashboard | Travelly'
    if (hasSession()) loadAccount()
    return () => { request.current += 1 }
  }, [loadAccount])

  useEffect(() => {
    if (account && ['#owner-application', '#driver-application'].includes(hash)) {
      document.getElementById(hash.slice(1))?.scrollIntoView({ block: 'start' })
    }
    setApplicationError(null)
  }, [account, hash])

  async function apply(code) {
    if (action.current) return
    action.current = true; setBusy(true); setApplicationError(null); setConfirmation('')
    const version = request.current
    try {
      await api('/users/me/role-requests', { method: 'POST', body: JSON.stringify({ role_code: code }) })
      await loadAccount()
      if (version + 1 === request.current && hasSession()) setConfirmation(`${code === 'OWNER' ? 'Owner' : 'Driver'} application submitted. Approval is pending. Passenger remains your default workspace.`)
    } catch (err) {
      if (version !== request.current) return
      if (err.status === 401 || err.status === 403 || !hasSession()) await loadAccount()
      else if (err.status === 409) { await loadAccount(); setConfirmation('Your latest application status has been refreshed.') }
      else setApplicationError({ code, error: err })
    } finally { action.current = false; setBusy(false) }
  }

  async function signOut() {
    if (action.current) return
    action.current = true; setBusy(true); setError(null)
    try {
      await logout()
      request.current += 1; setAccount(null)
      navigate('/login', { replace: true })
    } catch (err) {
      if (!hasSession()) { setAccount(null); navigate('/login', { replace: true }) }
      else setError(err)
    } finally { action.current = false; setBusy(false) }
  }

  if (!hasSession()) return <Navigate to="/login" replace/>
  const user = account?.user
  const hasVerifiedContact = Boolean(user?.email_verified_at || user?.phone_verified_at)
  const outstandingContacts = user ? [user.email && !user.email_verified_at && 'email', user.phone_e164 && !user.phone_verified_at && 'mobile number'].filter(Boolean) : []

  return <div className="dashboard-page passenger-page">
    <Header dashboard>
      {user ? <DashboardNavigation user={user} roles={account.roles} signOut={signOut} busy={busy} notice={notice}/> : <><Link to="/">Home</Link><button className="button outline" onClick={signOut} disabled={busy}>Sign out</button></>}
    </Header>
    <main className="dashboard-main" id="main">
      <ErrorNotice error={error}/>
      {loading ? <div className="dashboard-loading" role="status"><span className="spinner"/> Preparing your Passenger workspace…</div> : !user ? <section className="dashboard-access-state"><Icon name="shield" size={42}/><h1>Your workspace couldn’t be loaded</h1><p>Your information stays private. Please try again or sign out.</p><button className="button" onClick={loadAccount}>Try again</button></section> : <>
        <section className="dashboard-welcome" aria-labelledby="dashboard-greeting">
          <div className="dashboard-welcome-copy"><span className="dashboard-kicker"><Icon name="user" size={16}/> YOUR PASSENGER WORKSPACE</span><h1 id="dashboard-greeting">Hello, {user.display_name || user.full_name}.</h1><p>Your journey, your way.<br/>Where will you go next?</p><ButtonLink to="/#rides" arrow>Explore your next journey</ButtonLink></div>
          <Asset file="White Toyota Hiace by the lake.png" alt="A car, bus, van and three-wheeler beside a Sri Lankan lake" immediate className="dashboard-welcome-image"/>
        </section>

        {outstandingContacts.length > 0 && <aside className="dashboard-verification"><span className="dashboard-reminder-icon"><Icon name="shield" size={27}/></span><div><h2>{hasVerifiedContact ? 'One more contact to verify' : 'A small step before your next booking'}</h2><p>{hasVerifiedContact ? `Your booking contact requirement is met. Your ${outstandingContacts.join(' and ')} is still unverified.` : 'Your Passenger membership is active. Verify an email address or mobile number before booking.'} Verify your email from your profile. Phone verification is not available yet.</p></div><Link to="/account" className="inline-link">View your profile<Icon name="arrow" size={17}/></Link></aside>}

        <section className="dashboard-section" aria-labelledby="dashboard-actions"><div className="dashboard-section-heading"><div><span className="dashboard-kicker">EVERY WAY TO TRAVEL</span><h2 id="dashboard-actions">What are you planning?</h2></div><span className="dashboard-muted">Three services. One Travelly.</span></div><div className="dashboard-actions">{services.map(service => <Link className="dashboard-action service-card" to={service.to} key={service.title}><Asset file={service.image} alt=""/><div><h3>{service.title}</h3><p>{service.copy}</p><span className="dashboard-action-link">{service.action}<Icon name="arrow" size={18}/></span></div></Link>)}</div><p className="dashboard-service-note">Discover your options today. Booking services are not available yet.</p></section>

        <div className="dashboard-journeys" id="journeys">
          <section className="dashboard-journey-panel" aria-labelledby="next-journey"><div className="dashboard-panel-heading"><Icon name="pin" size={22}/><h2 id="next-journey">Your next journey</h2></div><div className="dashboard-empty"><span className="dashboard-empty-icon"><Icon name="car" size={42}/></span><h3>A new journey starts with a little inspiration.</h3><p>Your next journey will appear here when journey services become available. In the meantime, find your kind of ride.</p><ButtonLink to="/#rides" arrow>Explore vehicles</ButtonLink></div></section>
          <section className="dashboard-journey-panel" aria-labelledby="upcoming-bookings"><div className="dashboard-panel-heading"><Icon name="calendar" size={22}/><h2 id="upcoming-bookings">Upcoming bookings</h2></div><div className="dashboard-empty"><span className="dashboard-empty-icon dashboard-ticket-icon"><Icon name="ticket" size={39}/></span><h3>Something to look forward to.</h3><p>Booking information is not available yet. Your real upcoming bookings will live here once booking services are ready.</p><ButtonLink to="/#services" outline arrow>See travel options</ButtonLink></div></section>
        </div>

        <section className="dashboard-section dashboard-explore" id="explore" aria-labelledby="explore-heading"><div className="dashboard-section-heading"><div><span className="dashboard-kicker">A LITTLE CLOSER TO SOMEWHERE NEW</span><h2 id="explore-heading">Explore Sri Lanka</h2><p>From coastal escapes to hill-country hideaways.</p></div><Link to="/#rides" className="section-link">Find inspiration<Icon name="arrow" size={19}/></Link></div><div className="dashboard-destinations">{destinations.map(destination => <Link className="dashboard-destination destination-card" to="/#rides" key={destination.title}><Asset file={destination.image} alt={destination.title}/><div><h3>{destination.title}<Icon name="arrow" size={19}/></h3><p>{destination.copy}</p></div></Link>)}</div></section>

        <section className="dashboard-section dashboard-applications" aria-labelledby="applications-heading"><div className="dashboard-section-heading"><div><span className="dashboard-kicker">ONE ACCOUNT. MORE POSSIBILITIES.</span><h2 id="applications-heading">Go further with Travelly</h2><p>Owner and Driver applications are reviewed separately. Passenger stays your default.</p></div><button type="button" className="inline-link dashboard-refresh" onClick={() => { setConfirmation(''); loadAccount() }} disabled={busy}><Icon name="shield" size={18}/> Refresh role status</button></div>{confirmation && <p className="notice success" role="status">{confirmation}</p>}<div className="dashboard-application-grid">{['OWNER', 'DRIVER'].map(code => <RoleApplicationCard key={code} code={code} role={account.roles.find(role => role.role_code === code)} user={user} busy={busy} apply={apply} expanded={hash === `#${code.toLowerCase()}-application`} error={applicationError?.code === code ? applicationError.error : null} workspace={() => workspaceUnavailable(code, notice)}/>)}</div><p className="dashboard-service-note">Submit private evidence from your profile. Admin reviews documents and each role independently.</p></section>
      </>}
    </main>
    <Footer/>
  </div>
}
