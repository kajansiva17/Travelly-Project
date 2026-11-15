import { t } from '../../i18n/language.js'
import {useCallback,useEffect,useRef,useState} from 'react'
import {Link,Navigate,useParams} from 'react-router-dom'
import {useWorkspace} from '../../context/workspaceContext'
import {fieldErrorMap} from '../../services/fieldErrors.js'
import OdometerStep from '../odometer/OdometerStep'
import TripMap from '../trips/TripMap'
import {useTripMap} from '../trips/tripHooks'
import OdometerProofCard from '../odometer/OdometerProofCard'
import {api,hasSession} from '../../services/api'
import {Header,ErrorNotice} from '../../components/components'
import {FlowShell,StateCard,FlowBanner} from '../booking/flow/FlowParts'
import {Button,Checkbox,Chip,FormField,Input,Select,InfoCallout} from '../../components/ui'
import HirePayment from '../booking/HirePayment'
import InfoTip from '../../components/ui/InfoTip'
import {RoadAlertsPanel,useRoadAlerts,useRoadAlertNotifications,useScreenWakeLock,useSpeaker} from './RoadAlerts'
import {codeLabel} from '../../i18n/codeLabels.js'

/* Trip operations for the assigned operator: check the Passenger, start, share the position,
   report a problem on the road, and finish. Everything uses the trip the Owner committed. */
const RUNNING=['IN_PROGRESS','BREAKDOWN','ASSISTANCE_REQUIRED']
const LIVE_SECONDS=30
const NOTICE_STYLE={background:'#e6f7ec',color:'#0b5d2a',border:'1px solid #7bcf9b',borderRadius:10,padding:'10px 14px',fontWeight:600,margin:0}
const PIN_INPUT={fontSize:'1.5rem',letterSpacing:'.3em',textAlign:'center'}
const clock=iso=>iso?new Date(iso).toLocaleTimeString('en-GB',{timeZone:'Asia/Colombo',hour:'2-digit',minute:'2-digit'}):''
const request=(path,body,method='POST')=>api(path,{method,body:JSON.stringify(body)})
const canScan=()=>typeof window!=='undefined'&&'BarcodeDetector'in window&&navigator.mediaDevices?.getUserMedia

