import test from 'node:test'
import assert from 'node:assert/strict'
import {validKm,belowMinimum,formatKm,outcomeOf,buildPhotoForm,proofBadge,photoShown,photoPath,cameraAvailable} from '../src/features/odometer/odometerFlow.js'

test('the reading is digits with at most one decimal',()=>{
 for(const ok of ['0','45230','45230.5',' 45230.0 '])assert.equal(validKm(ok),true,ok)
 for(const bad of ['','abc','45230.55','-5','45,230','1e3','.5','45230.'])assert.equal(validKm(bad),false,bad)
})
test('early check against minimum_km (the last odometer at start, the start reading at finish)',()=>{
 assert.equal(belowMinimum('45209.9','45210.0'),true);assert.equal(belowMinimum('45210.0','45210.0'),false);assert.equal(belowMinimum('50000','45210.0'),false)
 assert.equal(belowMinimum('abc','45210.0'),false);assert.equal(belowMinimum('100',undefined),false);assert.equal(belowMinimum('100',null),false)
})
test('numbers are shown with thousands separators and one decimal at most',()=>{
 assert.equal(formatKm('45320.0'),'45,320');assert.equal(formatKm('45230.5'),'45,230.5');assert.equal(formatKm(null),'—');assert.equal(formatKm('x'),'—')
})
test('MATCH: green, Start opens',()=>{
 const o=outcomeOf({result:'MATCH',can_continue:true,typed_km:'45230.0',read_km:'45230.0'})
 assert.deepEqual([o.kind,o.tone,o.canStart,o.retake,o.editNumber],['match','success',true,false,false])
})
test('MISMATCH: both numbers, Retake and Edit number, Start stays disabled',()=>{
 const o=outcomeOf({result:'MISMATCH',can_continue:false,typed_km:'45230.0',read_km:'45320.0',message:'x'})
 assert.deepEqual([o.kind,o.tone,o.canStart,o.retake,o.editNumber,o.readKm,o.typedKm],['mismatch','danger',false,true,true,'45320.0','45230.0'])
})
test('UNREADABLE: retake with the try count; after the third try the typed number may be used (orange)',()=>{
 const first=outcomeOf({result:'UNREADABLE',can_continue:false,tries_unreadable:1,unreadable_tries_allowed:3})
 assert.deepEqual([first.kind,first.canStart,first.retake,first.tries,first.allowed,first.orange],['unreadable',false,true,1,3,false])
 const third=outcomeOf({result:'UNREADABLE',can_continue:true,tries_unreadable:3,unreadable_tries_allowed:3})
 assert.deepEqual([third.kind,third.tone,third.canStart,third.retake,third.orange],['unreadable-final','warn',true,false,true])
})
test('NOT_CHECKED: the photo is kept as proof and Start opens',()=>{
 const o=outcomeOf({result:'NOT_CHECKED',can_continue:true});assert.deepEqual([o.kind,o.canStart,o.retake],['not-checked',true,false])
})
test('Start and Finish open only when the server says can_continue',()=>{
 assert.equal(outcomeOf({result:'MATCH',can_continue:false}).canStart,false)
 assert.equal(outcomeOf({result:'SURPRISE',can_continue:false}).canStart,false);assert.equal(outcomeOf({result:'SURPRISE',can_continue:false}).retake,true)
 assert.equal(outcomeOf(undefined).canStart,false)
})
test('the photo form has exactly the documented multipart fields',()=>{
 const blob=new Blob(['jpeg'],{type:'image/jpeg'})
 const form=buildPhotoForm({captureCode:'CODE1',stage:'START',typedKm:' 45230.5 ',position:{latitude:'6.927100',longitude:'79.861200',accuracy:12.4},blob})
 assert.deepEqual([...form.keys()].sort(),['accuracy_m','capture_code','file','latitude','longitude','stage','typed_km'])
 assert.equal(form.get('capture_code'),'CODE1');assert.equal(form.get('stage'),'START');assert.equal(form.get('typed_km'),'45230.5')
 assert.equal(form.get('latitude'),'6.927100');assert.equal(form.get('longitude'),'79.861200');assert.equal(form.get('accuracy_m'),'12')
 assert.equal(form.get('file').name,'odometer.jpg');assert.equal(form.get('file').type,'image/jpeg')
 const noAccuracy=buildPhotoForm({captureCode:'C',stage:'END',typedKm:'1',position:{latitude:'1',longitude:'2'},blob})
 assert.equal(noAccuracy.has('accuracy_m'),false)   // accuracy_m is optional
})
test('proof badges: Match, Not readable, Not checked',()=>{
 assert.equal(proofBadge('MATCH')[1],'Match ✓');assert.equal(proofBadge('UNREADABLE')[1],'Not readable');assert.equal(proofBadge('NOT_CHECKED')[1],'Not checked');assert.equal(proofBadge(undefined)[1],'Not checked')
})
test('after the keep days only the numbers stay: no photo is shown',()=>{
 assert.equal(photoShown({photo_available:true,photo_url:'/api/v1/trips/t1/odometer-photos/START'}),true)
 assert.equal(photoShown({photo_available:false,photo_url:null,photo_deleted_at:'2026-11-20T00:00:00Z'}),false)
 assert.equal(photoShown({photo_available:true,photo_url:null}),false);assert.equal(photoShown(null),false)
})
test('photo_url is an absolute API address; the app client adds the prefix itself',()=>{
 assert.equal(photoPath('/api/v1/trips/t1/odometer-photos/START'),'/trips/t1/odometer-photos/START');assert.equal(photoPath(null),'')
})
test('only an in-app camera (getUserMedia) can take the proof photo',()=>{
 assert.equal(cameraAvailable({mediaDevices:{getUserMedia(){}}}),true);assert.equal(cameraAvailable({}),false);assert.equal(cameraAvailable({mediaDevices:{}}),false);assert.equal(cameraAvailable(null),false)
})
