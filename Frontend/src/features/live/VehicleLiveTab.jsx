import { t } from '../../i18n/language.js'
import { ErrorNotice, Icon } from '../../components/components'
import VehicleLiveCard from './VehicleLiveCard'
import { useLive } from './liveSender'
import { useLiveVehicles } from './liveVehicles'

// "Live" tab of a vehicle in My vehicles: where the vehicle is now, and Go online / Book now for this one vehicle.
export default function VehicleLiveTab({ vehicleId }) {
  const live = useLive()
  const { items, error, busyId, toggle, bookNow } = useLiveVehicles()
  const item = (items || []).find(row => row.vehicle_id === vehicleId)
  if (!items && !error) return <p role="status">{t('Loading…')}</p>
  return <div className="live-page">
    {error && <ErrorNotice error={error}/>}
    {live.problem && item?.sending && <p className="live-alert" role="alert"><Icon name="alert" size={16}/><span>{live.problem}</span></p>}
    {item
      ? <VehicleLiveCard item={item} showName={false} busy={busyId === item.vehicle_id} onToggle={() => toggle(item)} onBookNow={() => bookNow(item)}/>
      : items && <p className="live-empty">{t('Go online is available after Admin approves this vehicle.')}</p>}
    <p className="flow-note">{t('While you are online, your phone location is sent so nearby Passengers can find the vehicle. Keep Travelly open on your phone. The location is sent only while the app is open.')}</p>
  </div>
}
