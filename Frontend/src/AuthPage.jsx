import React, { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { api, clearSession, login, register, setAuthFlow, acceptAuthResult } from './api'
import { Asset, ErrorNotice, Header, Icon, useNotice } from './components'
import RegisterPhoneField from './RegisterPhoneField'
import { registrationPhone } from './registrationPhone'

import GoogleSignIn from './GoogleSignIn'
import { emailError, passwordErrors, passwordHint } from './authValidation'

function Field({ label, icon, password = false, embedded = false, error, hint, ...props }) {
  const [visible, setVisible] = useState(false)
  const id = props.name
  return <div className={`auth-field ${embedded?'embedded-field':''}`}>
    {!embedded && <label htmlFor={id}>{label}</label>}
    <div className={`auth-input ${error?'invalid':''}`}><Icon name={icon} size={25}/><div className="auth-input-content">{embedded && <label htmlFor={id}>{label}</label>}<input {...props} id={id} type={password ? visible?'text':'password' : props.type || 'text'} aria-invalid={Boolean(error)} aria-describedby={error ? `${id}-error` : hint ? `${id}-hint` : undefined}/></div>{password && <button type="button" className="visibility" onClick={()=>setVisible(!visible)} aria-label={`${visible?'Hide':'Show'} password`}><Icon name={visible?'eye':'eyeOff'} size={23}/></button>}</div>
    {error && <span className="field-error" id={`${id}-error`}>{error}</span>}{hint && <small id={`${id}-hint`}>{hint}</small>}
  </div>
}

export default function AuthPage({ signup = false }) {
  const navigate=useNavigate()
  const location=useLocation()
  const notice=useNotice()
  const [pending,setPending]=useState(false)
  const [error,setError]=useState(null)
  const [fields,setFields]=useState({})
  const [remember,setRemember]=useState(false)
  const [phoneCountry,setPhoneCountry]=useState('LK')
  const [nationalPhone,setNationalPhone]=useState('')
  const [rememberedIdentifier]=useState(()=>{try{return localStorage.getItem('travelly-remembered-identifier') || ''}catch{return ''}})
  useEffect(()=>{setError(null);setFields({});setPhoneCountry('LK');setNationalPhone('');document.title=`${signup?'Create your account':'Log in'} | Travelly`},[signup])
  function validatePhone(country, number) {
    try { registrationPhone(country, number); setFields(previous=>({...previous,phone_e164:null})) }
    catch (error) { setFields(previous=>({...previous,phone_e164:error.message})) }
  }
  function policy(name) {
    notice({title:name,message:`The ${name} document has not been supplied for this preview. Its official destination will be added when available.`})
  }
  async function submit(event) {
    event.preventDefault()
    if(pending)return
    const values=Object.fromEntries(new FormData(event.currentTarget))
    setError(null);setFields({})
    let phone = null
    if(signup) {
      try { phone=registrationPhone(phoneCountry,nationalPhone) }
      catch(error){setFields({phone_e164:error.message});return}
      const invalid = {}
      if (!values.full_name.trim()) invalid.full_name = 'Enter your full name.'
      if (emailError(values.email)) invalid.email = emailError(values.email)
      if (!phone) invalid.phone_e164 = 'Enter your mobile number.'
      if (passwordErrors(values.password).length) invalid.password = passwordErrors(values.password).join(' ')
      if (!values.accept_terms) invalid.accept_terms = 'Agree to the Terms and Privacy Policy to continue.'
      if (Object.keys(invalid).length) { setFields(invalid); return }
    }
    setPending(true)
    try {
      if(signup) {
        const result = await register({full_name:values.full_name,email:values.email.trim(),phone_e164:phone,password:values.password,preferred_language:'en',accept_terms:true})
        setAuthFlow(result)
        navigate('/check-email',{replace:true})
      } else {
        const result = await login({identifier:values.identifier,password:values.password})
        if (result.status === 'verification_required') { navigate('/check-email', { replace:true }); return }
        // Confirm current identity and membership before entering private UI.
        // Dashboard entry revalidates these reads rather than storing profile
        // data in browser history or persistent storage.
        try { await Promise.all([api('/users/me'), api('/users/me/roles')]) }
        catch (error) { if (error.status === 401 || error.status === 403) clearSession(); throw error }
        try{if(remember)localStorage.setItem('travelly-remembered-identifier',values.identifier);else localStorage.removeItem('travelly-remembered-identifier')}catch{/* Login remains available when browser storage is disabled. */}
        navigate('/dashboard',{replace:true})
      }
    } catch(err) {
      setError(err instanceof TypeError?new Error('We could not reach Travelly. Please try again.'):err)
      setFields(Object.fromEntries((err.fields || []).map(field=>[field.field,field.message])))
    } finally {setPending(false)}
  }
  return <div className={`auth-page ${signup?'register-page':'login-page'}`}><Header auth signup={signup}/><main className="auth-layout" id="main">
    <aside className="auth-brand-panel" aria-label="Your journey, your way. One account. Every way to travel.">
      <Asset file="auth/Quiet ivory canvas with peach curves.png" alt="" className="auth-road"/>
      <div className="journey-pass-frame">
        <Asset file={signup?'auth/Screenshot 2026-10-25 011557.png':'auth/Screenshot 2026-10-25 011752.png'} alt="Travelly journey pass: Your journey, your way. One account. Every way to travel. Choose a ride, book with ease, travel your way." className="journey-pass" immediate/>
        <span className="ticket-border-light" aria-hidden="true"/>
      </div>
    </aside>
    <section className="auth-form-panel"><div className="auth-form-inner"><div className="auth-heading"><h1>{signup?'Start your journey':'Welcome back'}</h1><h2>{signup?'Create your Travelly account':'Log in to Travelly'}</h2><p>{signup?'One account for every ride.':'Enter your details to continue your journey.'}</p></div>
      {!signup && location.state?.registered && <div className="notice success" role="status"><Icon name="check"/> Your account is ready. Sign in to continue.</div>}<ErrorNotice error={error}/>
      <form key={signup?'register':'login'} onSubmit={submit} noValidate aria-label={signup?'Create account':'Log in'}>
        {signup ? <>
          <Field embedded name="full_name" label="Full name" icon="user" placeholder="e.g. John Smith" autoComplete="name" required maxLength={150} error={fields.full_name}/>
          <Field embedded name="email" label="Email address" icon="mail" type="email" placeholder="e.g. john@example.com" autoComplete="email" required maxLength={254} error={fields.email}/>
          <RegisterPhoneField country={phoneCountry} value={nationalPhone} onCountryChange={country=>{setPhoneCountry(country);validatePhone(country,nationalPhone)}} onChange={number=>{setNationalPhone(number);if(fields.phone_e164)validatePhone(phoneCountry,number)}} onBlur={()=>validatePhone(phoneCountry,nationalPhone)} error={fields.phone_e164}/>
        </> : <Field name="identifier" label="Email address" icon="mail" placeholder="you@example.com" autoComplete="username" defaultValue={rememberedIdentifier} required maxLength={254} error={fields.identifier} hint="You can also use your international mobile number."/>}
        <Field embedded={signup} name="password" label="Password" icon="lock" password placeholder={signup?'Create a secure password':'Enter your password'} autoComplete={signup?'new-password':'current-password'} required minLength={signup?12:1} error={fields.password} hint={signup?passwordHint:null}/>
        {signup ? <label className="terms-check"><input type="checkbox" name="accept_terms" required/><span>I agree to the <button type="button" className="inline-link" onClick={()=>policy('Terms')}>Terms</button> and <button type="button" className="inline-link" onClick={()=>policy('Privacy Policy')}>Privacy Policy</button></span></label> : <><div className="login-options"><label><input type="checkbox" checked={remember} onChange={event=>setRemember(event.target.checked)} aria-describedby={remember?'remember-hint':undefined}/>Remember me</label><Link className="inline-link" to="/forgot-password">Forgot password?</Link></div>{remember && <small className="remember-hint" id="remember-hint">Remember your email on this device. Your password and session are never saved.</small>}</>}
        {fields.accept_terms && <p className="field-error" role="alert">{fields.accept_terms}</p>}
        <button type="submit" className="button auth-submit" disabled={pending}>{pending?<><span className="spinner"/>{signup?'Creating account…':'Logging in…'}</>:<>{signup?'Create account':'Log in'}<Icon name="arrow" size={24}/></>}</button>
      </form>
      <div className="auth-divider"><span>or</span></div>
      <GoogleSignIn onResult={result => {
        if (result.status === 'link_required') { setError(new Error(result.message)); return }
        acceptAuthResult(result)
        navigate(result.status === 'completion_required' ? '/google-complete' : result.status === 'verification_required' ? '/check-email' : '/dashboard')
      }}/>
      {signup ? <div className="auth-switch"><span>Already have an account? <Link to="/login">Log in</Link></span></div> : <><div className="auth-divider"><span>or</span></div><p className="auth-switch login-switch">New to Travelly? <Link to="/register">Create an account</Link></p></>}
    </div></section>
  </main></div>
}
