import React from 'react'
import {Header} from '../../components/components'
import {TravellyGlassPanel,TravellyState} from '../../components/TravellyVisualFoundation'

// The ticket audit needs bookings and holds, which are not available yet. Show an honest state, never fake data.
export default function AdminTicketAudit(){
  return <><Header/><main className="role-dashboard" id="main">
    <div className="workspace-heading"><p className="section-kicker">ADMIN · SERVICES &amp; ROUTES</p><h1>Ticket audit</h1>
      <p>Read-only departure, seat-hold, booking and boarding audit metadata will appear here. Credentials and private contact details are never exposed.</p></div>
    <TravellyGlassPanel><TravellyState title="Not available yet">Ticket audit opens once Passengers can book seats. No ticket activity exists to review.</TravellyState></TravellyGlassPanel>
  </main></>
}
