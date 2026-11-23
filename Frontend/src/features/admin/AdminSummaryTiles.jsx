import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { t } from '../../i18n/language.js'
import { api, hasSession } from '../../services/api'
import { BRAND_RED } from '../../components/brandColor.js'

const TILES = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
const ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors'
const GREEN = '#2e8b57'
const GREY = '#6b7280'

/* The numbers on the Admin Command Centre tiles (GET /admin/dashboard-summary); read again every 30 seconds. */
export function useAdminSummary() {
  const [state, setState] = useState({ loading: true, error: null, data: null })
  useEffect(() => {
    if (!hasSession()) return undefined
    let alive = true
    const load = () => api('/admin/dashboard-summary', { cache: 'no-store' }).then(data => alive && setState({ loading: false, error: null, data })).catch(error => alive && setState(old => ({ loading: false, error, data: old.data })))
    load()
    const timer = setInterval(() => { if (!document.hidden) load() }, 30000)
    return () => { alive = false; clearInterval(timer) }
  }, [])
  return state
}

const colour = vehicle => vehicle.on_trip ? BRAND_RED : vehicle.online ? GREEN : GREY

/* Vehicles that sent a position in the last 15 minutes: red = on a trip, green = online (Go online), grey = position only. */
export function LiveVehicleMap({ vehicles }) {
  const holder = useRef(null)
  const map = useRef(null)
  const layer = useRef(null)
  const fitted = useRef(false)
  useEffect(() => {
    const instance = L.map(holder.current, { zoomControl: true, attributionControl: true, zoomSnap: 0.5 }).setView([7.8731, 80.7718], 7)
    L.tileLayer(TILES, { maxZoom: 19, attribution: ATTRIBUTION, referrerPolicy: 'strict-origin-when-cross-origin' }).addTo(instance)
    layer.current = L.layerGroup().addTo(instance)
    map.current = instance
    const watch = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(() => instance.invalidateSize()) : null
    watch?.observe(holder.current)
    return () => { watch?.disconnect(); instance.stop(); instance.remove(); map.current = null; layer.current = null; fitted.current = false }
  }, [])
  useEffect(() => {
    if (!map.current || !layer.current) return
    layer.current.clearLayers()
    vehicles.forEach(vehicle => L.circleMarker([vehicle.latitude, vehicle.longitude], { radius: 7, color: '#fff', weight: 2, fillColor: colour(vehicle), fillOpacity: 1 })
      .bindTooltip(`${vehicle.registration || vehicle.reference}`).addTo(layer.current))
    if (vehicles.length && !fitted.current) {
      map.current.fitBounds(L.latLngBounds(vehicles.map(vehicle => [vehicle.latitude, vehicle.longitude])), { padding: [24, 24], maxZoom: 13 })
      fitted.current = true
    }
  }, [vehicles])
  return <div>
    <div ref={holder} role="img" aria-label={t('Map of vehicles with a recent position')} style={{ height: 220, borderRadius: 8, overflow: 'hidden' }}/>
    <p className="dash-soft" style={{ margin: '6px 0 0' }}>
      <span style={{ color: BRAND_RED }}>{'● '}</span>{t('On a trip')}{'  '}<span style={{ color: GREEN }}>{'● '}</span>{t('Online')}{'  '}<span style={{ color: GREY }}>{'● '}</span>{t('Position only')}{' · '}{vehicles.length}
    </p>
  </div>
}

/* Bookings made on each of the last 7 days (Sri Lanka time). */
export function TrendBars({ days }) {
  const top = Math.max(1, ...days.map(day => day.bookings))
  const total = days.reduce((sum, day) => sum + day.bookings, 0)
  return <div>
    <div role="img" aria-label={t('Bookings in the last 7 days: {value0}', { value0: total })} style={{ display: 'flex', alignItems: 'flex-end', gap: 8, height: 120 }}>
      {days.map(day => <div key={day.date} style={{ flex: 1, textAlign: 'center' }}>
        <div style={{ fontSize: 12 }}>{day.bookings}</div>
        <div style={{ height: Math.max(2, Math.round(day.bookings * 80 / top)), background: BRAND_RED, borderRadius: 3, opacity: day.bookings ? 1 : .25 }}/>
        <div style={{ fontSize: 11, opacity: .7 }}>{day.date.slice(8)}</div>
      </div>)}
    </div>
    <p className="dash-soft" style={{ margin: '6px 0 0' }}>{t('Bookings in the last 7 days: {value0}', { value0: total })}</p>
  </div>
}
