import { t } from './i18n/language.js'
import { useLanguage } from './i18n/useLanguage.js'
import React, { lazy, Suspense } from 'react'
import { BrowserRouter, Navigate, Outlet, Route, Routes, useLocation } from 'react-router-dom'
import { NoticeProvider, ScrollToPage, useSession } from './components/components'
import { DriverPage, OwnerPage, PassengerPage } from './features/landing/ReferenceLandingPages'
import AuthPage from './features/auth/AuthPage'
import AccountPage from './pages/AccountPage'
import PassengerDashboard from './features/passenger/PassengerDashboard'
import {PassengerLongDistanceDetails,PassengerRequestReview,PassengerRequestStatus,PassengerRequirements,PassengerRideConfirmed,PassengerServiceSelection,PassengerTripDetails,PassengerVehicleMatching,PassengerVehicleReview} from './features/passenger/PassengerBookingFlow'
import { CheckEmail, AuthLink, ForgotPassword, GoogleCompletion } from './features/auth/AuthFlows'
import AdminApplications from './features/admin/AdminApplications'
import OwnerRates from './features/owner/OwnerRates'
import OwnerServiceReadiness from './features/owner/OwnerServiceReadiness'
import OwnerEventPackages from './features/owner/OwnerEventPackages'
import OwnerEventOperations from './features/owner/OwnerEventOperations'
import { HireSearchPage, BookingPage } from './features/booking/TripPricing'
import VehicleWorkspace,{PublicVehicle} from './features/owner/VehicleWorkspace'
import VehicleCalendar from './features/owner/VehicleCalendar'
import VehicleMaintenancePage from './features/owner/VehicleMaintenancePage'
import AdminWorkflowPage from './features/admin/AdminWorkflowPage'
import AdminServiceCatalogue from './features/admin/AdminServiceCatalogue'
import PassengerEventHire from './features/passenger/PassengerEventHire'
import PassengerTicketBooking from './features/passenger/PassengerTicketBooking'
import PassengerRental from './features/passenger/PassengerRental'
import {RentalRoleUi} from './features/rental/RentalUi'
import PassengerFinalFare from './features/passenger/PassengerFinalFare'
import OwnerTicketDepartures from './features/owner/OwnerTicketDepartures'
import OwnerVehicleSetup from './features/owner/OwnerVehicleSetup'
import OwnerFinanceOverview from './features/owner/OwnerFinanceOverview'
import DriverTicketBoarding from './features/driver/DriverTicketBoarding'
import AdminTicketAudit from './features/admin/AdminTicketAudit'
import AdminOversight from './features/admin/AdminOversight'
import TripOperationPage from './features/booking/TripOperationPage'
import TripFinancePage from './features/booking/TripFinancePage'
import WorkspaceShell from './components/WorkspaceShell'
const UiKitPreview=import.meta.env.DEV?lazy(()=>import('./components/ui/UiKitPreview')):null
import RoleOnboarding from './features/auth/RoleOnboarding'
import {legacyApplicationRole,onboardingPath} from './features/auth/onboardingJourney'
import {useWorkspace} from './context/workspaceContext'
import {accountPath} from './routes/workspaceRoutes'
import {OwnerDashboard,DriverDashboard,AdminDashboard,OwnerOperations,WorkspaceBookings,WorkspaceSettings,WorkspacePlaceholder,AdminDocuments,ManualFulfilment} from './components/RoleDashboards'
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
import './styles/passengerDashboard.css'
import './styles/referenceDesign.css'
import './styles/accountContext.css'
import './styles/authPromoCard.css'
import './styles/navbarSpeedometer.css'
import './styles/authFormCompact.css'
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
function OptionalPassengerWorkspace(){return useSession()?<WorkspaceShell role="PASSENGER"/>:<Outlet/>}
const placeholders={
 OWNER:['ticket-departures','seat-inventory','earnings','reviews','support','reports'],
 DRIVER:['road-alerts','reels','feed','earnings','availability','support'],
 ADMIN:['services-routes','bookings','payments','social-reviews','road-alerts','reports']
}
export default function App() {
  useLanguage()
  return (
    <BrowserRouter>
      <NoticeProvider>
        <ScrollToPage />
        <a className="skip-link" href="#main">{t("Skip to content")}</a>
        <LegacyApplicationBoundary><Routes>
          <Route path="/" element={<PassengerPage />} />
          <Route path="/for-owners" element={<PublicRoleEntry role="OWNER"><OwnerPage/></PublicRoleEntry>} />
          <Route path="/drive-with-us" element={<PublicRoleEntry role="DRIVER"><DriverPage/></PublicRoleEntry>} />
          <Route path="/owner/onboarding" element={<RoleOnboarding key="owner" role="OWNER"/>}/>
          <Route path="/driver/onboarding" element={<RoleOnboarding key="driver" role="DRIVER"/>}/>
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
            <Route path="/trips/:tripId/operation" element={<TripOperationPage/>}/>
            <Route path="/trips/:tripId/finance" element={<TripFinancePage/>}/>
            <Route path="/passenger/bookings" element={<WorkspaceBookings/>}/>
            <Route path="/passenger/saved-places" element={<WorkspacePlaceholder/>}/>
            <Route path="/passenger/payments" element={<WorkspacePlaceholder/>}/>
            <Route path="/passenger/support" element={<WorkspacePlaceholder/>}/>
            <Route path="/passenger/settings" element={<WorkspaceSettings/>}/>
            <Route path="/travel/book/service" element={<PassengerServiceSelection/>}/>
            <Route path="/travel/book/event" element={<PassengerEventHire/>}/>
            <Route path="/travel/book/tickets" element={<PassengerTicketBooking/>}/>
            <Route path="/travel/book/rental" element={<PassengerRental/>}/>
            <Route path="/passenger/trips/:tripId/finance" element={<PassengerFinalFare/>}/>
            <Route path="/travel/book/details/airport" element={<PassengerTripDetails variant="airport"/>}/>
            <Route path="/travel/book/details/local" element={<PassengerTripDetails variant="local"/>}/>
            <Route path="/travel/book/details/event" element={<PassengerTripDetails variant="event"/>}/>
            <Route path="/travel/book/details/long-distance/one-day" element={<PassengerLongDistanceDetails/>}/>
            <Route path="/travel/book/details/long-distance/multi-day" element={<PassengerLongDistanceDetails multiDay/>}/>
            <Route path="/travel/book/requirements" element={<PassengerRequirements/>}/>
            <Route path="/travel/book/vehicles" element={<PassengerVehicleMatching/>}/>
            <Route path="/travel/book/vehicles/:vehicleId/review" element={<PassengerVehicleReview/>}/>
            <Route path="/travel/book/review" element={<PassengerRequestReview/>}/>
            <Route path="/trips/:tripId/request-status" element={<PassengerRequestStatus/>}/>
            <Route path="/trips/:tripId/confirmed" element={<PassengerRideConfirmed/>}/>
          </Route>
          <Route element={<WorkspaceShell role="OWNER"/>}>
            <Route path="/owner/personal/hire" element={<HireSearchPage/>}/>
            <Route path="/owner/personal/owners/:ownerReference" element={<HireSearchPage/>}/>
            <Route path="/owner/personal/bookings" element={<WorkspaceBookings personal/>}/>
            <Route path="/owner/personal/bookings/:bookingId" element={<BookingPage/>}/>
            <Route path="/owner/personal/vehicles/:vehicleId" element={<PublicVehicle/>}/>
            <Route path="/owner/dashboard" element={<OwnerDashboard/>}/>
            <Route path="/owner/rates" element={<OwnerRates/>}/>
            <Route path="/owner/service-readiness" element={<OwnerServiceReadiness/>}/>
            <Route path="/owner/event-packages" element={<OwnerEventPackages/>}/>
            <Route path="/owner/event-operations" element={<OwnerEventOperations/>}/>
            <Route path="/owner/ticket-departures" element={<OwnerTicketDepartures/>}/>
            <Route path="/owner/vehicles" element={<VehicleRoute/>}/>
            <Route path="/owner/vehicle-setup" element={<OwnerVehicleSetup/>}/>
            <Route path="/owner/vehicles/:vehicleId" element={<VehicleRoute/>}/>
            <Route path="/owner/vehicles/:vehicleId/calendar" element={<VehicleCalendar/>}/>
            <Route path="/owner/vehicles/:vehicleId/maintenance" element={<VehicleMaintenancePage/>}/>
            <Route path="/owner/bookings" element={<WorkspaceBookings/>}/>
            <Route path="/owner/assignments" element={<WorkspaceBookings kind="assignments"/>}/>
            <Route path="/owner/operations" element={<OwnerOperations/>}/>
            <Route path="/owner/earnings" element={<OwnerFinanceOverview/>}/>
            <Route path="/owner/rentals" element={<RentalRoleUi role="OWNER"/>}/>
            <Route path="/owner/settings" element={<WorkspaceSettings/>}/>
            {placeholders.OWNER.map(path=><Route key={path} path={'/owner/'+path} element={<WorkspacePlaceholder/>}/>)}
          </Route>
          <Route element={<WorkspaceShell role="DRIVER"/>}>
            <Route path="/driver/personal/hire" element={<HireSearchPage/>}/>
            <Route path="/driver/personal/owners/:ownerReference" element={<HireSearchPage/>}/>
            <Route path="/driver/personal/bookings" element={<WorkspaceBookings personal/>}/>
            <Route path="/driver/personal/bookings/:bookingId" element={<BookingPage/>}/>
            <Route path="/driver/personal/vehicles/:vehicleId" element={<PublicVehicle/>}/>
            <Route path="/driver/dashboard" element={<DriverDashboard/>}/>
            <Route path="/driver/assignments" element={<WorkspaceBookings kind="assignments"/>}/>
            <Route path="/driver/operate-trip" element={<WorkspaceBookings kind="operate"/>}/>
            <Route path="/driver/trips/:tripId/assigned" element={<TripOperationPage/>}/>
            <Route path="/driver/trips/:tripId/verify-passenger" element={<TripOperationPage/>}/>
            <Route path="/driver/trips/:tripId/live" element={<TripOperationPage/>}/>
            <Route path="/driver/trips/:tripId/cash" element={<TripFinancePage/>}/>
            <Route path="/driver/ticket-boarding" element={<DriverTicketBoarding/>}/>
            <Route path="/driver/rentals" element={<RentalRoleUi role="DRIVER"/>}/>
            <Route path="/driver/trip-history" element={<WorkspaceBookings kind="history"/>}/>
            <Route path="/driver/settings" element={<WorkspaceSettings/>}/>
            {placeholders.DRIVER.map(path=><Route key={path} path={'/driver/'+path} element={<WorkspacePlaceholder/>}/>)}
          </Route>
          <Route element={<WorkspaceShell role="ADMIN"/>}>
            <Route path="/admin/personal/hire" element={<HireSearchPage/>}/>
            <Route path="/admin/personal/owners/:ownerReference" element={<HireSearchPage/>}/>
            <Route path="/admin/personal/bookings" element={<WorkspaceBookings personal/>}/>
            <Route path="/admin/personal/bookings/:bookingId" element={<BookingPage/>}/>
            <Route path="/admin/personal/vehicles/:vehicleId" element={<PublicVehicle/>}/>
            <Route path="/admin/dashboard" element={<AdminDashboard/>}/>
            <Route path="/admin/applications" element={<AdminApplicationRoute/>}/>
            <Route path="/admin/applications/:roleId" element={<AdminApplicationRoute/>}/>
            <Route path="/admin/vehicles" element={<VehicleRoute reviewer/>}/>
            <Route path="/admin/vehicles/:vehicleId" element={<VehicleRoute reviewer/>}/>
            <Route path="/admin/vehicles/:vehicleId/calendar" element={<VehicleCalendar reviewer/>}/>
            <Route path="/admin/documents" element={<AdminDocuments/>}/>
            <Route path="/admin/services-routes" element={<AdminServiceCatalogue/>}/>
            <Route path="/admin/services-routes/tickets" element={<AdminTicketAudit/>}/>
            <Route path="/admin/bookings" element={<AdminWorkflowPage kind="bookings"/>}/>
            <Route path="/admin/oversight" element={<AdminOversight/>}/>
            <Route path="/admin/rentals" element={<RentalRoleUi role="ADMIN"/>}/>
            <Route path="/admin/payments" element={<AdminWorkflowPage kind="payments"/>}/>
            <Route path="/admin/social-reviews" element={<AdminWorkflowPage kind="reviews"/>}/>
            <Route path="/admin/road-alerts" element={<AdminWorkflowPage kind="alerts"/>}/>
            <Route path="/admin/reports" element={<AdminWorkflowPage kind="reports"/>}/>
            <Route path="/admin/manual-fulfilment" element={<AdminWorkflowPage kind="manual"/>}/>
            <Route path="/admin/settings" element={<WorkspaceSettings/>}/>
            {placeholders.ADMIN.map(path=><Route key={path} path={'/admin/'+path} element={<WorkspacePlaceholder/>}/>)}
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
