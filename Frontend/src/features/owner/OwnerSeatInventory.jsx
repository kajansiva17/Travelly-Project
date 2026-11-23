import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { t } from '../../i18n/language.js'
import { api } from '../../services/api'
import { Header, ErrorNotice } from '../../components/components'
import { FlowShell } from '../booking/flow/FlowParts'
import { Chip, FormField, Select } from '../../components/ui'
import { displayTime } from '../../hooks/workspaceData'

const words = value => String(value || '').toLowerCase().split('_').map(part => part.replace(/^./, letter => letter.toUpperCase())).join(' ')
const lkr = value => Number(value).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

/* Sidebar > Seat inventory (Owner): how full each ticket departure is. Read only; departures are managed on the Tickets page. */
export default function OwnerSeatInventory() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [when, setWhen] = useState('UPCOMING')
  useEffect(() => { api('/owners/me/seat-inventory', { cache: 'no-store' }).then(setData).catch(setError) }, [])
  const now = Date.now()
  const live = item => !['CANCELLED', 'COMPLETED'].includes(item.status) && new Date(item.departure_at).getTime() >= now
  const items = (data?.items || []).filter(item => when === 'ALL' || (when === 'UPCOMING' ? live(item) : !live(item)))
    .sort((a, b) => (when === 'UPCOMING' ? 1 : -1) * (new Date(a.departure_at) - new Date(b.departure_at)))
  const upcoming = (data?.items || []).filter(live)
  const sum = key => upcoming.reduce((total, item) => total + item.seats[key], 0)

  return <><Header/><FlowShell heading={t('Seat inventory')} title={t('How full your departures are')} icon="ticket"
    info={t('Seats for sale, held while a Passenger pays, and booked on each of your ticket departures.')}>
    <ErrorNotice error={error}/>
    {!data && !error && <p role="status">{t('Loading…')}</p>}
    {data && <>
      <p><strong>{t('Upcoming departures')}{': '}{upcoming.length}</strong>{' · '}{t('Seats booked')}{': '}{sum('booked')}{' · '}{t('Seats available')}{': '}{sum('available')}{' · '}{t('Seats held')}{': '}{sum('held')}</p>
      <div className="flow-fields" style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'flex-end' }}>
        <FormField label={t('Show')}>
          {({ id }) => <Select id={id} value={when} onChange={event => setWhen(event.target.value)}>
            <option value="UPCOMING">{t('Upcoming')}</option><option value="PAST">{t('Past')}</option><option value="ALL">{t('All')}</option></Select>}
        </FormField>
        <Link className="ui-button ui-button-secondary" to="/owner/ticket?tab=departures">{t('Manage departures')}</Link>
      </div>
      {!items.length && <p className="flow-note" role="status">{data.items.length ? t('No departures match this filter.') : t('No departures yet.')}</p>}
      {items.map(item => {
        const missing = item.minimum_confirmed_seats ? Math.max(0, item.minimum_confirmed_seats - item.seats.booked) : 0
        const percent = item.seats.total ? Math.round(item.seats.booked * 100 / item.seats.total) : 0
        return <article className="tk-row" key={item.id} style={{ display: 'block' }}>
          <div style={{ display: 'flex', gap: 12, justifyContent: 'space-between', flexWrap: 'wrap' }}>
            <div className="tk-row-main"><strong>{item.route}</strong><span>{item.departure_reference}{' · '}{displayTime(item.departure_at)}{' · '}{item.vehicle}</span></div>
            <div><Chip tone="muted">{t(words(item.status))}</Chip></div>
          </div>
          <div role="img" aria-label={t('{value0} of {value1} seats booked', { value0: item.seats.booked, value1: item.seats.total })}
            style={{ height: 8, borderRadius: 4, background: 'rgba(128,128,128,.25)', margin: '8px 0', overflow: 'hidden' }}><div style={{ width: percent + '%', height: '100%', background: '#2e8b57' }}/></div>
          <p style={{ margin: 0 }}>{t('{value0} of {value1} seats booked', { value0: item.seats.booked, value1: item.seats.total })}{' · '}{t('Available')}{' '}{item.seats.available}{' · '}{t('Held')}{' '}{item.seats.held}{item.seats.other > 0 ? ' · ' + t('Not for sale') + ' ' + item.seats.other : ''}</p>
          <p className="flow-note" style={{ margin: 0 }}>{t('Fare per seat')}{': '}{'LKR '}{lkr(item.fare_per_seat)}{' · '}{t('Booked')}{': '}{'LKR '}{lkr(item.booked_amount)}</p>
          {missing > 0 && !['CANCELLED', 'COMPLETED'].includes(item.status) && <p className="flow-note" style={{ margin: 0 }}>{t('Needs {value0} more seats to be confirmed.', { value0: missing })}</p>}
        </article>
      })}
    </>}
  </FlowShell></>
}
