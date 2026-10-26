import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Asset, ButtonLink, Footer, Header, Icon, SectionHeading, useNotice } from './components'

const vehicleData = [
  ['Car','vehicle-car-owner.png','City trips & everyday travel','City trips, airport transfers and everyday travel.'],
  ['Van','vehicle-van-owner.png','Family & group journeys','Group travel, family trips and custom journeys.'],
  ['Bus','vehicle-bus-owner.png','More seats, shared journeys','More seats, longer journeys and tour groups.'],
  ['Three-wheeler','vehicle-three-wheeler-owner.png','Quick local rides','Quick local trips and short-distance travel.'],
]

function Page({ title, children, className = '' }) {
  useEffect(()=>{document.title=`${title} | Travelly`},[title])
  return <div className={`public-page ${className}`}><Header/><main id="main">{children}</main><Footer/></div>
}

function VehicleCards({ owner = false }) {
  return <div className="vehicle-grid">{vehicleData.map(([title,file,passengerCopy,ownerCopy])=>
    <Link className="vehicle-card" to="/register" key={title}>
      <div className={`vehicle-picture ${!owner ? 'passenger-picture' : ''}`}><Asset file={!owner && title==='Three-wheeler' ? 'vehicle-three-wheeler-passenger.png' : file} alt={`${title} available through Travelly`}/></div>
      <div className="card-copy"><h3>{title}<Icon name="arrow"/></h3><p>{owner ? ownerCopy : passengerCopy}</p></div>
    </Link>)}</div>
}

function SearchPanel() {
  const [active,setActive]=useState('Hire a vehicle')
  const notice=useNotice()
  const today=new Date().toLocaleDateString('en-CA')
  function search(event) {
    event.preventDefault()
    const values=Object.fromEntries(new FormData(event.currentTarget))
    notice({title:'Your next journey',message:`${values.pickup} to ${values.destination} · ${values.date} · ${values.passengers}. Sign in to your Travelly account to continue.`,content:<ButtonLink to="/login" arrow>Sign in</ButtonLink>})
  }
  return <section className="search-panel" id="search" aria-label="Plan your journey">
    <div className="search-tabs" role="tablist" aria-label="Travel service">{[['Hire a vehicle','car'],['Book tickets','ticket'],['Rentals','key']].map(([name,icon])=><button type="button" key={name} id={`tab-${icon}`} role="tab" aria-selected={name===active} aria-controls="search-fields" tabIndex={name===active?0:-1} className={name===active?'selected':''} onClick={()=>setActive(name)} onKeyDown={event=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){event.preventDefault();const tabs=['Hire a vehicle','Book tickets','Rentals'];const index=event.key==='Home'?0:event.key==='End'?2:(tabs.indexOf(active)+(event.key==='ArrowRight'?1:2))%3;setActive(tabs[index]);event.currentTarget.parentElement.children[index].focus()}}}><Icon name={icon}/>{name}</button>)}</div>
    <form id="search-fields" role="tabpanel" aria-labelledby={`tab-${active==='Hire a vehicle'?'car':active==='Book tickets'?'ticket':'key'}`} onSubmit={search}>
      <label>{active==='Book tickets'?'From':'Pickup location'}<span className="search-input"><Icon name="pin"/><input name="pickup" placeholder="Where from?" required maxLength={100} autoComplete="off" list="travelly-places"/></span></label>
      <label>Destination<span className="search-input"><Icon name="pin"/><input name="destination" placeholder="Where to?" required maxLength={100} autoComplete="off" list="travelly-places"/></span></label>
      <label>{active==='Rentals'?'Rental date':'Travel date'}<span className="search-input"><input type="date" name="date" required min={today} aria-label={active==='Rentals'?'Rental date':'Travel date'}/></span></label>
      <label>Passengers<span className="search-input"><Icon name="users"/><select name="passengers" defaultValue="2 adults, 1 child"><option>1 adult</option><option>2 adults</option><option>2 adults, 1 child</option><option>3–6 passengers</option><option>7+ passengers</option></select></span></label>
      <button className="button search-submit" type="submit">{active==='Book tickets'?'Find tickets':active==='Rentals'?'Find a rental':'Find a ride'}<Icon name="arrow"/></button>
      <datalist id="travelly-places">{['Colombo','Kandy','Galle','Ella','Negombo','Jaffna','Anuradhapura','Sigiriya'].map(place=><option key={place} value={place}/>)}</datalist>
    </form>
    <div className="group-trip"><Icon name="users"/><span>Planning a group trip?</span><a href="#rides">Explore buses and vans<Icon name="arrow"/></a></div>
  </section>
}

