import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { t } from '../../i18n/language.js'
import { ButtonLink, Icon, useNotice } from '../../components/components'

// Retain this working form until its separate design reference is supplied.
export default function DashboardSearchPanel({ groupLink = '#rides', assurance = false }) {
  const navigate = useNavigate()
  const [active, setActive] = useState('Hire a vehicle')
  const notice = useNotice()
  const today = new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Colombo' })
  const tabs = [['Hire a vehicle', 'car'], ['Book tickets', 'ticket'], ['Rentals', 'key']]

  function search(event) {
    event.preventDefault()
    const values = Object.fromEntries(new FormData(event.currentTarget))
    if (active === 'Hire a vehicle') {
      navigate('/hire', { state: { seed: { pickup: values.pickup, destination: values.destination, departure: values.date } } })
      return
    }
    notice({
      title: 'Your next journey',
      message: active === 'Book tickets'
        ? 'Scheduled ticket search and checkout are not available yet. Private vehicle hire is available now.'
        : 'Rental checkout is not available yet. You can plan a private hire with a driver.',
      content: <ButtonLink to="/hire" arrow>{t('Plan a private hire')}</ButtonLink>,
    })
  }

  return <section className="search-panel" id="search" aria-label={t('Plan your journey')}>
    <div className="search-tabs" role="tablist" aria-label={t('Travel service')}>{tabs.map(([name, icon]) => <button type="button" key={name} id={`tab-${icon}`} role="tab" aria-selected={name === active} aria-controls="search-fields" tabIndex={name === active ? 0 : -1} className={name === active ? 'selected' : ''} onClick={() => setActive(name)} onKeyDown={event => {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return
      event.preventDefault()
      const index = event.key === 'Home' ? 0 : event.key === 'End' ? 2 : (tabs.findIndex(([label]) => label === active) + (event.key === 'ArrowRight' ? 1 : 2)) % 3
      setActive(tabs[index][0])
      event.currentTarget.parentElement.children[index].focus()
    }}><Icon name={icon}/>{t(name)}</button>)}</div>
    <form id="search-fields" role="tabpanel" aria-labelledby={`tab-${active === 'Hire a vehicle' ? 'car' : active === 'Book tickets' ? 'ticket' : 'key'}`} onSubmit={search}>
      <label>{active === 'Book tickets' ? t('From') : t('Pickup location')}<span className="search-input"><Icon name="pin"/><input name="pickup" placeholder={t('Where from?')} required maxLength={100} autoComplete="off" list="travelly-places"/></span></label>
      <label>{t('Destination')}<span className="search-input"><Icon name="pin"/><input name="destination" placeholder={t('Where to?')} required maxLength={100} autoComplete="off" list="travelly-places"/></span></label>
      <label>{active === 'Rentals' ? t('Rental date') : t('Travel date')}<span className="search-input"><input type="datetime-local" name="date" required min={`${today}T00:00`} aria-label={active === 'Rentals' ? t('Rental date') : t('Travel date')}/></span></label>
      <label>{t('Passengers')}<span className="search-input"><Icon name="users"/><select name="passengers" defaultValue="2 adults, 1 child"><option value="1 adult">{t('1 adult')}</option><option value="2 adults">{t('2 adults')}</option><option value="2 adults, 1 child">{t('2 adults, 1 child')}</option><option value="3–6 passengers">{t('3–6 passengers')}</option><option value="7+ passengers">{t('7+ passengers')}</option></select></span></label>
      <button className="button search-submit" type="submit">{active === 'Book tickets' ? t('Find tickets') : active === 'Rentals' ? t('Find a rental') : t('Find a ride')}<Icon name="arrow"/></button>
      <datalist id="travelly-places">{['Colombo', 'Kandy', 'Galle', 'Ella', 'Negombo', 'Jaffna', 'Anuradhapura', 'Sigiriya'].map(place => <option key={place} value={place}/>)}</datalist>
    </form>
    {assurance ? <div className="search-assurance">{[['shield', 'Eligibility checks'], ['car', 'A range of vehicles'], ['document', 'Agreed trip prices'], ['check', 'Clear journey details']].map(([icon, label]) => <span key={label}><Icon name={icon} size={20}/>{t(label)}</span>)}</div> : <div className="group-trip"><Icon name="users"/><span>{t('Planning a group trip?')}</span><Link to={groupLink}>{t('Explore buses and vans')}<Icon name="arrow"/></Link></div>}
  </section>
}
