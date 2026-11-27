import { t } from '../../i18n/language.js'
import { useState } from 'react'
import { Icon } from '../../components/components'
import { Thumb } from '../booking/BookingCardParts'

/* Pieces shared by the Owner and Driver people pages (My drivers, My owners, Pay Drivers, Earnings): one card per person,
   a reference strip and small stat cards. They use the same card shape as the booking cards. */

// One person (or one payment) as a card: round photo / first letter, name, a few short lines, chips, and the actions on the right.
export function PersonCard({ name, lines = [], photo, chips = null, actions = null, live = false, tone = '', onPhoto, extra = null, icon = 'user' }) {
  const thumb = <Thumb src={photo} name={name} round icon={icon} size={56}/>
  return <article className={'bc-card pl-card' + (live ? ' is-live' : '') + (tone ? ' is-' + tone : '')}>
    {onPhoto && photo ? <button type="button" className="pl-photo" aria-label={t('View photo of {value0}', { value0: name })} onClick={onPhoto}>{thumb}</button> : thumb}
    <div className="bc-body"><strong className="bc-name">{name}</strong>
      {lines.filter(Boolean).map((line, i) => <span className="bc-sub" key={i}>{line}</span>)}
      {chips && <span className="pl-chips">{chips}</span>}</div>
    {actions && <div className="bc-side pl-side">{actions}</div>}
    {extra && <div className="pl-extra">{extra}</div>}
  </article>
}

// "Your Travelly reference" with a Copy button, so the person can hand it over.
export function ReferenceCard({ reference, hint }) {
  const [copied, setCopied] = useState(false)
  async function copy() { try { await navigator.clipboard.writeText(reference); setCopied(true); setTimeout(() => setCopied(false), 1800) } catch { /* the reference stays visible to copy by hand */ } }
  return <section className="bc-card pl-ref"><span className="pl-ico"><Icon name="shield" size={22}/></span>
    <div className="bc-body"><span className="bc-sub">{t('Your Travelly reference')}</span><strong className="pl-ref-code">{reference}</strong>{hint && <span className="bc-sub">{hint}</span>}</div>
    <button type="button" className="ui-button ui-button-secondary pl-copy" onClick={copy}>{copied ? t('Copied') : t('Copy')}</button></section>
}

// Two or three small figures side by side (for example Confirmed / Waiting).
export function StatStrip({ items }) {
  return <div className="pl-stats">{items.map(item => <div className={'pl-stat' + (item.tone ? ' is-' + item.tone : '')} key={item.label}>
    <span className="pl-ico"><Icon name={item.icon || 'wallet'} size={20}/></span><span className="pl-stat-text"><em>{item.label}</em><strong>{item.value}</strong></span></div>)}</div>
}

// A friendly empty card, kept inside the list area.
export function EmptyCard({ icon = 'user', title, children }) {
  return <div className="bc-card pl-empty"><span className="pl-ico"><Icon name={icon} size={24}/></span><div className="bc-body"><strong className="bc-name">{title}</strong>{children && <span className="bc-sub">{children}</span>}</div></div>
}
