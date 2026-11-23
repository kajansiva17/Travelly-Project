import { t } from './i18n/language.js'
import { useLanguage } from './i18n/useLanguage.js'
import React, { lazy, Suspense, useEffect } from 'react'
import { BrowserRouter, Navigate, Outlet, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { Header, NoticeProvider, ScrollToPage, useSession } from './components/components'
import { DriverPage, OwnerPage, PassengerPage } from './features/landing/ReferenceLandingPages'
import AuthPage from './features/auth/AuthPage'
import AccountPage from './pages/AccountPage'
import PassengerDashboard from './features/passenger/PassengerDashboard'
import FavouriteVehicles from './features/favourites/FavouriteVehicles'
import {PassengerLongDistanceDetails,PassengerRequestReview,PassengerRequestStatus,PassengerRequirements,PassengerRideConfirmed,PassengerServiceSelection,PassengerTripDetails,PassengerVehicleMatching,PassengerVehicleReview} from './features/passenger/PassengerBookingFlow'
import { CheckEmail, AuthLink, ForgotPassword, GoogleCompletion } from './features/auth/AuthFlows'
import AdminApplications from './features/admin/AdminApplications'
import OwnerRates from './features/owner/OwnerRates'
import OwnerServiceReadiness from './features/owner/OwnerServiceReadiness'
import { HireSearchPage, BookingPage } from './features/booking/TripPricing'
import VehicleWorkspace,{PublicVehicle} from './features/owner/VehicleWorkspace'
import VehicleCalendar from './features/owner/VehicleCalendar'
import AdminWorkflowPage from './features/admin/AdminWorkflowPage'
import AdminServiceCatalogue from './features/admin/AdminServiceCatalogue'
import PassengerTicketBooking from './features/passenger/PassengerTicketBooking'
import PassengerRental from './features/passenger/PassengerRental'
import OwnerTicketDepartures,{OwnerReplacementRequests} from './features/owner/OwnerTicketDepartures'
import OwnerDriving from './features/owner/OwnerDriving'
import MyDrivers from './features/owner/MyDrivers'

import VehicleServicePage from './features/owner/VehicleServicePage'
import OwnerHire from './features/owner/OwnerHire'
import OwnerVehicleSetup from './features/owner/OwnerVehicleSetup'
import OwnerFinanceOverview from './features/owner/OwnerFinanceOverview'
import DriverTicketBoarding from './features/driver/DriverTicketBoarding'
import AdminTicketAudit from './features/admin/AdminTicketAudit'
import AdminRoutes from './features/admin/AdminRoutes'
import AdminTicketSettings from './features/admin/AdminTicketSettings'
import AdminOversight from './features/admin/AdminOversight'
import AdminDocuments from './features/admin/AdminDocuments'
import AdminRoadAlerts from './features/admin/AdminRoadAlerts'
import AdminPayments from './features/admin/AdminPayments'
import DriverTripPage from './features/driver/DriverTripPage'
import RoadAlerts from './features/driver/RoadAlerts'
import Availability from './features/driver/Availability'
import PassengerPayments from './features/passenger/PassengerPayments'
import MyOwners from './features/driver/MyOwners'
import WorkspaceShell from './components/WorkspaceShell'
import { hasSession, sessionEndReason } from './services/api'
import {safeReturnPath} from './features/auth/loginFlow'
const UiKitPreview=import.meta.env.DEV?lazy(()=>import('./components/ui/UiKitPreview')):null
import RoleOnboarding from './features/auth/RoleOnboarding'
import {legacyApplicationRole,onboardingPath} from './features/auth/onboardingJourney'
import {useWorkspace} from './context/workspaceContext'
import {accountPath,canDriveAsOwner} from './routes/workspaceRoutes'
import {OwnerDashboard,DriverDashboard,AdminDashboard,OwnerOperations,WorkspaceBookings,WorkspaceSettings,WorkspacePlaceholder} from './components/RoleDashboards'
import DriverEarnings, { OwnerDriverPayments } from './features/driverPayments/DriverPayments'
import DriverReport from './features/reports/DriverReport'
// Load global, public, auth and responsive styles in cascade order.
import './styles/colorTokens.css'
import './styles/styles.css'
import './styles/public.css'
import './styles/auth.css'
import './styles/review.css'
import './styles/responsive.css'
import './styles/TravellyBrand.css'
import './styles/uiRefinement.css'
import './styles/authExperience.css'
import './styles/workspaces.css'
import './styles/travellyTheme.css'
import './styles/redesign.css'
import './styles/referenceDesign.css'
import './styles/accountContext.css'
import './styles/navbarSpeedometer.css'
import TripMapPage from './features/trips/TripMapPage'
import './styles/redButtonGlass.css'
import './styles/adminProfile.css'
import './styles/dashboardReferences.css'
import './styles/workspaceNavigation.css'
import './styles/languages.css'
import './styles/dashboardLightGlass.css'
import './styles/adminReferenceGlass.css'
import './styles/roleReferenceGlass.css'
import './styles/dashboardScenicBackground.css'
import './styles/travellyVisualFoundation.css'
import './styles/ui-theme.css'
import './styles/ui-kit.css'
import './styles/app-navbar.css'
import './styles/app-sidebar.css'
import './styles/travel-booking.css'
import './styles/flow.css'
import './styles/passengerBookingFlow.css'
import './styles/authGlass.css'
import './styles/frame.css'
import SocialProfile from './features/social/SocialProfile'
import ReelsPage from './features/social/ReelsPage'
import './styles/ai.css'
import './styles/social.css'
import PostCreate from './features/social/PostCreate'
import AdminSocialPosts from './features/admin/AdminSocialPosts'
import OwnerReport from './features/reports/OwnerReport'
import AdminReport from './features/reports/AdminReport'
import './styles/reports.css'
import './styles/mobile.css'

function AdminApplicationRoute() {
  const { pathname } = useLocation()
  // Queue and each private detail have separate state; never render a previous DTO on arrival.
  return <AdminApplications key={pathname}/>
}
function VehicleRoute({reviewer=false}){const {pathname}=useLocation();return <VehicleWorkspace key={pathname} reviewer={reviewer}/>}

function PassengerEntry(){const {hash}=useLocation(),role=legacyApplicationRole(hash);return role?<Navigate to={onboardingPath(role)} replace/>:<PassengerDashboard/>}
function AccountEntry(){
 const {hash,search}=useLocation(),workspace=useWorkspace(),legacy=legacyApplicationRole(hash),documents=new URLSearchParams(search).get('documents'),evidenceRole=documents==='owner'?'OWNER':documents==='driver'?'DRIVER':null
 if(legacy)return <Navigate to={onboardingPath(legacy)} replace/>
 if(evidenceRole&&workspace.role==='PASSENGER')return <Navigate to={workspace.allowed.includes(evidenceRole)?accountPath(evidenceRole)+'#own-documents-heading':onboardingPath(evidenceRole)} replace/>
 return <AccountPage/>
}
function PublicRoleEntry({role,children}){return useSession()?<Navigate to={onboardingPath(role)} replace/>:children}
function LegacyPassengerEntry(){const {hash,pathname}=useLocation(),role=legacyApplicationRole(hash)||({'/passenger/owner-application':'OWNER','/passenger/driver-application':'DRIVER'}[pathname]);return <Navigate to={role?onboardingPath(role):'/dashboard'} replace/>}
function LegacyApplicationBoundary({children}){
 const {hash,pathname,search}=useLocation(),signedIn=useSession(),q=new URLSearchParams(search),documents=q.get('documents'),legacyDocuments=!signedIn&&pathname==='/account'&&(!q.has('workspace')||q.get('workspace')==='passenger')&&(documents==='owner'||documents==='driver')?documents.toUpperCase():null,role=legacyApplicationRole(hash)||legacyDocuments
 return role&&['/dashboard','/account','/passenger/dashboard'].includes(pathname)?<Navigate to={onboardingPath(role)} replace/>:children
}
// A reload keeps the sign-in (main.jsx renews it from the HttpOnly session cookie). This only helps when a session
// EXPIRED, or a signed-out person opened a private link: after signing in they return to that page. It never applies
// after a deliberate logout, and only when the page belongs to the workspace they signed in to, so signing in as
// someone else (or as another role) never lands on the previous person's page.
const RETURN_KEY='returnTo'
const RETURN_PREFIXES=['/owner/','/driver/','/admin/','/travel/','/bookings','/trips/','/account','/passenger/']
const returnable=pathname=>RETURN_PREFIXES.some(prefix=>pathname.startsWith(prefix))&&!pathname.endsWith('/onboarding')
const workspaceOf=path=>{const [url]=path.split('#'),[base,query]=url.split('?'),role=['owner','driver','admin'].find(r=>base.startsWith('/'+r+'/'))
 return role?role.toUpperCase():base==='/account'?(new URLSearchParams(query).get('workspace')||'passenger').toUpperCase():'PASSENGER'}
const readReturn=()=>{try{const stored=sessionStorage.getItem(RETURN_KEY),safe=safeReturnPath(stored);if(stored&&!safe)sessionStorage.removeItem(RETURN_KEY);return safe}catch{return null}}
const writeReturn=value=>{try{if(value)sessionStorage.setItem(RETURN_KEY,value);else sessionStorage.removeItem(RETURN_KEY)}catch{/* Without browser storage the person simply lands on their dashboard. */}}
;(function rememberRequestedPage(){
  if(hasSession())return writeReturn(null)
  const {pathname,search,hash}=window.location
  writeReturn(returnable(pathname)?pathname+search+hash:null)
})()
function ReturnToRequestedPage(){
  const signedIn=useSession(),navigate=useNavigate(),{pathname,search,hash}=useLocation(),here=pathname+search+hash
  const last=React.useRef(null),was=React.useRef(signedIn),tries=React.useRef(0)
  // The session ended while on a page: remember it only if it expired, never after choosing to log out.
  useEffect(()=>{
    if(was.current&&!signedIn)writeReturn(sessionEndReason()==='expired'?last.current:null)
    was.current=signedIn
    if(signedIn&&returnable(pathname))last.current=here
    else if(!signedIn&&returnable(pathname)&&sessionEndReason()!=='logout')writeReturn(here)
  },[signedIn,here])
  // After signing in, wait for the landing page, then go back only within the same workspace.
  useEffect(()=>{
    if(!signedIn||pathname==='/login'||pathname==='/register')return
    const target=readReturn()
    if(!target)return
    // Landing on an onboarding page means this person is not approved for that workspace: never push them on to its private pages.
    if(pathname.endsWith('/onboarding')){writeReturn(null);tries.current=0;return}
    if(workspaceOf(target)!==workspaceOf(here)||target===here||target.split('#')[0]===pathname+search||tries.current>=4){writeReturn(null);tries.current=0;return}
    tries.current+=1
    navigate(target,{replace:true})
  },[signedIn,here])
  return null
}
// Owner and Driver workspaces hold every Passenger page under <prefix>/travel (contract 03W). The pages are the same components.
const travelRoutes=prefix=>[
 <Route key="home" path={prefix+'/travel'} element={<PassengerServiceSelection/>}/>,
 <Route key="hire" path={prefix+'/travel/hire'} element={<HireSearchPage/>}/>,
 <Route key="owners" path={prefix+'/travel/owners/:ownerReference'} element={<HireSearchPage/>}/>,
 <Route key="vehicle" path={prefix+'/travel/vehicles/:vehicleId'} element={<PublicVehicle/>}/>,
 <Route key="trips" path={prefix+'/travel/bookings'} element={<WorkspaceBookings personal/>}/>,
 <Route key="trip" path={prefix+'/travel/bookings/:bookingId'} element={<BookingPage/>}/>,
 <Route key="service" path={prefix+'/travel/book/service'} element={<PassengerServiceSelection/>}/>,
 <Route key="event" path={prefix+'/travel/book/event'} element={<Navigate to={prefix+'/travel/book/details/event'} replace/>}/>,
 <Route key="tickets" path={prefix+'/travel/book/tickets'} element={<PassengerTicketBooking/>}/>,
 <Route key="rental" path={prefix+'/travel/book/rental'} element={<PassengerRental/>}/>,
 <Route key="airport" path={prefix+'/travel/book/details/airport'} element={<PassengerTripDetails variant="airport"/>}/>,
 <Route key="local" path={prefix+'/travel/book/details/local'} element={<PassengerTripDetails variant="local"/>}/>,
 <Route key="devent" path={prefix+'/travel/book/details/event'} element={<PassengerTripDetails variant="event"/>}/>,
 <Route key="one" path={prefix+'/travel/book/details/long-distance/one-day'} element={<PassengerLongDistanceDetails/>}/>,
 <Route key="multi" path={prefix+'/travel/book/details/long-distance/multi-day'} element={<PassengerLongDistanceDetails multiDay/>}/>,
 <Route key="req" path={prefix+'/travel/book/requirements'} element={<PassengerRequirements/>}/>,
 <Route key="veh" path={prefix+'/travel/book/vehicles'} element={<PassengerVehicleMatching/>}/>,
 <Route key="review1" path={prefix+'/travel/book/vehicles/:vehicleId/review'} element={<PassengerVehicleReview/>}/>,
 <Route key="review" path={prefix+'/travel/book/review'} element={<PassengerRequestReview/>}/>,
 <Route key="status" path={prefix+'/travel/trips/:tripId/request-status'} element={<PassengerRequestStatus/>}/>,
 <Route key="confirmed" path={prefix+'/travel/trips/:tripId/confirmed'} element={<PassengerRideConfirmed/>}/>,
 <Route key="map" path={prefix+'/travel/trips/:tripId/map'} element={<TripMapPage/>}/>,
 <Route key="newpost" path={prefix+'/travel/social/post'} element={<PostCreate/>}/>,
 <Route key="reels" path={prefix+'/travel/reels'} element={<ReelsPage/>}/>,
 <Route key="reel" path={prefix+'/travel/reels/:postId'} element={<ReelsPage/>}/>,
 <Route key="profile" path={prefix+'/travel/social/users/:reference'} element={<SocialProfile/>}/>,
 <Route key="old" path={prefix+'/personal/*'} element={<OldPersonalPath/>}/>
]
// Earlier links to <prefix>/personal/... keep working and land on the same page under /travel.
function OldPersonalPath(){const {pathname,search}=useLocation();return <Navigate to={pathname.replace('/personal/','/travel/')+search} replace/>}
// My driving needs both approved roles (an Owner-only person never drives).
function DrivingGate({children}){const {user}=useWorkspace();return canDriveAsOwner(user)?children:<Navigate to="/owner/dashboard" replace/>}
function OptionalPassengerWorkspace(){return useSession()?<WorkspaceShell role="PASSENGER"/>:<Outlet/>}
// Booking pages are open to guests: search and quote are public and sign-in is asked only when the request is sent (a guest gets the public header).
function GuestOrWorkspace({header=false}){return useSession()?<WorkspaceShell/>:header?<><Header/><Outlet/></>:<Outlet/>}
const placeholders={
 OWNER:['seat-inventory','reviews','support'],
 DRIVER:['reels','feed','support'],
 ADMIN:[]
}
export default function App() {
  useLanguage()
  return (
    <BrowserRouter>
      <NoticeProvider>
        <ScrollToPage />
        <ReturnToRequestedPage />
        <a className="skip-link" href="#main">{t("Skip to content")}</a>
        <LegacyApplicationBoundary><Routes>
          <Route path="/" element={<PassengerPage />} />
          <Route path="/for-owners" element={<PublicRoleEntry role="OWNER"><OwnerPage/></PublicRoleEntry>} />
          <Route path="/drive-with-us" element={<PublicRoleEntry role="DRIVER"><DriverPage/></PublicRoleEntry>} />
          <Route element={<WorkspaceShell role="PASSENGER"/>}>
            <Route path="/owner/onboarding" element={<RoleOnboarding key="owner" role="OWNER"/>}/>
            <Route path="/driver/onboarding" element={<RoleOnboarding key="driver" role="DRIVER"/>}/>
          </Route>
          <Route path="/register" element={<AuthPage signup />} />
          <Route path="/login" element={<AuthPage />} />
          {import.meta.env.DEV&&<Route path="/__ui-kit" element={<Suspense fallback={null}><UiKitPreview/></Suspense>}/>}
          <Route path="/check-email" element={<CheckEmail/>}/>
          <Route path="/verify-email" element={<AuthLink key="verify"/>}/>
          <Route path="/forgot-password" element={<ForgotPassword/>}/>
          <Route path="/reset-password" element={<AuthLink key="reset" reset/>}/>
          <Route path="/google-complete" element={<GoogleCompletion/>}/>
          <Route path="/passenger/*" element={<LegacyPassengerEntry/>}/>
          <Route element={<WorkspaceShell/>}>
            <Route path="/dashboard" element={<PassengerEntry/>}/>
            <Route path="/account" element={<AccountEntry/>}/>
            <Route path="/bookings" element={<WorkspaceBookings/>}/>
            <Route path="/bookings/:bookingId" element={<BookingPage/>}/>
            <Route path="/trips/:tripId/operation" element={<DriverTripPage/>}/>
            <Route path="/passenger/bookings" element={<WorkspaceBookings/>}/>
            <Route path="/passenger/favourites" element={<FavouriteVehicles/>}/>
            <Route path="/passenger/saved-places" element={<WorkspacePlaceholder/>}/>
            <Route path="/passenger/payments" element={<PassengerPayments/>}/>
            <Route path="/passenger/support" element={<WorkspacePlaceholder/>}/>
            <Route path="/passenger/settings" element={<WorkspaceSettings/>}/>
            <Route path="/trips/:tripId/request-status" element={<PassengerRequestStatus/>}/>
            <Route path="/trips/:tripId/confirmed" element={<PassengerRideConfirmed/>}/>
            <Route path="/trips/:tripId/map" element={<TripMapPage/>}/>
            <Route path="/social/post" element={<PostCreate/>}/>
            <Route path="/reels" element={<ReelsPage/>}/>
            <Route path="/reels/:postId" element={<ReelsPage/>}/>
            <Route path="/social/users/:reference" element={<SocialProfile/>}/>
          </Route>
          <Route element={<WorkspaceShell role="OWNER"/>}>
            {travelRoutes('/owner')}
            <Route path="/owner/replacement-requests" element={<OwnerReplacementRequests/>}/>
            <Route path="/owner/drivers" element={<MyDrivers/>}/>
            <Route path="/owner/driver-payments" element={<OwnerDriverPayments/>}/>
            <Route path="/owner/driving" element={<DrivingGate><OwnerDriving/></DrivingGate>}/>
            <Route path="/owner/driving/trips/:tripId" element={<DrivingGate><DriverTripPage/></DrivingGate>}/>
            <Route path="/owner/dashboard" element={<OwnerDashboard/>}/>
            <Route path="/owner/rates" element={<OwnerHire/>}/>
            <Route path="/owner/rates/advanced" element={<OwnerRates/>}/>
            <Route path="/owner/service-readiness" element={<OwnerServiceReadiness/>}/>
            <Route path="/owner/ticket" element={<OwnerTicketDepartures/>}/>
            <Route path="/owner/ticket-departures" element={<Navigate to="/owner/ticket?tab=departures" replace/>}/>
            <Route path="/owner/routes" element={<Navigate to="/owner/ticket?tab=routes" replace/>}/>
            <Route path="/owner/maintenance" element={<VehicleServicePage kind="maintenance"/>}/>
            <Route path="/owner/event-packages" element={<VehicleServicePage kind="event-packages"/>}/>
            <Route path="/owner/rental" element={<VehicleServicePage kind="rental"/>}/>
            <Route path="/owner/vehicles" element={<VehicleRoute/>}/>
            <Route path="/owner/vehicle-setup" element={<OwnerVehicleSetup/>}/>
            <Route path="/owner/vehicles/:vehicleId" element={<VehicleRoute/>}/>
            <Route path="/owner/vehicles/:vehicleId/calendar" element={<VehicleCalendar/>}/>
            <Route path="/owner/bookings" element={<WorkspaceBookings/>}/>
            <Route path="/owner/assignments" element={<WorkspaceBookings kind="assignments"/>}/>
            <Route path="/owner/operations" element={<OwnerOperations/>}/>
            <Route path="/owner/earnings" element={<OwnerFinanceOverview/>}/>
            <Route path="/owner/reports" element={<OwnerReport/>}/>
            <Route path="/owner/rentals" element={<Navigate to="/owner/bookings" replace/>}/>
            <Route path="/owner/settings" element={<WorkspaceSettings/>}/>
            {placeholders.OWNER.map(path=><Route key={path} path={'/owner/'+path} element={<WorkspacePlaceholder/>}/>)}
          </Route>
          <Route element={<WorkspaceShell role="DRIVER"/>}>
            {travelRoutes('/driver')}
            <Route path="/driver/owners" element={<MyOwners/>}/>
            <Route path="/driver/dashboard" element={<DriverDashboard/>}/>
            <Route path="/driver/assignments" element={<WorkspaceBookings kind="assignments"/>}/>
            <Route path="/driver/operate-trip" element={<WorkspaceBookings kind="operate"/>}/>
            <Route path="/driver/trips/:tripId/assigned" element={<DriverTripPage/>}/>
            <Route path="/driver/trips/:tripId/verify-passenger" element={<DriverTripPage/>}/>
            <Route path="/driver/trips/:tripId/live" element={<DriverTripPage/>}/>
            <Route path="/driver/maintenance" element={<VehicleServicePage kind="maintenance" driver/>}/>
            <Route path="/driver/ticket-boarding" element={<DriverTicketBoarding/>}/>
            <Route path="/driver/rentals" element={<Navigate to="/driver/assignments" replace/>}/>
            <Route path="/driver/trip-history" element={<WorkspaceBookings kind="history"/>}/>
            <Route path="/driver/availability" element={<Availability/>}/>
            <Route path="/driver/earnings" element={<DriverEarnings/>}/>
            <Route path="/driver/reports" element={<DriverReport/>}/>
            <Route path="/driver/road-alerts" element={<RoadAlerts/>}/>
            <Route path="/driver/settings" element={<WorkspaceSettings/>}/>
            {placeholders.DRIVER.map(path=><Route key={path} path={'/driver/'+path} element={<WorkspacePlaceholder/>}/>)}
          </Route>
          <Route element={<WorkspaceShell role="ADMIN"/>}>
            {travelRoutes('/admin')}
            <Route path="/admin/dashboard" element={<AdminDashboard/>}/>
            <Route path="/admin/applications" element={<AdminApplicationRoute/>}/>
            <Route path="/admin/applications/:roleId" element={<AdminApplicationRoute/>}/>
            <Route path="/admin/vehicles" element={<VehicleRoute reviewer/>}/>
            <Route path="/admin/vehicles/:vehicleId" element={<VehicleRoute reviewer/>}/>
            <Route path="/admin/vehicles/:vehicleId/calendar" element={<VehicleCalendar reviewer/>}/>
            <Route path="/admin/documents" element={<AdminDocuments/>}/>
            <Route path="/admin/services-routes" element={<AdminServiceCatalogue/>}/>
            <Route path="/admin/services-routes/tickets" element={<AdminTicketAudit/>}/>
            <Route path="/admin/services-routes/routes" element={<AdminRoutes/>}/>
            <Route path="/admin/services-routes/ticket-settings" element={<AdminTicketSettings/>}/>
            <Route path="/admin/bookings" element={<AdminWorkflowPage kind="bookings"/>}/>
            <Route path="/admin/oversight" element={<AdminOversight/>}/>
            <Route path="/admin/rentals" element={<Navigate to="/admin/oversight" replace/>}/>
            <Route path="/admin/payments" element={<AdminPayments/>}/>
            <Route path="/admin/social-reviews" element={<AdminSocialPosts/>}/>
            <Route path="/admin/road-alerts" element={<AdminRoadAlerts/>}/>
            <Route path="/admin/reports" element={<AdminReport/>}/>
            <Route path="/admin/manual-fulfilment" element={<AdminWorkflowPage kind="manual"/>}/>
            <Route path="/admin/settings" element={<WorkspaceSettings/>}/>
            {placeholders.ADMIN.map(path=><Route key={path} path={'/admin/'+path} element={<WorkspacePlaceholder/>}/>)}
          </Route>
          <Route element={<GuestOrWorkspace header/>}>
            <Route path="/travel/book/event" element={<Navigate to="/travel/book/details/event" replace/>}/>
            <Route path="/travel/book/service" element={<PassengerServiceSelection/>}/>
            <Route path="/travel/book/details/airport" element={<PassengerTripDetails variant="airport"/>}/>
            <Route path="/travel/book/details/local" element={<PassengerTripDetails variant="local"/>}/>
            <Route path="/travel/book/details/event" element={<PassengerTripDetails variant="event"/>}/>
            <Route path="/travel/book/details/long-distance/one-day" element={<PassengerLongDistanceDetails/>}/>
            <Route path="/travel/book/details/long-distance/multi-day" element={<PassengerLongDistanceDetails multiDay/>}/>
            <Route path="/travel/book/requirements" element={<PassengerRequirements/>}/>
            <Route path="/travel/book/vehicles" element={<PassengerVehicleMatching/>}/>
            <Route path="/travel/book/vehicles/:vehicleId/review" element={<PassengerVehicleReview/>}/>
            <Route path="/travel/book/review" element={<PassengerRequestReview/>}/>
          </Route>
          <Route element={<GuestOrWorkspace/>}>
            <Route path="/travel/book/tickets" element={<PassengerTicketBooking/>}/>
            <Route path="/travel/book/rental" element={<PassengerRental/>}/>
          </Route>
          <Route element={<OptionalPassengerWorkspace/>}>
            <Route path="/vehicles/:vehicleId" element={<PublicVehicle/>}/>
            <Route path="/hire" element={<HireSearchPage/>}/>
            <Route path="/owners/:ownerReference" element={<HireSearchPage/>}/>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes></LegacyApplicationBoundary>
      </NoticeProvider>
    </BrowserRouter>
  )
}
