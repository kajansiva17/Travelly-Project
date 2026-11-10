import React from 'react'
import {Header} from '../../components/components'
import {FlowShell} from '../booking/flow/FlowParts'
import {Empty} from '../ticketing/TicketParts'

// Boarding verification needs ticket bookings, which are not available yet. Show an honest state, never fake data.
export default function DriverTicketBoarding(){
  return <><Header/><FlowShell heading="Ticket boarding" icon="ticket" title="Not available yet"
    info="Only the assigned Driver or Owner-driver will verify Passenger credentials here.">
    <Empty>Ticket boarding opens once Passengers can book seats. There is nothing to verify right now.</Empty>
  </FlowShell></>
}
