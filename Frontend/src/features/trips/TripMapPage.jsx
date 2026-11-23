import { t } from '../../i18n/language.js'
import {useEffect,useState} from 'react'
import {useNavigate,useParams} from 'react-router-dom'
import {api} from '../../services/api'
import {Header} from '../../components/components'
import Chip from '../../components/ui/Chip'
import {FlowShell} from '../booking/flow/FlowParts'
import {useWorkspace} from '../../context/workspaceContext'
import {RoadAlertsPanel,useRoadAlertNotifications,useRoadAlerts,useScreenWakeLock,useSpeaker} from '../driver/RoadAlerts'
import TripMap from './TripMap'
import {useTripMap} from './tripHooks'
import {routeText} from './tripMapModel'
import {drivesTrip,tripLink} from './tripLinks'
import PickupCode from '../passenger/PickupCode'
import ReturnWaiting from './ReturnWaiting'

/* The read-only live trip map (contract 03O, C): the route, the vehicle's position and the nearby road alerts, with the speaker switch.
   No alert buttons and no microphone. A person who drives this trip is sent to the Operate trip page, whose map has the driver controls. */
const RUNNING=['IN_PROGRESS','BREAKDOWN','ASSISTANCE_REQUIRED']
const clock=iso=>iso?new Date(iso).toLocaleTimeString('en-GB',{timeZone:'Asia/Colombo',hour:'2-digit',minute:'2-digit'}):''

export default function TripMapPage(){
  const {tripId}=useParams(),navigate=useNavigate(),workspace=useWorkspace(),role=workspace?.role||'PASSENGER'
  const map=useTripMap(tripId,{poll:true}),running=RUNNING.includes(map.data?.status),onTheWay=map.data?.status==='READY'&&map.data?.book_now,speaker=useSpeaker()
  const alerts=useRoadAlerts({tripId,running,onNew:speaker.say})
  useRoadAlertNotifications({running,onNew:speaker.sayNotification})
  const wake=useScreenWakeLock(running&&speaker.enabled)   // keep the screen on only while the speaker is on (contract 03A)
  const [follow,setFollow]=useState(false)
  useEffect(()=>{
    let alive=true
    api('/trips/active',{cache:'no-store'}).then(result=>{const item=(result?.items||[]).find(x=>x.trip_id===tripId);if(alive&&drivesTrip(item))navigate(tripLink(item,role),{replace:true})}).catch(()=>{})
    return()=>{alive=false}
  },[tripId])
  const position=map.data?.position,title=routeText(map.data)||t('Live trip')
  return <><Header/><FlowShell heading={t('Live trip')} icon="pin" title={title}>
    {map.error&&<p className="tk-line is-warn" role="alert">{map.error}</p>}
    {!map.loaded&&!map.error?<p role="status">{t('Loading…')}</p>
      :map.data&&<div className="flow-fields tm-view">
        {onTheWay&&map.data.viewer_is_passenger&&<PickupCode tripId={tripId}/>}
        {map.data.book_now&&<ReturnWaiting tripId={tripId}/>}
        <RoadAlertsPanel readOnly trip={{id:tripId}} alerts={alerts} speaker={speaker} disabled keepScreenOn={speaker.enabled&&wake.unavailable}
          strip={<div className="tm-strip"><Chip tone={running||onTheWay?'success':'muted'} icon="pin">{onTheWay?t('Vehicle is on the way to your pickup'):running?t('Trip in progress'):t('Trip finished')}</Chip>
            <span className="ra-position">{position?.updated_at?t('Last seen at {value0}',{value0:clock(position.updated_at)}):t('The vehicle position is not shared yet.')}</span></div>}
          renderMap={({selectedId,onSelect})=><TripMap data={map.data} position={position} alerts={alerts.items} selectedId={selectedId} onSelect={onSelect} follow={follow} onFollow={setFollow}/>}/>
      </div>}
  </FlowShell></>
}
