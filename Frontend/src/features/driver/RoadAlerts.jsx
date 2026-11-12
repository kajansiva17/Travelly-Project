import { t, getLanguage } from '../../i18n/language.js'
import React,{useCallback,useEffect,useRef,useState} from 'react'
import {api} from '../../services/api'
import {Icon} from '../../components/components'
import Chip from '../../components/ui/Chip'
import {hasVoice,isYes,readSetting,recognitionConstructor,saveSetting,speak,speechLang} from './roadAlertSpeech'

/* Road alerts on the Driver's live trip (contract 03A). Only the assigned Driver of a running trip reports. Every alert
   needs one tap (buttons) or one confirmation (voice). The server decides who sees what, in each person's language. */
export const ALERT_TYPES=[['POLICE_PRESENCE','Police','shield'],['SPEED_CHECK','Speed check','watch'],['ACCIDENT','Accident','car'],['ROADBLOCK','Roadblock','close'],['ROAD_HAZARD','Road hazard','alert']]
const STATUS={UNCONFIRMED:['muted','Unconfirmed'],ACTIVE:['info','Active'],VERIFIED:['success','Verified']}
const POLL_MS=45000   // contract: every 30 to 60 seconds while the trip runs

const hasGeolocation=()=>typeof navigator!=='undefined'&&Boolean(navigator.geolocation)
// The place and heading of the alert: the device now, otherwise the position the trip last shared.
function placeOfAlert(trip){
  const fallback=trip?.location?{latitude:String(trip.location.latitude),longitude:String(trip.location.longitude)}:null
  return new Promise((resolve,reject)=>{
    const noPlace=()=>fallback?resolve({...fallback}):reject(new Error(t('Allow this page to use your location so the alert can be placed.')))
    if(!hasGeolocation())return noPlace()
    navigator.geolocation.getCurrentPosition(position=>{
      const {latitude,longitude,heading}=position.coords
      const place={latitude:latitude.toFixed(6),longitude:longitude.toFixed(6)}
      if(Number.isFinite(heading)&&heading>=0)place.travel_direction_degrees=heading.toFixed(1)
      resolve(place)
    },noPlace,{enableHighAccuracy:true,timeout:4000,maximumAge:15000})
  })
}

// Runs `load` now and every 45 seconds while `active`, only while the tab is visible, and again when it becomes visible.
function usePoll(load,active){
  useEffect(()=>{
    if(!active)return undefined
    const tick=()=>{if(document.visibilityState==='visible')load()}
    tick()
    const timer=setInterval(tick,POLL_MS)
    document.addEventListener('visibilitychange',tick)
    return()=>{clearInterval(timer);document.removeEventListener('visibilitychange',tick)}
  },[active,load])
}

/* Nearby alerts for the trip. Polls while the trip runs and the tab is visible, one request at a time. */
export function useRoadAlerts({tripId,running,onNew}){
  const [state,setState]=useState({items:[],note:null,error:null,loaded:false})
  const inFlight=useRef(false),seen=useRef(null),newer=useRef(onNew)
  useEffect(()=>{newer.current=onNew},[onNew])
  const load=useCallback(async()=>{
    if(inFlight.current)return
    inFlight.current=true
    try{
      const result=await api(`/road-alerts?trip_id=${encodeURIComponent(tripId)}`)
      const items=result.items||[]
      // The first answer is what is already up; only items that appear later are new arrivals.
      const fresh=seen.current===null?[]:items.filter(item=>!seen.current.has(item.id))
      seen.current=new Set([...(seen.current||[]),...items.map(item=>item.id)])
      setState({items,note:result.note||null,error:null,loaded:true})
      fresh.forEach(item=>newer.current&&newer.current(item))
    }catch(error){setState(current=>({...current,error,loaded:true}))}
    finally{inFlight.current=false}
  },[tripId])
  usePoll(load,running)
  const replace=useCallback(item=>setState(current=>({...current,items:current.items.map(x=>x.id===item.id?item:x)})),[])
  return {...state,reload:load,replace}
}

/* New ROAD_ALERT notifications (contract 03A, section 5): GET /notifications carries notification_type. The first answer is what
   already exists; only notifications that appear later are new, so each one is spoken once. */
