import { t, getLanguage } from '../i18n/language.js'
import React, { useEffect, useId, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {TravellyAsset} from '../components/TravellyVisuals'
import { Asset, ButtonLink, Footer, Header, Icon, SectionHeading, useNotice } from '../components/components'

const vehicleData = [
  ['Car','vehicle-car-owner.png','City trips & everyday travel','City trips, airport transfers and everyday travel.'],
  ['Van','vehicle-van-owner.png','Family & group journeys','Group travel, family trips and custom journeys.'],
  ['Bus','vehicle-bus-owner.png','More seats, shared journeys','More seats, longer journeys and tour groups.'],
  ['Three-wheeler','vehicle-three-wheeler-owner.png','Quick local rides','Quick local trips and short-distance travel.'],
]

function Page({ title, children, className = '' }) {
  useEffect(()=>{document.title=`${t(title)} | Travelly`},[title,getLanguage()])
  return <div className={`public-page ${className}`}><Header/><main id="main">{children}</main><Footer/></div>
}

function VehicleCards({ owner = false }) {
  return <div className="vehicle-grid">{vehicleData.map(([title,file,passengerCopy,ownerCopy])=>
    <Link className="vehicle-card" to={owner ? '/owner/onboarding' : '/hire'} key={title}>
      <div className={`vehicle-picture ${!owner ? 'passenger-picture' : ''}`}><Asset file={!owner && title==='Three-wheeler' ? 'vehicle-three-wheeler-passenger.png' : file} alt={`${title} available through Travelly`}/></div>
      <div className="card-copy"><h3>{t(title)}<Icon name="arrow"/></h3><p>{owner ? t(ownerCopy) : t(passengerCopy)}</p></div>
    </Link>)}</div>
}

export function SearchPanel({groupLink='#rides',assurance=false}) {
  const navigate = useNavigate()
  const [active,setActive]=useState('Hire a vehicle')
  const notice=useNotice()
  const today=new Date().toLocaleDateString('en-CA',{timeZone:'Asia/Colombo'})
  function search(event) {
    event.preventDefault()
    const values=Object.fromEntries(new FormData(event.currentTarget))
    if (active === 'Hire a vehicle') { navigate('/hire', { state: { seed: { pickup: values.pickup, destination: values.destination, departure: values.date } } }); return }
    notice({title:'Your next journey',message:active==='Book tickets'?'Scheduled ticket search and checkout are not available yet. Private vehicle hire is available now.':'Rental checkout is not available yet. You can plan a private hire with a driver.',content:<ButtonLink to="/hire" arrow>{t("Plan a private hire")}</ButtonLink>})
  }
  return <section className="search-panel" id="search" aria-label={t("Plan your journey")}>
    <div className="search-tabs" role="tablist" aria-label={t("Travel service")}>{[['Hire a vehicle','car'],['Book tickets','ticket'],['Rentals','key']].map(([name,icon])=><button type="button" key={name} id={`tab-${icon}`} role="tab" aria-selected={name===active} aria-controls="search-fields" tabIndex={name===active?0:-1} className={name===active?'selected':''} onClick={()=>setActive(name)} onKeyDown={event=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){event.preventDefault();const tabs=['Hire a vehicle','Book tickets','Rentals'];const index=event.key==='Home'?0:event.key==='End'?2:(tabs.indexOf(active)+(event.key==='ArrowRight'?1:2))%3;setActive(tabs[index]);event.currentTarget.parentElement.children[index].focus()}}}><Icon name={icon}/>{t(name)}</button>)}</div>
    <form id="search-fields" role="tabpanel" aria-labelledby={`tab-${active==='Hire a vehicle'?'car':active==='Book tickets'?'ticket':'key'}`} onSubmit={search}>
      <label>{active==='Book tickets'?t('From'):t('Pickup location')}<span className="search-input"><Icon name="pin"/><input name="pickup" placeholder={t("Where from?")} required maxLength={100} autoComplete="off" list="travelly-places"/></span></label>
      <label>{t("Destination")}<span className="search-input"><Icon name="pin"/><input name="destination" placeholder={t("Where to?")} required maxLength={100} autoComplete="off" list="travelly-places"/></span></label>
      <label>{active==='Rentals'?t('Rental date'):t('Travel date')}<span className="search-input"><input type="datetime-local" name="date" required min={today+'T00:00'} aria-label={active==='Rentals'?t('Rental date'):t('Travel date')}/></span></label>
      <label>{t("Passengers")}<span className="search-input"><Icon name="users"/><select name="passengers" defaultValue="2 adults, 1 child"><option value={"1 adult"}>{t("1 adult")}</option><option value={"2 adults"}>{t("2 adults")}</option><option value={"2 adults, 1 child"}>{t("2 adults, 1 child")}</option><option value={"3–6 passengers"}>{t("3–6 passengers")}</option><option value={"7+ passengers"}>{t("7+ passengers")}</option></select></span></label>
      <button className="button search-submit" type="submit">{active==='Book tickets'?t('Find tickets'):active==='Rentals'?t('Find a rental'):t('Find a ride')}<Icon name="arrow"/></button>
      <datalist id="travelly-places">{['Colombo','Kandy','Galle','Ella','Negombo','Jaffna','Anuradhapura','Sigiriya'].map(place=><option key={place} value={place}/>)}</datalist>
    </form>
    {assurance?<div className="search-assurance">{[['shield','Eligibility checks'],['car','A range of vehicles'],['document','Agreed trip prices'],['check','Clear journey details']].map(([icon,label])=><span key={label}><Icon name={icon} size={20}/>{t(label)}</span>)}</div>:<div className="group-trip"><Icon name="users"/><span>{t("Planning a group trip?")}</span><Link to={groupLink}>{t("Explore buses and vans")}<Icon name="arrow"/></Link></div>}
  </section>
}

