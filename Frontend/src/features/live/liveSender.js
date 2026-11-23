import { useSyncExternalStore } from 'react'

// What the live-location sender reports to pages (Go online shows it): when each vehicle's position was last sent and any location problem.
let state = { sentAt: {}, problem: '' }
const listeners = new Set()

export const LIVE_CHANGED = 'travelly:live-changed'
export const getLive = () => state
export function setLive(patch) { state = { ...state, ...patch }; listeners.forEach(listener => listener()) }
export const subscribeLive = listener => { listeners.add(listener); return () => listeners.delete(listener) }
export const useLive = () => useSyncExternalStore(subscribeLive, getLive)
// A page that turned a vehicle online or offline asks the sender to read the list again at once.
export const liveChanged = () => window.dispatchEvent(new Event(LIVE_CHANGED))
