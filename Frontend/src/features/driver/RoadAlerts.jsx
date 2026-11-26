import { t, getLanguage } from '../../i18n/language.js'
import {useCallback,useEffect,useRef,useState} from 'react'
import {createPortal} from 'react-dom'
import {api} from '../../services/api'
import {Icon} from '../../components/components'
import Chip from '../../components/ui/Chip'
import {CONFIRM_SECONDS,alertName,alertText,answerOf,hasVoice,readSetting,recognitionConstructor,saveSetting,speak,speechLang,warmVoices} from './roadAlertSpeech'
import {acquireWakeLock,releaseWakeLock} from './screenWakeLock'
import {usePoll as usePollEvery} from '../trips/usePoll'
import {codeEnglish} from '../../i18n/codeLabels.js'
import {Link} from 'react-router-dom'
import {StateCard} from '../booking/flow/FlowParts'

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

// Every 45 seconds while `active`, only while the tab is visible, and again when it becomes visible (shared with the trip map).
const usePoll=(load,active)=>usePollEvery(load,active,POLL_MS)

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
/* `onPopup({key,name,text})` is called for an alert that was not spoken aloud (speaker off, or no voice for the language): the Driver's screen is on, so it is shown as a popup. */
export function useSpeaker({onPopup}={}){
  const [enabled,setEnabledState]=useState(()=>readSetting()),[textOnly,setTextOnly]=useState(false),spoken=useRef(new Set())
  const setEnabled=on=>{setEnabledState(on);saveSetting(on);if(!on){setTextOnly(false);globalThis.speechSynthesis?.cancel?.()}}
  const enabledRef=useRef(enabled);useEffect(()=>{enabledRef.current=enabled},[enabled])
  useEffect(()=>{warmVoices()},[])
  const popupRef=useRef(onPopup);useEffect(()=>{popupRef.current=onPopup},[onPopup])
  // One alert is announced once, whether it arrives in the nearby list (id = the alert) or as a notification (action_payload.road_alert_id).
  // Speaker on: it is spoken aloud. Otherwise (or with no voice for the language) the page shows it as a popup. Always in the page language.
  const sayText=useCallback((key,text,name)=>{
    if(!text||spoken.current.has(key))return
    spoken.current.add(key)
    if(enabledRef.current){if(speak(text,speechLang(getLanguage())))return;setTextOnly(true)}   // no voice for this language: the text stays on screen
    if(popupRef.current)popupRef.current({key,name,text})
  },[])
  // Never announced to the Driver who reported it (or to anyone on that trip): they were there.
  const say=useCallback(item=>{if(item&&!item.reported_by_me&&!item.own_trip)sayText('alert:'+item.id,alertText(item,getLanguage()),alertName(item,getLanguage()))},[sayText])
  const sayNotification=useCallback(note=>{
    if(!note||note.notification_type!=='ROAD_ALERT'||(note.expires_at&&new Date(note.expires_at)<new Date()))return
    const payload=note.action_payload||{},language=getLanguage()
    sayText(payload.road_alert_id?'alert:'+payload.road_alert_id:'note:'+note.id,payload.speak_all?.[language]||payload.speak||note.message||note.body,payload.names?.[language]||payload.titles?.[language]||note.title)
  },[sayText])
  return {enabled,setEnabled,say,sayNotification,textOnly}
}

const errorText=error=>error.message||t('The alert could not be sent. Please try again.')

/* Keeps the screen on while the trip runs (Screen Wake Lock, contract 03A). The browser drops the lock when the person switches
   app, so it is asked for again when the page becomes visible. `unavailable` means this browser or device did not give it. */
export function useScreenWakeLock(active){
  const [unavailable,setUnavailable]=useState(false)
  useEffect(()=>{
    if(!active)return undefined
    let lock=null,stopped=false
    const ask=async()=>{
      if(stopped||document.visibilityState!=='visible'||(lock&&!lock.released))return
      const result=await acquireWakeLock()
      if(stopped){await releaseWakeLock(result.lock);return}
      lock=result.lock;setUnavailable(result.status!=='held')
    }
    const again=()=>{if(document.visibilityState==='visible')ask()}
    const leave=()=>{releaseWakeLock(lock);lock=null}
    ask()
    document.addEventListener('visibilitychange',again);window.addEventListener('pagehide',leave)
    return()=>{stopped=true;document.removeEventListener('visibilitychange',again);window.removeEventListener('pagehide',leave);releaseWakeLock(lock);lock=null}
  },[active])
  return {unavailable}
}

