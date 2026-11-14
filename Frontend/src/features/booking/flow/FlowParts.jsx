import { t } from '../../../i18n/language.js'
import { useEffect, useState } from 'react'
import { Link } from '../../passenger/travelRouter'
import { Icon } from '../../../components/components'
import VehiclePhoto from '../../../components/VehiclePhoto'
import { Stepper, Tabs, ServiceTile, InfoTip } from '../../../components/ui'
import { useWorkspace } from '../../../context/workspaceContext'
import ExtraLines from '../ExtraLines'

/* Presentational parts of the Travel & Booking flow. The passenger wizard
   (/travel/book/*) and the owner / driver / admin personal booking page
   (/<role>/personal/hire) both render through these, so the layout is the same.
   They contain no fetching, storage or workflow decisions; every value shown is
   passed in by the caller from data the existing API calls already return. */

const photos = '/images/travelly/landing-2026-11-07/'
export const flowImage = (service, duration) => ({
  airport: photos + 'home-airport.png',
  local: photos + 'home-local.png',
  event: photos + 'home-hire.png',
  rental: photos + 'home-rentals.png',
  ticket: photos + 'home-tickets.png',
  'long-distance': photos + (duration === 'MULTI_DAY' ? 'home-multi-day.png' : 'home-long-distance.png'),
}[service] || null)

/* Page frame: heading, optional tabs, stepper, main card and Trip summary. */
/* Public (signed-out) pages have no workspace shell: mark the body so the same compact, no-scroll flow layout applies. */
function useStandaloneFlow() {
  const workspace = useWorkspace()
  useEffect(() => {
    if (workspace) return undefined
    const body = document.body
    const place = () => { const header = document.querySelector('.site-header'); body.style.setProperty('--workspace-header-height', `${Math.ceil(header ? header.getBoundingClientRect().bottom : 90)}px`) }
    body.classList.add('flow-standalone'); place(); window.addEventListener('resize', place)
    return () => { body.classList.remove('flow-standalone'); body.style.removeProperty('--workspace-header-height'); window.removeEventListener('resize', place) }
  }, [workspace])
}

export function FlowShell({ title, subtitle, icon = 'calendar', info, tabs, steps, current = 0, onStepSelect, summary, card = true, heading = 'Travel & Booking', stepperLabel = 'Booking progress', children }) {
  useStandaloneFlow()
  const body = card
    ? <section className="flow-card ui-card">
        <header className="flow-card-head"><span className="flow-card-icon"><Icon name={icon} size={26} aria-hidden="true"/></span><div><h2>{t(title)}{info && <InfoTip>{info}</InfoTip>}</h2>{subtitle && <p>{t(subtitle)}</p>}</div></header>
        {children}
      </section>
    : children
  return <main className="flow-page" id="main">
    <div className="flow-top"><h1 className="flow-heading">{heading}</h1>{tabs && <Tabs label={heading} items={tabs}/>}</div>
    {steps && <div className="flow-stepper ui-card"><Stepper steps={steps} current={current + 1} label={stepperLabel} onSelect={onStepSelect}/></div>}
    <div className={`flow-body${summary ? ' has-summary' : ''}`}>
      <div className="flow-main">{body}</div>
      {summary}
    </div>
  </main>
}

/* Shared compact state card (loading / access denied / unavailable): one glass card, centred, no scroll. */
export function StateCard({ icon = 'shield', title, children, actions, busy = false }) {
  return <main className="flow-page" id="main" role={busy ? 'status' : undefined}>
    <section className="flow-card ui-card state-card">
      <span className="flow-card-icon">{busy ? <span className="spinner"/> : <Icon name={icon} size={30} aria-hidden="true"/>}</span>
      <h1>{title}</h1>
      {children}
      {actions && <div className="state-card-actions">{actions}</div>}
    </section>
  </main>
}

/* Tiles for choosing a service. items: [{ id, icon, title, description, badge, selected, onChoose }] */
export function ServiceChoice({ items }) {
  return <div className="flow-service-grid" style={{ '--tiles': items.length % 4 === 0 ? 4 : 3 }}>{items.map(item => <ServiceTile key={item.id} icon={item.icon} title={item.title} description={item.description} badge={item.badge} disabled={item.disabled} selected={item.selected} onClick={item.onChoose}/>)}</div>
}

/* Two-or-more way toggle drawn as a segmented control (radio group). */
export function SegmentedChoice({ legend, name, value, options, onChange }) {
  return <fieldset className="flow-segmented"><legend>{legend}</legend>
    {options.map(([key, label]) => <label key={key} className={value === key ? 'is-selected' : ''}>
      <input type="radio" name={name} value={key} checked={value === key} onChange={() => onChange(key)}/><span>{label}</span>
    </label>)}
  </fieldset>
}

