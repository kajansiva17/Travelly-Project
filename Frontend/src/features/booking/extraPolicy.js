/* Extra charge choices (contract 03XP) and nearby vehicle order (contract 03WH): pure rules shared by the Owner rate form,
   the Passenger price screens and the vehicle search list. */

// Owner: which extras a pricing method uses, the rate fields each one controls, and the three modes.
export const EXTRA_KEYS_BY_METHOD = {
  DISTANCE: ['WAITING', 'EXTRA_KM'],
  DAY_HIRE: ['WAITING', 'EXTRA_KM', 'EXTRA_HOURS', 'OVERNIGHT'],
  FIXED_ROUTE: ['WAITING'],
}
export const EXTRA_RATE_FIELDS = {
  WAITING: ['free_wait_minutes', 'waiting_hour_rate'],
  EXTRA_KM: ['extra_km_rate'],
  EXTRA_HOURS: ['extra_hour_rate'],
  OVERNIGHT: ['overnight_driver_cost'],
}
export const EXTRA_MODES = ['NOT_OFFERED', 'FREE', 'CHARGED']
export const MODE_LABEL = { NOT_OFFERED: 'Not offered', FREE: 'No extra charge', CHARGED: 'Charge' }
export const EXTRA_LABEL = { WAITING: 'Waiting', EXTRA_KM: 'Extra distance', EXTRA_HOURS: 'Extra hours', OVERNIGHT: 'Overnight stay' }

export const extraKeys = method => EXTRA_KEYS_BY_METHOD[method] || []
// A rule without extra_policy (or without that key) behaves as CHARGED.
export const modeOf = (rule, key) => (EXTRA_MODES.includes(rule?.extra_policy?.[key]) ? rule.extra_policy[key] : 'CHARGED')

// The rule as the API takes it: only the extras the method uses, and "0" for the rates of an extra that is not charged.
export function withExtraPolicy(rule) {
  const out = { ...rule }
  const policy = {}
  for (const key of extraKeys(rule.method)) {
    const mode = modeOf(rule, key)
    policy[key] = mode
    if (mode !== 'CHARGED') for (const field of EXTRA_RATE_FIELDS[key]) out[field] = '0'
  }
  out.extra_policy = policy
  return out
}

// Passenger: one entry per extra in calculation.extra_policies. The price may be the calculation itself or hold it.
export const policiesOf = price => {
  const list = price?.extra_policies || price?.calculation?.extra_policies
  return Array.isArray(list) ? list.filter(entry => entry?.code) : []
}
const lkr = value => `LKR ${Number(value || 0).toLocaleString('en-LK', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
// {label, key, params}: the English key and values for t(); null when the CHARGED entry has no rate to show.
export function extraLine(entry) {
  const label = EXTRA_LABEL[entry.code] || entry.code
  if (entry.mode === 'NOT_OFFERED') return { code: entry.code, label, key: 'Not available' }
  if (entry.mode === 'FREE') return { code: entry.code, label, key: 'No extra charge' }
  if (entry.code === 'WAITING') return { code: entry.code, label, key: 'First {value0} minutes free, then {value1} per hour', params: { value0: Number(entry.free_minutes || 0), value1: lkr(entry.hour_rate) } }
  if (entry.code === 'EXTRA_KM') return { code: entry.code, label, key: '{value0} per km', params: { value0: lkr(entry.km_rate) } }
  if (entry.code === 'EXTRA_HOURS') return { code: entry.code, label, key: '{value0} per hour', params: { value0: lkr(entry.hour_rate) } }
  if (entry.code === 'OVERNIGHT') return { code: entry.code, label, key: '{value0} per overnight stay', params: { value0: lkr(entry.cost) } }
  return { code: entry.code, label, key: 'Not available' }
}
export const extraLines = price => policiesOf(price).map(extraLine)

// Search order (03WH): the server order is kept; near entries first, then those with near false. Nothing is hidden.
export const isNear = entry => entry?.near !== false
export const orderNearFirst = list => [...(list || []).filter(isNear), ...(list || []).filter(entry => !isNear(entry))]
// "about N km away" value (one decimal at most) or null; location_source is never shown.
export function distanceValue(entry) {
  if (entry?.distance_km === null || entry?.distance_km === undefined || entry?.distance_km === '') return null
  const n = Number(entry.distance_km)
  return Number.isFinite(n) ? String(Math.round(n * 10) / 10) : null
}
/* One page-ordered list: priced vehicles, then "ask the Owner" vehicles, each part near first. Headings sit before the first entry
   of a part on a page: 'ASK' (Ask the Owner for a price) and 'FAR' (Farther away). */
export function searchEntries(result) {
  const priced = orderNearFirst(result?.items).map(entry => ({ ...entry, quote_required: false }))
  const requested = result?.quote_on_request || []
  const confirmations = orderNearFirst(requested.filter(entry => entry.owner_confirmation_required)).map(entry => ({ ...entry, quote_required: true }))
  const asked = orderNearFirst(requested.filter(entry => !entry.owner_confirmation_required)).map(entry => ({ ...entry, quote_required: true }))
  return [...priced, ...confirmations, ...asked]
}
export function headingsBefore(entry, previous) {
  const out = [], far = !isNear(entry)
  if (entry.owner_confirmation_required && !previous?.owner_confirmation_required) out.push('CONFIRM')
  else if (entry.quote_required && (!previous?.quote_required || previous?.owner_confirmation_required)) out.push('ASK')
  if (far && (!previous || previous.quote_required !== entry.quote_required || previous.owner_confirmation_required !== entry.owner_confirmation_required || isNear(previous))) out.push('FAR')
  return out
}

/* Pages of the list: a page never mixes parts, so its heading sits once at the top. */
export function pageEntries(entries, fit) {
  const part = entry => `${entry.quote_required ? 1 : 0}${entry.owner_confirmation_required ? 1 : 0}${isNear(entry) ? 0 : 1}`
  const pages = []
  let i = 0
  while (i < entries.length) {
    const first = entries[i], capacity = Math.max(1, fit), page = []
    while (i < entries.length && page.length < capacity && part(entries[i]) === part(first)) page.push(entries[i++])
    pages.push(page)
  }
  return pages
}
