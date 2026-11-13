import {accountPath} from '../../routes/workspaceRoutes.js'

/* Reminders (contract 03R and 03N): DOCUMENT_EXPIRY and MAINTENANCE_DUE, matched by notification_type. Their links come from
   action_payload (vehicle_id, document_id); nothing is guessed from the wording of the title or body. */
export function reminderKind(note){
  const type=note?.notification_type
  return type==='DOCUMENT_EXPIRY'||type==='MAINTENANCE_DUE'?type:null
}
export function reminderLink(note,role){
  const kind=reminderKind(note),payload=note?.action_payload,vehicleId=payload?.vehicle_id
  // A missing payload key falls back to the vehicle list.
  if(kind==='MAINTENANCE_DUE')return vehicleId?`/owner/vehicles/${vehicleId}?tab=maintenance`:'/owner/vehicles'
  if(kind==='DOCUMENT_EXPIRY'){
    // vehicle_id is present for vehicle documents only: they are under that vehicle. Any other document is the person's own.
    if(vehicleId)return `/owner/vehicles/${vehicleId}?tab=documents`
    if(!payload||!payload.document_id)return role==='OWNER'?'/owner/vehicles':accountPath(role,role==='DRIVER'?'driver':'')+'#own-documents-heading'
    return accountPath(role,role==='OWNER'?'owner':role==='DRIVER'?'driver':'')+'#own-documents-heading'
  }
  return null
}
// Tab named in the address of a vehicle page (?tab=documents or ?tab=maintenance).
export const vehicleTabFromSearch=search=>({documents:1,maintenance:5})[new URLSearchParams(search).get('tab')]||0
