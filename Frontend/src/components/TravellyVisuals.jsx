import { t } from '../i18n/language.js'
import React from 'react'
import manifest from '../assets/travelly/manifest.json'

export function TravellyAsset({name,alt='',className='',eager=false,sizes='(max-width: 767px) 100vw, 50vw',...props}){
 const variants=manifest[name]
 if(!variants)return null
 const largest=variants.at(-1)
 return <img className={className} src={largest.src} srcSet={variants.map(v=>`${v.src} ${v.width}w`).join(', ')} sizes={sizes} width={largest.width} height={largest.height} alt={alt} loading={eager?'eager':'lazy'} fetchPriority={eager?'high':'auto'} decoding="async" {...props}/>
}

// Counts describe returned booking records, never synthetic trends or earnings.
export function BookingPipeline({items}){
 const groups=[['Requested',['REQUESTED']],['Awaiting driver',['AWAITING_DRIVER','OWNER_ACTION_REQUIRED']],['Confirmed',['CONFIRMED']],['On trip',['IN_PROGRESS']],['Completed',['COMPLETED']]]
 const counts=groups.map(([,statuses])=>items.filter(b=>statuses.includes(b.status)).length),maximum=Math.max(1,...counts)
 return <figure className="booking-pipeline"><figcaption>{t("Booking status across the latest returned records")}</figcaption><div className="pipeline-columns" style={{'--pipeline-max':maximum}}>{groups.map(([label],i)=><div className="pipeline-row" key={label}><strong>{counts[i]}</strong><div className="pipeline-track"><span style={{height:`${counts[i]/maximum*100}%`}}/></div><span>{t(label)}</span></div>)}</div><p>{t("Current records, not a revenue or historical trend forecast.")}</p></figure>
}
