import { messages } from './messages.js'

export const languages = [
  { code: 'en', name: 'English' },
  { code: 'ta', name: 'தமிழ்' },
  { code: 'si', name: 'සිංහල' },
]
export const languageKey = 'travelly-language'
const supported = code => languages.some(language => language.code === code)
let language = 'en'
try {
  const saved = globalThis.localStorage?.getItem(languageKey)
  if (supported(saved)) language = saved
} catch { /* Storage can be unavailable in private or restricted browsers. */ }
const listeners = new Set()
const caseKeys = new Map(Object.keys(messages).map(key => [key.toLowerCase(), key]))
export const getLanguage = () => language
export const getLocale = () => ({ en: 'en-LK', ta: 'ta-LK', si: 'si-LK' })[language]
export const subscribeLanguage = listener => { listeners.add(listener); return () => listeners.delete(listener) }
export function setLanguage(code) {
  if (!supported(code) || code === language) return
  language = code
  try { globalThis.localStorage?.setItem(languageKey, code) } catch { /* Selection still works in memory. */ }
  listeners.forEach(listener => listener())
}

// Only explicitly marked interface copy passes through this dictionary.
// Names, locations, evidence and other server/user data stay as supplied.
export function translate(text, code = language, values = {}) {
  if (typeof text !== 'string') return text
  const key = text.trim().replace(/\s+/g, ' ')
  const entry = messages[key] || messages[caseKeys.get(key.toLowerCase())]
  const translated = code === 'en' ? text : entry?.[code]
    ? text.match(/^\s*/)[0] + entry[code] + text.match(/\s*$/)[0]
    : text
  return translated.replace(/\{(\w+)\}/g, (match, key) => Object.hasOwn(values, key) ? String(values[key]) : match)
}
export const t = (text, values) => translate(text, language, values)
