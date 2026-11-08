import { t } from '../i18n/language.js'
import React,{useEffect,useState} from 'react'
import {api,mediaUrl} from '../services/api'
import {ErrorNotice} from './components'

export default function VehiclePhoto({photo,privatePreview=false,alt='Vehicle photo'}){
  const [url,setUrl]=useState(null),[error,setError]=useState(null)
  const variants=photo?.variants||[],first=variants[0]
  useEffect(()=>{if(!privatePreview||!first)return;let active=true,object;setUrl(null);setError(null);api(first.url.replace('/api/v1',''),{binary:true}).then(blob=>{object=URL.createObjectURL(blob);if(active)setUrl(object);else URL.revokeObjectURL(object)}).catch(e=>{if(active)setError(e)});return()=>{active=false;if(object)URL.revokeObjectURL(object)}},[first?.url,privatePreview])
  if(!first)return null
  if(privatePreview)return <><ErrorNotice error={error}/>{url?<img className="vehicle-photo" src={url} alt={alt} width={first.width} height={first.height} loading="lazy" decoding="async"/>:!error&&<p>{t("Loading protected photo…")}</p>}</>
  const unique=[...new Map(variants.map(v=>[v.width,v])).values()]
  return <img className="vehicle-photo" src={mediaUrl(first.url)} srcSet={unique.map(v=>`${mediaUrl(v.url)} ${v.width}w`).join(', ')} sizes="(max-width:767px) calc(100vw - 64px), 480px" alt={alt} width={first.width} height={first.height} loading="lazy" decoding="async"/>
}
