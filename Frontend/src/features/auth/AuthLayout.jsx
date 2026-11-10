import { t } from '../../i18n/language.js'
import React, { useState } from 'react'
import { Header, Icon } from '../../components/components'
import InfoTip from '../../components/ui/InfoTip'

const fleet = '/images/travelly/vehicles/'

// "Your journey, your way" ticket card shown beside every sign-in form (presentation only).
export function JourneyCard() {
  return <div className="journey-pass-frame"><div className="journey-pass">
    <h2>{t('Your journey,')} <span>{t('your way')}</span></h2>
    <i className="journey-rule" aria-hidden="true"/>
    <div className="journey-fleet" aria-hidden="true">
      {['bus', 'van', 'car', 'tuk-tuk'].map(name => <img key={name} src={`${fleet}vehicle-${name}-400.webp`} alt="" width="400" height="260" decoding="async"/>)}
    </div>
    <ul className="journey-services">
      <li><Icon name="car" size={34}/><span>{t('Vehicle Hire')}</span></li>
      <li><Icon name="ticket" size={34}/><span>{t('Tickets')}</span></li>
      <li><Icon name="calendar" size={34}/><span>{t('Rentals')}</span></li>
    </ul>
    <ol className="journey-steps">
      {[['01', 'Choose a ride'], ['02', 'Book with ease'], ['03', 'Travel your way']].map(([n, label], i) => <React.Fragment key={n}>
        {i > 0 && <li className="journey-arrow" aria-hidden="true"><Icon name="arrow" size={18}/></li>}
        <li><b>{i + 1}</b><span><strong>{n}</strong>{t(label)}</span></li>
      </React.Fragment>)}
    </ol>
  </div></div>
}

// Icon + placeholder pill. The visible label is the placeholder (as in the design); a real label stays for screen readers.
export function Field({ label, icon, password = false, error, hint, ...props }) {
  const [visible, setVisible] = useState(false)
  const id = props.name
  return <div className="auth-field">
    <label htmlFor={id}>{t(label)}</label>
    <div className={`auth-input ${error ? 'invalid' : ''}`}><Icon name={icon} size={22}/><div className="auth-input-content"><input {...props} placeholder={t(props.placeholder)} id={id} type={password ? visible ? 'text' : 'password' : props.type || 'text'} aria-invalid={Boolean(error)} aria-describedby={error ? `${id}-error` : hint ? `${id}-hint` : undefined}/></div>{password && <button type="button" className="visibility" onClick={() => setVisible(!visible)} aria-label={t(visible ? id === 'confirm_password' ? 'Hide confirm password' : 'Hide password' : id === 'confirm_password' ? 'Show confirm password' : 'Show password')}><Icon name={visible ? 'eye' : 'eyeOff'} size={20}/></button>}</div>
    {error && <span className="field-error" id={`${id}-error`}>{Array.isArray(error) ? error.map(message => t(message)).join(' ') : t(error)}</span>}{hint && <small id={`${id}-hint`}>{t(hint)}</small>}
  </div>
}

// Page frame: shared navbar, journey card on the left, frosted form card on the right.
export function AuthLayout({ variant = 'login', title, subtitle, tip, children }) {
  const words = title.trim().split(' '), last = words.pop()
  return <div className={`auth-page ${variant}-page`}><Header auth signup={variant === 'register'}/><main className="auth-layout" id="main">
    <aside className="auth-brand-panel"><JourneyCard/></aside>
    <section className="auth-form-panel" aria-labelledby="auth-title"><div className="auth-form-inner">
      <div className="auth-heading"><h1 id="auth-title">{words.join(' ')} <span>{last}</span></h1><h2>{subtitle}{tip && <InfoTip>{tip}</InfoTip>}</h2></div>
      {children}
    </div></section>
  </main></div>
}
