/* Odometer photo proof (contract 03O). Pure helpers for the start and finish steps and for the proof card. */
// The reading: digits with at most one decimal.
export const validKm=value=>/^\d{1,9}(\.\d)?$/.test(String(value??'').trim())
// An early check against minimum_km (the vehicle's last odometer at start, the start reading at finish).
export const belowMinimum=(typed,minimum)=>validKm(typed)&&minimum!=null&&minimum!==''&&Number(typed)<Number(minimum)
export const formatKm=value=>value==null||value===''||Number.isNaN(Number(value))?'—':Number(value).toLocaleString('en-US',{maximumFractionDigits:1})

// What the screen shows for a photo result. can_continue from the server decides whether Start or Finish opens.
export function outcomeOf(response){
  const result=response?.result,canStart=response?.can_continue===true
  if(result==='MATCH')return {kind:'match',tone:'success',canStart,retake:false,editNumber:false}
  if(result==='MISMATCH')return {kind:'mismatch',tone:'danger',canStart,retake:true,editNumber:true,readKm:response.read_km,typedKm:response.typed_km}
  if(result==='UNREADABLE')return {kind:canStart?'unreadable-final':'unreadable',tone:canStart?'warn':'danger',canStart,retake:!canStart,editNumber:false,tries:response.tries_unreadable,allowed:response.unreadable_tries_allowed,orange:canStart}
  if(result==='NOT_CHECKED')return {kind:'not-checked',tone:'info',canStart,retake:false,editNumber:false}
  return {kind:'unknown',tone:'danger',canStart,retake:!canStart,editNumber:false}
}

// The multipart body of POST /trips/{id}/odometer-photo: exactly the documented fields. The file is the JPEG taken in the app.
export function buildPhotoForm({captureCode,stage,typedKm,position,blob}){
  const form=new FormData()
  form.set('capture_code',captureCode);form.set('stage',stage);form.set('typed_km',String(typedKm).trim())
  form.set('latitude',String(position.latitude));form.set('longitude',String(position.longitude))
  if(Number.isFinite(position.accuracy))form.set('accuracy_m',String(Math.round(position.accuracy)))
  form.set('file',blob,'odometer.jpg')
  return form
}

// The proof card: the badge of one photo's result.
export const PROOF_BADGES={MATCH:['success','Match ✓'],UNREADABLE:['warn','Not readable'],NOT_CHECKED:['muted','Not checked'],MISMATCH:['muted','Not checked']}
export const proofBadge=result=>PROOF_BADGES[result]||['muted','Not checked']
// The photos are gone after the keep days: the numbers stay and no photo is shown.
export const photoShown=side=>Boolean(side&&side.photo_available&&side.photo_url)
// photo_url is an absolute API address (/api/v1/...); the app's API client adds the prefix itself.
export const photoPath=url=>String(url||'').replace(/^\/api\/v1/,'')
// Camera: the in-app camera only. A browser without getUserMedia cannot take the proof photo.
export const cameraAvailable=(nav=globalThis.navigator)=>Boolean(nav?.mediaDevices&&typeof nav.mediaDevices.getUserMedia==='function')
