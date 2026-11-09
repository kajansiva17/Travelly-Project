import React from 'react'
import {Header} from '../../components/components'
import {TravellyGlassPanel,TravellyState} from '../../components/TravellyVisualFoundation'

// Boarding verification needs ticket bookings, which are not available yet. Show an honest state, never fake data.
export default function DriverTicketBoarding(){
  return <><Header/><main className="role-dashboard" id="main">
    <div className="workspace-heading"><p className="section-kicker">DRIVER · ASSIGNED DEPARTURES</p><h1>Ticket boarding</h1>
      <p>Only the assigned Driver or Owner-driver will verify Passenger credentials here.</p></div>
    <TravellyGlassPanel><TravellyState title="Not available yet">Ticket boarding opens once Passengers can book seats. There is nothing to verify right now.</TravellyState></TravellyGlassPanel>
  </main></>
}
