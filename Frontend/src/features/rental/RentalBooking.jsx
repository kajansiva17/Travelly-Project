import { t } from '../../i18n/language.js'
import React,{useRef,useState} from 'react'
import {Link} from 'react-router-dom'
import {api} from '../../services/api'
import Chip from '../../components/ui/Chip'
import {Checkbox} from '../../components/ui'
import {Field,RateErrors} from '../owner/OwnerRates'
import {FlowShell} from '../booking/flow/FlowParts'
import {money} from '../passenger/TicketCancel'
import {formatDate,formatDateTime} from '../../i18n/dateTime.js'
import {fieldErrorMap,fieldErrorText} from '../../services/fieldErrors.js'
import HirePayment from '../booking/HirePayment'
import OdometerStep from '../odometer/OdometerStep'
import OdometerProofCard from '../odometer/OdometerProofCard'
import {STATUS_CHIP,ownerSteps,renterConfirms,rentalOf} from './rentalModel'

/* A self-drive rental booking (contract 03RN): status, the rates the Owner had when it was asked, the estimate (before the return) or the final bill
   (after it), the Owner's steps (accept, decline, cancel, hand over, take back, each with a confirm step), the renter's confirmations, payment after
   COMPLETED and the odometer proof. Odometer photos use the existing 03O step on the rental trip (booking.trip.id). */
const km=value=>value==null||value===''?'—':`${Number(value).toLocaleString('en-LK',{maximumFractionDigits:1})} km`
const chip=status=>{const [tone,label]=STATUS_CHIP[status]||['muted',String(status||'').replaceAll('_',' ')];return <Chip tone={tone}>{t(label)}</Chip>}

function BillTable({price,label}){
  return <table className="rp-table rb-bill" aria-label={label}><thead><tr><th scope="col">{t('Charge')}</th><th scope="col">{t('Quantity')}</th><th scope="col">{t('Rate')}</th><th scope="col">{t('Amount')}</th></tr></thead>
    <tbody>{price.breakdown.map(row=><tr key={row.code}><td data-label={t('Charge')} data-top="1">{row.label}</td><td data-label={t('Quantity')}>{row.quantity}</td><td data-label={t('Rate')}>{money(price.currency,row.rate)}</td><td data-label={t('Amount')} data-top="1">{money(price.currency,row.amount)}</td></tr>)}</tbody>
    <tfoot><tr><th scope="row" colSpan={3}>{t('Total')}</th><td><strong>{money(price.currency,price.total)}</strong></td></tr></tfoot></table>
}