function BenefitCards({ items, className = '' }) {
  return <div className={`benefit-grid ${className}`}>{items.map(([icon,title,copy])=><article className="benefit-card" key={title}><span className="benefit-icon"><Icon name={icon} size={38}/></span><div><h3>{title}</h3><p>{copy}</p></div></article>)}</div>
}

function Faq({ owner = false }) {
  const questions=owner ? [
    ['What documents do I need?','Complete your Owner setup with your vehicle details and the required ownership, registration and verification documents. Your vehicle must be verified before accepting trip requests.'],
    ['Can I assign an approved driver?','Yes. Drivers need their own approved Driver membership and the required current documents. Owner and Driver approvals are separate.'],
    ['Can I drive my vehicle myself?','Yes, after your Driver membership is approved independently of your Owner membership and your driving documents meet the journey requirements.'],
    ['When can I view payment details?','Your Owner workspace will show completed trip payment details and settlement information separately from passenger payment status.'],
  ] : [
    ['What documents do I need?','Complete Driver setup with your licence details and the required current documents. Travelly reviews your application before approving Driver membership.'],
    ['How do I receive a trip assignment?','After approval, you can receive assignments from vehicle owners. Review the vehicle, pickup, destination and trip details before accepting.'],
    ['Can I accept or decline a request?','Yes. Review each assignment and accept or decline it based on your availability and eligibility.'],
    ['When can I start a trip?','Start an accepted trip when the scheduled journey is ready and the required account, vehicle and document checks are satisfied.'],
  ]
  return <section className={`faq-section ${owner?'owner-faq':''}`} id="questions"><SectionHeading title={owner?'Questions from vehicle owners':'Questions from drivers.'} subtitle={owner?'Find quick answers to common questions about partnering with Travelly.':'Quick answers to help you get started.'}/><div className="faq-grid">{questions.map(([question,answer])=><details key={question}><summary>{question}<Icon name="chevron" size={19}/></summary><p>{answer}</p></details>)}</div></section>
}

function Steps({ driver = false }) {
  const items = [
    ['user','Create your Travelly account','Sign up once and start as a Passenger.'],
    ['document',`Complete ${driver?'Driver':'Owner'} setup`,driver?'Add licence details and required documents.':'Add vehicle details and submit the required documents.'],
    [driver?'check':'calendar',driver?'Get approved and receive assignments':'Get approved and accept trip requests',driver?'After verification, accept or decline assigned journeys.':'After verification, manage requests from your Owner Dashboard.'],
  ]
  return <section className={`steps-panel ${driver?'driver-steps':''}`} aria-label={`${driver?'Driver':'Owner'} application steps`}>
    {driver && <h2>Start driving with Travelly<br/>in three simple steps.</h2>}
    <ol>{items.map(([icon,title,copy],i)=><li key={title}><span className="step-number">{i+1}</span><Icon className="step-icon" name={icon} size={40}/><div><h3>{title}</h3><p>{copy}</p></div>{i<2 && <Icon className="step-next" name="chevron" size={23}/>}</li>)}</ol>
  </section>
}

