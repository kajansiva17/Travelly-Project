import { t } from '../../i18n/language.js'
import React,{useCallback,useEffect,useRef,useState} from 'react'
import {Link,Navigate,useParams} from 'react-router-dom'
import {useWorkspace} from '../../context/workspaceContext'
import {api,hasSession} from '../../services/api'
import {Header,ErrorNotice} from '../../components/components'
import {FlowShell,StateCard,FlowBanner} from '../booking/flow/FlowParts'
import {Button,Checkbox,FormField,Input,Select,InfoCallout} from '../../components/ui'
import HirePayment from '../booking/HirePayment'
import InfoTip from '../../components/ui/InfoTip'
import {RoadAlertsPanel,useRoadAlerts,useRoadAlertNotifications,useSpeaker} from './RoadAlerts'

/* Trip operations for the assigned operator: check the Passenger, start, share the position,
   report a problem on the road, and finish. Everything uses the trip the Owner committed. */
const RUNNING=['IN_PROGRESS','BREAKDOWN','ASSISTANCE_REQUIRED']
const LIVE_SECONDS=30
const NOTICE_STYLE={background:'#e6f7ec',color:'#0b5d2a',border:'1px solid #7bcf9b',borderRadius:10,padding:'10px 14px',fontWeight:600,margin:0}
const PIN_INPUT={fontSize:'1.5rem',letterSpacing:'.3em',textAlign:'center'}
const words=value=>String(value||'').replaceAll('_',' ').toLowerCase()
const clock=iso=>iso?new Date(iso).toLocaleTimeString('en-GB',{timeZone:'Asia/Colombo',hour:'2-digit',minute:'2-digit'}):''
const request=(path,body,method='POST')=>api(path,{method,body:JSON.stringify(body)})
const canScan=()=>typeof window!=='undefined'&&'BarcodeDetector'in window&&navigator.mediaDevices?.getUserMedia