/* Back (secondary) on the left, primary action on the right. */
export function FlowActions({ back, children }) {
  return <div className="flow-actions">
    {back ? <Link className="ui-button ui-button-secondary" to={back} state={{ resume: true }}><Icon name="arrow" size={18} className="ui-back-arrow" aria-hidden="true"/><span>{t("Back")}</span></Link> : <span/>}
    {children}
  </div>
}

/* Cover picture in a fixed 16/9 box: never stretched; a neutral placeholder when the picture is missing or fails to load. */
export function CoverImage({ src, className = '', alt = '' }) {
  const [failed, setFailed] = useState(false)
  useEffect(() => { setFailed(false) }, [src])
  if (!src || failed) return <div className={`${className} is-empty`} aria-hidden="true"><Icon name="car" size={30}/></div>
  return <img className={className} src={src} alt={alt} loading="lazy" decoding="async" onError={() => setFailed(true)}/>
}

/* Trip summary aside. rows: [{ icon, label, value }]; rows without a value are skipped. */
export function TripSummary({ title = 'Trip summary', image, rows = [], empty = 'Details appear here as you fill in the form.' }) {
  const shown = rows.filter(row => row && row.value)
  return <aside className="flow-summary ui-card" aria-label={title}>
    <h2><Icon name="document" size={22} aria-hidden="true"/>{title}</h2>
    <CoverImage className="flow-summary-image" src={image}/>
    {shown.length ? <dl>{shown.map(row => <div key={row.label}><dt><Icon name={row.icon || 'check'} size={18} aria-hidden="true"/>{row.label}</dt><dd className={row.nowrap ? 'is-nowrap' : undefined} title={typeof row.value === 'string' ? row.value : undefined}>{row.value}</dd></div>)}</dl> : <p className="flow-summary-empty">{empty}</p>}
  </aside>
}

/* Vehicle card used for matching results and the selected vehicle. */
export function FlowVehicleCard({ vehicle, title, specs = [], chips, action, selected = false }) {
  return <article className={`flow-vehicle ui-card${selected ? ' is-selected' : ''}`}>
    <div className="flow-vehicle-photo">{vehicle?.photos?.[0] ? <VehiclePhoto photo={vehicle.photos[0]} alt={`${title} exterior`}/> : <Icon name="car" size={44} aria-hidden="true"/>}{selected && <span className="flow-vehicle-badge"><Icon name="check" size={14} aria-hidden="true"/>{t("Selected")}</span>}</div>
    <div className="flow-vehicle-info">
      <h3>{title}</h3>
      <ul>{specs.filter(Boolean).map(spec => <li key={spec.label}><Icon name={spec.icon || 'check'} size={17} aria-hidden="true"/><span>{spec.label}</span></li>)}</ul>
      {chips}
    </div>
    {action && <div className="flow-vehicle-action">{action}</div>}
  </article>
}

/* Estimate / quote block: breakdown rows, total and exclusions from the API price. */
export function FlowEstimate({ title = 'Trip estimate (LKR)', price }) {
  if (!price) return null
  return <section className="flow-estimate ui-card"><h2><Icon name="wallet" size={22} aria-hidden="true"/>{title}</h2>
    <dl>{(price.breakdown || []).map(row => <div key={row.code}><dt>{row.label}</dt><dd>{row.kind === 'CREDIT' ? '−' : ''}{row.amount}</dd></div>)}</dl>
    <p className="flow-estimate-total"><span>{t("Total estimate")}</span><strong>{t("LKR")} {price.total}</strong></p>
    <ExtraLines price={price}/>
    {(price.exclusions || []).map(text => <p key={text} className="flow-note">{text}</p>)}
  </section>
}

/* Status banner (request status, confirmation). tone: info | success | warning */
export function FlowBanner({ tone = 'info', icon = 'clock', title, children, aside }) {
  return <div className={`flow-banner flow-banner-${tone}`}><span className="flow-banner-icon"><Icon name={icon} size={30} aria-hidden="true"/></span><div><strong>{title}</strong>{children && <p>{children}</p>}</div>{aside}</div>
}

/* How many result cards fit one screen without scrolling (depends on window height). */
export function useFitCount() {
  const [height, setHeight] = useState(typeof window === 'undefined' ? 900 : window.innerHeight)
  useEffect(() => { const resize = () => setHeight(window.innerHeight); window.addEventListener('resize', resize); return () => window.removeEventListener('resize', resize) }, [])
  return height < 800 ? 2 : height < 1200 ? 4 : 6
}

