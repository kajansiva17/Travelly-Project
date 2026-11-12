import test from 'node:test'
import assert from 'node:assert/strict'
import {reminderKind,reminderLink,vehicleTabFromSearch} from '../src/features/notifications/reminders.js'

const vehicles=[{id:'v1',registration_number:'CAB-1234'},{id:'v2',registration_number:'KY-9999'}]
const doc=(body,title='Insurance expires soon')=>({id:'n1',title,body,booking_id:null})
test('reminders are recognised from the server wording until the API returns notification_type',()=>{
 assert.equal(reminderKind(doc('Your insurance for vehicle CAB-1234 expires on 20 Nov 2026. Upload a renewed copy before then.')),'DOCUMENT_EXPIRY')
 assert.equal(reminderKind(doc('Your driving licence expired on 01 Nov 2026. Upload a renewed copy.','Driving licence expired')),'DOCUMENT_EXPIRY')
 assert.equal(reminderKind({title:'Oil change overdue',body:'Oil change overdue for CAB-1234 (1000.0 km past the limit). Add a record in the Maintenance tab when it is done.'}),'MAINTENANCE_DUE')
 assert.equal(reminderKind({title:'x',body:'y',notification_type:'MAINTENANCE_DUE'}),'MAINTENANCE_DUE')
 assert.equal(reminderKind({title:'Refund sent',body:'Your refund was sent. Upload a renewed copy',booking_id:'b1'}),null)
 assert.equal(reminderKind({title:'Booking resolved',body:'The pending booking was cancelled.'}),null)
})
test('document expiry links to the document upload; maintenance to the vehicle Maintenance tab',()=>{
 const vehicleDoc=doc('Your insurance for vehicle CAB-1234 expires on 20 Nov 2026. Upload a renewed copy before then.')
 assert.equal(reminderLink(vehicleDoc,vehicles,'OWNER'),'/owner/vehicles/v1?tab=documents')
 assert.equal(reminderLink({...vehicleDoc,action_payload:{vehicle_id:'v2'}},vehicles,'OWNER'),'/owner/vehicles/v2?tab=documents')
 assert.equal(reminderLink(doc('Your insurance for vehicle ZZ-1 expires on 20 Nov 2026. Upload a renewed copy before then.'),vehicles,'OWNER'),'/owner/vehicles')
 const mine=doc('Your driving licence expires on 20 Nov 2026. Upload a renewed copy before then.','Driving licence expires soon')
 assert.equal(reminderLink(mine,vehicles,'DRIVER'),'/account?workspace=driver&documents=driver#own-documents-heading')
 const service={title:'Oil change overdue',body:'Oil change overdue for KY-9999 (5.0 km past the limit). Add a record in the Maintenance tab when it is done.'}
 assert.equal(reminderLink(service,vehicles,'OWNER'),'/owner/vehicles/v2?tab=maintenance')
 assert.equal(reminderLink({...service,body:service.body.replace('KY-9999','NONE')},vehicles,'OWNER'),'/owner/vehicles')
})
test('a vehicle page opens the tab named in its address',()=>{
 assert.equal(vehicleTabFromSearch('?tab=maintenance'),5)
 assert.equal(vehicleTabFromSearch('?tab=documents'),1)
 assert.equal(vehicleTabFromSearch('?tab=other'),0)
 assert.equal(vehicleTabFromSearch(''),0)
})
