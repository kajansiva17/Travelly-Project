import { t } from '../../i18n/language.js'
import { extraLines } from './extraPolicy'

/* What an extra costs before booking (03XP): "Not available", "No extra charge" or the rate. Compact on the vehicle card,
   full (with a heading) on the quote and booking pages. Nothing is shown when the price has no extra_policies. */
export default function ExtraLines({ price, compact = false }) {
  const lines = extraLines(price)
  if (!lines.length) return null
  const list = <ul className={compact ? 'extra-lines extra-lines-compact' : 'extra-lines'} aria-label={t('Extra charges')}>
    {lines.map(line => <li key={line.code}><span>{t(line.label)}{compact ? ':' : ''}</span> <span>{t(line.key, line.params)}</span></li>)}</ul>
  return compact ? list : <><p className="extra-lines-title">{t('Extra charges')}</p>{list}</>
}
