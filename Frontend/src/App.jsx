import React from 'react'
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { Header, NoticeProvider, ScrollToPage } from './components'
import { DriverPage, OwnerPage, PassengerPage } from './PublicPages'
import AuthPage from './AuthPage'
import AccountPage from './AccountPage'
import { CheckEmail, AuthLink, ForgotPassword, GoogleCompletion } from './AuthFlows'
import PassengerDashboard from './PassengerDashboard'
import AdminApplications from './AdminApplications'
// Load global, public, auth and responsive styles in cascade order.
import './styles.css'
import './public.css'
import './auth.css'
import './dashboard.css'
import './review.css'
import './responsive.css'

function AdminApplicationRoute() {
  const { pathname } = useLocation()
  // Queue and each private detail have separate state; never render a previous DTO on arrival.
  return <AdminApplications key={pathname}/>
}

export default function App() {
  return (
    <BrowserRouter>
      <NoticeProvider>
        <ScrollToPage />
        <a className="skip-link" href="#main">Skip to content</a>
        <Routes>
          <Route path="/" element={<PassengerPage />} />
          <Route path="/for-owners" element={<OwnerPage />} />
          <Route path="/drive-with-us" element={<DriverPage />} />
          <Route path="/register" element={<AuthPage signup />} />
          <Route path="/login" element={<AuthPage />} />
          <Route path="/dashboard" element={<PassengerDashboard />} />
          <Route path="/check-email" element={<CheckEmail/>}/>
          <Route path="/verify-email" element={<AuthLink key="verify"/>}/>
          <Route path="/forgot-password" element={<ForgotPassword/>}/>
          <Route path="/reset-password" element={<AuthLink key="reset" reset/>}/>
          <Route path="/google-complete" element={<GoogleCompletion/>}/>
          <Route path="/account" element={<><Header /><AccountPage /></>} />
          <Route path="/admin/applications" element={<AdminApplicationRoute />} />
          <Route path="/admin/applications/:roleId" element={<AdminApplicationRoute />} />
          {/* Add future dashboard routes here, alongside the existing pages. */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </NoticeProvider>
    </BrowserRouter>
  )
}
