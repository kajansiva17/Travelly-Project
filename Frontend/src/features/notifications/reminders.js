import {accountPath} from '../../routes/workspaceRoutes.js'

/* Reminders (contract 03R): DOCUMENT_EXPIRY and MAINTENANCE_DUE. GET /notifications returns id, title, body, booking_id
   and status; it does not return notification_type or action_payload. When the API adds them they are used. Until then
   a reminder is recognised by its fixed wording, and its vehicle is found from the registration number in the text
   against the Owner's own vehicles. */
export function reminderKind(note){
  if(!note||note.booking_id)return null
  if(note.notification_type==='DOCUMENT_EXPIRY'||note.notification_type==='MAINTENANCE_DUE')return note.notification_type
  const body=note.body||''
  if(/Add a record in the Maintenance tab when it is done\.$/.test(body))return 'MAINTENANCE_DUE'
  if(/ (expires on|expired on) .*Upload a renewed copy/.test(body)&&/ (expires soon|expired)$/.test(note.title||''))return 'DOCUMENT_EXPIRY'
  return null
}
const vehicleFromText=(note,vehicles)=>(vehicles||[]).find(v=>v.registration_number&&(note.body||'').includes(v.registration_number))
export function reminderLink(note,vehicles,role){
  const kind=reminderKind(note),vehicleId=note.action_payload?.vehicle_id||vehicleFromText(note,vehicles)?.id
  if(kind==='MAINTENANCE_DUE')return vehicleId?`/owner/vehicles/${vehicleId}?tab=maintenance`:'/owner/vehicles'
  if(kind==='DOCUMENT_EXPIRY'){
    const ofVehicle=Boolean(note.action_payload?.vehicle_id)||/ for vehicle /.test(note.body||'')
    if(ofVehicle)return vehicleId?`/owner/vehicles/${vehicleId}?tab=documents`:'/owner/vehicles'
    return accountPath(role,role==='OWNER'?'owner':role==='DRIVER'?'driver':'')+'#own-documents-heading'
  }
  return null
}
// Tab named in the address of a vehicle page (?tab=documents or ?tab=maintenance).
export const vehicleTabFromSearch=search=>({documents:1,maintenance:5})[new URLSearchParams(search).get('tab')]||0
