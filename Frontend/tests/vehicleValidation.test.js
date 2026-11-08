import {test} from 'node:test'
import assert from 'node:assert/strict'
import {vehiclePayload,validatePhoto,vehicleTypes} from '../src/features/owner/vehicleValidation.js'
test('draft facts stay missing, explicit zero luggage remains zero and BEV does not invent fuel',()=>{
  assert.deepEqual(vehiclePayload({make:'',seat_capacity:'',large_luggage_capacity:'0',power_type:'BEV',engine_fuel_type:'PETROL',air_conditioned:''}),{make:null,seat_capacity:null,large_luggage_capacity:0,power_type:'BEV',engine_fuel_type:null,air_conditioned:null})
  assert.deepEqual(vehicleTypes,['CAR','VAN','BUS','THREE_WHEELER'])
})
test('vehicle count/type/odometer input rejects guessed or incoherent quantities',()=>{
  for(const value of ['1.2','-1','1e2'])assert.throws(()=>vehiclePayload({seat_capacity:value}))
  assert.throws(()=>vehiclePayload({vehicle_type_code:'PLANE'}))
  assert.throws(()=>vehiclePayload({current_odometer_km:'1.25'}))
  assert.equal(vehiclePayload({air_conditioned:'false'}).air_conditioned,false)
})
test('public photo input accepts only bounded JPEG/PNG and keeps documents separate',()=>{
  assert.equal(validatePhoto({name:'car.png',type:'image/png',size:10485760}),null)
  for(const file of [{name:'doc.pdf',type:'application/pdf',size:10},{name:'car.png',type:'text/html',size:10},{name:'car.jpg',type:'image/jpeg',size:10485761},{name:'car.png',size:0}])assert.ok(validatePhoto(file))
})