export default function RentalBooking({booking,user,personal=false,reload,backTo='/bookings',payReturn}){
  const rental=rentalOf(booking)||{},price=booking.price||{},owner=!personal&&booking.owner_user_id===user?.id,passenger=booking.passenger_user_id===user?.id
  const steps=ownerSteps(booking),confirms=renterConfirms(booking),tripId=booking.trip?.id
  const [tab,setTab]=useState(()=>payReturn?3:0),[pending,setPending]=useState(null),[reason,setReason]=useState(''),[note,setNote]=useState(''),[checked,setChecked]=useState(false),[reading,setReading]=useState(null)
  const [busy,setBusy]=useState(false),[message,setMessage]=useState({text:'',warn:false}),[errors,setErrors]=useState({}),sending=useRef(false)
  const terms=price.terms||{},estimate=price.estimate,final=price.final
  const hasProof=Boolean(tripId&&(passenger||owner)&&['IN_PROGRESS','COMPLETED'].includes(booking.status))
  const close=()=>{setPending(null);setReason('');setNote('');setChecked(false);setReading(null);setErrors({})}

  async function run(path,body,done){
    if(sending.current)return
    sending.current=true;setBusy(true);setMessage({text:'',warn:false});setErrors({})
    try{await api(path,{method:'POST',body:JSON.stringify(body)});close();setMessage({text:done,warn:false});await reload()}
    catch(error){setErrors(fieldErrorMap(error));setMessage({text:fieldErrorText(error),warn:true});if(error.code==='VERSION_CONFLICT')await reload()}
    finally{sending.current=false;setBusy(false)}
  }
  const v=booking.version,id=booking.id
  const go=(kind)=>{
    if(kind==='accept')return run(`/rentals/${id}/accept`,{expected_version:v},t('Rental accepted'))
    if(kind==='decline')return run(`/rentals/${id}/decline`,{expected_version:v,reason:reason.trim()},t('Rental declined'))
    if(kind==='cancel')return run(`/rentals/${id}/cancel`,{expected_version:v,reason:reason.trim()},t('Rental cancelled'))
    if(kind==='handover')return run(`/rentals/${id}/handover`,{expected_version:v,start_odometer_km:reading,licence_checked:true,...(note.trim()?{note:note.trim()}:{})},t('Rental started'))
    if(kind==='return')return run(`/rentals/${id}/return`,{expected_version:v,end_odometer_km:reading,...(note.trim()?{note:note.trim()}:{})},t('Rental completed'))
  }
  const needsReason=pending==='decline'||pending==='cancel'
  const label={accept:'Accept this rental',decline:'Decline',cancel:'Cancel this rental',handover:'Hand over the vehicle',return:'Take the vehicle back'}
  const confirmText={accept:'Accept this rental? The vehicle is reserved for these dates.',decline:'Decline this rental request?',cancel:'Cancel this rental? The vehicle is free again.',handover:'Record the handover?',return:'Record the return and work out the bill?'}
  const ready=pending==='handover'?Boolean(reading)&&checked:pending==='return'?Boolean(reading):needsReason?reason.trim().length>0:true

  const tabs=[['Rental','key'],['Price','wallet'],['Actions','check'],...(booking.status==='COMPLETED'&&(passenger||owner)?[['Payment','wallet']]:[]),...(hasProof?[['Trip distance','route']]:[])]
  const names=tabs.map(x=>x[0]),active=names[Math.min(tab,names.length-1)]
  const tabItems=tabs.map(([name,icon],i)=>({label:t(name),icon,active:active===name,onClick:()=>setTab(i)}))

  const actionList=<div className="rb-actions">
    {owner&&steps.accept&&pending!=='accept'&&!pending&&<button type="button" className="ui-button ui-button-primary" onClick={()=>setPending('accept')}>{t(label.accept)}</button>}
    {owner&&steps.decline&&!pending&&<button type="button" className="ui-button ui-button-secondary" onClick={()=>setPending('decline')}>{t(label.decline)}</button>}
    {owner&&steps.handover&&!pending&&<button type="button" className="ui-button ui-button-primary" onClick={()=>setPending('handover')}>{t(label.handover)}</button>}
    {owner&&steps.return&&!pending&&<button type="button" className="ui-button ui-button-primary" onClick={()=>setPending('return')}>{t(label.return)}</button>}
    {(owner||passenger)&&steps.cancel&&!pending&&<button type="button" className="ui-button ui-button-secondary" onClick={()=>setPending('cancel')}>{t(label.cancel)}</button>}
    {passenger&&confirms.HANDOVER&&!pending&&<button type="button" className="ui-button ui-button-primary" disabled={busy} onClick={()=>run(`/rentals/${id}/confirm`,{stage:'HANDOVER'},t('Handover confirmed'))}>{t('Confirm the handover')}</button>}
    {passenger&&confirms.RETURN&&!pending&&<button type="button" className="ui-button ui-button-primary" disabled={busy} onClick={()=>run(`/rentals/${id}/confirm`,{stage:'RETURN'},t('Return confirmed'))}>{t('Confirm the return')}</button>}
  </div>
  const nothing=!actionList.props.children.some(Boolean)

  return <FlowShell heading={booking.reference} title={t(STATUS_CHIP[booking.status]?.[1]||String(booking.status).replaceAll('_',' '))} icon="key" tabs={tabItems}>
    <RateErrors.Provider value={errors}><div className="rb-pane">
      {message.text&&<p className={'tk-line'+(message.warn?' is-warn':'')} role={message.warn?'alert':'status'}>{message.text}</p>}
      {active==='Rental'&&<div className="tk-pane">
        <div className="tk-bar"><Chip tone="info" icon="key">{t('Self-drive rental')}</Chip>{chip(booking.status)}</div>
        <dl className="flow-review">
          <div><dt>{t('Pickup')}</dt><dd>{formatDateTime(booking.start_at)}</dd></div><div><dt>{t('Return by')}</dt><dd>{formatDateTime(booking.end_at)}</dd></div>
          <div><dt>{t('Rental days')}</dt><dd>{rental.days}</dd></div>
          {rental.licence_number&&<div><dt>{t('Driving licence number')}</dt><dd>{rental.licence_number}</dd></div>}
          {rental.handover&&<div><dt>{t('Handover')}</dt><dd>{formatDateTime(rental.handover.at)} · {km(rental.handover.start_odometer_km)}{rental.handover.note?` · ${rental.handover.note}`:''} · {rental.handover.passenger_confirmed_at?t('Confirmed by the renter'):t('Not confirmed yet')}</dd></div>}
          {rental.return&&<div><dt>{t('Return')}</dt><dd>{formatDateTime(rental.return.at)} · {km(rental.return.end_odometer_km)}{rental.return.note?` · ${rental.return.note}`:''} · {rental.return.passenger_confirmed_at?t('Confirmed by the renter'):t('Not confirmed yet')}</dd></div>}</dl>
        {terms.notes&&<p className="tk-line"><strong>{t('Notes from the Owner')}:</strong> {terms.notes}</p>}</div>}
      {active==='Price'&&<div className="tk-pane">
        {final
          ?<><h4 className="rp-h">{t('Final bill')}</h4><BillTable price={final} label={t('Final bill')}/><p className="tk-line">{t('Distance driven')}: {km(final.distance_km)} · {t('Free km')}: {km(final.free_km)} · {t('Late hours')}: {final.late_hours}</p></>
          :estimate&&<><h4 className="rp-h">{t('Estimate')}</h4>
            <dl className="flow-review"><div><dt>{t('Day rate')}</dt><dd>{money(estimate.currency,estimate.day_rate)} × {estimate.days}</dd></div>
              {Number(estimate.extras_price)>0&&<div><dt>{t('Extras')}</dt><dd>{money(estimate.currency,estimate.extras_price)}{(price.chosen_extras||[]).length?` (${price.chosen_extras.map(x=>x.name).join(', ')})`:''}</dd></div>}
              <div><dt>{t('Estimate')}</dt><dd><strong>{money(estimate.currency,estimate.base_price)}</strong></dd></div>
              <div><dt>{t('Free km')}</dt><dd>{km(estimate.free_km_total)}</dd></div><div><dt>{t('Extra km rate')}</dt><dd>{money(estimate.currency,estimate.extra_km_rate)}</dd></div>
              <div><dt>{t('Late hour rate')}</dt><dd>{money(estimate.currency,estimate.late_hour_rate)} · {t('{value0} hour grace',{value0:estimate.late_grace_hours})}</dd></div></dl>
            <p className="tk-line">{t('The final price is worked out when the vehicle is returned, from the odometer readings and these rates.')}</p></>}</div>}
      {active==='Actions'&&<div className="tk-pane">
        {pending
          ?<div className="tk-hold rb-confirm">
            <p className="tk-line"><strong>{t(confirmText[pending])}</strong></p>
            {pending==='handover'&&tripId&&<><OdometerStep key={'start'+tripId} tripId={tripId} stage="START" onReady={setReading} fieldError={errors.start_odometer_km}/><Checkbox checked={checked} onChange={e=>setChecked(e.target.checked)}>{t('I checked the renter’s driving licence.')}</Checkbox></>}
            {pending==='return'&&tripId&&<OdometerStep key={'end'+tripId} tripId={tripId} stage="END" onReady={setReading} fieldError={errors.end_odometer_km}/>}
            {needsReason&&<Field label="Reason"><input name="reason" maxLength={500} value={reason} onChange={e=>setReason(e.target.value)}/></Field>}
            {(pending==='handover'||pending==='return')&&<Field label="Note" optional help="Fuel level, deposit taken, marks found."><input name="note" maxLength={500} value={note} onChange={e=>setNote(e.target.value)}/></Field>}
            <div className="tk-bar"><button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={close}>{t('Back')}</button>
              <button type="button" className="ui-button ui-button-primary" disabled={busy||!ready} onClick={()=>go(pending)}>{busy?t('Please wait…'):t(label[pending])}</button></div></div>
          :nothing?<p className="tk-line" role="status">{t('Nothing to do right now.')}</p>:actionList}</div>}
      {active==='Payment'&&<HirePayment key={booking.id} bookingId={booking.id} passengerUserId={booking.passenger_user_id} userId={user?.id} returned={payReturn}/>}
      {active==='Trip distance'&&hasProof&&<OdometerProofCard key={tripId} tripId={tripId}/>}
      <div className="flow-actions"><Link className="ui-button ui-button-secondary" to={backTo}>{t('Back to my trips')}</Link><span/></div>
    </div></RateErrors.Provider>
  </FlowShell>
}
