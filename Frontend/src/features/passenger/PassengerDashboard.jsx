import { t } from '../../i18n/language.js'
import React from 'react'
import {Link} from 'react-router-dom'
import {Icon} from '../../components/components'
import {Chip} from '../../components/ui'
import {TravellyAiPanel} from '../../components/ReferenceWidgets'
import {DashPage,DashStat,Tile,Soft,DashList,DashLinks,useDashRows,bookingsNote} from '../../components/RoleDashboards'
import {useWorkspace} from '../../context/workspaceContext'
import {api} from '../../services/api'
import {ReplacementRow} from './ReplacementCard'
import {isExpired,isReplacementAction,isRoadAlertNotice,noticeBookingId} from '../notifications/notices'
import {displayTime,loadBookings,pendingBooking,tripRoute,useWorkspaceData,words} from '../../hooks/workspaceData'
import TripInProgressCard from '../trips/TripInProgressCard'
import {useActiveTrips} from '../trips/tripHooks'
import ReelsCard,{useReelsPreview} from '../social/ReelsCard'

// Passenger dashboard: the same grid, stat cards, tiles and Travelly AI card as the Owner and Driver dashboards.
const byStart=(a,b)=>new Date(a.start_at)-new Date(b.start_at)
export default function PassengerDashboard(){
 const {user,roles,allowed}=useWorkspace(),active=useActiveTrips(),reels=useReelsPreview(),trips=useWorkspaceData(()=>loadBookings(user.id,'PASSENGER'),[user.id]),notices=useWorkspaceData(()=>api('/notifications'),[])
 const first=(user.display_name||user.full_name).trim().split(/\s+/)[0],rows=useDashRows()
 const all=trips.data||[],upcoming=all.filter(pendingBooking).sort(byStart),next=upcoming[0]
 const recent=all.filter(b=>!pendingBooking(b)).sort((a,b)=>byStart(b,a))
 const notes=notices.data?.items||[],verified=Boolean(user.email_verified_at||user.phone_verified_at)
 const count=(r,fn)=>r.loading?'?':r.error?'Unavailable':fn(r.data)
 const applications=(roles||[]).filter(row=>['OWNER','DRIVER'].includes(row.role_code))
 return <DashPage title={t("Where will you go next, {name}?",{name:first})} subtitle={t("Sri Lanka’s rides, tickets and rentals — all in one place.")} hero={<TripInProgressCard items={active.items}/>}
  stats={<><DashStat icon="calendar" label="Upcoming trips" value={count(trips,d=>d.filter(pendingBooking).length)} to="/bookings" note="Latest returned records"/><DashStat tone="green" icon="check" label="Completed" value={count(trips,d=>d.filter(b=>b.status==='COMPLETED').length)} to="/bookings" note="Latest returned records"/><DashStat icon="bell" label="Notifications" value={count(notices,d=>(d.items||[]).length)} to="/bookings"/><DashStat tone={verified?'blue':'red'} icon="shield" label="Contact" value={verified?'Verified':'Unverified'} to="/account" note="Verify your email from your profile before making a booking."/></>}>
  <Tile className="a-main" icon="calendar" title="Your next trip" to="/bookings" link="View all trips">
   {bookingsNote(trips,()=>next?<div className="dash-assignment"><span className="dash-vehicle-art big"><Icon name="car" size={34} aria-hidden="true"/></span><div className="dash-assignment-main"><strong className="dash-route">{tripRoute(next)}</strong><div className="dash-facts"><span><Icon name="clock" size={15}/>{displayTime(next.start_at)}{t(" · Sri Lanka time")}</span><span><Icon name="users" size={15}/>{next.passenger_count}{t(" passengers")}</span><Chip tone="info">{t(words(next.status))}</Chip></div><div className="dash-buttons"><Link className="ui-button ui-button-secondary" to={'/bookings/'+next.id}>{t("View booking")}</Link></div></div></div>:<Soft>{t("No upcoming trip")} <Link to="/hire">{t("Search for a journey")}</Link></Soft>)}</Tile>
  <Tile className="a-side" icon="spark" title="Quick actions"><DashLinks items={[['Hire a vehicle','/hire','car'],['Book tickets','/travel/book/tickets','ticket'],['Rentals','/travel/book/rental','key'],['My account','/account','user']]}/></Tile>
  <Tile className="b-1" icon="clock" title="Upcoming trips" to="/bookings" link="View all">{bookingsNote(trips,()=>upcoming.length>1?<DashList items={upcoming.slice(1,rows)} role="PASSENGER"/>:<Soft>{t("No other upcoming trips")}</Soft>)}</Tile>
  <Tile className="b-2" icon="calendar" title="Recent bookings" to="/bookings" link="View all">{bookingsNote(trips,()=>recent.length?<DashList items={recent.slice(0,rows-1)} role="PASSENGER"/>:<Soft>{t("No past bookings yet")}</Soft>)}</Tile>
  <Tile className="b-3" icon="bell" title="Notifications">{notices.loading?<Soft>{t(" Loading…")}</Soft>:notices.error?<Soft>{t("Unable to load this information")}</Soft>:notes.length?<div className="dash-list"><ReplacementRow notes={notes}/>{notes.slice(0,Math.max(1,rows-1-(notes.some(isReplacementAction)?1:0))).map(n=><Link className={'dash-row'+(isExpired(n)?' is-expired':'')} key={n.id} to={noticeBookingId(n)?'/bookings/'+noticeBookingId(n):'/bookings'}><Icon name="bell" size={16}/><div><strong>{t(n.title)}{isRoadAlertNotice(n)&&isExpired(n)&&<> · {t('Expired')}</>}</strong><span>{n.body}</span></div></Link>)}</div>:<Soft>{t("No notifications")}</Soft>}</Tile>
  <ReelsCard className="c-main" state={reels}/>
  <Tile className="c-mid" icon="document" title="Your applications and documents" tip={t("Open an application to review the private evidence available to your account. Document review and role approval remain separate decisions.")}>
   {applications.length?<div className="dash-list">{applications.slice(0,rows-1).map(row=><Link className="dash-row" key={row.role_code} to={allowed.includes(row.role_code)?`/${row.role_code.toLowerCase()}/dashboard`:`/${row.role_code.toLowerCase()}/onboarding`}><Icon name="document" size={16}/><div><strong>{row.role_code==='OWNER'?t('Owner'):t('Driver')}{t(" application: ")}{t(row.approval_status.toLowerCase())}</strong><span>{allowed.includes(row.role_code)?t('Open dashboard'):t('View application')}</span></div><Chip tone={row.approval_status==='APPROVED'?'success':row.approval_status==='REJECTED'?'danger':'muted'}>{t(row.approval_status.toLowerCase())}</Chip></Link>)}</div>:<DashLinks items={[['My documents','/account#own-documents-heading','document'],['My account','/account','user']]}/>}</Tile>
  <TravellyAiPanel className="dash-tile c-side"/>
 </DashPage>
}
