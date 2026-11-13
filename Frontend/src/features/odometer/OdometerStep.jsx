import { t } from '../../i18n/language.js'
import React,{useCallback,useEffect,useRef,useState} from 'react'
import {api} from '../../services/api'
import {fieldErrorText} from '../../services/fieldErrors.js'
import {FormField,Input} from '../../components/ui'
import {Icon} from '../../components/components'
import {belowMinimum,buildPhotoForm,cameraAvailable,formatKm,outcomeOf,validKm} from './odometerFlow'

/* The odometer step before Start and Finish (contract 03O, A and B): the typed reading and a live photo of the odometer taken with the
   in-app camera only (no file picker, no gallery), sent with the time and the GPS position. The server compares the photo with the number.
   Start or Finish opens only when the server says can_continue. `onReady(km)` gives the proven reading (or null while there is none). */
const LONG_EDGE=1600
const CAMERA_TEXT='The camera is not available. Allow the camera to take the odometer photo.'
const LOCATION_TEXT='Allow this page to use your location so the photo can be sent with its position.'

// Live preview from the back camera and a capture button. The frame is drawn on a canvas and sent as a JPEG.
function CameraDialog({onCapture,onClose,onUnavailable}){
  const dialog=useRef(null),video=useRef(null),stream=useRef(null),[ready,setReady]=useState(false)
  useEffect(()=>{
    dialog.current?.showModal()
    let stopped=false
    navigator.mediaDevices.getUserMedia({video:{facingMode:'environment'},audio:false}).then(media=>{
      if(stopped){media.getTracks().forEach(track=>track.stop());return}
      stream.current=media
      if(video.current){video.current.srcObject=media;video.current.play().catch(()=>{})}
      setReady(true)
    }).catch(()=>{if(!stopped)onUnavailable()})
    return()=>{stopped=true;stream.current?.getTracks().forEach(track=>track.stop());stream.current=null;try{dialog.current?.close()}catch{/* Already closed. */}}
  },[])
  function capture(){
    const element=video.current
    if(!element||!element.videoWidth)return
    const scale=Math.min(1,LONG_EDGE/Math.max(element.videoWidth,element.videoHeight))
    const canvas=document.createElement('canvas');canvas.width=Math.round(element.videoWidth*scale);canvas.height=Math.round(element.videoHeight*scale)
    canvas.getContext('2d').drawImage(element,0,0,canvas.width,canvas.height)
    canvas.toBlob(blob=>{if(blob)onCapture(blob)},'image/jpeg',0.85)
  }
  return <dialog ref={dialog} className="odo-camera" aria-label={t('Odometer photo')} onClose={onClose} onCancel={onClose}>
    <div className="odo-camera-box">
      <video ref={video} playsInline muted aria-label={t('Camera preview')}/>
      <div className="odo-camera-actions"><button type="button" className="ui-button ui-button-secondary odo-big" onClick={()=>dialog.current?.close()}>{t('Cancel')}</button>
        <button type="button" className="ui-button ui-button-primary odo-big" disabled={!ready} onClick={capture}><Icon name="eye" size={20}/>{t('Capture')}</button></div>
    </div>
  </dialog>
}