/* Voice (contract 03A, section 2): one tap, then hands free. The app listens once, asks the server what was said, speaks the
   confirmation, listens by itself for confirm_seconds, and posts only on a yes. The microphone is off between alerts and never on
   while the app speaks. Nothing is sent before a yes word or Send. */
function useVoice({trip,onSent,onUnclear,onProblem}){
  const Recognition=recognitionConstructor()
  const [phase,setPhase]=useState('idle'),[heard,setHeard]=useState(null),[blocked,setBlocked]=useState(false),[message,setMessage]=useState(''),[outcome,setOutcome]=useState('')
  const recognizer=useRef(null),job=useRef(null),finished=useRef(true),timer=useRef(null),session=useRef(0)
  const stopMic=()=>{const r=recognizer.current;recognizer.current=null;try{r&&r.abort&&r.abort()}catch{/* Already stopped. */}}
  const stopAll=()=>{stopMic();clearTimeout(timer.current);timer.current=null;globalThis.speechSynthesis?.cancel?.()}
  const reset=useCallback(()=>{session.current++;stopAll();job.current=null;finished.current=true;setPhase('idle');setHeard(null)},[])
  useEffect(()=>reset,[reset])
  // Phase one (describing the alert) and phase two (the yes or no) both keep the microphone open and read words as they come.
  const configure=recognition=>{recognition.lang=speechLang(getLanguage());recognition.interimResults=true;recognition.maxAlternatives=3;recognition.continuous=true}
  const micProblem=event=>{
    if(event.error==='not-allowed'||event.error==='service-not-allowed'){setBlocked(true);setMessage(t('The microphone is not allowed. Use the five buttons.'));return true}
    return false
  }
  // Says the closing text when the device has a voice for the language; it is always shown on screen too.
  const say=text=>{if(text)speak(text,speechLang(getLanguage()))}
  const finish=useCallback(async answer=>{
    const current=job.current
    if(finished.current||!current)return
    finished.current=true;clearTimeout(timer.current);timer.current=null;stopMic();globalThis.speechSynthesis?.cancel?.()
    const id=session.current
    if(answer!=='yes'){setOutcome(current.notSent);setPhase('idle');setHeard(null);say(current.notSent);job.current=null;return}
    setPhase('sending')
    try{
      const place=await placeOfAlert(trip)
      const body={trip_id:trip.id,alert_type:current.alert_type,...place,source_input:'VOICE',confidence_score:current.confidence.toFixed(2),driver_confirmed:true}
      if(current.summary)body.summaries=current.summary   // what was understood, in every language: each listener hears their own
      const result=await api('/road-alerts',{method:'POST',body:JSON.stringify(body)})
      if(id!==session.current)return
      setHeard(null);setPhase('idle');job.current=null
      onSent(result,current.sent);say(current.sent)
    }catch(error){if(id===session.current){setHeard(null);setPhase('idle');job.current=null;onProblem(errorText(error))}}
  },[trip,onSent,onProblem])
  const wordsHeard=event=>{let all=''
    for(let i=0;i<(event.results?.length||0);i++)for(let j=0;j<(event.results[i]?.length||0);j++)all+=' '+(event.results[i][j]?.transcript||'')
    return all}
  // While the confirmation window is open, the microphone stays open (it is restarted if the browser ends it). A yes or no word, even half said, answers at once.
  const listenWindow=useCallback(id=>{
    const again=()=>{
      if(id!==session.current||finished.current)return
      const recognition=new Recognition();configure(recognition)
      recognition.onresult=event=>{
        const answer=answerOf(wordsHeard(event),job.current?.yes,job.current?.no)
        if(answer)finish(answer)
      }
      recognition.onerror=event=>{if(micProblem(event)){recognizer.current=null}}
      recognition.onend=()=>{if(recognizer.current===recognition){recognizer.current=null;setTimeout(again,120)}}
      recognizer.current=recognition
      try{recognition.start()}catch{recognizer.current=null}
    }
    again()
  },[Recognition,finish])
  const understand=useCallback(async(id,transcript,recognised)=>{
    setPhase('classifying')
    try{
      const result=await api('/road-alerts/voice-classify',{method:'POST',body:JSON.stringify({transcript:transcript.slice(0,300),language:getLanguage()})})
      if(id!==session.current)return
      if(!result.alert_type){setPhase('idle');setMessage(result.message||'');speak(result.message,'en-US');onUnclear();return}
      // The window is at least 15 seconds: the app has just spoken a whole sentence, and the answer is one word.
      const seconds=Math.max(15,Number(result.confirm_seconds)>0?Number(result.confirm_seconds):CONFIRM_SECONDS)
      job.current={alert_type:result.alert_type,summary:result.summary||null,confidence:recognised??(Number(result.confidence)||0),yes:result.yes_words||[],no:result.no_words||[],sent:result.sent_text||t('Alert sent.'),notSent:result.not_sent_text||t('Alert not sent.')}
      finished.current=false
      setHeard({prompt:result.confirm_prompt,seconds,listening:false});setPhase('confirm')
      let begun=false
      const begin=()=>{
        if(begun||id!==session.current||finished.current)return
        begun=true;setHeard(h=>h&&({...h,listening:true}))
        timer.current=setTimeout(()=>finish('timeout'),seconds*1000)
        listenWindow(id)
      }
      // The app says what it understood and asks; it listens as soon as the speech ends (or at once when this device has no voice for the language).
      if(!speak(result.confirm_prompt,speechLang(getLanguage()),{onEnd:begin}))begin()
    }catch(error){if(id===session.current){setPhase('idle');onProblem(errorText(error))}}
  },[finish,listenWindow,onUnclear,onProblem])
  // One press: the Driver speaks as long as needed (the app waits for a short pause), hears what was understood, says yes. No second press.
  const start=useCallback(()=>{
    if(!Recognition||phase!=='idle'||blocked)return
    const id=++session.current
    setMessage('');setOutcome('');setPhase('listening')
    const recognition=new Recognition();configure(recognition)
    let got=false,text='',confidence=null,quiet=null,limit=null
    const settle=()=>{
      if(got||id!==session.current)return
      got=true;clearTimeout(quiet);clearTimeout(limit);recognizer.current=null;try{recognition.abort()}catch{/* Already stopped. */}
      if(!text.trim()){setPhase('idle');setMessage(t('We did not hear anything. Try again or use the buttons.'));return}
      understand(id,text.trim(),confidence)
    }
    recognition.onresult=event=>{
      if(got||id!==session.current)return
      let all='',best=null
      for(let i=0;i<event.results.length;i++){const first=event.results[i][0];all+=' '+(first?.transcript||'');if(event.results[i].isFinal&&Number.isFinite(first?.confidence))best=first.confidence}
      text=all;confidence=best
      clearTimeout(quiet);quiet=setTimeout(settle,1700)   // a pause of about two seconds after words means the Driver has finished
    }
    recognition.onerror=event=>{
      if(micProblem(event)){recognizer.current=null;clearTimeout(quiet);clearTimeout(limit);setPhase('idle');return}
      if(event.error==='aborted')return
      if(event.error==='no-speech'){return}   // keep waiting: the limit below ends it
      recognizer.current=null;clearTimeout(quiet);clearTimeout(limit);setPhase('idle');setMessage(t('Voice did not work. Use the five buttons.'))
    }
    recognition.onend=()=>{if(recognizer.current===recognition&&!got){if(text.trim())settle();else{recognizer.current=null;clearTimeout(limit);setPhase('idle');setMessage(t('We did not hear anything. Try again or use the buttons.'))}}}
    limit=setTimeout(settle,20000)   // never listen for more than twenty seconds
    recognizer.current=recognition
    try{recognition.start()}catch{recognizer.current=null;clearTimeout(limit);setPhase('idle');setMessage(t('Voice did not work. Use the five buttons.'))}
  },[Recognition,phase,blocked,understand])
  return {supported:Boolean(Recognition),blocked,phase,heard,message,outcome,start,cancel:reset,send:()=>finish('yes'),decline:()=>finish('no')}
}