function BenefitCards({ items, className = '' }) {
  return <div className={`benefit-grid ${className}`}>{items.map(([icon,title,copy])=><article className="benefit-card" key={title}><span className="benefit-icon"><Icon name={icon} size={38}/></span><div><h3>{t(title)}</h3><p>{t(copy)}</p></div></article>)}</div>
}

function FaqCard({ question, answer }) {
  const [open, setOpen] = useState(false)
  const id = useId()
  return <article className="faq-card" data-open={open}>
    <h3 className="faq-question">
      <button type="button" id={`${id}-question`} aria-expanded={open} aria-controls={`${id}-answer`} onClick={() => setOpen(value => !value)}>
        <span>{t(question)}</span><Icon name="chevron" size={19}/>
      </button>
    </h3>
    <div className="faq-answer" id={`${id}-answer`} role="region" aria-labelledby={`${id}-question`} aria-hidden={!open} inert={!open}>
      <div className="faq-answer-inner"><p>{t(answer)}</p></div>
    </div>
  </article>
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
  return <section className={`faq-section ${owner?'owner-faq':''}`} id="questions"><SectionHeading title={owner?'Questions from vehicle owners':'Questions from drivers.'} subtitle={owner?'Find quick answers to common questions about partnering with Travelly.':'Quick answers to help you get started.'}/><div className="faq-grid">{questions.map(([question,answer])=><FaqCard key={question} question={question} answer={answer}/>)}</div></section>
}

function Steps({ driver = false }) {
  const items = [
    ['user','Create your Travelly account','Sign up once; your Passenger membership stays included.'],
    ['document',`Complete ${driver?'Driver':'Owner'} setup`,driver?'Add licence details and required documents.':'Add vehicle details and submit the required documents.'],
    [driver?'check':'calendar',driver?'Get approved and receive assignments':'Get approved and accept trip requests',driver?'After verification, accept or decline assigned journeys.':'After verification, manage requests from your Owner Dashboard.'],
  ]
  return <section className={`steps-panel ${driver?'driver-steps':''}`} aria-label={t("{value0} application steps", {value0: driver?'Driver':'Owner'})}>
    {driver && <h2>{t("Start driving with Travelly")}<br/>{t("in three simple steps.")}</h2>}
    <ol>{items.map(([icon,title,copy],i)=><li key={title}><span className="step-number">{i+1}</span><Icon className="step-icon" name={icon} size={40}/><div><h3>{t(title)}</h3><p>{t(copy)}</p></div>{i<2 && <Icon className="step-next" name="chevron" size={23}/>}</li>)}</ol>
  </section>
}

