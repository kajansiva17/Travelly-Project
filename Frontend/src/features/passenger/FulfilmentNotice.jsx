import { t } from '../../i18n/language.js'
import React,{useEffect,useState} from 'react'
import {api} from '../../services/api'
import Chip from '../../components/ui/Chip'
import {isRefundNotice,isReplacementInfo,noticeBookingId} from '../notifications/notices'

// REPLACEMENT and REFUND notices of a protected-fulfilment departure (contract 03F2 and 03N) for ONE booking, read from GET /notifications.
// A notice is recognised by its notification_type and booking (booking_id or action_payload.booking_id), never by its wording.
// A REPLACEMENT that needs an answer (action_required) is the change card, not a notice. Nothing is shown that the API did not return.
export default function FulfilmentNotice({bookingId,version}){
  const [notes,setNotes]=useState([])
  useEffect(()=>{
    let alive=true
    api('/notifications').then(r=>{if(alive)setNotes((r.items||[]).filter(n=>noticeBookingId(n)===bookingId&&(isReplacementInfo(n)||isRefundNotice(n))).slice(0,2))}).catch(()=>{})
    return ()=>{alive=false}
  },[bookingId,version])
  if(!notes.length)return null
  return <div className="tk-notices">{notes.map(n=>{const kind=n.notification_type
    return <p className="tk-line tk-notice" key={n.id} role="status">
      <Chip tone={kind==='REPLACEMENT'?'info':'success'} icon={kind==='REPLACEMENT'?'route':'wallet'}>{kind==='REPLACEMENT'?t('Journey being arranged'):t('Refund')}</Chip>
      <span><strong>{n.title}</strong> {n.body} {kind==='REPLACEMENT'?t('You do not need to do anything.'):t('The refund status is shown below.')}</span></p>})}</div>
}