export default function DriverTripPage(){
  const {tripId}=useParams(),workspace=useWorkspace()
  const [trip,setTrip]=useState(null),[error,setError]=useState(null),[busy,setBusy]=useState(false)
  const [notice,setNotice]=useState(''),[tab,setTab]=useState(null)
  // The readings come from the odometer step (typed number + live photo checked by the server); Start and Finish use exactly that number.
  const [startKm,setStartKm]=useState(null),[ready,setReady]=useState(false),[stepKey,setStepKey]=useState(0),[showProof,setShowProof]=useState(false)
  const [kind,setKind]=useState('BREAKDOWN'),[details,setDetails]=useState('')
  const [endKm,setEndKm]=useState(null),[notes,setNotes]=useState('')
  const [sharing,setSharing]=useState(false),[sentAt,setSentAt]=useState(null)
  const [scanning,setScanning]=useState(false),[pin,setPin]=useState('')
  const latest=useRef(null),video=useRef(null)
  // Road alerts (contract 03A): nearby alerts are polled while the trip runs, and spoken once when the Driver switched the speaker on.
  const [alertsOpen,setAlertsOpen]=useState(false),speaker=useSpeaker(),alerts=useRoadAlerts({tripId,running:Boolean(trip&&RUNNING.includes(trip.status)),onNew:speaker.say})
  useRoadAlertNotifications({running:Boolean(trip&&RUNNING.includes(trip.status)),onNew:speaker.sayNotification})
  const wake=useScreenWakeLock(Boolean(trip&&RUNNING.includes(trip.status)))
  // The live trip map (contract 03O, C) is the main view while the trip runs: route, road line and position from GET /trips/{id}/map, the vehicle from our own location updates.
  const [follow,setFollow]=useState(true),map=useTripMap(tripId,{enabled:Boolean(trip&&RUNNING.includes(trip.status))}),autoShared=useRef(false)   // keep the screen on while the trip runs (contract 03A)
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
  // A running trip shares its position by itself (the Passenger and the Owner follow it on the map); the Driver can stop it.
  useEffect(()=>{if(trip&&RUNNING.includes(trip.status)&&!autoShared.current){autoShared.current=true;setSharing(true)}},[trip])

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
    try{await run();setNotice(message)}catch(e){setError(e);if(e.code==='PICKUP_NOT_VERIFIED'){setTab('verify');load()}if(['ODOMETER_PROOF_REQUIRED','CAPTURE_CODE_INVALID'].includes(e.code)){setStepKey(k=>k+1);setStartKm(null);setEndKm(null)}}finally{setBusy(false)}
  }
  const start=event=>{event.preventDefault();act(async()=>{
    await request(`/trips/${tripId}/start`,{expected_version:trip.version,start_odometer_km:startKm,checklist_confirmed:true})
    await load();setTab(null)
  },'Trip started. Share your position so the Passenger can follow.')}
  const report=event=>{event.preventDefault();act(async()=>{
    const result=await request(`/trips/${tripId}/breakdown`,{expected_version:trip.version,kind,details})
    setTrip(result.trip);setDetails('')
  },'The Owner and the Passenger were told.')}
  const finish=event=>{event.preventDefault();act(async()=>{
    const result=await request(`/trips/${tripId}/complete`,{expected_version:trip.version,end_odometer_km:endKm,completion_notes:notes||null})
    setTrip(result.trip)
  },'Trip completed.')}

  if(!hasSession())return <Navigate to="/login" replace/>
  if(!trip)return error
    ?<StateCard icon="alert" title={t('Trip unavailable')} actions={<Button onClick={load}>{t('Try again')}</Button>}><ErrorNotice error={error}/></StateCard>
    :<StateCard busy title={t('Loading your trip')}/>

  const fieldMsg=fieldErrorMap(error)
  const running=RUNNING.includes(trip.status)
  const finished=['COMPLETED','CANCELLED'].includes(trip.status)
  const checked=Boolean(trip.pickup?.verified_at)
  const panels=finished||running?[]
    :trip.status==='READY'?[...(checked?[]:[['verify','Check the Passenger','user']]),...(checked||trip.pickup?.required===false?[['start','Start the trip','car']]:[])]:[]
  // Running: the map is the main view; Problem on the road, Finish and (if still needed) the passenger check open from its side column.
  const open=running?(['problem','finish','verify'].includes(tab)?tab:'map'):(panels.some(([id])=>id===tab)?tab:panels[0]?.[0])
  const tabs=panels.length>1?panels.map(([id,label,icon])=>({label:t(label),icon,active:open===id,onClick:()=>setTab(id)})):undefined
  const backToMap=running&&open!=='map'?<Button variant="secondary" onClick={()=>setTab(null)}>{t('Back to the map')}</Button>:null

  return <><Header/><FlowShell heading={t('Operate trip')} icon="car" title={codeLabel(trip.status)}
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
      <FormField label={t('Or the six digits under the code')} error={fieldMsg.pin||fieldMsg.qr_token}
        hint={t('Attempts left: ')+(trip.pickup?.attempts_left??5)}>
        {({id})=><Input id={id} inputMode="numeric" maxLength={6} value={pin} style={PIN_INPUT}
          onChange={e=>setPin(e.target.value.replace(/\D/g,'').slice(0,6))}/>}
      </FormField>
      <div className="flow-actions">{backToMap}<Button disabled={busy||pin.length!==6} onClick={()=>check({pin})}>{busy?t('Checking…'):t('Check the Passenger')}</Button></div>
    </div>}

    {checked&&open!=='verify'&&open!=='map'&&!finished&&<FlowBanner tone="success" icon="check" title={t('Passenger checked')}>
      {t('Checked at ')+clock(trip.pickup.verified_at)+t(' Sri Lanka time.')}</FlowBanner>}

    {open==='start'&&<form className="flow-fields" onSubmit={start}>
      <OdometerStep key={'start'+stepKey} tripId={tripId} stage="START" onReady={setStartKm} fieldError={fieldMsg.start_odometer_km}/>
      <Checkbox checked={ready} onChange={e=>setReady(e.target.checked)}>{t('I checked the vehicle and we are ready to go.')}</Checkbox>
      <div className="flow-actions"><Button type="submit" disabled={busy||!ready||!startKm} arrow>{busy?t('Starting…'):t('Start trip')}</Button></div>
    </form>}

    {open==='map'&&<div className="flow-fields tm-view">
      <RoadAlertsPanel trip={trip} alerts={alerts} speaker={speaker} disabled={!running} onOpenChange={setAlertsOpen} keepScreenOn={wake.unavailable}
        strip={!alertsOpen&&<div className="tm-strip">
          <Chip tone={trip.location?'success':'info'} icon="pin">{trip.location?t('Your position is shared'):t('Position not shared yet')}</Chip>
          <span className="ra-position">{trip.location
            ?t('Last sent at ')+clock(sentAt||trip.location.updated_at)+t(' Sri Lanka time.')+' · '+t('Map position')+': '+trip.location.latitude+', '+trip.location.longitude+(trip.location.accuracy_m?` · ${t('Accuracy')} ${Math.round(Number(trip.location.accuracy_m))} m`:'')+(trip.location.speed_kph?` · ${t('Speed')} ${Math.round(Number(trip.location.speed_kph))} ${t('km/h')}`:'')
            :t('Only the Passenger, the Owner and Travelly Admin can see it.')}<InfoTip>{t('Sharing stops by itself when the trip is completed.')}</InfoTip></span>
          <span className="tm-strip-actions">{sharing?<Button variant="secondary" onClick={()=>setSharing(false)}>{t('Stop sharing')}</Button>:<Button onClick={()=>setSharing(true)}>{t('Share every 30 seconds')}</Button>}
            <Button variant="secondary" disabled={busy} onClick={()=>sendPosition()}>{t('Send my position now')}</Button></span></div>}
        renderMap={({selectedId,onSelect})=><TripMap data={map.data} position={trip.location||map.data?.position} alerts={alerts.items} selectedId={selectedId} onSelect={onSelect} follow={follow} onFollow={setFollow}/>}
        extras={<>
          {!checked&&<button type="button" className="ui-button ui-button-secondary ra-side-btn" onClick={()=>setTab('verify')}>{t('Check the Passenger')}</button>}
          <button type="button" className="ui-button ui-button-secondary ra-side-btn" onClick={()=>setTab('problem')}>{t('Problem on the road')}</button>
          <button type="button" className="ui-button ui-button-primary ra-side-btn" onClick={()=>setTab('finish')}>{t('Finish trip')}</button></>}/>
      {map.error&&<p className="tk-line is-warn" role="status">{map.error}</p>}
    </div>}

    {open==='problem'&&<form className="flow-fields" onSubmit={report}>
      {trip.breakdown_details&&<FlowBanner tone="warning" icon="alert" title={codeLabel(trip.status)}>{trip.breakdown_details}</FlowBanner>}
      <FormField label={t('What is happening?')} required error={fieldMsg.kind}>
        {({id})=><Select id={id} value={kind} onChange={e=>setKind(e.target.value)}>
          <option value="BREAKDOWN">{t('The vehicle broke down')}</option>
          <option value="ASSISTANCE_REQUIRED">{t('We need help, the vehicle is fine')}</option>
        </Select>}
      </FormField>
      <FormField label={t('Tell the Owner and the Passenger')} required error={fieldMsg.details} hint={t('Write what happened and where you are.')}>
        {({id})=><textarea id={id} required maxLength={2000} rows={3} value={details} onChange={e=>setDetails(e.target.value)}/>}
      </FormField>
      <div className="flow-actions">{backToMap}<Button type="submit" disabled={busy||!details.trim()}>{busy?t('Sending…'):t('Tell them now')}</Button></div>
      <InfoCallout>{t('The booking stays active; reporting a problem never cancels it.')}</InfoCallout>
    </form>}

    {open==='finish'&&<form className="flow-fields" onSubmit={finish}>
      <OdometerStep key={'end'+stepKey} tripId={tripId} stage="END" onReady={setEndKm} fieldError={fieldMsg.end_odometer_km}/>
      <FormField label={t('Anything to note? (Optional)')} error={fieldMsg.completion_notes}>
        {({id})=><textarea id={id} maxLength={2000} rows={2} value={notes} onChange={e=>setNotes(e.target.value)}/>}
      </FormField>
      <div className="flow-actions">{backToMap}<Button type="submit" disabled={busy||!endKm} arrow>{busy?t('Finishing…'):t('Finish trip')}</Button></div>
    </form>}

    {finished&&showProof&&<div className="flow-fields">
      <OdometerProofCard tripId={tripId}/>
      <div className="flow-actions"><Button variant="secondary" onClick={()=>setShowProof(false)}>{t('Back')}</Button></div>
    </div>}

    {finished&&!showProof&&<div className="flow-fields">
      <FlowBanner tone="success" icon="check" title={codeLabel(trip.status)}>{trip.completion_notes||t('Thank you. This trip is closed.')}</FlowBanner>
      <dl className="flow-review">
        <div><dt>{t('Started')}</dt><dd>{clock(trip.actual_start_at)}</dd></div>
        <div><dt>{t('Finished')}</dt><dd>{clock(trip.actual_end_at)}</dd></div>
        <div><dt>{t('Odometer')}</dt><dd>{trip.start_odometer_km} → {trip.end_odometer_km} {t('km')}</dd></div>
        <div><dt>{t('Distance')}</dt><dd>{trip.calculated_distance_km} {t('km')}</dd></div>
      </dl>
      {trip.status==='COMPLETED'&&trip.booking_id&&<HirePayment asCollector bookingId={trip.booking_id}/>}
      <div className="flow-actions"><Link className="ui-button ui-button-secondary" to={workspace?.role==='OWNER'?'/owner/driving':'/driver/trip-history'}>{workspace?.role==='OWNER'?t('My driving'):t('My trips')}</Link>{trip.status==='COMPLETED'&&<Button variant="secondary" onClick={()=>setShowProof(true)}>{t('See proof')}</Button>}</div>
    </div>}

    {!panels.length&&!running&&!finished&&<InfoCallout>{t('This trip is not ready to operate yet.')}</InfoCallout>}
  </FlowShell></>
}