export function useRoadAlertNotifications({running,onNew}){
  const inFlight=useRef(false),seen=useRef(null),newer=useRef(onNew)
  useEffect(()=>{newer.current=onNew},[onNew])
  const load=useCallback(async()=>{
    if(inFlight.current)return
    inFlight.current=true
    try{
      const result=await api('/notifications')
      const alerts=(result.items||[]).filter(note=>note.notification_type==='ROAD_ALERT')
      const fresh=seen.current===null?[]:alerts.filter(note=>!seen.current.has(note.id))
      seen.current=new Set([...(seen.current||[]),...alerts.map(note=>note.id)])
      fresh.forEach(note=>newer.current&&newer.current(note))
    }catch{/* The nearby-alerts list still works; the next poll tries again. */}
    finally{inFlight.current=false}
  },[])
  usePoll(load,running)
}

/* "Speak road alerts": on or off, kept on this device. Each alert is spoken once, in the language the server sent it. */
export function useSpeaker(){
  const [enabled,setEnabledState]=useState(()=>readSetting()),[textOnly,setTextOnly]=useState(false),spoken=useRef(new Set())
  const setEnabled=on=>{setEnabledState(on);saveSetting(on);if(!on){setTextOnly(false);globalThis.speechSynthesis?.cancel?.()}}
  const enabledRef=useRef(enabled);useEffect(()=>{enabledRef.current=enabled},[enabled])
  // One alert is spoken once, whether it arrives in the nearby list (id = the alert) or as a notification (action_payload.road_alert_id).
  const sayText=useCallback((key,text,language)=>{
    if(!enabledRef.current||!text||spoken.current.has(key))return
    spoken.current.add(key)
    if(!speak(text,speechLang(language||getLanguage())))setTextOnly(true)   // no voice for this language: the text stays on screen
  },[])
  const say=useCallback(item=>{if(item)sayText('alert:'+item.id,item.action_payload?.speak||item.message,item.language)},[sayText])
  const sayNotification=useCallback(note=>{
    if(!note||note.notification_type!=='ROAD_ALERT'||(note.expires_at&&new Date(note.expires_at)<new Date()))return
    const payload=note.action_payload||{}
    sayText(payload.road_alert_id?'alert:'+payload.road_alert_id:'note:'+note.id,payload.speak||note.message||note.body,payload.language)
  },[sayText])
  return {enabled,setEnabled,say,sayNotification,textOnly}
}

const errorText=error=>error.message||t('The alert could not be sent. Please try again.')

