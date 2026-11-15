import { useEffect, useState } from 'react'
import { t } from '../../i18n/language.js'
import { api } from '../../services/api'
import { ErrorNotice, Icon } from '../../components/components'
import { Checkbox } from '../../components/ui'
import { formatDateTime } from '../../i18n/dateTime.js'
import { AmountField, Compact, emptyRule } from '../owner/OwnerRates'
import { DateTimeFields } from '../ticketing/TicketParts'
import { withExtraPolicy, modeOf } from './extraPolicy.js'
import { validateRateRules, departureMatches } from '../owner/rateValidation'

/* The Owner's quick answer to a Passenger request. The request (route, date, time) is already known, so the Owner only types the
   prices that matter for it. Everything else (area, tolls, waiting, return, change limits) is filled in from the Owner's own saved
   rule for this route, or from plain defaults. The same rule is saved for later matching requests. */

const AREA_KM = 15, zero = '0'
const localTime = v => v ? new Date(new Date(v).getTime() + 330 * 60000).toISOString().slice(0, 16) : ''
const decimal = v => typeof v === 'string' && /^[0-9]{1,10}(\.[0-9]{1,10})?$/.test(v)
const num = v => v == null ? '' : String(v)
const same = (a, b) => JSON.stringify(a.map(p => [p.latitude, p.longitude])) === JSON.stringify(b.map(p => [p.latitude, p.longitude]))

function box(place, km) {
  const lat = Number(place.latitude), lon = Number(place.longitude), dy = km / 111.32, dx = dy / Math.cos(lat * Math.PI / 180)
  return { label: `${String(place.label).split(',')[0].slice(0, 80)} · ${km} km`, south: String(lat - dy), north: String(lat + dy), west: String(lon - dx), east: String(lon + dx) }
}

