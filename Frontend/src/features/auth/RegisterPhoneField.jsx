import { t } from '../../i18n/language.js'
import { useEffect, useRef, useState } from 'react'
import { Icon } from '../../components/components'
import { phoneCountries } from './registrationPhone'

export default function RegisterPhoneField({ country, value, onCountryChange, onChange, onBlur, error }) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [active, setActive] = useState(0)
  const container = useRef(null), trigger = useRef(null), options = useRef(null)
  const selected = phoneCountries.find(item => item.code === country)
  const term = query.trim().toLowerCase().replace(/^\+/, '')
  const filtered = phoneCountries.filter(item => !term || item.name.toLowerCase().includes(term) || item.code.toLowerCase() === term || item.callingCode.startsWith(term))
    .sort((a, b) => Number(b.code.toLowerCase() === term) - Number(a.code.toLowerCase() === term))

  useEffect(() => {
    if (!open) return
    const outside = event => { if (!container.current?.contains(event.target)) setOpen(false) }
    document.addEventListener('pointerdown', outside)
    document.addEventListener('focusin', outside)
    return () => { document.removeEventListener('pointerdown', outside); document.removeEventListener('focusin', outside) }
  }, [open])

  function choose(item) { onCountryChange(item.code); setOpen(false); trigger.current.focus() }
  function keyboard(event) {
    if (event.key === 'Escape') { event.preventDefault(); setOpen(false); trigger.current.focus(); return }
    if (event.key === 'Enter') { event.preventDefault(); if (filtered[active]) choose(filtered[active]); return }
    if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return
    event.preventDefault()
    const next = event.key === 'Home' ? 0 : event.key === 'End' ? filtered.length - 1 : Math.max(0, Math.min(filtered.length - 1, active + (event.key === 'ArrowDown' ? 1 : -1)))
    setActive(next); options.current?.children[next]?.scrollIntoView({ block: 'nearest' })
  }

  return <div className="auth-field register-phone-field" ref={container}>
    <label htmlFor="national_phone">{t("Mobile number")}</label>
    <div className={`auth-input ${error ? 'invalid' : ''}`}><Icon name="phone" size={25}/><div className="auth-input-content">
      <div className="register-phone-row">
        <button type="button" ref={trigger} className="phone-country-trigger" aria-label={t("Country code: {value0} (+{value1})", {value0: selected.name, value1: selected.callingCode})} aria-haspopup="dialog" aria-expanded={open} aria-controls={open ? 'phone-country-picker' : undefined} onClick={() => { setQuery(''); setActive(0); setOpen(!open) }}><span className="phone-country-iso">{selected.code}</span><span>+{selected.callingCode}</span><Icon name="chevron" size={14}/></button>
        <input id="national_phone" name="national_phone" type="tel" inputMode="tel" autoComplete="tel-national" placeholder={country === 'LK' ? '77 123 4567' : t('National mobile number')} maxLength={40} value={value} onChange={event => onChange(event.target.value)} onBlur={onBlur} aria-invalid={Boolean(error)} aria-describedby={error ? 'phone-entry-error phone-entry-hint' : 'phone-entry-hint'}/>
      </div>
    </div></div>
    {open && <div className="phone-country-picker" role="dialog" id="phone-country-picker" aria-label={t("Choose your country code")}>
      <label htmlFor="phone-country-search">{t("Search country or calling code")}</label>
      <input id="phone-country-search" type="search" autoComplete="off" autoFocus value={query} onChange={event => { setQuery(event.target.value); setActive(0) }} onKeyDown={keyboard} role="combobox" aria-autocomplete="list" aria-expanded="true" aria-controls="phone-country-options" aria-activedescendant={filtered[active] ? `phone-country-${filtered[active].code}` : undefined}/>
      <div className="phone-country-options" role="listbox" id="phone-country-options" aria-label={t("Countries and calling codes")} ref={options}>
        {filtered.map((item, index) => <button type="button" role="option" id={`phone-country-${item.code}`} key={item.code} tabIndex={-1} aria-selected={item.code === country} className={index === active ? 'phone-country-active' : ''} onClick={() => choose(item)}><span>{item.name} <small>{item.code}</small></span><strong>+{item.callingCode}</strong></button>)}
      </div>
      {!filtered.length && <p role="status">{t("No matching country. Try a country name or calling code.")}</p>}
    </div>}
    {error && <span className="field-error" id="phone-entry-error">{t(error)}</span>}
    <small id="phone-entry-hint">{t("Select your country code. Enter the national number without the country code.")}</small>
  </div>
}