export function PassengerPage() {
  const notice = useNotice()
  function showJourneyGuide() {
    notice({
      title: 'How Travelly works',
      message: 'Plan a private hire in a few simple steps.',
      content: <ol className="home-journey-steps">
        <li>{t("Enter your pickup, destination and travel date to explore vehicles or request a quote.")}</li>
        <li>{t("Review your itinerary and agreed price before accepting.")}</li>
        <li>{t("Follow your booking status while the Owner and assigned Driver confirm the journey.")}</li>
      </ol>,
    })
  }
  return <Page title="Your journey, your way" className="passenger-page reference-landing">
    <section className="hero passenger-hero">
      <TravellyAsset name="heroes/passenger-hero.png" eager sizes="100vw" className="passenger-hero-image" alt={t("Illustrated Sri Lankan twilight landscape with a coach, van, car and tuk-tuk")}/>
      <div className="hero-copy"><h1>{t("One account.")}<br/><span>{t("Every way to travel.")}</span></h1><p className="hero-description">{t("Ride, ticket, rental. Travel Sri Lanka your way.")}</p>
        <div className="home-hero-actions">
          <ButtonLink to="/#search" className="home-journey-start" arrow>{t("Start your journey")}</ButtonLink>
          <button type="button" className="button outline home-journey-guide" onClick={showJourneyGuide}>
            <svg className="home-play-icon" viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><circle cx="12" cy="12" r="11" fill="currentColor" stroke="none"/><path d="m10 7 7 5-7 5Z" fill="#143763" stroke="none"/></svg>{t("See how it works")}</button>
        </div>
      </div>
    </section>
    <div className="page-content passenger-content"><SearchPanel/>
      <section className="content-section" id="services"><span id="rides"/><SectionHeading title="Your next journey starts here." subtitle="Choose the way you want to travel, all in one trusted account."/>
        <div className="service-grid">{[['service-hire','Vehicle hire','From cars to vans, find the right vehicle for your journey.','Explore vehicles','/hire'],['service-tickets','Tickets','Explore travel options and plan your next journey.','Explore tickets','/#search'],['service-rentals','Rentals','A vehicle for your plans, with a professional driver.','Browse rentals','/#search']].map(([file,title,copy,label,to])=><article className="service-card" key={title}><TravellyAsset name={'icons/'+file+'.png'}/><div><h3>{t(title)}</h3><p>{t(copy)}</p><Link className="section-link" to={to}>{t(label)}<Icon name="arrow"/></Link></div></article>)}</div>
      </section>
      <section className="content-section confidence-section"><h2 className="sr-only">{t("Travel with more confidence")}</h2><BenefitCards className="confidence-grid" items={[
        ['shield','Verified vehicles','Vehicle eligibility is checked before commitment.'],['document','Clear trip details','Review your itinerary and agreed price.'],['check','Travelly Protected','Account, document and trip checks at every step.'],['headset','Local support','One place for your journeys and account.']
      ]}/></section>
    </div>
  </Page>
}

export function OwnerPage() {
  return <Page title="For vehicle owners" className="owner-page">
    <section className="hero owner-hero"><div className="owner-hero-art"><img src="/images/travelly/heroes/owner-hero-1920.webp" alt={t("Vehicle owner beside Travelly vehicles on a scenic road")}/></div><div className="hero-copy"><p className="eyebrow">{t("YOUR VEHICLE. YOUR BUSINESS.")}</p><h1>{t("Turn every vehicle")}<br/><span>{t("into an opportunity.")}</span></h1><p className="hero-description">{t("List your car, van, bus or three-wheeler,")}<br/>{t("and start receiving trip requests.")}<br/>{t("Manage your drivers, vehicles and trips")}<br/>{t("all in one place.")}</p><div className="hero-actions"><ButtonLink arrow>{t("List your vehicle")}</ButtonLink><ButtonLink to="/login" outline>{t("Sign in")}</ButtonLink></div></div></section>
    <div className="page-content owner-content"><Steps/>
      <section className="content-section" id="rides"><SectionHeading title="List the vehicle you own." subtitle="Join a growing network of vehicle owners across Sri Lanka." link="List a vehicle"/><VehicleCards owner/></section>
      <section className="content-section" id="benefits"><SectionHeading title="Built for vehicle owners." subtitle="Everything you need to manage and grow your vehicle business." link="Learn more" to="/for-owners#questions"/><BenefitCards items={[
        ['document','Manage trip requests','View and respond to trip requests that match your availability.'],
        ['users','Drive yourself or assign a driver','Choose to drive your vehicle or assign a trusted driver from your team.'],
        ['wallet','Track active trips & completed payment details','Keep track of your upcoming trips and view completed payment details securely through Travelly.'],
      ]}/></section>
      <Faq owner/>
    </div>
    <section className="owner-final"><picture><source media="(max-width: 760px)" srcSet="/images/owner-hero-fleet.png" width="802" height="321"/><Asset file="owner-footer-scenery.png" alt={t("Sri Lanka\u2019s coast and vehicles ready for new journeys")}/></picture><div className="owner-final-copy"><div><h2>{t("Ready to grow with Travelly?")}</h2><p>{t("List your vehicle, connect with travellers and be part")}<br/>{t("of Sri Lanka’s trusted travel marketplace.")}</p></div><ButtonLink arrow>{t("Become a Travelly Owner")}</ButtonLink></div></section>
  </Page>
}