/* Voice: listen, classify, ask, and only after a confirmation post the alert. Nothing is sent before that. */
function useVoice({trip,onSent,onUnclear,onProblem}){
  const Recognition=recognitionConstructor()
  const [phase,setPhase]=useState('idle'),[heard,setHeard]=useState(null),[blocked,setBlocked]=useState(false),[message,setMessage]=useState('')
  const recognizer=useRef(null),pending=useRef(null),sending=useRef(false)
  const stopListening=()=>{try{recognizer.current?.abort?.()}catch{/* Already stopped. */}recognizer.current=null}
  const cancel=useCallback(()=>{stopListening();globalThis.speechSynthesis?.cancel?.();pending.current=null;sending.current=false;setPhase('idle');setHeard(null);setMessage('')},[])
  useEffect(()=>cancel,[cancel])
  const listen=useCallback((onText)=>{
    const recognition=new Recognition()
    recognition.lang=speechLang(getLanguage());recognition.interimResults=false;recognition.maxAlternatives=1;recognition.continuous=false
    recognition.onresult=event=>{const best=event.results?.[0]?.[0];if(best)onText(best.transcript||'',Number.isFinite(best.confidence)?best.confidence:null)}
    recognition.onerror=event=>{
      recognizer.current=null
      if(event.error==='not-allowed'||event.error==='service-not-allowed'){setBlocked(true);setPhase('idle');setMessage(t('The microphone is not allowed. Use the five buttons.'))}
      else if(event.error==='no-speech'||event.error==='aborted'){if(event.error==='no-speech'){setPhase('idle');setMessage(t('We did not hear anything. Try again or use the buttons.'))}}
      else{setPhase('idle');setMessage(t('Voice did not work. Use the five buttons.'))}
    }
    recognition.onend=()=>{if(recognizer.current===recognition)recognizer.current=null}
    recognizer.current=recognition
    try{recognition.start()}catch{recognizer.current=null;setPhase('idle');setMessage(t('Voice did not work. Use the five buttons.'))}
  },[Recognition])
  const send=useCallback(async()=>{
    const job=pending.current
    if(!job||sending.current)return
    sending.current=true;stopListening();globalThis.speechSynthesis?.cancel?.();setPhase('sending')
    try{
      const place=await placeOfAlert(trip)
      const body={trip_id:trip.id,alert_type:job.alert_type,...place,source_input:'VOICE',confidence_score:job.confidence.toFixed(2),driver_confirmed:true}
      if(job.transcript)body.description=job.transcript.slice(0,500)
      onSent(await api('/road-alerts',{method:'POST',body:JSON.stringify(body)}))
      pending.current=null;setPhase('idle');setHeard(null)
    }catch(error){onProblem(errorText(error));setPhase('confirm')}
    finally{sending.current=false}
  },[trip,onSent,onProblem])
  const sendRef=useRef(send);useEffect(()=>{sendRef.current=send},[send])
  const start=useCallback(()=>{
    if(!Recognition||phase!=='idle')return
    setMessage('');setPhase('listening')
    listen(async(transcript,recognised)=>{
      setPhase('classifying')
      try{
        const result=await api('/road-alerts/voice-classify',{method:'POST',body:JSON.stringify({transcript,language:getLanguage()})})
        if(!result.alert_type){setPhase('idle');setMessage(result.message||'');onUnclear();return}
        pending.current={alert_type:result.alert_type,transcript,confidence:recognised??(Number(result.confidence)||0)}
        setHeard({transcript,prompt:result.confirm_prompt,type:result.alert_type});setPhase('confirm')
        // Ask aloud when the device has a voice, then also listen for the spoken yes.
        const lang=speechLang(getLanguage()),listenForYes=()=>listen(said=>{if(isYes(said))sendRef.current()})
        if(!speak(result.confirm_prompt,lang,{onEnd:listenForYes}))listenForYes()
      }catch(error){setPhase('idle');onProblem(errorText(error))}
    })
  },[Recognition,phase,listen,onUnclear,onProblem])
  return {supported:Boolean(Recognition),blocked,phase,heard,message,start,cancel,send}
}

