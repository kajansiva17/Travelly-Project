import { t } from '../../i18n/language.js'
import React from 'react'
import {FlowBanner} from '../booking/flow/FlowParts'
import {money} from '../passenger/TicketCancel'
import {formatDate} from '../../i18n/dateTime.js'
import {bannerKind} from './commissionStanding'

/* One banner per commission stage for the Owner (contract 03CM, Screens). No banner when nothing is owed. */
export default function CommissionBanner({standing,currency='LKR',className=''}){
  const kind=bannerKind(standing)
  if(!kind)return null
  const amount=money(currency,standing.amount_due)
  const text=kind==='BLOCKED'?t('New bookings are stopped until you pay {value0}. Bookings you already have are not affected.',{value0:amount})
    :kind==='EXTENDED'?t('Bookings are open until {value0}. Pay {value1} before then or new bookings stop.',{value0:formatDate(standing.extended_until),value1:amount})
    :kind==='GRACE'?t('Pay {value0} by {value1} or new bookings stop.',{value0:amount,value1:formatDate(standing.blocked_from)})
    :t('You owe {value0} commission. Please pay by {value1}.',{value0:amount,value1:formatDate(standing.free_until)})
  return <div className={'cm-banner cm-'+kind.toLowerCase()+(className?' '+className:'')} role={kind==='FREE'?'status':'alert'}>
    <FlowBanner tone={kind==='FREE'?'info':'warning'} icon={kind==='FREE'?'wallet':'alert'} title={text}/></div>
}
