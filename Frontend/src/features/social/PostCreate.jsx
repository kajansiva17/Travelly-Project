import { t } from '../../i18n/language.js'
import {useEffect,useRef,useState} from 'react'
import {useLocation} from 'react-router-dom'
import {useNavigate} from '../passenger/travelRouter'
import {api,uploadForm} from '../../services/api'
import {Header,Icon} from '../../components/components'
import EmptyState from '../../components/ui/EmptyState'
import {Field,Compact,RateErrors} from '../owner/OwnerRates'
import {FlowShell} from '../booking/flow/FlowParts'
import {fieldErrorMap,fieldErrorText} from '../../services/fieldErrors.js'
import {LIMITS,POST_TYPES,VIDEO_TYPES,buildPostForm,checkDuration,checkVideoFile,problems,thumbSize} from './postModel'
import {VISIBILITY,parseTags,sharePath} from './socialModel'

/* "+ Post" (contract 03SO, section 1): pick Reel / Photo / Review, add the media, then caption, place, hashtags and who can see it.
   A Reel's length is read in the browser (over 60 seconds or 50 MB is refused, nothing is uploaded) and a frame is captured on a canvas
   as the thumbnail. One upload at a time, with progress and Cancel. Posts are public at once. */
const STEPS=['Choose the kind','Add the media','Words and sharing']
const BLANK={also_share:true,post_type:'',visibility:'PUBLIC',file:null,thumbnail:null,duration:0,caption:'',hashtags:'',location_name:'',linked_vehicle_id:'',rating:0}

// Reads the video's length and grabs one frame as a JPEG. Resolves {duration, thumbnail|null}; rejects when the file cannot be read.
function readVideo(file){
  return new Promise((resolve,reject)=>{
    const url=URL.createObjectURL(file),video=document.createElement('video')
    video.preload='metadata';video.muted=true;video.playsInline=true
    const done=(fn,value)=>{URL.revokeObjectURL(url);fn(value)}
    video.onerror=()=>done(reject,new Error('unreadable'))
    video.onloadedmetadata=()=>{
      const duration=video.duration
      if(checkDuration(duration))return done(resolve,{duration,thumbnail:null})   // too long or unreadable: no frame needed
      video.onseeked=()=>{
        try{
          const {width,height}=thumbSize(video.videoWidth,video.videoHeight),canvas=document.createElement('canvas')
          canvas.width=width;canvas.height=height;canvas.getContext('2d').drawImage(video,0,0,width,height)
          canvas.toBlob(blob=>done(resolve,{duration,thumbnail:blob}),'image/jpeg',0.82)
        }catch{done(resolve,{duration,thumbnail:null})}
      }
      video.currentTime=Math.min(1,duration/2)
    }
    video.src=url
  })
}

function Stars({value,onChange,disabled}){
  return <div className="pc-stars" role="radiogroup" aria-label={t('Rating')}>{[1,2,3,4,5].map(n=><button type="button" key={n} role="radio" aria-checked={value===n} aria-label={t('{value0} out of 5 stars',{value0:n})} disabled={disabled} className={n<=value?'is-on':''} onClick={()=>onChange(n)}>★</button>)}</div>
}

