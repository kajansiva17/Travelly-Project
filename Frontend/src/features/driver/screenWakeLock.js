/* Screen Wake Lock (contract 03A): a phone with its screen off pauses the page, so live position, new alerts and the speaker stop.
   While a trip runs the page asks the browser to keep the screen on. This only wraps navigator.wakeLock. */
export const wakeLockSupported=(nav=globalThis.navigator)=>Boolean(nav&&nav.wakeLock&&typeof nav.wakeLock.request==='function')
// Asks for the lock. Never throws: the answer says whether it is held, unsupported, or refused (low battery, no permission, hidden page).
export async function acquireWakeLock(nav=globalThis.navigator){
  if(!wakeLockSupported(nav))return {status:'unsupported',lock:null}
  try{return {status:'held',lock:await nav.wakeLock.request('screen')}}
  catch{return {status:'failed',lock:null}}
}
export async function releaseWakeLock(lock){try{if(lock&&!lock.released)await lock.release()}catch{/* Already released by the browser. */}}
