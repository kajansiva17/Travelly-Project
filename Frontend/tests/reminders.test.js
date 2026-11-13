import test from 'node:test'
import assert from 'node:assert/strict'
import {reminderKind,reminderLink,vehicleTabFromSearch} from '../src/features/notifications/reminders.js'

// Matching is by notification_type and action_payload (contract 03N); the wording of the title and body never decides anything.
const note=(type,payload,o={})=>({id:'n1',notification_type:type,title:'Whatever the server says',body:'Any text',booking_id:null,action_payload:payload,action_required:true,...o})
test('reminders are recognised by notification_type only',()=>{
 assert.equal(reminderKind(note('DOCUMENT_EXPIRY',{})),'DOCUMENT_EXPIRY')
 assert.equal(reminderKind(note('MAINTENANCE_DUE',{})),'MAINTENANCE_DUE')
 for(const type of ['REFUND','REPLACEMENT','ROAD_ALERT','ADMIN_ACTION','PAYMENT','BOOKING_REQUEST',undefined])assert.equal(reminderKind(note(type,{})),null)
 // Old wording with no type is not a reminder any more.
 assert.equal(reminderKind({id:'x',title:'Insurance expires soon',body:'Your insurance for vehicle CAB-1234 expires on 20 Nov 2026. Upload a renewed copy before then.'}),null)
 assert.equal(reminderKind({id:'x',title:'Oil change overdue',body:'Add a record in the Maintenance tab when it is done.'}),null)
 assert.equal(reminderKind(null),null)
})
test('document expiry links by action_payload: the vehicle in vehicle_id, otherwise the person\'s own documents',()=>{
 assert.equal(reminderLink(note('DOCUMENT_EXPIRY',{document_id:'d1',vehicle_id:'v2',document_type:'INSURANCE'}),'OWNER'),'/owner/vehicles/v2?tab=documents')
 assert.equal(reminderLink(note('DOCUMENT_EXPIRY',{document_id:'d2',document_type:'DRIVING_LICENCE',stage:'EXPIRING'}),'DRIVER'),'/account?workspace=driver&documents=driver#own-documents-heading')
 assert.equal(reminderLink(note('DOCUMENT_EXPIRY',{document_id:'d3',document_type:'NIC'}),'OWNER'),'/account?workspace=owner&documents=owner#own-documents-heading')
})
test('maintenance due links to that vehicle\'s Maintenance tab by action_payload.vehicle_id',()=>{
 assert.equal(reminderLink(note('MAINTENANCE_DUE',{vehicle_id:'v1',task:'OIL_CHANGE',stage:'OVERDUE',record_id:'r1'}),'OWNER'),'/owner/vehicles/v1?tab=maintenance')
})
test('a missing payload key falls back to the vehicle list; the registration number in the text is never used',()=>{
 assert.equal(reminderLink(note('MAINTENANCE_DUE',{}),'OWNER'),'/owner/vehicles')
 assert.equal(reminderLink(note('MAINTENANCE_DUE',undefined,{body:'Oil change overdue for CAB-1234. Add a record in the Maintenance tab when it is done.'}),'OWNER'),'/owner/vehicles')
 assert.equal(reminderLink(note('DOCUMENT_EXPIRY',null,{body:'Your insurance for vehicle CAB-1234 expires on 20 Nov 2026.'}),'OWNER'),'/owner/vehicles')
 assert.equal(reminderLink(note('DOCUMENT_EXPIRY',{},{}),'OWNER'),'/owner/vehicles')
 assert.equal(reminderLink(note('REFUND',{vehicle_id:'v1'}),'OWNER'),null)
})
test('a vehicle page opens the tab named in its address',()=>{
 assert.equal(vehicleTabFromSearch('?tab=maintenance'),5)
 assert.equal(vehicleTabFromSearch('?tab=documents'),1)
 assert.equal(vehicleTabFromSearch('?tab=other'),0)
 assert.equal(vehicleTabFromSearch(''),0)
})