export default function DriverTripPage(){
  const {tripId}=useParams(),workspace=useWorkspace()
  const [trip,setTrip]=useState(null),[error,setError]=useState(null),[busy,setBusy]=useState(false)
  const [notice,setNotice]=useState(''),[tab,setTab]=useState(null)
  const [odometer,setOdometer]=useState(''),[ready,setReady]=useState(false)
  const [kind,setKind]=useState('BREAKDOWN'),[details,setDetails]=useState('')
  const [endOdometer,setEndOdometer]=useState(''),[notes,setNotes]=useState('')
  const [sharing,setSharing]=useState(false),[sentAt,setSentAt]=useState(null)
  const [scanning,setScanning]=useState(false),[pin,setPin]=useState('')
  const latest=useRef(null),video=useRef(null)
  // Road alerts (contract 03A): nearby alerts are polled while the trip runs, and spoken once when the Driver switched the speaker on.
  const [alertsOpen,setAlertsOpen]=useState(false),speaker=useSpeaker(),alerts=useRoadAlerts({tripId,running:Boolean(trip&&RUNNING.includes(trip.status)),onNew:speaker.say})
  useRoadAlertNotifications({running:Boolean(trip&&RUNNING.includes(trip.status)),onNew:speaker.sayNotification})
  useEffect(()=>{latest.current=trip},[trip])
  useEffect(()=>{if(!notice)return;const timer=setTimeout(()=>setNotice(''),8000);return()=>clearTimeout(timer)},[notice])

  const load=useCallback(async()=>{try{setTrip(await api('/trips/'+tripId));setError(null)}catch(e){setError(e)}},[tripId])
  useEffect(()=>{load()},[load])

  const sendPosition=useCallback(()=>new Promise(done=>{
    const current=latest.current
    if(!current||!RUNNING.includes(current.status)){done(false);return}
    if(!navigator.geolocation){setError(new Error('This device cannot read a position.'));done(false);return}
    navigator.geolocation.getCurrentPosition(async position=>{
      const {latitude,longitude,accuracy,speed}=position.coords
      const body={expected_version:latest.current.version,latitude:latitude.toFixed(6),longitude:longitude.toFixed(6)}
      if(Number.isFinite(accuracy))body.accuracy_m=Math.min(accuracy,99999999).toFixed(2)
      if(Number.isFinite(speed)&&speed!==null)body.speed_kph=Math.min(speed*3.6,999999).toFixed(2)
      try{setTrip(await api(`/trips/${tripId}/location`,{method:'PATCH',body:JSON.stringify(body)}));setSentAt(new Date().toISOString());setError(null);done(true)}
      catch(e){setError(e);done(false)}
    },()=>{setError(new Error('Allow this page to use your location so the Passenger and the Owner can follow the trip.'));done(false)},
    {enableHighAccuracy:true,timeout:15000,maximumAge:0})
  }),[tripId])

  useEffect(()=>{
    if(!sharing)return
    let active=true
    const tick=()=>{if(active)sendPosition()}
    tick()
    const timer=setInterval(tick,LIVE_SECONDS*1000)
    return()=>{active=false;clearInterval(timer)}
  },[sharing,sendPosition])
  useEffect(()=>{if(trip&&!RUNNING.includes(trip.status))setSharing(false)},[trip])

  const check=useCallback(async body=>{
    setBusy(true);setError(null)
    try{
      const result=await request(`/trips/${tripId}/pickup-verifications`,{expected_version:latest.current.version,...body})
      setTrip(result.trip);setPin('');setNotice('Passenger checked.')
      return true
    }catch(e){setError(e);return false}finally{setBusy(false)}
  },[tripId])

  useEffect(()=>{
    if(!scanning)return
    if(!canScan()){setError(new Error('This browser cannot scan a code. Ask the Passenger to read out the six digits.'));setScanning(false);return}
    let stream=null,stopped=false,timer=null
    const detector=new window.BarcodeDetector({formats:['qr_code']})
    const read=async()=>{
      if(stopped)return
      try{
        const found=video.current?await detector.detect(video.current):[]
        if(found.length&&found[0].rawValue){
          const done=await check({qr_token:found[0].rawValue})
          if(done){setScanning(false);return}
        }
      }catch{/* a frame that cannot be read is normal; try the next one */}
      timer=setTimeout(read,400)
    }
    navigator.mediaDevices.getUserMedia({video:{facingMode:'environment'}}).then(async media=>{
      stream=media
      if(video.current){video.current.srcObject=media;await video.current.play().catch(()=>{})}
      read()
    }).catch(()=>{setError(new Error('Allow the camera, or ask the Passenger to read out the six digits.'));setScanning(false)})
    return()=>{stopped=true;clearTimeout(timer);stream?.getTracks().forEach(track=>track.stop())}
  },[scanning,check])

  async function act(run,message){
    setBusy(true);setError(null)
    try{await run();setNotice(message)}catch(e){setError(e)}finally{setBusy(false)}
  }
  const start=event=>{event.preventDefault();act(async()=>{
    await request(`/trips/${tripId}/start`,{expected_version:trip.version,start_odometer_km:odometer,checklist_confirmed:true})
    await load();setTab('live')
  },'Trip started. Share your position so the Passenger can follow.')}
  const report=event=>{event.preventDefault();act(async()=>{
    const result=await request(`/trips/${tripId}/breakdown`,{expected_version:trip.version,kind,details})
    setTrip(result.trip);setDetails('')
  },'The Owner and the Passenger were told.')}
  const finish=event=>{event.preventDefault();act(async()=>{
    const result=await request(`/trips/${tripId}/complete`,{expected_version:trip.version,end_odometer_km:endOdometer,completion_notes:notes||null})
    setTrip(result.trip)
  },'Trip completed.')}

  if(!hasSession())return <Navigate to="/login" replace/>
  if(!trip)return error
    ?<StateCard icon="alert" title={t('Trip unavailable')} actions={<Button onClick={load}>{t('Try again')}</Button>}><ErrorNotice error={error}/></StateCard>
    :<StateCard busy title={t('Loading your trip')}/>

  const running=RUNNING.includes(trip.status)
  const finished=['COMPLETED','CANCELLED'].includes(trip.status)
  const checked=Boolean(trip.pickup?.verified_at)
  const panels=finished?[]:running
    ?[...(checked?[]:[['verify','Check the Passenger','user']]),['live','Live position','pin'],['problem','Problem on the road','alert'],['finish','Finish the trip','check']]
    :trip.status==='READY'?[...(checked?[]:[['verify','Check the Passenger','user']]),['start','Start the trip','car']]:[]
  const open=panels.some(([id])=>id===tab)?tab:panels[0]?.[0]
  const tabs=panels.length>1?panels.map(([id,label,icon])=>({label:t(label),icon,active:open===id,onClick:()=>setTab(id)})):undefined

  return <><Header/><FlowShell heading={t('Operate trip')} icon="car" title={t('Trip ')+words(trip.status)}
    subtitle={t('Planned ')+clock(trip.scheduled_start_at)+t(' to ')+clock(trip.scheduled_end_at)+t(' Sri Lanka time')} tabs={tabs}>
    {notice&&<p role="status" style={NOTICE_STYLE}>{'✓ '}{notice}</p>}
    <ErrorNotice error={error}/>

    {open==='verify'&&<div className="flow-fields">
      <FlowBanner tone="info" icon="user" title={t('Check the Passenger at the pickup')}>
        {t('Ask them to open their pickup code. Scan it, or type the six digits printed under it.')}</FlowBanner>
      {scanning
        ?<div style={{display:'grid',justifyItems:'center',gap:8}}>
          <video ref={video} playsInline muted style={{width:260,maxWidth:'100%',borderRadius:12,background:'#000'}}/>
          <Button variant="secondary" onClick={()=>setScanning(false)}>{t('Stop the camera')}</Button>
        </div>
        :<div className="flow-actions"><Button icon="eye" disabled={busy} onClick={()=>setScanning(true)}>{t('Scan the QR code')}</Button></div>}
      <FormField label={t('Or the six digits under the code')}
        hint={t('Attempts left: ')+(trip.pickup?.attempts_left??5)}>
        {({id})=><Input id={id} inputMode="numeric" maxLength={6} value={pin} style={PIN_INPUT}
          onChange={e=>setPin(e.target.value.replace(/\D/g,'').slice(0,6))}/>}
      </FormField>
      <div className="flow-actions"><Button disabled={busy||pin.length!==6} onClick={()=>check({pin})}>{busy?t('Checking…'):t('Check the Passenger')}</Button></div>
    </div>}

    {checked&&open!=='verify'&&!finished&&<FlowBanner tone="success" icon="check" title={t('Passenger checked')}>
      {t('Checked at ')+clock(trip.pickup.verified_at)+t(' Sri Lanka time.')}</FlowBanner>}

    {open==='start'&&<form className="flow-fields" onSubmit={start}>
      <FormField label={t('Odometer now (km)')} required hint={t('Copy the number on the dashboard; one decimal place is allowed.')}>
        {({id})=><Input id={id} required type="number" min="0" step="0.1" value={odometer} onChange={e=>setOdometer(e.target.value)}/>}
      </FormField>
      <Checkbox checked={ready} onChange={e=>setReady(e.target.checked)}>{t('I checked the vehicle and we are ready to go.')}</Checkbox>
      <div className="flow-actions"><Button type="submit" disabled={busy||!ready||!odometer} arrow>{busy?t('Starting…'):t('Start the trip')}</Button></div>
    </form>}

    {open==='live'&&<div className="flow-fields ra-live">
      {!alertsOpen&&<FlowBanner tone={trip.location?'success':'info'} icon="pin" title={trip.location?t('Your position is shared'):t('Position not shared yet')}
        aside={<div className="ra-banner-actions">{sharing?<Button variant="secondary" onClick={()=>setSharing(false)}>{t('Stop sharing')}</Button>
          :<Button onClick={()=>setSharing(true)}>{t('Share every 30 seconds')}</Button>}<Button variant="secondary" disabled={busy} onClick={()=>sendPosition()}>{t('Send my position now')}</Button></div>}>
        {trip.location
          ?t('Last sent at ')+clock(sentAt||trip.location.updated_at)+t(' Sri Lanka time.')
          :t('Only the Passenger, the Owner and Travelly Admin can see it.')}
        <InfoTip>{t('Sharing stops by itself when the trip is completed.')}</InfoTip>
        {trip.location&&<span className="ra-position"> · {t('Map position')}: {trip.location.latitude}, {trip.location.longitude}{trip.location.accuracy_m?` · ${t('Accuracy')} ${Math.round(Number(trip.location.accuracy_m))} m`:''}{trip.location.speed_kph?` · ${t('Speed')} ${Math.round(Number(trip.location.speed_kph))} ${t('km/h')}`:''}</span>}
      </FlowBanner>}
      <RoadAlertsPanel trip={trip} alerts={alerts} speaker={speaker} disabled={!running} onOpenChange={setAlertsOpen}/>
    </div>}

    {open==='problem'&&<form className="flow-fields" onSubmit={report}>
      {trip.breakdown_details&&<FlowBanner tone="warning" icon="alert" title={t(words(trip.status))}>{trip.breakdown_details}</FlowBanner>}
      <FormField label={t('What is happening?')} required>
        {({id})=><Select id={id} value={kind} onChange={e=>setKind(e.target.value)}>
          <option value="BREAKDOWN">{t('The vehicle broke down')}</option>
          <option value="ASSISTANCE_REQUIRED">{t('We need help, the vehicle is fine')}</option>
        </Select>}
      </FormField>
      <FormField label={t('Tell the Owner and the Passenger')} required hint={t('Write what happened and where you are.')}>
        {({id})=><textarea id={id} required maxLength={2000} rows={3} value={details} onChange={e=>setDetails(e.target.value)}/>}
      </FormField>
      <div className="flow-actions"><Button type="submit" disabled={busy||!details.trim()}>{busy?t('Sending…'):t('Tell them now')}</Button></div>
      <InfoCallout>{t('The booking stays active; reporting a problem never cancels it.')}</InfoCallout>
    </form>}

    {open==='finish'&&<form className="flow-fields" onSubmit={finish}>
      <FormField label={t('Odometer at the end (km)')} required
        hint={t('It cannot be lower than ')+(trip.start_odometer_km||'0')+t(' km, the reading you gave at the start.')}>
        {({id})=><Input id={id} required type="number" min={trip.start_odometer_km||'0'} step="0.1" value={endOdometer} onChange={e=>setEndOdometer(e.target.value)}/>}
      </FormField>
      <FormField label={t('Anything to note? (Optional)')}>
        {({id})=><textarea id={id} maxLength={2000} rows={2} value={notes} onChange={e=>setNotes(e.target.value)}/>}
      </FormField>
      <div className="flow-actions"><Button type="submit" disabled={busy||!endOdometer} arrow>{busy?t('Finishing…'):t('Finish the trip')}</Button></div>
    </form>}

    {finished&&<div className="flow-fields">
      <FlowBanner tone="success" icon="check" title={t('Trip ')+words(trip.status)}>{trip.completion_notes||t('Thank you. This trip is closed.')}</FlowBanner>
      <dl className="flow-review">
        <div><dt>{t('Started')}</dt><dd>{clock(trip.actual_start_at)}</dd></div>
        <div><dt>{t('Finished')}</dt><dd>{clock(trip.actual_end_at)}</dd></div>
        <div><dt>{t('Odometer')}</dt><dd>{trip.start_odometer_km} → {trip.end_odometer_km} {t('km')}</dd></div>
        <div><dt>{t('Distance')}</dt><dd>{trip.calculated_distance_km} {t('km')}</dd></div>
      </dl>
      {trip.status==='COMPLETED'&&trip.booking_id&&<HirePayment asCollector bookingId={trip.booking_id}/>}
      <div className="flow-actions"><Link className="ui-button ui-button-secondary" to={workspace?.role==='OWNER'?'/owner/driving':'/driver/trip-history'}>{workspace?.role==='OWNER'?t('My driving'):t('My trips')}</Link></div>
    </div>}

    {!panels.length&&!finished&&<InfoCallout>{t('This trip is not ready to operate yet.')}</InfoCallout>}
  </FlowShell></>
}