/* Countdown ring: it starts when the app starts listening, and runs for confirm_seconds. */
function Countdown({seconds,live}){
  const [left,setLeft]=useState(seconds)
  useEffect(()=>{
    if(!live)return undefined
    setLeft(seconds)
    const timerId=setInterval(()=>setLeft(n=>Math.max(0,n-1)),1000)
    return()=>clearInterval(timerId)
  },[live,seconds])
  return <span className={'ra-ring'+(live?' is-live':'')} style={{'--ra-seconds':seconds+'s'}} role="timer" aria-label={t('{value0} seconds left',{value0:left})}>
    <svg viewBox="0 0 56 56" width="56" height="56" aria-hidden="true"><circle className="ra-ring-track" cx="28" cy="28" r="24"/><circle className="ra-ring-run" cx="28" cy="28" r="24"/></svg><b>{left}</b></span>
}

function useMatchMedia(query){
  const get=()=>typeof window!=='undefined'&&typeof window.matchMedia==='function'&&window.matchMedia(query).matches
  const [value,setValue]=useState(get)
  useEffect(()=>{
    if(typeof window==='undefined'||typeof window.matchMedia!=='function')return undefined
    const media=window.matchMedia(query),on=()=>setValue(media.matches)
    on();media.addEventListener?.('change',on)
    return()=>media.removeEventListener?.('change',on)
  },[query])
  return value
}

