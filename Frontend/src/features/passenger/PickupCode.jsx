import { t } from '../../i18n/language.js'
import React,{useCallback,useEffect,useState} from 'react'
import {api} from '../../services/api'
import {ErrorNotice} from '../../components/components'
import {Button,InfoCallout} from '../../components/ui'
import {FlowBanner} from '../booking/flow/FlowParts'
import QrCode from '../../components/QrCode'

/* The Passenger's pickup code. The Driver scans it; if the scan fails they type the six digits.
   The code is never stored, so this shows the same one every time until a new one is asked for. */
const PIN_STYLE={display:'inline-block',marginLeft:10,fontSize:'1.6rem',fontWeight:800,letterSpacing:'.22em',color:'#121552'}

export default function PickupCode({tripId}){
  const [code,setCode]=useState(null),[error,setError]=useState(null),[busy,setBusy]=useState(false)
  const load=useCallback(async()=>{
    try{setCode(await api('/trips/'+tripId+'/pickup-code'));setError(null)}catch(e){setError(e)}
  },[tripId])
  useEffect(()=>{load()},[load])
  async function fresh(){
    setBusy(true);setError(null)
    try{setCode(await api(`/trips/${tripId}/pickup-code/reissue`,{method:'POST',body:'{}'}))}
    catch(e){setError(e)}finally{setBusy(false)}
  }
  if(error)return <ErrorNotice error={error}/>
  if(!code)return null
  if(code.verified_at)return <FlowBanner tone="success" icon="check" title={t('Pickup checked')}>
    {t('Your Driver checked this code. Have a good trip.')}</FlowBanner>
  return <section className="pickup-code" style={{display:'grid',justifyItems:'center',gap:10}}>
    <h3 style={{margin:0}}>{t('Show this to your Driver at pickup')}</h3>
    <QrCode value={code.qr_token} label={t('Pickup QR code')}/>
    <p style={{margin:0}}>{t('If it will not scan, read out')}<strong style={PIN_STYLE}>{code.pin}</strong></p>
    <Button variant="secondary" disabled={busy} onClick={fresh}>{busy?t('Getting a new code…'):t('Get a new code')}</Button>
    <InfoCallout>{t('Only your assigned Driver can check this code. A new code stops the old one working.')}</InfoCallout>
  </section>
}
