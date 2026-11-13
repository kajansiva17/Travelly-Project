import { t } from '../../i18n/language.js'
import React,{useEffect,useState} from 'react'
import {publicRead} from '../../services/api'
import Chip from '../../components/ui/Chip'
import {ratingOf} from './socialModel'

/* Star rating of a vehicle (contract 03SO, section 4): GET /social/vehicles/{id}/reviews, average_rating and rating_count, with the latest reviews.
   Nothing shows while there are no ratings or when the read fails (the vehicle page works without it). */
export default function VehicleRating({vehicleId}){
  const [data,setData]=useState(null)
  useEffect(()=>{let alive=true;publicRead(`/social/vehicles/${encodeURIComponent(vehicleId)}/reviews`).then(r=>alive&&setData(r)).catch(()=>alive&&setData(null));return()=>{alive=false}},[vehicleId])
  const count=Number(data?.rating_count||0)
  if(!data||!count)return null
  const latest=(data.items||[]).slice(0,2)
  return <div className="vr-rating">
    <Chip tone="info" icon="star" aria-label={t('{value0} out of 5 stars, {value1} ratings',{value0:data.average_rating,value1:count})}>{data.average_rating} ({count})</Chip>
    {latest.map(item=><span className="vr-review" key={item.id} title={item.caption}><span className="vr-stars" aria-hidden="true">{'★'.repeat(ratingOf(item))}</span> {item.caption}{item.author?.name?` — ${item.author.name}`:''}</span>)}
  </div>
}
