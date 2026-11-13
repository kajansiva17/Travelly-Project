import { t } from '../../i18n/language.js'
import React,{useEffect,useRef,useState} from 'react'
import {api} from '../../services/api'
import {fieldErrorText} from '../../services/fieldErrors.js'
import Chip from '../../components/ui/Chip'
import {formatKm,photoPath,photoShown,proofBadge} from './odometerFlow'

/* "Trip distance" proof card (contract 03O, E): start km, end km and the distance, with the two photos. Shown on the Passenger booking
   (private hire), the Owner booking and the Admin booking. The photos are private: each is fetched with the sign-in token as a blob and
   shown from an object URL, which is revoked when the card closes. After the keep days the photos are deleted and only the numbers stay. */
const BADGE_TONE={success:'success',warn:'danger',muted:'muted',danger:'danger'}

function Photo({side,label,onOpen,urls,failed}){
  const [tone,badge]=proofBadge(side?.result),shown=photoShown(side)
  return <figure className="odo-photo">
    <figcaption><strong>{label}</strong>{side&&<Chip tone={BADGE_TONE[tone]||'muted'}>{t(badge)}</Chip>}</figcaption>
    {shown?(urls[label]?<button type="button" className="odo-thumb" onClick={()=>onOpen(label)} aria-label={t('Enlarge the {value0} photo',{value0:label})}><img src={urls[label]} alt={t('Odometer photo, {value0}',{value0:label})}/></button>
      :<div className="odo-thumb is-empty">{failed[label]?t('The photo could not be loaded.'):t('Loading…')}</div>)
      :<div className="odo-thumb is-empty">{side?t('No photo kept'):'—'}</div>}
    {side&&<small>{formatKm(side.reading_km)} {t('km')}</small>}
  </figure>
}

export default function OdometerProofCard({tripId}){
  const [proof,setProof]=useState(null),[error,setError]=useState(''),[urls,setUrls]=useState({}),[failed,setFailed]=useState({}),[open,setOpen]=useState(null),big=useRef(null)
  useEffect(()=>{
    let alive=true
    setProof(null);setError('');setUrls({});setFailed({})
    api(`/trips/${tripId}/odometer-proof`,{cache:'no-store'}).then(result=>{if(alive)setProof(result)}).catch(e=>{if(alive)setError(fieldErrorText(e,t('The trip distance could not be loaded.')))})
    return()=>{alive=false}
  },[tripId])
  // Fetch each available photo as a blob; revoke the object URLs when the card closes or the proof changes.
  useEffect(()=>{
    if(!proof)return undefined
    let alive=true;const made=[]
    for(const [label,side] of [[t('Start'),proof.start],[t('End'),proof.end]]){
      if(!photoShown(side))continue
      api(photoPath(side.photo_url),{binary:true}).then(blob=>{if(!alive)return;const url=URL.createObjectURL(blob);made.push(url);setUrls(u=>({...u,[label]:url}))}).catch(()=>{if(alive)setFailed(f=>({...f,[label]:true}))})
    }
    return()=>{alive=false;made.forEach(url=>URL.revokeObjectURL(url))}
  },[proof])
  useEffect(()=>{if(open&&big.current&&!big.current.open)big.current.showModal()},[open])
  if(error)return <p className="tk-line is-warn" role="alert">{error}</p>
  if(!proof)return <p role="status">{t('Loading…')}</p>
  const startLabel=t('Start'),endLabel=t('End'),anyPhoto=photoShown(proof.start)||photoShown(proof.end)
  return <section className="odo-proof" aria-label={t('Trip distance')}>
    <h3>{t('Trip distance')}</h3>
    <dl className="odo-numbers">
      <div><dt>{t('Start')}</dt><dd>{formatKm(proof.start?.reading_km)} {t('km')}</dd></div>
      <div><dt>{t('End')}</dt><dd>{formatKm(proof.end?.reading_km)} {t('km')}</dd></div>
      <div><dt>{t('Distance')}</dt><dd><strong>{formatKm(proof.distance_km)} {t('km')}</strong></dd></div>
    </dl>
    <div className="odo-photos"><Photo side={proof.start} label={startLabel} onOpen={setOpen} urls={urls} failed={failed}/><Photo side={proof.end} label={endLabel} onOpen={setOpen} urls={urls} failed={failed}/></div>
    {!anyPhoto&&<p className="tk-line">{t('Photos are kept for {value0} days after the trip',{value0:proof.photos_kept_days??7})}</p>}
    <dialog ref={big} className="odo-big-photo" aria-label={t('Odometer photo')} onClose={()=>setOpen(null)} onClick={e=>{if(e.target===big.current)big.current.close()}}>
      {open&&urls[open]&&<><img src={urls[open]} alt={t('Odometer photo, {value0}',{value0:open})}/><button type="button" className="ui-button ui-button-primary" onClick={()=>big.current.close()}>{t('Close')}</button></>}
    </dialog>
  </section>
}
