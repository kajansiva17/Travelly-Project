import { t } from '../../i18n/language.js'
import { useEffect } from 'react'
import { api } from '../../services/api'
import { LIVE_CHANGED, setLive, getLive } from './liveSender'

const SEND_EVERY_MS = 30000
const LIST_EVERY_MS = 60000

// Sends the phone position for every vehicle this person has switched online, on whatever page of the workspace they are on,
// so the Passenger keeps following the vehicle after the Driver leaves the Go online page (to check the Passenger, start the trip...).
// Foreground only: a web page cannot report once the phone is locked (the mobile app will).
export default function LiveLocationSender({ enabled }) {
  useEffect(() => {
    if (!enabled) return undefined
    let alive = true
    let sending = []
    let fix = null
    let watch = null
    const push = async () => {
      if (!fix) return
      for (const id of sending) {
        try {
          await api(`/vehicles/${id}/live/location`, { method: 'PUT', body: JSON.stringify(fix) })
          setLive({ sentAt: { ...getLive().sentAt, [id]: new Date() } })
        } catch { read() }
      }
    }
    const read = async () => {
      try {
        const result = await api('/me/live-vehicles')
        if (!alive) return
        const before = sending.join(',')
        sending = (result?.items || []).filter(item => item.sending).map(item => item.vehicle_id)
        if (sending.join(',') !== before) setLive({ sendingIds: sending })   // the ride-request banner polls only while a vehicle is online
        if (sending.length) startWatch(); else stopWatch()
        if (sending.length && sending.join(',') !== before) push()   // just went online: the first position goes at once
      } catch { /* the next read tries again */ }
    }
    // The phone's location is asked for only while a vehicle is online.
    const startWatch = () => {
      if (watch !== null || !navigator.geolocation) return
      watch = navigator.geolocation.watchPosition(result => {
        const first = fix === null
        fix = { latitude: result.coords.latitude, longitude: result.coords.longitude, accuracy_m: Math.min(1000, Math.round(result.coords.accuracy || 0)) }
        setLive({ problem: '' })
        if (first && sending.length) push()
      }, problem => setLive({ problem: problem.code === 1
        ? t('Location is blocked. Allow location for this site in your browser, then try again.')
        : t('Your device could not find its location. Check that location is switched on.') }),
      { enableHighAccuracy: true, maximumAge: 10000, timeout: 30000 })
    }
    const stopWatch = () => { if (watch !== null) { navigator.geolocation.clearWatch(watch); watch = null; fix = null } }
    read()
    const sendTimer = setInterval(() => { if (sending.length) push() }, SEND_EVERY_MS)
    const listTimer = setInterval(read, LIST_EVERY_MS)
    window.addEventListener(LIVE_CHANGED, read)
    return () => {
      alive = false
      clearInterval(sendTimer); clearInterval(listTimer)
      window.removeEventListener(LIVE_CHANGED, read)
      stopWatch()
    }
  }, [enabled])

  return null
}