export default function OdometerStep({tripId,stage,onReady,fieldError}){
  const [session,setSession]=useState(null),[sessionError,setSessionError]=useState(''),[typed,setTyped]=useState(''),[result,setResult]=useState(null),[problem,setProblem]=useState(''),[camera,setCamera]=useState(false),[sending,setSending]=useState(false)
  const positionRef=useRef(null),used=useRef(false),input=useRef(null)
  const openSession=useCallback(async()=>{
    const next=await api(`/trips/${tripId}/odometer-session`,{method:'POST',body:JSON.stringify({stage})})
    setSession(next);used.current=false;return next
  },[tripId,stage])
  useEffect(()=>{openSession().catch(error=>setSessionError(fieldErrorText(error,t('The odometer step could not be opened. Please try again.'))))},[openSession])

  const clean=typed.trim(),valid=validKm(clean),low=belowMinimum(clean,session?.minimum_km)
  const noPhotoNeeded=session?.photo_required===false
  const outcome=result?outcomeOf(result):null
  // The proven reading: the photo result must belong to the number that is in the box now.
  const proven=noPhotoNeeded?valid&&!low:Boolean(outcome?.canStart&&valid&&Number(result.typed_km)===Number(clean))
  useEffect(()=>{onReady&&onReady(proven?clean:null)},[proven,clean])

  const change=value=>{setTyped(value);setProblem('');if(result)setResult(null)}
  const position=()=>new Promise((resolve,reject)=>{
    if(!navigator.geolocation){reject(new Error('no-location'));return}
    navigator.geolocation.getCurrentPosition(p=>resolve({latitude:p.coords.latitude.toFixed(6),longitude:p.coords.longitude.toFixed(6),accuracy:p.coords.accuracy}),()=>reject(new Error('no-location')),{enableHighAccuracy:true,timeout:10000,maximumAge:0})
  })
  async function takePhoto(){
    setProblem('')
    if(!cameraAvailable()){setProblem(t(CAMERA_TEXT));return}
    // Location is asked for at the same time as the camera opens; each photo needs its own capture code.
    positionRef.current=position();positionRef.current.catch(()=>{})
    try{if(!session||used.current)await openSession()}catch(error){setProblem(fieldErrorText(error,t('The odometer step could not be opened. Please try again.')));return}
    setCamera(true)
  }
  async function send(blob){
    setCamera(false);setSending(true);setProblem('')
    try{
      let place
      try{place=await positionRef.current}catch{setProblem(t(LOCATION_TEXT));return}
      used.current=true
      const response=await api(`/trips/${tripId}/odometer-photo`,{method:'POST',body:buildPhotoForm({captureCode:session.capture_code,stage,typedKm:clean,position:place,blob})})
      setResult(response);setSession(s=>s&&({...s,tries_unreadable:response.tries_unreadable??s.tries_unreadable}))
    }catch(error){
      if(error.code==='CAPTURE_CODE_INVALID'){used.current=true;setProblem('');setSending(false);await takePhoto();return}   // the code ran out or was used: open the camera again
      if(error.code==='NOT_AT_PICKUP'){setProblem(t('Take the start photo at the pickup point.'));return}
      setProblem(fieldErrorText(error,t('The photo could not be sent. Please try again.')))
    }finally{setSending(false)}
  }
  const retake=()=>{setResult(null);takePhoto()}
  const editNumber=()=>{setResult(null);setTimeout(()=>input.current?.focus(),0)}

  const minimum=session?.minimum_km
  const hint=minimum!=null&&minimum!==''?t('Last recorded: {value0} km',{value0:formatKm(minimum)}):undefined
  return <div className="odo-step">
    {sessionError&&<p className="tk-line is-warn" role="alert">{sessionError}</p>}
    <div className="odo-row">
      <FormField label={t('Odometer reading')} required error={fieldError||(low?' ':undefined)} hint={hint}>
        {({id})=><Input id={id} ref={input} inputMode="decimal" autoComplete="off" value={typed} aria-invalid={low||undefined} onChange={e=>change(e.target.value.replace(/[^0-9.]/g,'').slice(0,12))}/>}
      </FormField>
      {!noPhotoNeeded&&(!result||outcome?.kind==='match'||outcome?.kind==='not-checked'||outcome?.kind==='unreadable-final')
        ?<button type="button" className="ui-button ui-button-secondary odo-take" disabled={!valid||low||!session||sending} onClick={takePhoto}><Icon name="eye" size={18}/>{sending?t('Sending…'):result?t('Retake'):t('Take photo')}</button>
        :null}
    </div>
    {!valid&&clean&&<p className="tk-line is-warn" role="status">{t('Type the reading with at most one decimal.')}</p>}
    {outcome&&<div className={'odo-result is-'+outcome.tone} role="status">
      {outcome.kind==='match'&&<strong>{t('Photo matches ✓')}</strong>}
      {outcome.kind==='mismatch'&&<><strong>{t('Photo: {value0} • You typed: {value1}',{value0:formatKm(outcome.readKm),value1:formatKm(outcome.typedKm)})}</strong>{result.message&&<span>{result.message}</span>}</>}
      {(outcome.kind==='unreadable'||outcome.kind==='unreadable-final')&&<strong>{outcome.kind==='unreadable'?t("Couldn't read the photo (try {value0} of {value1}). Move closer, turn on the light.",{value0:outcome.tries,value1:outcome.allowed}):t('Start with the typed number')}</strong>}
      {outcome.kind==='not-checked'&&<strong>{t('Photo saved as proof')}</strong>}
      {(outcome.retake||outcome.editNumber)&&<div className="odo-actions">{outcome.retake&&<button type="button" className="ui-button ui-button-primary" onClick={retake}>{t('Retake')}</button>}{outcome.editNumber&&<button type="button" className="ui-button ui-button-secondary" onClick={editNumber}>{t('Edit number')}</button>}</div>}
    </div>}
    {problem&&<p className="tk-line is-warn" role="alert">{problem}</p>}
    {camera&&<CameraDialog onCapture={send} onClose={()=>setCamera(false)} onUnavailable={()=>{setCamera(false);setProblem(t(CAMERA_TEXT))}}/>}
  </div>
}
