import { t } from '../../i18n/language.js'
import React,{useCallback,useEffect,useState} from 'react'
import {Link} from 'react-router-dom'
import {api} from '../../services/api'
import Chip from '../../components/ui/Chip'
import {onboardingPath} from './onboardingJourney'

/* Profile > My roles (contract 03W, section 4). Passenger is always there; Owner and Driver show their application status
   from GET /users/me/role-requests/{OWNER|DRIVER}/status. The buttons open the existing landing-page application
   (/owner/onboarding, /driver/onboarding): one form, two entry points. */
const NAMES={OWNER:'Owner',DRIVER:'Driver'}
function stateOf(status){
  const app=status?.application
  if(!app)return {key:'NONE'}
  // The reason that belongs to the state shown: rejection_reason for REJECTED (Needs correction), suspension_reason for SUSPENDED (contract 03N).
  const reason=app.approval_status==='REJECTED'?app.rejection_reason:app.approval_status==='SUSPENDED'?app.suspension_reason:''
  return {key:app.approval_status,reason:reason||''}
}
function RoleRow({code}){
  const [state,setState]=useState({loading:true,status:null,error:null})
  const load=useCallback(()=>{setState(s=>({...s,loading:true,error:null}));api(`/users/me/role-requests/${code}/status`,{cache:'no-store'}).then(status=>setState({loading:false,status,error:null})).catch(error=>setState({loading:false,status:null,error}))},[code])
  useEffect(()=>{load()},[load])
  const name=NAMES[code],{key,reason}=stateOf(state.status)
  const label=state.loading?t('Loading…'):state.error?t('Status unavailable'):key==='APPROVED'?t('Approved'):key==='PENDING'?t('Waiting for approval'):key==='REJECTED'?t('Needs correction'):key==='SUSPENDED'?t('Suspended'):t('Not applied')
  const tone=key==='APPROVED'?'success':key==='REJECTED'||key==='SUSPENDED'?'danger':key==='PENDING'?'info':'muted'
  const note=state.error?(state.error.message||t('The status could not be loaded.')):key==='REJECTED'?(reason||t('Review your application for the decision details.')):key==='SUSPENDED'?(reason||t('This role needs an authorized review. It cannot be reinstated from your account.')):key==='PENDING'?t('Your application is with Admin for review.'):key==='APPROVED'?t('Your role is approved.'):code==='OWNER'?t('Have a vehicle? Start your Owner application with this account.'):t('Take the next step. Apply for Driver membership with this account.')
  return <article className="tk-row"><div className="tk-row-main"><strong>{t(name)}</strong><span className={key==='REJECTED'||state.error?'is-warn':undefined} title={note}>{note}</span></div>
    <div className="tk-row-actions"><Chip tone={tone} icon={key==='APPROVED'?'check':undefined}>{label}</Chip>
      {state.error&&<button type="button" className="ui-button ui-button-secondary" onClick={load}>{t('Try again')}</button>}
      {!state.loading&&!state.error&&key==='NONE'&&<Link className="ui-button ui-button-primary" to={onboardingPath(code)}>{code==='OWNER'?t('Become an Owner'):t('Become a Driver')}</Link>}
      {!state.loading&&!state.error&&key==='REJECTED'&&<Link className="ui-button ui-button-primary" to={onboardingPath(code)}>{t('Fix and resubmit')}</Link>}
      {!state.loading&&!state.error&&key==='PENDING'&&<Link className="ui-button ui-button-secondary" to={onboardingPath(code)}>{t('View application')}</Link>}</div></article>
}
export default function MyRoles(){
  return <div className="tk-pane"><div className="tk-rows">
    <article className="tk-row"><div className="tk-row-main"><strong>{t('Passenger')}</strong><span>{t('Every Travelly account can search, book and pay.')}</span></div><div className="tk-row-actions"><Chip tone="success" icon="check">{t('Approved')}</Chip></div></article>
    <RoleRow code="OWNER"/><RoleRow code="DRIVER"/></div></div>
}