/* Previous / next page of results, shown in the Back / Next row. */
export function Pager({ page, pages, onPage }) {
  if (pages <= 1) return null
  return <nav className="flow-pager" aria-label="Result pages">
    <button type="button" className="ui-button ui-button-secondary" disabled={page === 0} onClick={() => onPage(page - 1)} aria-label="Previous page"><Icon name="arrow" size={16} className="ui-back-arrow" aria-hidden="true"/></button>
    <span>{page + 1} / {pages}</span>
    <button type="button" className="ui-button ui-button-secondary" disabled={page >= pages - 1} onClick={() => onPage(page + 1)} aria-label="Next page"><Icon name="arrow" size={16} aria-hidden="true"/></button>
  </nav>
}

/* ---- Step-by-step pages (owner forms): one step per screen, nothing scrolls. ---- */
export function useWizard(count) {
  const [step, setStep] = useState(0)
  return { step, count, setStep, back: () => setStep(current => Math.max(0, current - 1)), forward: () => setStep(current => Math.min(count - 1, current + 1)), goTo: index => { if (index < step) setStep(index) } }
}

/* All steps stay mounted so entered values survive Back; only the current one is visible. */
export function WizardPane({ w, index, paneRef, children, className = '' }) {
  return <div ref={paneRef} className={`wizard-pane${className ? ' ' + className : ''}`} hidden={w.step !== index}>{children}</div>
}

/* Native validity of the visible pane: returns { controlName: message } and focuses the first problem. */
export function checkPane(pane) {
  const errors = {}
  let first = null
  pane?.querySelectorAll('input, select, textarea').forEach(el => {
    if (el.disabled || el.checkValidity()) return
    if (!first) first = el
    if (el.name) errors[el.name] = el.validationMessage
  })
  if (first) first.reportValidity()
  return { errors, valid: !first }
}

/* Back on the left, optional extra actions, Next on the right (not shown on the last step). */
export function WizardNav({ w, onNext, extra, nextLabel = 'Next' }) {
  return <div className="flow-actions">
    {w.step > (w.min ?? 0) ? <button type="button" className="ui-button ui-button-secondary" onClick={w.back}><Icon name="arrow" size={18} className="ui-back-arrow" aria-hidden="true"/><span>{t("Back")}</span></button> : <span/>}
    {extra}
    {w.step < w.count - 1 && <button type="button" className="ui-button ui-button-primary" onClick={onNext || w.forward}><span>{nextLabel}</span><Icon name="arrow" size={18} aria-hidden="true"/></button>}
  </div>
}

/* How many compact list rows fit one screen (row height in px) without scrolling. */
export function useRowCount(rowHeight = 64) {
  const [height, setHeight] = useState(typeof window === 'undefined' ? 900 : window.innerHeight)
  useEffect(() => { const resize = () => setHeight(window.innerHeight); window.addEventListener('resize', resize); return () => window.removeEventListener('resize', resize) }, [])
  return Math.max(2, Math.floor((height - 340) / rowHeight))
}

/* Pages a list: returns the current slice and a Pager element. */
export function usePaged(items, size) {
  const [page, setPage] = useState(0)
  const pages = Math.max(1, Math.ceil((items || []).length / size)), current = Math.min(page, pages - 1)
  return { slice: (items || []).slice(current * size, (current + 1) * size), pager: <Pager page={current} pages={pages} onPage={setPage}/>, page: current, pages, setPage }
}

/* How many stop rows (pickup, stops, destination) fit one screen without scrolling. */
export function useMiddleCount() {
  const [height, setHeight] = useState(typeof window === 'undefined' ? 900 : window.innerHeight)
  useEffect(() => { const resize = () => setHeight(window.innerHeight); window.addEventListener('resize', resize); return () => window.removeEventListener('resize', resize) }, [])
  return height < 700 ? 2 : height < 850 ? 3 : height < 1000 ? 5 : height < 1200 ? 8 : 12
}

/* How many photo thumbnails fit one screen (3 per row). */
export function usePhotoCount() {
  const [height, setHeight] = useState(typeof window === 'undefined' ? 900 : window.innerHeight)
  useEffect(() => { const resize = () => setHeight(window.innerHeight); window.addEventListener('resize', resize); return () => window.removeEventListener('resize', resize) }, [])
  return height < 700 ? 3 : height < 900 ? 6 : height < 1200 ? 9 : 12
}

/* How many uploaded-document rows fit one screen (2 per row). */
export function useDocCount() {
  const [height, setHeight] = useState(typeof window === 'undefined' ? 900 : window.innerHeight)
  useEffect(() => { const resize = () => setHeight(window.innerHeight); window.addEventListener('resize', resize); return () => window.removeEventListener('resize', resize) }, [])
  return height < 700 ? 2 : height < 900 ? 4 : 8
}
