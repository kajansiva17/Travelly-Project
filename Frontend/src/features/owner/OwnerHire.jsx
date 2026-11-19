import { t } from '../../i18n/language.js'
import React, { useEffect, useMemo, useState } from 'react'
import { createPortal } from 'react-dom'
import { Link, Navigate, useLocation } from 'react-router-dom'
import { api, hasSession } from '../../services/api'
import { ErrorNotice, Header } from '../../components/components'
import Chip from '../../components/ui/Chip'
import { Checkbox } from '../../components/ui'
import { Field, AmountField, PlaceSearch, Compact, CashSwitch } from './OwnerRates'
import EventPackages from './EventPackages'
import { FlowShell } from '../booking/flow/FlowParts'
import { validateRateRules } from './rateValidation'
import { withExtraPolicy } from '../booking/extraPolicy.js'
import { fieldErrors } from '../../services/fieldErrors.js'

/* Hire prices (one screen per hire type). The Owner picks a vehicle and a hire type; the type's prices are set in a few small tabs:
   Area and terms, Per km, Day package, Fixed routes. Event hire uses its packages. The rates are saved as the same reusable rate rules
   as before (one-way, any departure time, starting today), so quotes and bookings are unchanged. Rules this page does not make
   (for example a Return journey rule) are kept exactly as they are. */

const TYPES = [['LOCAL', 'Local'], ['AIRPORT', 'Airport'], ['LONG_DISTANCE', 'Long distance'], ['EVENT', 'Event']]
const RADIUS = { LOCAL: '25', AIRPORT: '100', LONG_DISTANCE: '400' }
const today = () => new Date(Date.now() + 330 * 60000).toISOString().slice(0, 10)
const zero = '0'
const num = v => v === '' || v == null ? '' : String(v)
const decimal = v => typeof v === 'string' && /^[0-9]{1,10}(\.[0-9]{1,10})?$/.test(v)

const emptyTerms = () => ({ waiting: false, free_wait_minutes: '', waiting_hour_rate: '', tolls: 'SEPARATE_AT_COST', parking: 'SEPARATE_AT_COST', returnSeparate: false, returnCharge: '', returnNotes: '' })
const emptyKm = () => ({ on: false, base_charge: '', included_km: '', extraKm: false, extra_km_rate: '' })
const emptyPackage = () => ({ on: false, day_charge: '', included_hours_per_day: '', included_km_per_day: '', extraKm: false, extra_km_rate: '', extraHours: false, extra_hour_rate: '' })

const isMine = r => r.direction === 'ONE_WAY' && ((['DISTANCE', 'DAY_HIRE'].includes(r.method) && ['ANY', 'AREA'].includes(r.coverage.kind)) || (r.method === 'FIXED_ROUTE' && r.coverage.kind === 'ROUTE' && r.coverage.places.length === 2))
const charged = (r, key) => (r.extra_policy?.[key] ?? 'CHARGED') === 'CHARGED'

function hydrate(rules) {
  const mine = rules.filter(isMine), others = rules.filter(r => !isMine(r))
  const km = mine.find(r => r.method === 'DISTANCE'), pkg = mine.find(r => r.method === 'DAY_HIRE')
  const base = km || pkg || mine.find(r => r.method === 'FIXED_ROUTE')
  const state = { others, terms: emptyTerms(), km: emptyKm(), pkg: emptyPackage(), fixed: [], from: today() }
  if (base) {
    state.terms = { waiting: charged(base, 'WAITING') && Number(base.waiting_hour_rate) > 0, free_wait_minutes: num(base.free_wait_minutes), waiting_hour_rate: num(base.waiting_hour_rate), tolls: base.tolls, parking: base.parking, returnSeparate: base.return_to_base === 'SEPARATE_FIXED', returnCharge: num(base.return_to_base_charge), returnNotes: base.return_to_base_notes || '' }
  }
  if (km) state.km = { id: km.id, on: true, coverage: km.coverage, pickup_area: km.pickup_area, base_charge: num(km.base_charge), included_km: num(km.included_km), extraKm: (km.extra_policy?.EXTRA_KM ?? 'CHARGED') === 'CHARGED', extra_km_rate: num(km.extra_km_rate) }
  if (pkg) state.pkg = { id: pkg.id, on: true, coverage: pkg.coverage, pickup_area: pkg.pickup_area, day_charge: num(pkg.day_charge), included_hours_per_day: num(pkg.included_hours_per_day), included_km_per_day: num(pkg.included_km_per_day), extraKm: (pkg.extra_policy?.EXTRA_KM ?? 'CHARGED') === 'CHARGED', extra_km_rate: num(pkg.extra_km_rate), extraHours: (pkg.extra_policy?.EXTRA_HOURS ?? 'CHARGED') === 'CHARGED', extra_hour_rate: num(pkg.extra_hour_rate) }
  state.fixed = mine.filter(r => r.method === 'FIXED_ROUTE').map(r => ({ id: r.id, from: r.coverage.places[0], to: r.coverage.places[1], fixed_fare: num(r.fixed_fare), kept: r }))
  if (base) state.from = base.effective_from
  return state
}