export function RoadAlertsPanel({trip,alerts,speaker,disabled,onOpenChange}){
  const [open,setOpenState]=useState(false),[busy,setBusy]=useState(false),[notice,setNotice]=useState(''),[problem,setProblem]=useState(''),[votes,setVotes]=useState({})
  const setOpen=useCallback(value=>{setOpenState(value);onOpenChange&&onOpenChange(value)},[onOpenChange])
  const sent=useCallback(result=>{
    setProblem('');setOpen(false)
    setNotice(result.merged?t('This alert was already up here. It counted as a confirmation.'):t('Alert sent.'))
    alerts.reload()
  },[alerts,setOpen])
  const unclear=useCallback(()=>setOpen(true),[setOpen])
  const voice=useVoice({trip,onSent:sent,onUnclear:unclear,onProblem:setProblem})
  async function report(type){
    if(busy||disabled)return
    setBusy(true);setProblem('');setNotice('')
    try{
      const place=await placeOfAlert(trip)
      sent(await api('/road-alerts',{method:'POST',body:JSON.stringify({trip_id:trip.id,alert_type:type,...place,source_input:'BUTTON'})}))
    }catch(error){setProblem(errorText(error))}finally{setBusy(false)}
  }
  async function vote(item,answer){
    setVotes(current=>({...current,[item.id]:true}));setProblem('')
    try{alerts.replace(await api(`/road-alerts/${item.id}/votes`,{method:'POST',body:JSON.stringify({vote:answer})}))}
    catch(error){setProblem(errorText(error));alerts.reload()}
    finally{setVotes(current=>({...current,[item.id]:false}))}
  }
  const voiceBusy=voice.phase!=='idle'
  const voiceText=voice.phase==='listening'?t('Listening…'):voice.phase==='classifying'?t('Checking what you said…'):voice.phase==='sending'?t('Sending…'):''
  return <div className="ra-layout">
    <div className="ra-main">
      {!voice.supported&&<p className="tk-line" role="status">{t('Voice is not available on this device. Use the five buttons.')}</p>}
      {voice.message&&<p className="tk-line is-warn" role="status">{voice.message}</p>}
      {notice&&<p className="tk-line" role="status">✓ {notice}</p>}
      {problem&&<p className="tk-line is-warn" role="alert">{problem}</p>}
      {(voiceText||busy)&&<p className="tk-line" role="status"><strong>{voiceText||t('Sending…')}</strong></p>}
      {voice.heard&&(voice.phase==='confirm'||voice.phase==='sending')&&<div className="tk-hold ra-confirm" role="alertdialog" aria-label={voice.heard.prompt}>
        <p className="tk-line"><strong>{voice.heard.prompt}</strong></p>
        <div className="ra-confirm-actions"><button type="button" className="ui-button ui-button-primary ra-big" disabled={voice.phase==='sending'} onClick={voice.send}>{t('Send')}</button><button type="button" className="ui-button ui-button-secondary ra-big" disabled={voice.phase==='sending'} onClick={voice.cancel}>{t('Cancel')}</button></div></div>}
      {speaker.enabled&&speaker.textOnly&&<p className="tk-line" role="status">{t('This device has no voice for this language. Alerts are shown as text only.')}</p>}
      <div className="ra-list" aria-label={t('Road alerts near you')}>
        {alerts.error&&<p className="tk-line is-warn" role="status">{alerts.error.message}</p>}
        {alerts.items.length
          ?alerts.items.map(item=>{const [tone,label]=STATUS[item.status]||['muted',String(item.status||'').replaceAll('_',' ')]
            return <article className="tk-row ra-item" key={item.id}>
              <div className="tk-row-main"><strong>{item.name}</strong><span title={item.message}>{item.message}</span></div>
              <div className="tk-row-actions">{typeof item.distance_km==='number'&&<span className="tk-line">{t('{value0} km',{value0:item.distance_km})}</span>}<Chip tone={tone}>{t(label)}</Chip>
                {item.can_vote&&<><button type="button" className="ui-button ui-button-secondary" disabled={votes[item.id]} onClick={()=>vote(item,'CONFIRM')}>{t('Still there')}</button><button type="button" className="ui-button ui-button-secondary" disabled={votes[item.id]} onClick={()=>vote(item,'DENY')}>{t('Not there')}</button></>}</div></article>})
          :alerts.loaded&&!alerts.error&&<p className="tk-line">{alerts.note||t('No road alerts near you.')}</p>}
      </div>
    </div>
    <aside className={'ra-rail'+(open?' is-open':'')} aria-label={t('Road alert controls')}>
      {open
        ?<>
          <button type="button" className="ra-round ra-close" aria-label={t('Close')} onClick={()=>setOpen(false)}><Icon name="close" size={22}/></button>
          {ALERT_TYPES.map(([type,label,icon])=><button type="button" key={type} className="ra-type" disabled={busy||disabled} onClick={()=>report(type)}><Icon name={icon} size={26}/><span>{t(label)}</span></button>)}
        </>
        :<>
          <button type="button" className="ra-round ra-alert" aria-label={t('Report a road alert')} title={t('Report a road alert')} disabled={disabled||voiceBusy} onClick={()=>{setNotice('');setProblem('');setOpen(true)}}><Icon name="alert" size={30}/></button>
          <button type="button" className={'ra-round ra-mic'+(voiceBusy?' is-live':'')} aria-label={voiceBusy?t('Stop listening'):t('Speak an alert')} title={voice.supported?(voice.blocked?t('The microphone is not allowed. Use the five buttons.'):t('Speak an alert')):t('Voice is not available on this device. Use the five buttons.')}
            disabled={disabled||!voice.supported||voice.blocked||busy} onClick={voiceBusy?voice.cancel:voice.start}><Icon name="mic" size={28}/></button>
          <label className="ui-switch ra-speak" title={t('Speak road alerts')}><input type="checkbox" role="switch" checked={speaker.enabled} onChange={e=>speaker.setEnabled(e.target.checked)}/><span className="ui-switch-track" aria-hidden="true"/><span>{t('Speak road alerts')}</span></label>
        </>}
    </aside>
  </div>
}
