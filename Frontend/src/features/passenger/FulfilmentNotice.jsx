import { t } from '../../i18n/language.js'
import React,{useEffect,useState} from 'react'
import {api} from '../../services/api'
import Chip from '../../components/ui/Chip'

// REPLACEMENT and REFUND notices of a protected-fulfilment departure (contract 03F2) for ONE booking, read from GET /notifications.
// That list does not carry notification_type, so a notice is recognised by its booking and by the exact title the server uses for it.
// Anything else in the list is ignored; nothing is shown that the API did not return.
const KINDS={
  'We are arranging your journey':'REPLACEMENT',
  'Departure cancelled - full refund':'REFUND',
  'Refund sent':'REFUND',
  'Booking cancelled':'REFUND'
}
export default function FulfilmentNotice({bookingId,version}){
  const [notes,setNotes]=useState([])
  useEffect(()=>{
    let alive=true
    api('/notifications').then(r=>{if(alive)setNotes((r.items||[]).filter(n=>n.booking_id===bookingId&&KINDS[n.title]).slice(0,2))}).catch(()=>{})
    return ()=>{alive=false}
  },[bookingId,version])
  if(!notes.length)return null
  return <div className="tk-notices">{notes.map(n=>{const kind=KINDS[n.title]
    return <p className="tk-line tk-notice" key={n.id} role="status">
      <Chip tone={kind==='REPLACEMENT'?'info':'success'} icon={kind==='REPLACEMENT'?'route':'wallet'}>{kind==='REPLACEMENT'?t('Journey being arranged'):t('Refund')}</Chip>
      <span><strong>{n.title}</strong> {n.body} {kind==='REPLACEMENT'?t('You do not need to do anything.'):t('The refund status is shown below.')}</span></p>})}</div>
}
