import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { t } from '../../i18n/language.js'
import { api } from '../../services/api'
import { ErrorNotice } from '../../components/components'
import { Chip, FormField, Select } from '../../components/ui'
import { displayTime } from '../../hooks/workspaceData'

const month = value => new Date(value).toLocaleDateString('en-CA', { timeZone: 'Asia/Colombo' }).slice(0, 7)
const lkr = value => Number(value).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

/* Owner > Operations > Vehicle Expenses: every cost of the fleet (service, repair, fuel, charging and trip costs), by month and vehicle. */
export default function VehicleExpenses() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [when, setWhen] = useState(month(new Date()))
  const [vehicle, setVehicle] = useState('')
  useEffect(() => { api('/owners/me/expenses', { cache: 'no-store' }).then(setData).catch(setError) }, [])

  const months = useMemo(() => [...new Set([month(new Date()), ...(data?.items || []).map(item => month(item.recorded_at))])].sort().reverse(), [data])
  const plate = useMemo(() => Object.fromEntries((data?.vehicles || []).map(item => [item.id, item.registration])), [data])
  const rows = (data?.items || []).filter(item => month(item.recorded_at) === when && (!vehicle || item.vehicle_id === vehicle))
  const counted = rows.filter(item => item.counts)
  const total = counted.reduce((sum, item) => sum + Math.round(Number(item.amount) * 100), 0) / 100
  const byType = Object.entries(counted.reduce((all, item) => ({ ...all, [item.type]: (all[item.type] || 0) + Math.round(Number(item.amount) * 100) }), {}))

  return <div className="tk-pane">
    <ErrorNotice error={error}/>
    {!data && !error && <p role="status">{t('Loading…')}</p>}
    {data && <>
      <div className="flow-fields" style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'flex-end' }}>
        <FormField label={t('Month')}>
          {({ id }) => <Select id={id} value={when} onChange={event => setWhen(event.target.value)}>{months.map(item => <option key={item} value={item}>{item}</option>)}</Select>}
        </FormField>
        <FormField label={t('Vehicle')}>
          {({ id }) => <Select id={id} value={vehicle} onChange={event => setVehicle(event.target.value)}><option value="">{t('All vehicles')}</option>{data.vehicles.map(item => <option key={item.id} value={item.id}>{item.label}</option>)}</Select>}
        </FormField>
        <Link className="ui-button ui-button-secondary" to="/owner/maintenance">{t('Add a record')}</Link>
      </div>
      <p><strong>{t('Total this month')}{': '}{'LKR '}{lkr(total)}</strong></p>
      {byType.length > 0 && <p className="flow-note">{byType.map(([type, cents]) => `${t(type)} ${lkr(cents / 100)}`).join(' · ')}</p>}
      {!rows.length && <p className="flow-note" role="status">{t('No costs recorded for this month.')}</p>}
      {rows.map(item => <article className="tk-row" key={item.source + item.id}>
        <div className="tk-row-main"><strong>{t(item.type)}{' · '}{plate[item.vehicle_id]}</strong><span>{displayTime(item.recorded_at)}{item.detail ? ' · ' + item.detail : ''}</span></div>
        <div className="tk-row-actions">{!item.counts && <Chip tone="muted">{t(item.status)}</Chip>}<strong>{'LKR '}{lkr(item.amount)}</strong></div>
      </article>)}
    </>}
  </div>
}
