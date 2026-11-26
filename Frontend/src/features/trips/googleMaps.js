import {getLanguage} from '../../i18n/language.js'

/* Loads the Google Maps JavaScript API once. The key lives in the build environment (VITE_GOOGLE_MAPS_KEY); without it the app keeps
   using the OpenStreetMap map. A key the browser cannot use (wrong referrer, API not enabled, billing off) calls gm_authFailure. */
export const googleKey=()=>String(import.meta.env.VITE_GOOGLE_MAPS_KEY||'').trim()
let pending=null
export function loadGoogleMaps(){
  if(typeof window==='undefined')return Promise.reject(new Error('no window'))
  if(window.google?.maps?.Map)return Promise.resolve(window.google.maps)
  if(pending)return pending
  pending=new Promise((resolve,reject)=>{
    window.__travellyGoogleReady=()=>resolve(window.google.maps)
    const script=document.createElement('script')
    script.async=true;script.onerror=()=>{pending=null;reject(new Error('Google Maps could not be loaded'))}
    script.src='https://maps.googleapis.com/maps/api/js?key='+encodeURIComponent(googleKey())+'&v=weekly&region=LK&language='+encodeURIComponent(getLanguage()||'en')+'&loading=async&callback=__travellyGoogleReady'
    document.head.appendChild(script)
  })
  return pending
}