function build(state) {
  const { terms } = state
  const common = (id, label, method, coverage, pickup, extraPolicy) => ({
    id: id || crypto.randomUUID(), label: label.slice(0, 120), method, direction: 'ONE_WAY', effective_from: state.from, effective_until: null,
    coverage, pickup_area: pickup, free_wait_minutes: terms.waiting ? terms.free_wait_minutes : zero, waiting_hour_rate: terms.waiting ? terms.waiting_hour_rate : zero,
    return_to_base: terms.returnSeparate ? 'SEPARATE_FIXED' : 'INCLUDED', return_to_base_charge: terms.returnSeparate ? terms.returnCharge : null,
    return_to_base_notes: (terms.returnNotes || '').trim() || 'Return to base is included in the rates.', tolls: terms.tolls, parking: terms.parking, other_charges: [],
    change_limits: { added_km: zero, added_hours: zero, added_wait_minutes: zero, added_amount: zero },
    extra_policy: { WAITING: terms.waiting ? 'CHARGED' : 'NOT_OFFERED', ...extraPolicy },
  })
  const out = [...state.others]
  const where = 'General'
  if (state.km.on) {
    const k = state.km
    out.push(withExtraPolicy({ ...common(state.km.id, `Per km · ${where}`, 'DISTANCE', k.coverage || { kind: 'ANY', places: null, area: null }, k.pickup_area || null, { EXTRA_KM: k.extraKm ? 'CHARGED' : 'NOT_OFFERED' }), departure: null,
      base_charge: k.base_charge, included_km: k.included_km, extra_km_rate: k.extraKm ? k.extra_km_rate : zero, night_km_rate: zero }))
  }
  if (state.pkg.on) {
    const p = state.pkg
    out.push(withExtraPolicy({ ...common(state.pkg.id, `Package · ${where}`, 'DAY_HIRE', p.coverage || { kind: 'ANY', places: null, area: null }, p.pickup_area || null, { EXTRA_KM: p.extraKm ? 'CHARGED' : 'NOT_OFFERED', EXTRA_HOURS: p.extraHours ? 'CHARGED' : 'NOT_OFFERED', OVERNIGHT: 'NOT_OFFERED' }), departure: null,
      day_charge: p.day_charge, included_km_per_day: p.included_km_per_day, included_hours_per_day: p.included_hours_per_day, extra_km_rate: p.extraKm ? p.extra_km_rate : zero, extra_hour_rate: p.extraHours ? p.extra_hour_rate : zero, night_km_rate: zero, overnight_driver_cost: zero }))
  }
  for (const f of state.fixed) {
    out.push(withExtraPolicy({ ...common(f.id, `${String(f.from.label).split(',')[0]} → ${String(f.to.label).split(',')[0]}`, 'FIXED_ROUTE', { kind: 'ROUTE', places: [f.from, f.to] }, null, {}), departure: { kind: 'ANY_TIME' }, fixed_fare: f.fixed_fare }))
  }
  return out
}

function problems(state, scope) {
  const list = []
  if (!state.km.on && !state.pkg.on && !state.fixed.length) list.push('Turn on at least one price first: Per km, Day package or Fixed routes.')
  const need = (ok, text) => { if (!ok) list.push(text) }
  if (state.terms.waiting) { need(decimal(state.terms.free_wait_minutes), 'Enter the free waiting minutes (0 if none).'); need(decimal(state.terms.waiting_hour_rate), 'Enter the extra waiting rate per hour.') }
  if (state.terms.returnSeparate) need(decimal(state.terms.returnCharge), 'Enter the return-to-base charge.')
  const k = state.km
  if (k.on) { need(decimal(k.base_charge) && decimal(k.included_km), 'Per km: enter the base charge and the included km.'); if (k.extraKm) need(decimal(k.extra_km_rate), 'Per km: enter the extra km rate.') }
  const p = state.pkg
  if (p.on) {
    need(decimal(p.day_charge) && decimal(p.included_km_per_day) && decimal(p.included_hours_per_day), 'Package: enter the price, the hours and the km.')
    need(Number(p.included_hours_per_day) > 0 && Number(p.included_hours_per_day) <= 24, 'Package: hours must be more than 0 and at most 24.')
    if (p.extraKm) need(decimal(p.extra_km_rate), 'Package: enter the extra km rate.')
    if (p.extraHours) need(decimal(p.extra_hour_rate), 'Package: enter the extra hour rate.')
  }
  state.fixed.forEach((f, i) => { need(f.from && f.to, `Fixed route ${i + 1}: choose both places.`); need(decimal(f.fixed_fare), `Fixed route ${i + 1}: enter the price.`) })
  return list
}

