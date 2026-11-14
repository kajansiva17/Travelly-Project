/* Service rules answered by the server when a trip does not fit the chosen service (owner decisions 15 Nov 2026):
   AIRPORT_LOCATION_REQUIRED (Airport hire needs an airport as pickup or destination) and
   TRIP_TOO_SHORT_FOR_LONG_DISTANCE (field_errors: distance_km and min_distance_km as text).
   The answer is the English key for t() and its values, so the page shows it in the chosen language. Pure, no network. */
const valueOf = (error, field) => {
  const row = (Array.isArray(error?.field_errors) ? error.field_errors : Array.isArray(error?.fields) ? error.fields : []).find(item => item?.field === field)
  return row?.message == null ? '' : String(row.message)
}
export function serviceRuleError(error) {
  if (error?.code === 'AIRPORT_LOCATION_REQUIRED') return { code: error.code, key: 'Airport hire is for trips to or from an airport. Choose an airport as the pickup or the destination, or choose Local hire.', params: {} }
  if (error?.code === 'TRIP_TOO_SHORT_FOR_LONG_DISTANCE') {
    const km = valueOf(error, 'distance_km'), minimum = valueOf(error, 'min_distance_km')
    if (km && minimum) return { code: error.code, key: 'This trip is about {value0} km. Long distance is for trips of {value1} km or more. Choose Local hire.', params: { value0: km, value1: minimum } }
    return { code: error.code, key: null, text: error.message, params: {} }
  }
  return null
}
// The card text of Long distance: "One day or multi-day" plus the minimum when the service has one.
export const minimumKm = service => { const n = Number(service?.min_distance_km); return Number.isFinite(n) && n > 0 ? n : null }
