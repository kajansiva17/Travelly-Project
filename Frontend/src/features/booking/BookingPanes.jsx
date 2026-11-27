import { t } from '../../i18n/language.js'
import { Icon } from '../../components/components'
import { InfoTip } from '../../components/ui'
import { codeLabel } from '../../i18n/codeLabels.js'
import ExtraLines from './ExtraLines'

const num = (v, min = 0) => { const n = Number(v); return Number.isFinite(n) ? n.toLocaleString('en-US', { minimumFractionDigits: min, maximumFractionDigits: 2 }) : v }

/* A short card telling the Passenger whether the vehicle is held yet (and the package, for an event). */
export function TripNote({ booking, eventPackage }) {
  const held = Boolean(booking.vehicle_committed)
  const text = held
    ? t('The vehicle is reserved for this agreed interval, including while another Driver is sought.')
    : t('This enquiry does not reserve the vehicle. Owner commitment and operational checks are still required.')
  return <section className={'bc-card tp-note' + (held ? ' is-held' : '')}>
    <span className="tp-ico"><Icon name={held ? 'check' : 'clock'} size={20}/></span>
    <div className="bc-body">
      {eventPackage && <strong className="bc-name">{t('Package')}: {eventPackage.name} · {t('{value0} hours', { value0: eventPackage.hours })}</strong>}
      <span className="bc-sub">{text}</span>
    </div>
  </section>
}

/* The price as two cards: what is charged, and the rules in a numbered list. Only non-zero charges are listed. */
export function PriceCards({ title, info, price, terms, newTime, action }) {
  const rows = (price.breakdown || []).filter(row => Number(row.amount) !== 0)
  return <section className="pp-wrap">
    <header className="pp-head"><h2>{t(title)}</h2><span className="pp-method">{codeLabel(price.method)}{t(' · LKR')}</span>{info}
      <InfoTip>{(price.exclusions || []).map(text => <span key={text} className="flow-tip-line">{t(text)}</span>)}<span className="flow-tip-line">{t('Separately payable actual costs are not included in the covered total.')}</span></InfoTip></header>
    {newTime}
    <div className="pp-grid">
      <section className="bc-card pp-card">
        <h3>{t('Charge')}</h3>
        <ul className="pp-rows">{rows.map(row => <li key={row.code}><span className="pp-label">{t(row.label)}<small>{num(row.quantity)} × {num(row.rate)}</small></span><strong>{row.kind === 'CREDIT' ? '−' : ''}{num(row.amount, 2)}</strong></li>)}</ul>
        <div className="pp-total"><span>{t('Covered total')}</span><strong>{t('LKR ')}{num(price.total, 2)}</strong></div>
        <div className="pp-extras"><ExtraLines price={price}/></div>
      </section>
      {terms && <section className="bc-card pp-card pp-terms">{terms}</section>}
    </div>
    {action}
  </section>
}