export default function PostCreate(){
  const navigate=useNavigate(),[v,setV]=useState(BLANK),[step,setStep]=useState(0),[note,setNote]=useState(''),[errors,setErrors]=useState({}),[preview,setPreview]=useState('')
  const [mine,setMine]=useState([]),[vehicles,setVehicles]=useState(null),[reading,setReading]=useState(false),[progress,setProgress]=useState(null),[busy,setBusy]=useState(false),controller=useRef(null),sending=useRef(false)
  const set=patch=>setV(c=>({...c,...patch}))
  useEffect(()=>()=>{controller.current?.abort()},[])
  useEffect(()=>()=>{if(preview)URL.revokeObjectURL(preview)},[preview])
  useEffect(()=>{if(v.post_type!=='REVIEW'||vehicles)return;api('/social/me/reviewable-vehicles',{cache:'no-store'}).then(r=>setVehicles(r.items||[])).catch(e=>{setVehicles([]);setNote(fieldErrorText(e))})},[v.post_type])

  useEffect(()=>{if(v.post_type==='REVIEW'||!v.post_type||step<2)return;api('/owners/me/vehicles',{cache:'no-store'}).then(r=>setMine((r.items||[]).filter(x=>x.verification_status==='APPROVED'||!x.verification_status))).catch(()=>setMine([]))},[v.post_type,step])
  const place=useLocation(),[done,setDone]=useState(null),canShare=typeof navigator!=='undefined'&&typeof navigator.share==='function'
  const kind=type=>{set({...BLANK,post_type:type,visibility:v.visibility});setPreview('');setNote('');setErrors({});setStep(1)}
  useEffect(()=>{const ask=new URLSearchParams(place.search).get('type');if(['REEL','PHOTO','REVIEW'].includes(ask))kind(ask)},[])
  async function chooseFile(e){
    const file=e.target.files?.[0];e.target.value='';if(!file)return
    setNote('');setErrors({});setPreview('')
    if(v.post_type==='PHOTO'||v.post_type==='REVIEW'){set({file});setPreview(URL.createObjectURL(file));return}
    const bad=checkVideoFile(file)
    if(bad==='TOO_LARGE'){set({file:null,thumbnail:null,duration:0});setNote(t('The video can be {value0} MB at most.',{value0:LIMITS.reelMb}));return}
    if(bad==='WRONG_TYPE'){set({file:null,thumbnail:null,duration:0});setNote(t('Choose an MP4, MOV or WebM video.'));return}
    setReading(true)
    try{
      const {duration,thumbnail}=await readVideo(file),over=checkDuration(duration)
      if(over==='TOO_LONG'){set({file:null,thumbnail:null,duration:0});setNote(t('Trim to 60 seconds'));return}
      if(over){set({file:null,thumbnail:null,duration:0});setNote(t('This video could not be read.'));return}
      set({file,thumbnail,duration});if(thumbnail)setPreview(URL.createObjectURL(thumbnail))
    }catch{set({file:null,thumbnail:null,duration:0});setNote(t('This video could not be read.'))}
    finally{setReading(false)}
  }
  async function send(){
    if(sending.current)return            // one submit per press
    sending.current=true;setBusy(true);setProgress(0);setNote('');setErrors({})
    controller.current=new AbortController()
    try{
      const post=await uploadForm('/social/posts',buildPostForm(v),{onProgress:setProgress,signal:controller.current.signal})
      if(v.also_share&&v.visibility==='PUBLIC'&&canShare)setDone({post,file:v.file,caption:v.caption})
      else navigate(`/reels/${post.id}`)
    }catch(error){
      if(error.code==='UPLOAD_CANCELLED')setNote(t('The upload was cancelled.'))
      else{setErrors(fieldErrorMap(error));setNote(fieldErrorText(error,t('The post could not be sent. Please try again.')))}
    }finally{sending.current=false;setBusy(false);setProgress(null)}
  }
  // A phone's own share sheet is the way into WhatsApp Status, Instagram, Facebook and TikTok: those apps do not let a website post for you.
  // The sheet needs a fresh tap (an upload takes longer than the browser allows), so it opens from the button on the "Posted" screen.
  async function shareOut(){
    try{
      const r=await api(`/social/posts/${done.post.id}/share`,{method:'POST',body:JSON.stringify({})})
      const url=sharePath(window.location.origin,r.share_path),text=[done.caption,url].filter(Boolean).join('\n')
      const data={title:t('Travel Reels'),text,url}
      if(done.file&&navigator.canShare?.({files:[done.file]}))data.files=[done.file]
      await navigator.share(data)
    }catch(e){if(e?.name!=='AbortError')setNote(fieldErrorText(e,t('The post could not be sent. Please try again.')))}
  }
  const bad=problems(v),has=name=>bad.includes(name),tagCount=parseTags(v.hashtags).length
  const ready=bad.length===0
  const mediaOk=v.post_type==='REVIEW'?!has('linked_vehicle_id')&&!has('rating'):!has('file')
  const title=[t('What do you want to post?'),v.post_type==='REEL'?t('Choose a video'):v.post_type==='PHOTO'?t('Choose a photo'):t('Review a vehicle'),t('Words and sharing')][step]
  if(done)return <><Header/><FlowShell heading={t('Travel Reels')} icon="video" title={t('Posted')} steps={STEPS.map(x=>t(x))} current={2}>
    {note&&<p className="tk-line is-warn" role="alert">{note}</p>}
    <div className="tk-pane pc-done"><button type="button" className="ui-button ui-button-primary" onClick={shareOut}><Icon name="share" size={18}/>{t('Share to WhatsApp, Instagram, Facebook…')}</button>
      <button type="button" className="ui-button ui-button-secondary" onClick={()=>navigate(`/reels/${done.post.id}`)}>{t('View reel')}</button></div>
  </FlowShell></>
  return <><Header/><FlowShell heading={t('Travel Reels')} icon="video" title={title} steps={STEPS.map(x=>t(x))} current={step} onStepSelect={i=>{if(i<step&&!busy)setStep(i)}}>
    <Compact.Provider value={true}><RateErrors.Provider value={errors}>
    {note&&<p className="tk-line is-warn" role="alert">{note}</p>}
    {step===0&&<div className="pc-kinds tk-pane">{POST_TYPES.map(([code,label,icon])=><button type="button" key={code} className="pc-kind" onClick={()=>kind(code)}><Icon name={icon} size={30}/><strong>{t(label)}</strong></button>)}</div>}
    {step===1&&<div className="tk-pane pc-media">
      {v.post_type==='REVIEW'&&(vehicles===null?<p role="status">{t('Loading…')}</p>:!vehicles.length?<EmptyState icon="car" title={t('Only for a vehicle you travelled in on a completed trip.')}>{''}</EmptyState>
        :<div className="tk-grid" style={{'--cols':2}}>
          <Field label="Vehicle"><select name="linked_vehicle_id" value={v.linked_vehicle_id} onChange={e=>set({linked_vehicle_id:e.target.value})}><option value="">{t('Choose a vehicle')}</option>{vehicles.map(x=><option key={x.vehicle_id} value={x.vehicle_id}>{x.name}{x.already_reviewed?` (${t('already reviewed')})`:''}</option>)}</select></Field>
          <Field label="Rating"><Stars value={v.rating} onChange={rating=>set({rating})}/></Field></div>)}
      {(v.post_type!=='REVIEW'||vehicles?.length>0)&&<div className="pc-file">
        <label className="ui-button ui-button-secondary pc-pick"><Icon name={v.post_type==='REEL'?'video':'star'} size={18}/>{v.file?t('Choose another'):v.post_type==='REVIEW'?t('Add a photo (optional)'):v.post_type==='REEL'?t('Choose a video'):t('Choose a photo')}
          <input type="file" name="file" className="ui-sr-only" accept={v.post_type==='REEL'?VIDEO_TYPES.join(','):'image/*'} onChange={chooseFile} disabled={reading}/></label>
        {reading&&<span role="status">{t('Reading the video…')}</span>}
        {v.file&&!reading&&<span className="tk-line">{v.file.name} · {t('{value0} MB',{value0:(v.file.size/1048576).toFixed(1)})}{v.post_type==='REEL'?` · ${t('{value0} s',{value0:Math.round(v.duration)})}`:''}</span>}
        {preview&&<img className="pc-preview" src={preview} alt=""/>}
        {errors.file&&<small className="is-warn">{errors.file}</small>}
        {v.post_type==='REEL'&&<small className="tk-line">{t('Up to {value0} seconds and {value1} MB.',{value0:LIMITS.reelSeconds,value1:LIMITS.reelMb})}</small>}</div>}
      <div className="flow-actions"><button type="button" className="ui-button ui-button-secondary" onClick={()=>setStep(0)}>{t('Back')}</button><button type="button" className="ui-button ui-button-primary" disabled={!mediaOk||reading} onClick={()=>setStep(2)}>{t('Next')}</button></div></div>}
    {step===2&&<div className="tk-pane pc-details">
      <div className="tk-grid" style={{'--cols':2}}>
        <Field label="Caption" optional={v.post_type!=='REVIEW'} help="Words and #tags. Tags in the caption become hashtags."><textarea name="caption" rows={3} maxLength={LIMITS.caption} value={v.caption} onChange={e=>set({caption:e.target.value})} disabled={busy}/></Field>
        <div className="pc-side">
          <Field label="Place" optional><input name="location_name" maxLength={LIMITS.place} value={v.location_name} onChange={e=>set({location_name:e.target.value})} disabled={busy}/></Field>
          {mine.length>0&&<Field label="Vehicle in this post" optional help="Passengers can then hire it from your reel."><select name="linked_vehicle_id" value={v.linked_vehicle_id} onChange={e=>set({linked_vehicle_id:e.target.value})} disabled={busy}><option value="">{t('No vehicle')}</option>{mine.map(x=><option key={x.id} value={x.id}>{[x.make,x.model].filter(Boolean).join(' ')||x.registration_number||x.id}</option>)}</select></Field>}
          <Field label="Hashtags" optional help="Separate them with commas. Up to 30."><input name="hashtags" value={v.hashtags} onChange={e=>set({hashtags:e.target.value})} disabled={busy}/></Field>
          <Field label="Who can see it"><select name="visibility" value={v.visibility} onChange={e=>set({visibility:e.target.value})} disabled={busy}>{VISIBILITY.map(([value,label])=><option key={value} value={value}>{t(label)}</option>)}</select></Field></div></div>
      {canShare&&v.visibility==='PUBLIC'&&<label className="pc-also"><input type="checkbox" checked={v.also_share} onChange={e=>set({also_share:e.target.checked})} disabled={busy}/>{t('Also share to WhatsApp, Instagram, Facebook after posting')}</label>}
      {tagCount>LIMITS.hashtags&&<p className="tk-line is-warn" role="status">{t('Up to {value0} hashtags.',{value0:LIMITS.hashtags})}</p>}
      {busy&&<div className="pc-progress"><progress max="100" value={Math.round((progress||0)*100)} aria-label={t('Upload progress')}/><span>{Math.round((progress||0)*100)}%</span></div>}
      <div className="flow-actions">{busy?<button type="button" className="ui-button ui-button-secondary" onClick={()=>controller.current?.abort()}>{t('Cancel upload')}</button>:<button type="button" className="ui-button ui-button-secondary" onClick={()=>setStep(1)}>{t('Back')}</button>}
        <button type="button" className="ui-button ui-button-primary" disabled={busy||!ready} onClick={send}>{t('Post')}</button></div></div>}
    </RateErrors.Provider></Compact.Provider>
  </FlowShell></>
}