export function DriverPage() {
  return <Page title="Drive with Travelly" className="driver-page">
    <section className="hero driver-hero"><div className="driver-hero-art"><img src="/images/travelly/heroes/driver-hero-1920.webp" alt={t("Travelly driver with a van on a scenic road")}/></div><div className="hero-copy"><p className="eyebrow">{t("MOVE PEOPLE. MOVE FORWARD.")}</p><h1>{t("Drive journeys")}<br/><span>{t("that matter.")}</span></h1><p className="hero-description">{t("Join Travelly to receive assigned\njourneys, manage your availability\nand keep every trip moving safely.")}</p><div className="hero-actions"><ButtonLink arrow>{t("Drive with Travelly")}</ButtonLink><ButtonLink to="/login" outline>{t("Sign in")}</ButtonLink></div></div></section>
    <div className="page-content driver-content"><Steps driver/>
      <section className="content-section"><SectionHeading title="Drive the way that works for you." subtitle="Flexible opportunities. Clear tools. A smoother driving experience."/>
        <div className="story-grid">{[
          ['driver-assigned-vehicle-trips.png','car','Assigned vehicle trips','Receive trips assigned by vehicle owners and drive with clear trip details.'],
          ['driver-owner-support.png','users','Owner self-drive support','Support owners who rent vehicles for self-drive, with clear coordination through Travelly.'],
          ['driver-workspace-context.png','mobile','Your Driver workspace','Use the Travelly app to view assignments, start trips and update journey status.'],
        ].map(([file,icon,title,copy])=><Link className="story-card" to="/driver/onboarding" key={title}><Asset file={file} alt={title}/><div className="story-copy"><Icon name={icon}/><div><h3>{t(title)}<Icon name="arrow" size={20}/></h3><p>{t(copy)}</p></div></div></Link>)}</div>
      </section>
      <section className="content-section"><SectionHeading title="Built for every journey." subtitle="From quick city rides to long distance travel."/><div className="story-grid journey-grid">{[
        ['vehicle-car-owner.png','City rides','Airport transfers, city trips and everyday travel.'],
        ['vehicle-van-owner.png','Family & group journeys','Tours, group travel and special occasions.'],
        ['vehicle-bus-owner.png','Scheduled route trips','Long distance and inter-city travel.'],
      ].map(([file,title,copy])=><Link className="story-card" to="/driver/onboarding" key={title}><Asset file={file} alt={title}/><div className="card-copy"><h3>{t(title)}<Icon name="arrow"/></h3><p>{t(copy)}</p></div></Link>)}</div></section>
      <section className="content-section"><SectionHeading title="Everything a driver needs on the road." subtitle="Simple tools to keep every trip on track."/><BenefitCards items={[
        ['document','View assignments','See upcoming trips with pickup, drop-off and trip details in one place.'],
        ['pin','Start & complete trips','Use the app to start your trip and mark it complete when you arrive.'],
        ['signal','Share live trip progress','Keep owners and passengers informed with real-time journey updates.'],
      ]}/></section>
      <Faq/>
    </div>
    <section className="driver-final"><div><h2>{t("Ready to drive with Travelly?")}</h2><p>{t("Join a trusted travel marketplace and be part of")}<br/>{t("smoother, safer journeys across Sri Lanka.")}</p><ButtonLink arrow>{t("Start your Driver application")}</ButtonLink></div><Asset file="White Toyota Hiace by the lake.png" alt={t("Vehicles by a Sri Lankan lake, ready for your next journey")}/></section>
  </Page>
}