export default function QuickQuote({ booking, itinerary, onSaved }) {
  const [saved, setSaved] = useState(null), [rule, setRule] = useState(null), [f, setF] = useState({}), [error, setError] = useState(null), [busy, setBusy] = useState(false)
  const [other, setOther] = useState(false), [when, setWhen] = useState('')
  const day = localTime(itinerary.start_at).slice(0, 10), dayHire = itinerary.method === 'DAY_HIRE'
  useEffect(() => {
    api(`/vehicles/${booking.vehicle_id}/services`).then(result => {
      const current = result.items.find(s => s.service_type_id === booking.service_type_id) || { version: 0, rules: [] }
      const places = itinerary.stops.map(s => s.place), method = dayHire ? 'DAY_HIRE' : 'DISTANCE'
      const found = current.rules.find(x => x.method === method && x.direction === itinerary.direction && x.coverage.kind === 'ROUTE' && same(x.coverage.places, places)
        && x.effective_from <= day && (!x.effective_until || x.effective_until >= day))
      const fresh = {
        ...emptyRule(), label: `${String(places[0].label).split(',')[0]} to ${String(places.at(-1).label).split(',')[0]}`.slice(0, 120), method, direction: itinerary.direction, effective_from: day,
        coverage: { kind: 'ROUTE', places }, pickup_area: box(places[0], AREA_KM), free_wait_minutes: zero, waiting_hour_rate: zero, return_to_base: 'INCLUDED', return_to_base_charge: null,
        return_to_base_notes: 'Return to base is included in the rates.', tolls: 'SEPARATE_AT_COST', parking: 'SEPARATE_AT_COST', other_charges: [],
        change_limits: { added_km: zero, added_hours: zero, added_wait_minutes: zero, added_amount: zero }, extra_policy: { WAITING: 'NOT_OFFERED' }, night_km_rate: zero, overnight_driver_cost: zero, departure: null }
      const r = found || fresh
      setSaved(current); setRule(r)
      setF({ base_charge: num(r.base_charge), included_km: num(r.included_km), day_charge: num(r.day_charge), included_hours_per_day: num(r.included_hours_per_day), included_km_per_day: num(r.included_km_per_day),
        extraKm: found ? modeOf(r, 'EXTRA_KM') === 'CHARGED' : false, extra_km_rate: found && modeOf(r, 'EXTRA_KM') === 'CHARGED' ? num(r.extra_km_rate) : '',
        extraHours: found ? modeOf(r, 'EXTRA_HOURS') === 'CHARGED' : false, extra_hour_rate: found && modeOf(r, 'EXTRA_HOURS') === 'CHARGED' ? num(r.extra_hour_rate) : '' })
    }).catch(setError)
  }, [booking.id, booking.version])
  const set = patch => setF(s => ({ ...s, ...patch }))
  const original = localTime(itinerary.start_at), proposing = other && when && when !== original
  async function send() {
    setError(null)
    const need = dayHire ? [f.day_charge, f.included_hours_per_day, f.included_km_per_day] : [f.base_charge, f.included_km]
    if (!need.every(decimal) || (f.extraKm && !decimal(f.extra_km_rate)) || (dayHire && f.extraHours && !decimal(f.extra_hour_rate))) { setError({ message: t('Fill in every price to send the quote. Enter 0 where nothing applies.') }); return }
    const from = proposing && when.slice(0, 10) < rule.effective_from ? when.slice(0, 10) : rule.effective_from
    const until = rule.effective_until && proposing && rule.effective_until < when.slice(0, 10) ? null : rule.effective_until
    const next = withExtraPolicy({ ...rule, effective_from: from, effective_until: until || null,
      ...(dayHire ? { day_charge: f.day_charge, included_hours_per_day: f.included_hours_per_day, included_km_per_day: f.included_km_per_day, extra_hour_rate: f.extraHours ? f.extra_hour_rate : zero, night_km_rate: zero, overnight_driver_cost: zero }
        : { base_charge: f.base_charge, included_km: f.included_km, night_km_rate: zero }),
      extra_km_rate: f.extraKm ? f.extra_km_rate : zero,
      extra_policy: { ...(rule.extra_policy || {}), EXTRA_KM: f.extraKm ? 'CHARGED' : 'NOT_OFFERED', ...(dayHire ? { EXTRA_HOURS: f.extraHours ? 'CHARGED' : 'NOT_OFFERED', OVERNIGHT: 'NOT_OFFERED' } : {}) } })
    const rules = saved.rules.some(x => x.id === rule.id) ? saved.rules.map(x => x.id === rule.id ? next : x) : [...saved.rules, next]
    const found = validateRateRules(rules)
    if (found.length) { setError({ message: found[0].message }); return }
    setBusy(true)
    try {
      const result = await api(`/bookings/${booking.id}/quote`, { method: 'POST', body: JSON.stringify({ expected_version: booking.version, ...(proposing ? { proposed_start_at: when + ':00+05:30' } : {}),
        rates: { service_type_id: booking.service_type_id, expected_version: saved.version, enabled: true, currency: 'LKR', rules } }) })
      onSaved(result)
    } catch (e) { setError(e) } finally { setBusy(false) }
  }
  return <section className="quick-quote">
    <ErrorNotice error={error}/>
    <p className="qq-ask"><Icon name="calendar" size={15}/> {t('Passenger asked for')} <strong>{formatDateTime(itinerary.start_at, { timeZone: 'Asia/Colombo' })}</strong>{!other && <> · <button type="button" className="inline-link" onClick={() => { setOther(true); setWhen(original) }}>{t('Cannot do this time? Propose a different date/time')}</button></>}</p>
    {other && <div className="qq-time"><DateTimeFields dateLabel="New date" timeLabel="New time" value={when} min={localTime(new Date().toISOString()).slice(0, 10)} onChange={setWhen}/><button type="button" className="inline-link" onClick={() => { setOther(false); setWhen('') }}>{t('Keep the requested time')}</button></div>}
    {!rule ? <p>{t('Loading vehicle rates…')}</p> : <Compact.Provider value={true}>
      {dayHire ? <div className="rate-grid qq-grid">
        <AmountField name="day_charge" label="Package price" help="One price for the hours and km below." value={f.day_charge} onChange={v => set({ day_charge: v })}/>
        <AmountField name="included_hours_per_day" label="Included hours" help="Service hours covered by the package, at most 24." value={f.included_hours_per_day} onChange={v => set({ included_hours_per_day: v })}/>
        <AmountField name="included_km_per_day" label="Included distance" help="Km covered by the package." value={f.included_km_per_day} onChange={v => set({ included_km_per_day: v })}/>
        <div className="hire-check"><Checkbox checked={f.extraKm} onChange={e => set({ extraKm: e.target.checked })}>{t('Charge for extra km')}</Checkbox></div>
        <div className="hire-check"><Checkbox checked={f.extraHours} onChange={e => set({ extraHours: e.target.checked })}>{t('Charge for extra hours')}</Checkbox></div><span/>
        {f.extraKm && <AmountField name="extra_km_rate" label="Rate per extra km" help="Charged for each km beyond the package km." value={f.extra_km_rate} onChange={v => set({ extra_km_rate: v })}/>}
        {f.extraHours && <AmountField name="extra_hour_rate" label="Rate per extra hour" help="Charged for each hour beyond the package hours." value={f.extra_hour_rate} onChange={v => set({ extra_hour_rate: v })}/>}
      </div> : <div className="rate-grid qq-grid">
        <AmountField name="base_charge" label="Starting price" help="Charged for every trip; it covers the included km." value={f.base_charge} onChange={v => set({ base_charge: v })}/>
        <AmountField name="included_km" label="Included distance" help="Km covered by the starting price. Enter 0 if none." value={f.included_km} onChange={v => set({ included_km: v })}/>
        <div className="hire-check"><Checkbox checked={f.extraKm} onChange={e => set({ extraKm: e.target.checked })}>{t('Charge for km beyond the included distance')}</Checkbox></div>
        {f.extraKm && <AmountField name="extra_km_rate" label="Rate per extra km" help="Charged for each km after the included distance." value={f.extra_km_rate} onChange={v => set({ extra_km_rate: v })}/>}
      </div>}
    </Compact.Provider>}
    <div className="qq-actions"><span/><button type="button" className="ui-button ui-button-primary" disabled={busy || !rule} onClick={send}>{busy ? t('Sending…') : t('Send quote')}</button></div>
  </section>
}
