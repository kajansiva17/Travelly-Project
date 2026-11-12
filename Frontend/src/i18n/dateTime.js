import { getLanguage, getLocale } from './language.js'

// One unambiguous date and time everywhere, e.g. "20 Nov 2026, 8:00 AM": the month is always a word, never dd/mm vs mm/dd.
// Uses the app language; pass { timeZone } to show another zone (default: the device).
export function formatDateTime(value, options = {}) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const base = { day: 'numeric', month: 'short', year: 'numeric', hour: 'numeric', minute: '2-digit', ...options }
  if (getLanguage() !== 'en') return new Intl.DateTimeFormat(getLocale(), base).format(date)
  const parts = Object.fromEntries(new Intl.DateTimeFormat('en-GB', { ...base, hour12: true }).formatToParts(date).map(p => [p.type, p.value]))
  return `${parts.day} ${parts.month} ${parts.year}, ${parts.hour}:${parts.minute} ${String(parts.dayPeriod || '').toUpperCase()}`.trim()
}