/* An alert from another vehicle, shown on the Driver's screen like a Book now request: it stays for a short time; the Driver can have it
   read aloud or dismiss it. (With the speaker on it is spoken instead and this does not appear.) */
export function AlertPopup({alert,onClose,seconds=20}){
  const [left,setLeft]=useState(seconds),voice=hasVoice(speechLang(getLanguage()))
  useEffect(()=>{const timerId=setInterval(()=>setLeft(n=>n-1),1000);return()=>clearInterval(timerId)},[])
  useEffect(()=>{if(left<=0)onClose()},[left,onClose])
  return createPortal(<div className="ra-popup" role="alertdialog" aria-live="assertive" aria-label={alert.name||t('Road alerts')}>
    <div className="ra-popup-main"><strong><Icon name="alert" size={18}/>{alert.name||t('Road alerts')}</strong><p>{alert.text}</p></div>
    <div className="ra-popup-actions">
      {voice&&<button type="button" className="ui-button ui-button-primary" onClick={()=>speak(alert.text,speechLang(getLanguage()))}>{t('Read aloud')}</button>}
      <button type="button" className="ui-button ui-button-secondary" onClick={onClose}>{t('Cancel')}</button></div>
    <span className="ra-popup-bar" style={{'--ra-seconds':seconds+'s'}} aria-hidden="true"/>
  </div>,document.body)
}

/* The Driver's side column and alert strip around the live trip map (contract 03A and 03O, C). `renderMap` draws the map in the middle;
   `strip` sits above it; `extras` are more buttons for the side column (problem on the road, finish). `readOnly` is the Passenger's
   version: no alert buttons and no microphone, only the speaker switch. */
