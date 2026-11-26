import { t } from '../../i18n/language.js'
import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { publicRead } from '../../services/api'

// Tap the map to choose a place. The server turns the pin into a signed place (nearest named place as the label); onPick(place) gets it.
const TILES = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
const ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors'

export default function PlaceMapPicker({ onPick, start }) {
  const holder = useRef(null), map = useRef(null), pin = useRef(null), pick = useRef(onPick)
  const [status, setStatus] = useState(''), [problem, setProblem] = useState('')
  pick.current = onPick

  useEffect(() => {
    const centre = start ? [Number(start.latitude), Number(start.longitude)] : [7.8731, 80.7718]
    const instance = L.map(holder.current, { zoomControl: true, attributionControl: true }).setView(centre, start ? 15 : 7)
    L.tileLayer(TILES, { maxZoom: 19, attribution: ATTRIBUTION, referrerPolicy: 'strict-origin-when-cross-origin' }).addTo(instance)
    map.current = instance
    const watch = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(() => instance.invalidateSize()) : null
    watch?.observe(holder.current)
    instance.on('click', async event => {
      const { lat, lng } = event.latlng
      if (pin.current) pin.current.setLatLng(event.latlng)
      else pin.current = L.circleMarker(event.latlng, { radius: 10, color: '#fff', weight: 3, fillColor: '#e11d2e', fillOpacity: 1 }).addTo(instance)
      setProblem(''); setStatus(t('Finding the place…'))
      try {
        const result = await publicRead(`/locations/reverse?lat=${lat.toFixed(6)}&lng=${lng.toFixed(6)}`)
        pick.current(result.items[0]); setStatus('')
      } catch (failure) { setStatus(''); setProblem(failure.message || t('Location search is temporarily unavailable. Please try again.')) }
    })
    return () => { watch?.disconnect(); instance.stop(); instance.remove(); map.current = null; pin.current = null }
  }, [])

  return <div className="place-map">
    <p className="place-map-help">{t('Tap the map to choose the place.')}</p>
    <div ref={holder} className="place-map-box"/>
    {status && <p role="status">{status}</p>}
    {problem && <p className="field-error" role="alert">{problem}</p>}
  </div>
}
