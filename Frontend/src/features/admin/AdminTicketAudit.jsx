import React from 'react'
import {Header} from '../../components/components'
import {FlowShell} from '../booking/flow/FlowParts'
import {Empty} from '../ticketing/TicketParts'

// The ticket audit needs bookings and holds, which are not available yet. Show an honest state, never fake data.
export default function AdminTicketAudit(){
  return <><Header/><FlowShell heading="Ticket audit" icon="shield" title="Not available yet"
    info="Read-only departure, seat-hold, booking and boarding audit metadata will appear here. Credentials and private contact details are never exposed.">
    <Empty>Ticket audit opens once Passengers can book seats. No ticket activity exists to review.</Empty>
  </FlowShell></>
}
