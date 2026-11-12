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

// Date only, e.g. "17 Nov 2026". A plain "YYYY-MM-DD" is read as that calendar day (no time zone shift).
export function formatDate(value, options = {}) {
  if (!value) return ''
  const text = String(value)
  const date = /^\d{4}-\d{2}-\d{2}$/.test(text) ? new Date(Number(text.slice(0, 4)), Number(text.slice(5, 7)) - 1, Number(text.slice(8, 10)), 12) : new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return new Intl.DateTimeFormat(getLanguage() === 'en' ? 'en-GB' : getLocale(), { day: 'numeric', month: 'short', year: 'numeric', ...options }).format(date)
}
