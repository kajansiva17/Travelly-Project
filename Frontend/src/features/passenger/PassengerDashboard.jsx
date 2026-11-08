import { t, getLanguage } from '../../i18n/language.js'
import React,{useEffect} from 'react'
import {Link} from 'react-router-dom'
import {ErrorNotice,Icon} from '../../components/components'
import {TravellyHelp,UnavailableFeature} from '../../components/ReferenceWidgets'
import {SearchPanel} from '../../pages/PublicPages'
import {useWorkspace} from '../../context/workspaceContext'
import ApplicationStatusNotices from '../../components/ApplicationStatusNotices'
import {displayTime,loadBookings,pendingBooking,tripRoute,useWorkspaceData,words} from '../../hooks/workspaceData'

export default function PassengerDashboard(){
 const {user}=useWorkspace(),trips=useWorkspaceData(()=>loadBookings(user.id,'PASSENGER'),[user.id])
 const next=(trips.data||[]).filter(pendingBooking).sort((a,b)=>new Date(a.start_at)-new Date(b.start_at))[0]
 const first=(user.display_name||user.full_name).trim().split(/\s+/)[0]
 useEffect(()=>{document.title=t('Your journeys | Travelly')},[getLanguage()])
 return <main id="main" className="passenger-dashboard public-page reference-passenger">
  <section className="passenger-welcome" aria-labelledby="passenger-title"><div className="passenger-welcome-copy"><h1 id="passenger-title">{t("Where will you go next, ")}{first}?</h1><p>{t("Sri Lanka’s rides, tickets and rentals — all in one place.")}</p></div></section>
  <div className="passenger-dashboard-content">
   <ApplicationStatusNotices all/>
   <SearchPanel groupLink="/hire" assurance/>
   {!(user.email_verified_at||user.phone_verified_at)&&<aside className="passenger-verification"><Icon name="shield"/><div><strong>{t("A small step before your next booking")}</strong><p>{t("Verify your email from your profile before making a booking.")}</p></div><Link to="/account">{t("Verify contact")}<Icon name="arrow" size={16}/></Link></aside>}
   <div className="reference-passenger-grid">
    <section className="workspace-card next-journey"><div className="workspace-card-heading"><h2><Icon name="calendar"/>{t("Your next trip")}</h2><Link to="/bookings">{t("View all trips")}<Icon name="arrow" size={15}/></Link></div>
     {trips.loading?<p role="status">{t("Finding your journeys…")}</p>:trips.error?<><ErrorNotice error={trips.error}/><button className="button outline" onClick={trips.reload}>{t("Try again")}</button></>:next?<div className="reference-next-trip"><div className="reference-trip-image"><Icon name="car" size={48} aria-hidden="true"/><Link className="button outline" to={'/bookings/'+next.id}>{t("View booking")}<Icon name="arrow" size={14}/></Link></div><div><span className="workspace-badge positive">{t(words(next.status))}</span><h3>{tripRoute(next)}</h3><p>{displayTime(next.start_at)}{t(" · Sri Lanka time")}</p><span className="reference-trip-people"><Icon name="users" size={18}/>{next.passenger_count}{t(" passengers")}</span><Link className="button" to={'/bookings/'+next.id}>{t("View trip")}<Icon name="arrow" size={16}/></Link></div></div>:<UnavailableFeature icon="route" compact>{t("No upcoming trips in your latest records. Start with a place you’d love to go.")}</UnavailableFeature>}
     <p className="workspace-note">{next?.reference}{next?.reference && ' · '}{t("Live tracking is unavailable.")}</p>
    </section>
    <section className="workspace-card passenger-quick"><div className="workspace-card-heading"><h2><Icon name="spark"/>{t("Quickly pick up where you left off")}</h2></div><div className="workspace-quick-actions">{[['Book again','/hire','clock','Plan a new private hire'],['Manage bookings','/bookings','calendar','Review your own trips'],['My documents','/account#own-documents-heading','document','Your private evidence'],['My account','/account','user','Your profile and settings']].map(([title,to,icon,note])=><Link to={to} key={title}><span className="reference-orb"><Icon name={icon}/></span><span><strong>{t(title)}</strong><small>{t(note)}</small></span><Icon name="arrow" size={15}/></Link>)}</div></section>
    <section className="workspace-card passenger-reels-card"><div className="workspace-card-heading"><h2><Icon name="video"/>{t("Travel Reels")}</h2><a href="#destinations">{t("Explore")}<Icon name="arrow" size={14}/></a></div><UnavailableFeature icon="video" compact>{t("Travel Reels are not available yet.")}</UnavailableFeature><Link className="inline-link" to="/hire">{t("Search for a journey")}</Link></section>
    <section id="destinations" className="workspace-card passenger-inspiration"><div className="workspace-card-heading"><h2><Icon name="globe"/>{t("Smart journeys for you")}</h2><Link to="/hire">{t("See more destinations")}<Icon name="arrow" size={15}/></Link></div><UnavailableFeature icon="globe" compact>{t("Personalised destination suggestions are not available yet.")}</UnavailableFeature></section>
    <div className="passenger-side-panels"><section className="workspace-card passenger-payments"><div className="workspace-card-heading"><h2><Icon name="wallet"/>{t("Travel credits & payments")}</h2></div><UnavailableFeature icon="wallet" compact>{t("A wallet and saved payment methods are not available yet. No balance has been calculated.")}</UnavailableFeature></section><section className="workspace-card passenger-driver"><div className="workspace-card-heading"><h2><Icon name="user"/>{t("Your trip details")}</h2></div><p>{t("Driver contact, live location and arrival estimates are not supplied by the current trip API.")}</p>{next&&<Link className="inline-link" to={'/bookings/'+next.id}>{t("Review agreed trip details")}<Icon name="arrow" size={15}/></Link>}</section></div>
   </div><TravellyHelp/>
  </div>
 </main>
}
