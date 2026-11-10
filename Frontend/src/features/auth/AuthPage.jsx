import { t, getLanguage } from '../../i18n/language.js'
import React, { useEffect, useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { api, clearSession, login, register, setAuthFlow, getAuthFlow, acceptAuthResult } from '../../services/api'
import { ErrorNotice, Icon, useNotice, useSession } from '../../components/components'
import { AuthLayout, Field } from './AuthLayout'
import RegisterPhoneField from './RegisterPhoneField'
import { registrationPhone } from './registrationPhone'

import {journeyRole,authJourney,journeyLink,authDestination} from './onboardingJourney'
import GoogleSignIn from './GoogleSignIn'
import { emailError, passwordErrors, passwordHint } from './authValidation'
import { loginDestination } from '../../routes/workspaceRoutes'

export default function AuthPage({ signup = false }) {
  const language = getLanguage()
  useEffect(()=>{document.title=`${t(signup?'Create your account':'Log in')} | Travelly`},[signup,language])
  const navigate=useNavigate()
  const signedIn=useSession()
  const location=useLocation()
  const journey=signup?journeyRole(location.search):authJourney(location.search)
  const notice=useNotice()
  const [pending,setPending]=useState(false)
  const [resolvedDestination,setResolvedDestination]=useState(null)
  const [error,setError]=useState(null)
  const [fields,setFields]=useState({})
  const [registrationValues,setRegistrationValues]=useState({full_name:'',email:'',password:'',confirm_password:''})
  const [registerStep,setRegisterStep]=useState(1)
  const [compactRegistration,setCompactRegistration]=useState(()=>signup&&window.matchMedia('(min-width: 1024px) and (max-height: 640px)').matches)
  const [remember,setRemember]=useState(false)
  const [phoneCountry,setPhoneCountry]=useState('LK')
  const [nationalPhone,setNationalPhone]=useState('')
  const [rememberedIdentifier]=useState(()=>{try{return localStorage.getItem('travelly-remembered-identifier') || ''}catch{return ''}})
  useEffect(()=>{
    setError(null);setFields({});setPhoneCountry('LK');setNationalPhone('')
    setRegistrationValues({full_name:'',email:'',password:'',confirm_password:''});setRegisterStep(1)
    const compact=window.matchMedia('(min-width: 1024px) and (max-height: 640px)')
    const updateLayout=()=>setCompactRegistration(signup&&compact.matches)
    updateLayout();compact.addEventListener('change',updateLayout)
    return ()=>compact.removeEventListener('change',updateLayout)
  },[signup])
  function updateRegistrationField(event) {
    const {name,value}=event.currentTarget
    setRegistrationValues(previous=>({...previous,[name]:value}))
  }
  function validatePhone(country, number) {
    try { registrationPhone(country, number); setFields(previous=>({...previous,phone_e164:null})) }
    catch (error) { setFields(previous=>({...previous,phone_e164:error.message})) }
  }
  function advanceRegistration(event) {
    event.preventDefault()
    const invalid={}
    if(!registrationValues.full_name.trim())invalid.full_name='Enter your full name.'
    const invalidEmail=emailError(registrationValues.email)
    if(invalidEmail)invalid.email=invalidEmail
    try { registrationPhone(phoneCountry,nationalPhone) }
    catch(error) { invalid.phone_e164=error.message }
    setFields(invalid)
    if(Object.keys(invalid).length)return
    setRegisterStep(2)
  }
  function policy(name) {
    notice({title:name,message:`The ${name} document has not been supplied for this preview. Its official destination will be added when available.`})
  }
  async function signedInDestination() {
    try {
      const [user, roles] = await Promise.all([api('/users/me',{cache:'no-store'}), api('/users/me/roles',{cache:'no-store'})])
      const destination = loginDestination(user, roles.items || [], journey)
      setResolvedDestination(destination)
      return destination
    } catch(error) {
      if(error.status===401||error.status===403)clearSession()
      throw error
    }
  }
  async function submit(event) {
    event.preventDefault()
    if(pending)return
    const formValues=Object.fromEntries(new FormData(event.currentTarget))
    const values=signup?{...registrationValues,...formValues}:formValues
    setError(null);setFields({})
    let phone = null
    if(signup) {
      try { phone=registrationPhone(phoneCountry,nationalPhone) }
      catch(error){setFields({phone_e164:error.message});return}
      const invalid = {}
      if (!values.full_name.trim()) invalid.full_name = 'Enter your full name.'
      if (emailError(values.email)) invalid.email = emailError(values.email)
      if (!phone) invalid.phone_e164 = 'Enter your mobile number.'
      if (passwordErrors(values.password).length) invalid.password = passwordErrors(values.password)
      if (values.password !== values.confirm_password) invalid.confirm_password = 'Your passwords do not match.'
      if (!values.accept_terms) invalid.accept_terms = 'Agree to the Terms and Privacy Policy to continue.'
      if (Object.keys(invalid).length) { setFields(invalid); return }
    }
    setPending(true)
    try {
      if(signup) {
        const result = await register({full_name:values.full_name,email:values.email.trim(),phone_e164:phone,password:values.password,preferred_language:getLanguage(),accept_terms:true,...(['OWNER','DRIVER'].includes(journey)?{journey}:{})})
        setAuthFlow({...result,journey})
        navigate(journeyLink('/check-email',journey),{replace:true})
      } else {
        const result = await login({identifier:values.identifier,password:values.password,...(['OWNER','DRIVER'].includes(journey)?{journey}:{})})
        if (result.status === 'verification_required') { setAuthFlow({...getAuthFlow(),journey}); navigate(journeyLink('/check-email',journey), { replace:true }); return }
        // Confirm current identity and membership before entering private UI.
        // Dashboard entry revalidates these reads rather than storing profile
        // data in browser history or persistent storage.
        const destination = await signedInDestination()
        try{if(remember)localStorage.setItem('travelly-remembered-identifier',values.identifier);else localStorage.removeItem('travelly-remembered-identifier')}catch{/* Login remains available when browser storage is disabled. */}
        navigate(destination,{replace:true})
      }
    } catch(err) {
      setError(err instanceof TypeError?new Error('We could not reach Travelly. Please try again.'):err)
      setFields(Object.fromEntries((err.fields || []).map(field=>[field.field,field.message])))
    } finally {setPending(false)}
  }
  function handleSubmit(event) {
    if(signup&&compactRegistration&&registerStep===1){advanceRegistration(event);return}
    submit(event)
  }
  if (signedIn && !pending) return <Navigate to={resolvedDestination || authDestination(journey)} replace/>
  return <AuthLayout variant={signup?'register':'login'} title={signup?t('Create your account'):t('Welcome back')} subtitle={signup?t('Start your journey with Travelly'):t('Log in to continue your journey')}>
      {signup&&compactRegistration&&<div className="registration-progress"><div><span>{t("Step ")}{registerStep}{t(" of 2")}</span><strong>{registerStep===1?t('Your details'):t('Secure your account')}</strong></div><div className="registration-progress-track" role="progressbar" aria-label={t("Registration progress")} aria-valuemin={1} aria-valuemax={2} aria-valuenow={registerStep}><span style={{width:registerStep===1?'50%':'100%'}}/></div></div>}
      {!signup && location.state?.registered && <div className="notice success" role="status"><Icon name="check"/>{t(" Your account is ready. Sign in to continue.")}</div>}<ErrorNotice error={error}/>
      <form className="auth-credentials-form" key={signup?'register':'login'} onSubmit={handleSubmit} noValidate aria-label={signup?t('Create account'):t('Log in')}>
        {signup&&(!compactRegistration||registerStep===1)&&<>
          <Field name="full_name" label="Full name" icon="user" placeholder="Full name" autoComplete="name" required maxLength={150} error={fields.full_name} value={registrationValues.full_name} onChange={updateRegistrationField}/>
          <Field name="email" label="Email address" icon="mail" type="email" placeholder="Email address" autoComplete="email" required maxLength={254} error={fields.email} value={registrationValues.email} onChange={updateRegistrationField}/>
          <RegisterPhoneField country={phoneCountry} value={nationalPhone} onCountryChange={country=>{setPhoneCountry(country);validatePhone(country,nationalPhone)}} onChange={number=>{setNationalPhone(number);if(fields.phone_e164)validatePhone(phoneCountry,number)}} onBlur={()=>validatePhone(phoneCountry,nationalPhone)} error={fields.phone_e164}/>
        </>}
        {!signup&&<Field name="identifier" label="Email address" icon="mail" placeholder="Email address" autoComplete="username" defaultValue={rememberedIdentifier} required maxLength={254} error={fields.identifier} hint="You can also use your international mobile number."/>}
        {(!signup||!compactRegistration||registerStep===2)&&<Field name="password" label="Password" icon="lock" password placeholder={'Password'} autoComplete={signup?'new-password':'current-password'} required minLength={signup?12:1} error={fields.password} hint={signup?passwordHint:null} value={signup?registrationValues.password:undefined} onChange={signup?updateRegistrationField:undefined}/>}
        {signup&&(!compactRegistration||registerStep===2)&&<Field name="confirm_password" label="Confirm password" icon="lock" password placeholder="Confirm your password" autoComplete="new-password" required error={fields.confirm_password} value={registrationValues.confirm_password} onChange={updateRegistrationField}/>}
        {signup&&(!compactRegistration||registerStep===2)&&<label className="terms-check"><input type="checkbox" name="accept_terms" required/><span>{t("I agree to the ")}<button type="button" className="inline-link" onClick={()=>policy('Terms')}>{t("Terms")}</button>{t(" and ")}<button type="button" className="inline-link" onClick={()=>policy('Privacy Policy')}>{t("Privacy Policy")}</button></span></label>}
        {!signup&&(
          <>
            <div className="login-options"><label><input type="checkbox" checked={remember} onChange={event=>setRemember(event.target.checked)} aria-describedby={remember?'remember-hint':undefined}/>{t("Remember me")}</label><Link className="inline-link" to={journeyLink('/forgot-password',journey)}>{t("Forgot password?")}</Link></div>
            {remember && <small className="remember-hint" id="remember-hint">{t("Remember your email on this device. Your password and session are never saved.")}</small>}
          </>
        )}
        {fields.accept_terms && <p className="field-error" role="alert">{t(fields.accept_terms)}</p>}
        {signup&&compactRegistration&&registerStep===2&&<button type="button" className="registration-back" onClick={()=>{setFields({});setRegisterStep(1)}}>{t("Back")}</button>}
        <button type="submit" className={`ui-button ui-button-primary auth-submit ${signup&&compactRegistration&&registerStep===1?'registration-continue':''} ${signup&&compactRegistration&&registerStep===2?'registration-final-step':''}`} disabled={pending}>{pending?<><span className="spinner"/>{signup?t('Creating account…'):t('Logging in…')}</>:<>{signup&&compactRegistration&&registerStep===1?t('Continue'):signup?t('Create account'):t('Log in')}<Icon name="arrow" size={20}/></>}</button>
      </form>
      <div className="auth-divider"><span>{t("or")}</span></div>
      <GoogleSignIn journey={journey} onResult={async result => {
        if (result.status === 'link_required') { setError(new Error(result.message)); return }
        if(journey==='ADMIN'&&result.status==='completion_required'){setError(new Error('Sign in with your existing approved Admin account. This Google identity has no Travelly account.'));return}
        setPending(true)
        try {
          acceptAuthResult(result)
          if(!result.access_token)setAuthFlow({...result,journey})
          navigate(result.status === 'completion_required' ? journeyLink('/google-complete',journey) : result.status === 'verification_required' ? journeyLink('/check-email',journey) : await signedInDestination(),{replace:true})
        } catch(error) {setError(error)}
        finally {setPending(false)}
      }}/>
      {signup ? <div className="auth-switch"><span>{t("Already have an account? ")}<Link to={journeyLink('/login',journey)}>{t("Log in")}</Link></span></div> : journey!=='ADMIN'&&<p className="auth-switch login-switch">{t("New to Travelly? ")}<Link to={journeyLink('/register',journey)}>{t("Create an account")}</Link></p>}
  </AuthLayout>
}
