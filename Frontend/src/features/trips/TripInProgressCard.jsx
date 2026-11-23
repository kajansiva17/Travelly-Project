import { t } from '../../i18n/language.js'
import {Link} from 'react-router-dom'
import Chip from '../../components/ui/Chip'
import {useWorkspace} from '../../context/workspaceContext'
import {formatDateTime} from '../../i18n/dateTime.js'
import {drivesTrip,isRentalTrip,tripLink} from './tripLinks'

/* "Trip in progress" card on the Passenger, Owner and Driver dashboards (contract 03O, GET /trips/active). One compact card per trip
   running now (two shown, then a count); tapping it opens the live trip map. Going back or to the dashboard never stops the trip:
   the card and the map are always reachable again. No trips means no card. */
export default function TripInProgressCard({items}){
  const workspace=useWorkspace(),role=workspace?.role||'PASSENGER'
  if(!items||!items.length)return null
  const shown=items.slice(0,2),more=items.length-shown.length
  return <div className="tip-cards" role="region" aria-label={t('Trip in progress')}>
    {shown.map(item=><Link className="tip-card" key={item.trip_id||item.booking_id} to={tripLink(item,role)}>
      <Chip tone="success" icon={isRentalTrip(item)?'key':'route'}>{isRentalTrip(item)?t('Self-drive rental'):item.phase==='PICKUP'?(drivesTrip(item)?t('Go to the pickup'):t('Vehicle is on the way')):t('Trip in progress')}</Chip>
      <span className="tip-text"><strong>{isRentalTrip(item)?(item.vehicle||t('Self-drive rental')):`${item.origin} → ${item.destination}`}</strong><small>{[item.vehicle,item.actual_start_at&&`${t('Started')} ${formatDateTime(item.actual_start_at)}`].filter(Boolean).join(' · ')}</small></span>
      <span className="tip-open">{isRentalTrip(item)?t('Open the rental'):t('Open the map')}</span>
    </Link>)}
    {more>0&&<span className="tip-more">{t('{value0} more trips',{value0:more})}</span>}
  </div>
}