export function PassengerPage() {
  return <Page title="Your journey, your way" className="passenger-page">
    <section className="hero passenger-hero">
      <picture className="passenger-hero-picture">
        <source media="(max-width: 767px)" srcSet="/images/passenger-mobile-hero.png" width="1024" height="1536"/>
        <Asset file="White Toyota Hiace by the lake.png" immediate className="passenger-hero-image" alt="Car, bus, van and three-wheeler beside a Sri Lankan mountain lake"/>
      </picture>
      <div className="hero-copy"><p className="eyebrow">YOUR JOURNEY, YOUR WAY.</p><h1>One place.<br/>Every way to travel.</h1><p className="hero-description">Vehicle hire, tickets and rentals,<br/>made simple.</p></div>
    </section>
    <div className="page-content passenger-content"><SearchPanel/>
      <section className="content-section" id="rides"><SectionHeading title="Find your kind of ride." subtitle="A vehicle for every plan." link="View all vehicles" to="/register"/><VehicleCards/></section>
      <section className="content-section" id="services"><SectionHeading title="What are you planning?" subtitle="Three services. One Travelly." link="Explore Travelly" to="/#search"/>
        <div className="service-grid">{[['service-icon-vehicle-hire.png','Vehicle hire','Cars, vans, buses and three-wheelers for your trip.','Explore vehicles','/#rides'],['service-icon-tickets.png','Tickets','Find your route and plan your next journey.','Explore tickets','/#search'],['service-icon-rentals.png','Rentals','Find a rental that fits your plans.','Browse rentals','/#search']].map(([file,title,copy,link,to])=><article className="service-card" key={title}><Asset file={file} alt=""/><div><h3>{title}</h3><p>{copy}</p><Link className="section-link" to={to}>{link}<Icon name="arrow"/></Link></div></article>)}</div>
      </section>
      <section className="content-section confidence-section"><SectionHeading title="Travel with more confidence." subtitle="A smoother, safer travel experience."/><BenefitCards className="confidence-grid" items={[
        ['shield','Verified vehicles','Quality vehicles from trusted partners.'],['document','Clear trip details','See key information before you book.'],['headset','Travelly Protected','Our team is here to support your journey.'],
      ]}/></section>
      <section className="content-section destinations"><SectionHeading title="Explore Sri Lanka your way." subtitle="Inspiring places, incredible journeys." link="Explore destinations" to="/#search"/>
        <div className="destination-grid">{[['coast','Beaches & heritage','Golden coasts and timeless history'],['hills','Hills & nature','Misty mountains and lush landscapes'],['city','City & local journeys','Vibrant cities and authentic experiences']].map(([file,title,copy])=><Link to="/#search" className="destination-card" key={file} aria-label={`${title}: ${copy}`}><Asset file={`destination-${file}-passenger.png`} alt={`${title}. ${copy}.`}/><span className="sr-only">Explore {title}</span></Link>)}</div>
      </section>
    </div>
    <section className="passenger-final"><Asset file="passenger-footer-scenery.png" alt="Where will Travelly take you next? From coastal escapes to mountain getaways, your next adventure is closer than you think."/><h2 className="sr-only">Where will Travelly take you next?</h2><Link to="/#search" className="banner-hit-area" aria-label="Start planning your journey"><span className="sr-only">Start planning</span></Link><ButtonLink to="/#search" arrow className="mobile-banner-action">Start planning</ButtonLink></section>
  </Page>
}

export function OwnerPage() {
  return <Page title="For vehicle owners" className="owner-page">
    <section className="hero owner-hero"><div className="owner-hero-art"><Asset file="owner-hero-fleet.png" immediate alt="A Travelly car, van, bus and three-wheeler by the lake"/></div><div className="hero-copy"><p className="eyebrow">YOUR VEHICLE. YOUR BUSINESS.</p><h1>Turn every vehicle<br/>into an opportunity.</h1><p className="hero-description">List your car, van, bus or three-wheeler,<br/>and start receiving trip requests.<br/>Manage your drivers, vehicles and trips<br/>all in one place.</p><div className="hero-actions"><ButtonLink arrow>List your vehicle</ButtonLink><ButtonLink to="/login" outline>Sign in</ButtonLink></div></div></section>
    <div className="page-content owner-content"><Steps/>
      <section className="content-section" id="rides"><SectionHeading title="List the vehicle you own." subtitle="Join a growing network of vehicle owners across Sri Lanka." link="List a vehicle"/><VehicleCards owner/></section>
      <section className="content-section" id="benefits"><SectionHeading title="Built for vehicle owners." subtitle="Everything you need to manage and grow your vehicle business." link="Learn more" to="/for-owners#questions"/><BenefitCards items={[
        ['document','Manage trip requests','View and respond to trip requests that match your availability.'],
        ['users','Drive yourself or assign a driver','Choose to drive your vehicle or assign a trusted driver from your team.'],
        ['wallet','Track active trips & completed payment details','Keep track of your upcoming trips and view completed payment details securely through Travelly.'],
      ]}/></section>
      <Faq owner/>
    </div>
    <section className="owner-final"><picture><source media="(max-width: 760px)" srcSet="/images/owner-hero-fleet.png" width="802" height="321"/><Asset file="owner-footer-scenery.png" alt="Sri Lanka’s coast and vehicles ready for new journeys"/></picture><div className="owner-final-copy"><div><h2>Ready to grow with Travelly?</h2><p>List your vehicle, connect with travellers and be part<br/>of Sri Lanka’s trusted travel marketplace.</p></div><ButtonLink arrow>Become a Travelly Owner</ButtonLink></div></section>
  </Page>
}