export function RoadAlertsPanel({trip,alerts,speaker,disabled,onOpenChange,onMenu=null,keepScreenOn=false,strip=null,renderMap=null,extras=null,readOnly=false}){
  const phone=useMatchMedia('(max-width: 767px)'),fullscreen=phone&&!readOnly&&Boolean(renderMap)
  const [selectedId,setSelectedId]=useState(null)
  const [open,setOpenState]=useState(false),[busy,setBusy]=useState(false),[notice,setNotice]=useState(''),[problem,setProblem]=useState(''),[votes,setVotes]=useState({})
  const setOpen=useCallback(value=>{setOpenState(value);onOpenChange&&onOpenChange(value)},[onOpenChange])
  const sent=useCallback((result,text)=>{
    setProblem('');setOpen(false)
    setNotice(result.merged?t('This alert was already up here. It counted as a confirmation.'):(text||t('Alert sent.')))
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
  useEffect(()=>{
    if(!fullscreen)return undefined
    const before=document.body.style.overflow;document.body.style.overflow='hidden'
    return()=>{document.body.style.overflow=before}
  },[fullscreen])
  const voiceBusy=voice.phase!=='idle'
  // The alert shown under the map: the one tapped on the map, otherwise the nearest one a Driver can still answer.
  const selected=alerts.items.find(item=>item.id===selectedId)||alerts.items.find(item=>item.can_vote)||null
  const voiceText=voice.phase==='listening'||(voice.phase==='confirm'&&voice.heard?.listening)?t('Listening…'):voice.phase==='classifying'?t('Checking what you said…'):voice.phase==='sending'?t('Sending…'):''
  const layout=<div className="ra-layout">
    <div className="ra-main">
      {strip}
      {!readOnly&&!voice.supported&&<p className="tk-line" role="status">{t('Voice is not available on this device. Use the five buttons.')}</p>}
      {keepScreenOn&&<p className="tk-line" role="status">{t('Keep the screen on during the trip so alerts and location keep working.')} {t('Tip: keep the phone on the charger.')}</p>}
      {voice.message&&<p className="tk-line is-warn" role="status">{voice.message}</p>}
      {voice.outcome&&<p className="tk-line" role="status">{voice.outcome}</p>}
      {notice&&<p className="tk-line" role="status">✓ {notice}</p>}
      {problem&&<p className="tk-line is-warn" role="alert">{problem}</p>}
      {(voiceText||busy)&&<p className="tk-line" role="status"><strong>{voiceText||t('Sending…')}</strong></p>}
      {voice.heard&&(voice.phase==='confirm'||voice.phase==='sending')&&<div className="tk-hold ra-confirm" role="alertdialog" aria-label={voice.heard.prompt}>
        <div className="ra-confirm-ask"><Countdown seconds={voice.heard.seconds} live={Boolean(voice.heard.listening)&&voice.phase==='confirm'}/><p className="tk-line"><strong>{voice.heard.prompt}</strong></p></div>
        <div className="ra-confirm-actions"><button type="button" className="ui-button ui-button-primary ra-big" disabled={voice.phase==='sending'} onClick={voice.send}>{t('Send')}</button><button type="button" className="ui-button ui-button-secondary ra-big" disabled={voice.phase==='sending'} onClick={voice.decline}>{t('Cancel')}</button></div></div>}
      {speaker.enabled&&speaker.textOnly&&<p className="tk-line" role="status">{t('This device has no voice for this language. Alerts are shown as text only.')}</p>}
      {renderMap&&<div className="ra-map">{renderMap({selectedId:selected?.id||null,onSelect:setSelectedId})}</div>}
      {renderMap&&alerts.error&&<p className="tk-line is-warn" role="status">{alerts.error.message}</p>}
      {renderMap&&selected&&(()=>{const item=selected,[tone,label]=STATUS[item.status]||['muted',codeEnglish(item.status)]
        return <article className="tk-row ra-item ra-info" aria-label={t('Road alerts near you')}>
          <div className="tk-row-main"><strong>{alertName(item,getLanguage())}</strong><span title={alertText(item,getLanguage())}>{alertText(item,getLanguage())}</span></div>
          <div className="tk-row-actions">{typeof item.distance_km==='number'&&<span className="tk-line">{t('{value0} km',{value0:item.distance_km})}</span>}<Chip tone={tone}>{t(label)}</Chip>
            {item.can_vote&&!readOnly&&<><button type="button" className="ui-button ui-button-secondary" disabled={votes[item.id]} onClick={()=>vote(item,'CONFIRM')}>{t('Still there')}</button><button type="button" className="ui-button ui-button-secondary" disabled={votes[item.id]} onClick={()=>vote(item,'DENY')}>{t('Not there')}</button></>}</div></article>})()}
      {!renderMap&&<div className="ra-list" aria-label={t('Road alerts near you')}>
        {alerts.error&&<p className="tk-line is-warn" role="status">{alerts.error.message}</p>}
        {alerts.items.length
          ?alerts.items.map(item=>{const [tone,label]=STATUS[item.status]||['muted',codeEnglish(item.status)]
            return <article className="tk-row ra-item" key={item.id}>
              <div className="tk-row-main"><strong>{alertName(item,getLanguage())}</strong><span title={alertText(item,getLanguage())}>{alertText(item,getLanguage())}</span></div>
              <div className="tk-row-actions">{typeof item.distance_km==='number'&&<span className="tk-line">{t('{value0} km',{value0:item.distance_km})}</span>}<Chip tone={tone}>{t(label)}</Chip>
                {item.can_vote&&<><button type="button" className="ui-button ui-button-secondary" disabled={votes[item.id]} onClick={()=>vote(item,'CONFIRM')}>{t('Still there')}</button><button type="button" className="ui-button ui-button-secondary" disabled={votes[item.id]} onClick={()=>vote(item,'DENY')}>{t('Not there')}</button></>}</div></article>})
          :alerts.loaded&&!alerts.error&&<p className="tk-line">{alerts.note||t('No road alerts near you.')}</p>}
      </div>}
    </div>
    <aside className={'ra-rail'+(open?' is-open':'')+(readOnly?' is-readonly':'')} aria-label={t('Road alert controls')}>
      {readOnly?<label className="ui-switch ra-speak" title={t('Speak road alerts')}><input type="checkbox" role="switch" checked={speaker.enabled} onChange={e=>speaker.setEnabled(e.target.checked)}/><span className="ui-switch-track" aria-hidden="true"/><span className="ra-speak-text">{t('Speak road alerts')}</span><Icon name={speaker.enabled?'volume':'mute'} size={22} className="ra-speak-icon" aria-hidden="true"/></label>:open
        ?<>
          <button type="button" className="ra-round ra-close" aria-label={t('Close')} onClick={()=>setOpen(false)}><Icon name="close" size={22}/></button>
          {ALERT_TYPES.map(([type,label,icon])=><button type="button" key={type} className="ra-type" disabled={busy||disabled} onClick={()=>report(type)}><Icon name={icon} size={26}/><span>{t(label)}</span></button>)}
        </>
        :<>
          <button type="button" className="ra-round ra-alert" aria-label={t('Report a road alert')} title={t('Report a road alert')} disabled={disabled||voiceBusy} onClick={()=>{setNotice('');setProblem('');setOpen(true)}}><Icon name="alert" size={30}/></button>
          {voice.supported&&!voice.blocked&&<button type="button" className={'ra-round ra-mic'+(voiceBusy?' is-live':'')} aria-label={voiceBusy?t('Stop listening'):t('Speak an alert')} title={voiceBusy?t('Stop listening'):t('Speak an alert')}
            disabled={disabled||busy} onClick={voiceBusy?voice.cancel:voice.start}><Icon name="mic" size={28}/></button>}
          <label className="ui-switch ra-speak" title={t('Speak road alerts')}><input type="checkbox" role="switch" checked={speaker.enabled} onChange={e=>speaker.setEnabled(e.target.checked)}/><span className="ui-switch-track" aria-hidden="true"/><span className="ra-speak-text">{t('Speak road alerts')}</span><Icon name={speaker.enabled?'volume':'mute'} size={22} className="ra-speak-icon" aria-hidden="true"/></label>
          {extras}
        </>}
    </aside>
  </div>
  // On a phone the live map takes the whole screen, like a navigation app; the controls sit over it. (Portal: nothing above it may clip or move it.)
  return fullscreen?createPortal(<div className="flow-page ra-fullscreen">
    {onMenu&&<button type="button" className="ra-menu" aria-label={t('Open workspace navigation')} onClick={onMenu}><Icon name="menu" size={24}/></button>}
    {layout}</div>,document.body):layout
}

export default function RoadAlerts(){
  return <StateCard icon="alert" title={t('Road alerts')} actions={<Link className="ui-button ui-button-primary" to="/driver/operate-trip">{t('Open an active trip')}</Link>}>
    <p>{t('Road alerts are available while you operate an active trip.')}</p>
  </StateCard>
}
