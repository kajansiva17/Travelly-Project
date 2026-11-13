import test from 'node:test'
import assert from 'node:assert/strict'
import {canSave,checkPackage,newPackageId,readEvent,toBody} from '../src/features/owner/eventPackageModel.js'

const pkg=(o={})=>({id:newPackageId(),name:'Wedding car 6 hours',hours:'6',price:'25000',notes:'',...o})
test('package checks: name, hours up to 24, price above 0 with two decimals', () => {
  assert.deepEqual(checkPackage(pkg()),{})
  assert.equal(checkPackage(pkg({name:' '})).name,'NAME');assert.equal(checkPackage(pkg({name:'x'.repeat(121)})).name,'NAME')
  assert.equal(checkPackage(pkg({hours:'0'})).hours,'HOURS');assert.equal(checkPackage(pkg({hours:'24.5'})).hours,'HOURS');assert.equal(checkPackage(pkg({hours:'24'})).hours,undefined);assert.equal(checkPackage(pkg({hours:''})).hours,'HOURS')
  assert.equal(checkPackage(pkg({price:'0'})).price,'PRICE');assert.equal(checkPackage(pkg({price:'10.005'})).price,'PRICE');assert.equal(checkPackage(pkg({price:'10.50'})).price,undefined);assert.equal(checkPackage(pkg({price:'abc'})).price,'PRICE')
  assert.equal(checkPackage(pkg({notes:'n'.repeat(501)})).notes,'NOTES')
})
test('1 to 20 packages can be saved', () => {
  assert.equal(canSave([]),false);assert.equal(canSave([pkg()]),true)
  assert.equal(canSave(Array.from({length:20},()=>pkg())),true);assert.equal(canSave(Array.from({length:21},()=>pkg())),false)
  assert.equal(canSave([pkg(),pkg({price:'0'})]),false)
})
test('PUT body: version, enabled, ids kept, price with two decimals, empty notes left out', () => {
  const a=pkg({notes:' Decorated car '}),b=pkg({price:'18000.5',notes:''})
  const body=toBody({serviceTypeId:'svc1',version:0,enabled:true,packages:[a,b]})
  assert.deepEqual(Object.keys(body),['service_type_id','expected_version','enabled','packages'])
  assert.equal(body.expected_version,0);assert.equal(body.packages[0].id,a.id);assert.equal(body.packages[0].price,'25000.00');assert.equal(body.packages[0].notes,'Decorated car');assert.equal(body.packages[1].price,'18000.50');assert.equal('notes' in body.packages[1],false)
  assert.match(a.id,/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/)
})
test('saved packages come from the Event service row, version 0 when none', () => {
  assert.deepEqual(readEvent([],'s'),{version:0,enabled:true,packages:[]})
  const row={service_type_id:'s',version:3,enabled:false,event_packages:[{id:'i1',name:'N',hours:'6',price:'25000.00',notes:null}]}
  assert.deepEqual(readEvent([{service_type_id:'x'},row],'s'),{version:3,enabled:false,packages:[{id:'i1',name:'N',hours:'6',price:'25000.00',notes:''}]})
})
