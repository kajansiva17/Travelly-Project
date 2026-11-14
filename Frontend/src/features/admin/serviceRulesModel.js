/* Checks for the Admin forms of the service rules (the server checks again). Return the English key for t(), or '' when the value is fine. Pure. */
export function checkMinKm(value) {
  const text = String(value ?? '').trim()
  return /^\d{1,4}$/.test(text) && Number(text) <= 2000 ? '' : 'Enter a whole number of km from 0 to 2000.'
}
export function checkAirports(list) {
  const rows = Array.isArray(list) ? list : []
  const codes = new Set()
  for (const item of rows) {
    const code = String(item?.code ?? '').trim().toUpperCase(), name = String(item?.name ?? '').trim().replace(/\s+/g, ' ')
    const lat = Number(String(item?.latitude ?? '').trim()), lon = Number(String(item?.longitude ?? '').trim())
    if (!/^[A-Z0-9]{2,6}$/.test(code)) return 'Each airport needs a code of 2 to 6 letters or digits.'
    if (name.length < 3) return 'Each airport needs a name.'
    if (!Number.isFinite(lat) || lat < 5 || lat > 10 || !Number.isFinite(lon) || lon < 79 || lon > 82.5) return 'Each airport needs a position inside Sri Lanka (latitude 5 to 10, longitude 79 to 82.5).'
    if (codes.has(code)) return 'Each airport code can be used once.'
    codes.add(code)
  }
  return ''
}