export default function OwnerHire() {
  const location = useLocation(), query = new URLSearchParams(location.search)
  const [vehicles, setVehicles] = useState([]), [services, setServices] = useState([]), [vehicle, setVehicle] = useState(() => query.get('vehicle') || ''), [scope, setScope] = useState(() => query.get('type') || 'LOCAL')
  const [saved, setSaved] = useState(null), [state, setState] = useState(null), [tab, setTab] = useState(0), [error, setError] = useState(null), [notice, setNotice] = useState(''), [busy, setBusy] = useState(false), [slot, setSlot] = useState(null), [user, setUser] = useState(null)
  useEffect(() => { if (!hasSession()) return; Promise.all([api('/users/me'), api('/owners/me/vehicles'), api('/service-types')]).then(([u, v, s]) => { setUser(u); setVehicles(v.items); setServices(s.items); setVehicle(cur => cur || (v.items[0] && v.items[0].id) || '') }).catch(setError) }, [])
  const service = services.find(s => s.pricing_scope === scope)
  useEffect(() => {
    setSaved(null); setState(null); setNotice(''); setError(null)
    if (!vehicle || !service) return
    let live = true
    api(`/vehicles/${vehicle}/services`).then(r => { if (!live) return; const row = (r.items || []).find(x => x.service_type_id === service.id) || { service_type_id: service.id, version: 0, rules: [], event_packages: [], cash_accepted: false }; setSaved(row); setState(scope === 'EVENT' ? null : hydrate(row.rules || [])) }).catch(e => { if (live) setError(e) })
    return () => { live = false }
  }, [vehicle, service?.id, scope])
  const set = (key, patch) => setState(s => ({ ...s, [key]: { ...s[key], ...patch } }))
  const Footer = ({ children }) => slot ? createPortal(children, slot) : null
  const issues = useMemo(() => state ? problems(state, scope) : [], [state, scope])
  async function save() {
    setError(null); setNotice('')
    if (issues.length) { setError({ message: issues[0] }); return }
    const rules = build(state), found = validateRateRules(rules)
    if (found.length) { setError({ message: found[0].message }); return }
    setBusy(true)
    try {
      const result = await api(`/vehicles/${vehicle}/services`, { method: 'PUT', body: JSON.stringify({ service_type_id: service.id, expected_version: saved.version, enabled: true, currency: 'LKR', rules }) })
      setSaved(result); setState(hydrate(result.rules || rules)); setNotice(t('Prices saved. Passengers get a fresh quote for each trip.'))
    } catch (e) { setError(e) } finally { setBusy(false) }
  }
  if (!hasSession()) return <Navigate to="/login" replace/>
  if (user && !user.approved_roles.includes('OWNER')) return <Navigate to="/" replace/>
  const isEvent = scope === 'EVENT', ready = saved && (isEvent || state)
  const tabNames = isEvent ? ['Packages', 'Extras and terms'] : ['Per km', 'Day package', 'Fixed routes', 'Extras and terms']
  const tabs = ready ? (isEvent ? [['Packages', 'calendar'], ['Extras and terms', 'settings']] : [['Per km', 'chart'], ['Day package', 'calendar'], ['Fixed routes', 'route'], ['Extras and terms', 'settings']]).map(([label, icon], i) => ({ label: t(label), icon, active: tab === i, onClick: () => setTab(i) })) : undefined
  const fixedList = state?.fixed || []
  return <><Header/><FlowShell heading={t('Hire prices')} icon="wallet" title={t(TYPES.find(x => x[0] === scope)[1]) + ' · ' + t(tabNames[tab])}
    info={t('Set prices for one hire type at a time. A fixed route price is used first, then your package, then per km. If nothing matches, the Passenger asks you for a price.')} tabs={tabs}>
    <Compact.Provider value={true}>
      <ErrorNotice error={error}/>{fieldErrors(error).length > 0 && <ul className="field-error" role="alert">{fieldErrors(error).map((f, i) => <li key={i}>{f.message}</li>)}</ul>}
      {notice && <p className="notice success" role="status">{notice}</p>}
      <div className="rate-grid hire-top">
        <Field label="Vehicle"><select value={vehicle} onChange={e => setVehicle(e.target.value)}><option value="">{t('Choose your vehicle')}</option>{vehicles.map(v => <option key={v.id} value={v.id}>{v.label}</option>)}</select></Field>
        <div className="rate-field"><label>{t('Hire type')}</label><div className="status-chips">{TYPES.map(([code, name]) => <Chip key={code} selected={scope === code} onClick={() => { setScope(code); setTab(0) }}>{t(name)}</Chip>)}</div></div>
      </div>
      {!vehicle && !error && <p className="flow-note">{vehicles.length ? t('Choose a vehicle to set its prices.') : <>{t('You have no vehicles yet.')} <Link to="/owner/vehicles">{t('Add a vehicle first')}</Link></>}</p>}
      {vehicle && isEvent && ready && tab === 0 && <EventPackages key={`${vehicle}-${saved.version}`} vehicle={{ id: vehicle }} Footer={Footer} onServiceLoaded={setSaved}/>}
      {vehicle && isEvent && service && !ready && !error && <p role="status">{t('Loading saved rates…')}</p>}
      {vehicle && !isEvent && !service && services.length > 0 && <p role="status">{t('This hire type is not set up yet. An Admin must activate it first.')}</p>}
      {vehicle && !isEvent && service && !ready && !error && <p role="status">{t('Loading saved rates…')}</p>}

      {ready && !isEvent && tab === 0 && <div className="hire-pane flow-wizard-form">
        <Checkbox checked={state.km.on} onChange={e => set('km', { on: e.target.checked })}>{t('I price this hire type per km')}</Checkbox>
        {state.km.on && <div className="rate-grid">
          <AmountField name="base_charge" label="Starting price" help="Charged for every trip; it covers the included km." value={state.km.base_charge} onChange={v => set('km', { base_charge: v })}/>
          <AmountField name="included_km" label="Included distance" help="Km covered by the starting price. Enter 0 if none." value={state.km.included_km} onChange={v => set('km', { included_km: v })}/>
          <div className="hire-check"><Checkbox checked={state.km.extraKm} onChange={e => set('km', { extraKm: e.target.checked })}>{t('Charge for km beyond the included distance')}</Checkbox></div>
          {state.km.extraKm && <AmountField name="extra_km_rate" label="Rate per extra km" help="Charged for each km after the included distance." value={state.km.extra_km_rate} onChange={v => set('km', { extra_km_rate: v })}/>}
        </div>}
      </div>}

      {ready && !isEvent && tab === 1 && <div className="hire-pane flow-wizard-form">
        <Checkbox checked={state.pkg.on} onChange={e => set('pkg', { on: e.target.checked })}>{t('I offer a fixed package (price for set hours and km)')}</Checkbox>
        {state.pkg.on && <div className="rate-grid">
          <AmountField name="day_charge" label="Package price" help="One price for the hours and km below." value={state.pkg.day_charge} onChange={v => set('pkg', { day_charge: v })}/>
          <AmountField name="included_hours_per_day" label="Included hours" help="Service hours covered by the package, at most 24." value={state.pkg.included_hours_per_day} onChange={v => set('pkg', { included_hours_per_day: v })}/>
          <AmountField name="included_km_per_day" label="Included distance" help="Km covered by the package." value={state.pkg.included_km_per_day} onChange={v => set('pkg', { included_km_per_day: v })}/>
          <div className="hire-check"><Checkbox checked={state.pkg.extraKm} onChange={e => set('pkg', { extraKm: e.target.checked })}>{t('Charge for extra km')}</Checkbox></div>
          {state.pkg.extraKm && <AmountField name="extra_km_rate" label="Rate per extra km" help="Charged for each km beyond the package km." value={state.pkg.extra_km_rate} onChange={v => set('pkg', { extra_km_rate: v })}/>}
          <div className="hire-check"><Checkbox checked={state.pkg.extraHours} onChange={e => set('pkg', { extraHours: e.target.checked })}>{t('Charge for extra hours')}</Checkbox></div>
          {state.pkg.extraHours && <AmountField name="extra_hour_rate" label="Rate per extra hour" help="Charged for each hour beyond the package hours." value={state.pkg.extra_hour_rate} onChange={v => set('pkg', { extra_hour_rate: v })}/>}
        </div>}
      </div>}

      {ready && !isEvent && tab === 2 && <div className="hire-pane flow-wizard-form">
        <p className="flow-note">{t('A fixed price from one place to another. It is used before your package or per km rates.')}</p>
        <div className="hire-fixed">{fixedList.map((f, i) => <div className="hire-fixed-row" key={f.id}>
          <PlaceSearch label="From" value={f.from} onChange={place => setState(s => ({ ...s, fixed: s.fixed.map((x, n) => n === i ? { ...x, from: place } : x) }))}/>
          <PlaceSearch label="To" value={f.to} onChange={place => setState(s => ({ ...s, fixed: s.fixed.map((x, n) => n === i ? { ...x, to: place } : x) }))}/>
          <AmountField name="fixed_fare" label="Price" help="One price for this trip from the first place to the second." value={f.fixed_fare} onChange={v => setState(s => ({ ...s, fixed: s.fixed.map((x, n) => n === i ? { ...x, fixed_fare: v } : x) }))}/>
          <button type="button" className="ui-button ui-button-secondary" onClick={() => setState(s => ({ ...s, fixed: s.fixed.filter((_, n) => n !== i) }))}>{t('Remove')}</button>
        </div>)}</div>
        <button type="button" className="ui-button ui-button-secondary" disabled={fixedList.length >= 20} onClick={() => setState(s => ({ ...s, fixed: [...s.fixed, { id: crypto.randomUUID(), from: null, to: null, fixed_fare: '' }] }))}>{t('Add a fixed route')}</button>
      </div>}

      {ready && !isEvent && tab === 3 && <div className="hire-pane flow-wizard-form">
        <div className="rate-grid">
          <div className="hire-check"><Checkbox checked={state.terms.waiting} onChange={e => set('terms', { waiting: e.target.checked })}>{t('Charge for waiting time')}</Checkbox></div>
          <Field label="Tolls"><select value={state.terms.tolls} onChange={e => set('terms', { tolls: e.target.value })}><option value="INCLUDED">{t('Included in my prices')}</option><option value="SEPARATE_AT_COST">{t('Passenger pays the actual cost')}</option></select></Field>
          {state.terms.waiting && <><AmountField name="free_wait_minutes" label="Free waiting" help="Minutes of waiting that are free on each booking. Enter 0 if none." value={state.terms.free_wait_minutes} onChange={v => set('terms', { free_wait_minutes: v })}/><AmountField name="waiting_hour_rate" label="Extra waiting rate" help="Charged per hour after the free minutes, in proportion to the minutes used." value={state.terms.waiting_hour_rate} onChange={v => set('terms', { waiting_hour_rate: v })}/></>}
          <Field label="Parking"><select value={state.terms.parking} onChange={e => set('terms', { parking: e.target.value })}><option value="INCLUDED">{t('Included in my prices')}</option><option value="SEPARATE_AT_COST">{t('Passenger pays the actual cost')}</option></select></Field>
          <div className="hire-check"><Checkbox checked={state.terms.returnSeparate} onChange={e => set('terms', { returnSeparate: e.target.checked })}>{t('Charge separately for the empty return to base')}</Checkbox></div>
          {state.terms.returnSeparate && <AmountField name="return_to_base_charge" label="Return-to-base charge" help="One extra charge added to the booking for driving back empty." value={state.terms.returnCharge} onChange={v => set('terms', { returnCharge: v })}/>}
          <Field label="Note for the Passenger" optional help="The Passenger reads this before booking, for example: Return to Jaffna is included in the fare."><input maxLength={500} value={state.terms.returnNotes} onChange={e => set('terms', { returnNotes: e.target.value })}/></Field>
        </div>
      </div>}

      {ready && ((isEvent && tab === 1) || (!isEvent && tab === 3)) && <CashSwitch vehicle={vehicle} service={service.id} saved={saved} onSaved={setSaved}/>}

      {ready && !isEvent && <div className="flow-actions"><span className="footer-slot" ref={setSlot}/><button type="button" className="ui-button ui-button-primary" disabled={busy} onClick={save}>{busy ? t('Saving…') : t('Save prices')}</button></div>}
      {isEvent && vehicle && <div className="flow-actions"><span className="footer-slot" ref={setSlot}/></div>}
    </Compact.Provider>
  </FlowShell></>
}
