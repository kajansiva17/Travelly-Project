import { t } from '../../i18n/language.js'
import React,{useState} from 'react'
import {Header} from '../../components/components'
import {FlowShell,FlowBanner} from '../booking/flow/FlowParts'
import {Field,Compact} from '../owner/OwnerRates'
import {TravellyState,TravellyStatusChip} from '../../components/TravellyVisualFoundation'
const steps=['Requirements','Matching vehicles','Selected package','Request status','Inspections']
const unavailableText=[null,['Rental matching unavailable','No approved rental matching API currently returns vehicles or packages, so no vehicle or price is shown.'],['Package review unavailable','Base rate, included mileage, extra-km, late-return, extra-day, fuel-return and document rules appear only after a real selected package is returned.']]
// Rental: the requirements form (no rental API yet, so later steps explain what is unavailable). Same compact kit as the other booking steps.
export function PassengerRental(){
  const [step,setStep]=useState(0)
  const unavailable=unavailableText[Math.min(step,2)]||['Rental status unavailable','Request, confirmation and pickup/return inspection status require the unfinished Rental backend workflow.']
  return <><Header/><FlowShell heading={t('Travel & Booking')} title={t('Rent a vehicle')} info={t('Choose a specific matching vehicle before package price and rental rules can be shown.')} icon="key" steps={steps.map(s=>t(s))} current={step}>
    <Compact.Provider value={true}>
      {step===0?<div className="tk-pane"><div className="tk-grid" style={{'--cols':4}}>
        <Field label="Pickup location"><input name="pickup" required/></Field>
        <Field label="Return location"><input name="return" required/></Field>
        <Field label="Pickup date and time"><input name="start" type="datetime-local" required/></Field>
        <Field label="Return date and time"><input name="end" type="datetime-local" required/></Field>
        <Field label="Driving option"><select name="mode"><option>{t('Self Drive')}</option><option>{t('With Driver')}</option></select></Field>
        <Field label="Vehicle type"><select name="type"><option>{t('Vehicle type')}</option></select></Field>
        <Field label="Travellers"><input name="travellers" type="number" min="1"/></Field>
        <Field label="Luggage / AC needs" optional><input name="needs"/></Field>
      </div></div>:<FlowBanner tone="warning" icon="clock" title={t(unavailable[0])}>{t(unavailable[1])}</FlowBanner>}
      <div className="flow-actions"><button type="button" className="ui-button ui-button-secondary" disabled={!step} onClick={()=>setStep(step-1)}>{t('Back')}</button><button type="button" className="ui-button ui-button-primary" onClick={()=>setStep(Math.min(4,step+1))}>{t('Continue')}</button></div>
    </Compact.Provider>
  </FlowShell></>
}

export function RentalRoleUi({role}){const labels={OWNER:['Rental packages and requests','Configure packages, review Self Drive licence status, assign a Driver, and review handovers.'],DRIVER:['Assigned rental inspections','Only assigned With Driver rentals may record pickup/return conditions and evidence.'],ADMIN:['Rental audit overview','Read-only Rental status, inspection and review metadata.']}[role];const [tab,setTab]=useState(0),names=['Rental packages','Request and assignment status','Pickup and return inspections'];return <><Header/><FlowShell heading={role+' · Rental'} title={labels[0]} icon="key" info={labels[1]} tabs={names.map((n,i)=>({label:n,active:tab===i,onClick:()=>setTab(i),icon:['car','calendar','shield'][i]}))}><div className="flow-wizard-form" hidden={tab!==0}><TravellyState title="Unavailable">{t('Rental package APIs are not implemented. No rate, vehicle, licence, or Driver data is fabricated.')}</TravellyState></div><div className="flow-wizard-form" hidden={tab!==1}><TravellyState title="Unavailable">{t('There are no returned Rental requests or assignments to review.')}</TravellyState></div><div className="flow-wizard-form" hidden={tab!==2}><div className="flow-grid-4"><label>{t('Keys & accessories')}<input disabled placeholder="API required"/></label><label>{t('Exterior')}<input disabled placeholder="API required"/></label><label>{t('Interior')}<input disabled placeholder="API required"/></label><label>{t('Tyres')}<input disabled placeholder="API required"/></label></div><TravellyStatusChip tone="warning">{t('Evidence unavailable')}</TravellyStatusChip><p className="flow-note">{t('Private rental inspection evidence is shown only when the approved media metadata API returns it.')}</p></div></FlowShell></>}
