import {useEffect} from 'react'

// Runs `load` now and then every `ms` while `active`, only while the tab is visible, and again when the tab becomes visible.
// Callers keep one request at a time themselves (an in-flight guard), so a slow answer never piles up requests.
export function usePoll(load,active,ms){
  useEffect(()=>{
    if(!active)return undefined
    const tick=()=>{if(document.visibilityState==='visible')load()}
    tick()
    const timer=setInterval(tick,ms)
    document.addEventListener('visibilitychange',tick)
    return()=>{clearInterval(timer);document.removeEventListener('visibilitychange',tick)}
  },[active,load,ms])
}