export function DriverPage() {
  return <Page title="Drive with Travelly" className="driver-page">
    <section className="hero driver-hero"><div className="driver-hero-art"><Asset file="driver-hero.png" immediate alt="A smiling Travelly driver at the wheel near Sigiriya"/></div><div className="hero-copy"><p className="eyebrow">MOVE PEOPLE. MOVE FORWARD.</p><h1>Drive journeys<br/>that matter.</h1><p className="hero-description">Join Travelly to receive assigned<br/>journeys, manage your availability<br/>and keep every trip moving safely.</p><div className="hero-actions"><ButtonLink arrow>Drive with Travelly</ButtonLink><ButtonLink to="/login" outline>Sign in</ButtonLink></div></div></section>
    <div className="page-content driver-content"><Steps driver/>
      <section className="content-section"><SectionHeading title="Drive the way that works for you." subtitle="Flexible opportunities. Clear tools. A smoother driving experience."/>
        <div className="story-grid">{[
          ['driver-assigned-vehicle-trips.png','car','Assigned vehicle trips','Receive trips assigned by vehicle owners and drive with clear trip details.'],
          ['driver-owner-support.png','users','Owner self-drive support','Support owners who rent vehicles for self-drive, with clear coordination through Travelly.'],
          ['driver-workspace-context.png','mobile','Your Driver workspace','Use the Travelly app to view assignments, start trips and update journey status.'],
        ].map(([file,icon,title,copy])=><Link className="story-card" to="/register" key={title}><Asset file={file} alt={title}/><div className="story-copy"><Icon name={icon}/><div><h3>{title}<Icon name="arrow" size={20}/></h3><p>{copy}</p></div></div></Link>)}</div>
      </section>
      <section className="content-section"><SectionHeading title="Built for every journey." subtitle="From quick city rides to long distance travel."/><div className="story-grid journey-grid">{[
        ['vehicle-car-owner.png','City rides','Airport transfers, city trips and everyday travel.'],
        ['vehicle-van-owner.png','Family & group journeys','Tours, group travel and special occasions.'],
        ['vehicle-bus-owner.png','Scheduled route trips','Long distance and inter-city travel.'],
      ].map(([file,title,copy])=><Link className="story-card" to="/register" key={title}><Asset file={file} alt={title}/><div className="card-copy"><h3>{title}<Icon name="arrow"/></h3><p>{copy}</p></div></Link>)}</div></section>
      <section className="content-section"><SectionHeading title="Everything a driver needs on the road." subtitle="Simple tools to keep every trip on track."/><BenefitCards items={[
        ['document','View assignments','See upcoming trips with pickup, drop-off and trip details in one place.'],
        ['pin','Start & complete trips','Use the app to start your trip and mark it complete when you arrive.'],
        ['signal','Share live trip progress','Keep owners and passengers informed with real-time journey updates.'],
      ]}/></section>
      <Faq/>
    </div>
    <section className="driver-final"><div><h2>Ready to drive with Travelly?</h2><p>Join a trusted travel marketplace and be part of<br/>smoother, safer journeys across Sri Lanka.</p><ButtonLink arrow>Start your Driver application</ButtonLink></div><Asset file="White Toyota Hiace by the lake.png" alt="Vehicles by a Sri Lankan lake, ready for your next journey"/></section>
  </Page>
}
