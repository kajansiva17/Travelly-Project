import test from 'node:test'
import assert from 'node:assert/strict'
import {checkExtra,checkRates,extraAmount,isRental,ownerSteps,previewTotal,readRates,renterConfirms,toRatesBody,validDays,validLicence} from '../src/features/rental/rentalModel.js'

const rates=(o={})=>({day_rate:'8000',free_km_per_day:'100',extra_km_rate:'40',late_hour_rate:'500',max_days:7,notes:'',extras:[],...o})
test('rental rates: amounts with two decimals, max days 1 to 30, extras at most 10', () => {
  assert.deepEqual(checkRates(rates()),{})
  assert.equal(checkRates(rates({day_rate:'0'})).day_rate,'AMOUNT');assert.equal(checkRates(rates({day_rate:'10.555'})).day_rate,'AMOUNT');assert.equal(checkRates(rates({day_rate:''})).day_rate,'AMOUNT')
  assert.equal(checkRates(rates({free_km_per_day:'0'})).free_km_per_day,undefined)
  assert.equal(checkRates(rates({max_days:0})).max_days,'DAYS');assert.equal(checkRates(rates({max_days:31})).max_days,'DAYS');assert.equal(checkRates(rates({max_days:30})).max_days,undefined)
  assert.equal(checkRates(rates({notes:'n'.repeat(501)})).notes,'NOTES')
  const extra={id:'1',name:'Child seat',price:'300',per:'DAY'}
  assert.equal(checkRates(rates({extras:Array.from({length:11},()=>extra)})).extras,'EXTRAS');assert.equal(checkRates(rates({extras:[{...extra,price:'0'}]})).extras,'EXTRA')
})
test('extras: name, price above 0, per DAY or ONCE', () => {
  assert.deepEqual(checkExtra({name:'GPS',price:'150',per:'ONCE'}),{})
  assert.equal(checkExtra({name:'',price:'150',per:'ONCE'}).name,'NAME');assert.equal(checkExtra({name:'GPS',price:'0',per:'ONCE'}).price,'PRICE');assert.equal(checkExtra({name:'GPS',price:'1',per:'WEEK'}).per,'PER')
})
test('PUT body keeps ids, two decimals and leaves empty notes out', () => {
  const body=toRatesBody({version:2,enabled:true,cashAccepted:true,rates:rates({notes:' Rs 20000 deposit '}),extras:[{id:'u1',name:' Child seat ',price:'300',per:'DAY'}]})
  assert.equal(body.expected_version,2);assert.equal(body.day_rate,'8000.00');assert.equal(body.free_km_per_day,'100');assert.equal(body.max_days,7);assert.equal(body.notes,'Rs 20000 deposit');assert.equal(body.cash_accepted,true)
  assert.deepEqual(body.extras,[{id:'u1',name:'Child seat',price:'300.00',per:'DAY'}])
  assert.equal('notes' in toRatesBody({version:0,enabled:false,rates:rates(),extras:[]}),false)
  assert.equal('cash_accepted' in toRatesBody({version:0,enabled:false,rates:rates(),extras:[]}),false)
})
test('first-time read and a saved read', () => {
  assert.deepEqual(readRates({service_type_id:'s',version:0,enabled:false}).rates.max_days,7);assert.equal(readRates({version:0,enabled:false}).extras.length,0)
  const saved=readRates({version:4,enabled:true,day_rate:'8000.00',free_km_per_day:'100',extra_km_rate:'40.00',late_hour_rate:'500.00',max_days:7,notes:'x',cash_accepted:true,extras:[{id:'a',name:'N',price:'300.00',per:'ONCE'}]})
  assert.equal(saved.version,4);assert.equal(saved.cashAccepted,true);assert.equal(saved.extras[0].per,'ONCE')
})
test('estimate preview: base_price of the searched days plus the amounts the server gave the chosen extras', () => {
  const day={amount:'600.00'},once={amount:'150.50'}
  assert.equal(extraAmount(day),600);assert.equal(extraAmount({}),0)
  assert.equal(previewTotal({base_price:'16000.00'},[day,once]),16750.5);assert.equal(previewTotal({base_price:'16000.00'},[]),16000);assert.equal(previewTotal(undefined,[]),0)
})
test('days, licence number, rental detection', () => {
  assert.equal(validDays('2'),true);assert.equal(validDays('0'),false);assert.equal(validDays('31'),false);assert.equal(validDays('1.5'),false)
  assert.equal(validLicence('B1234567'),true);assert.equal(validLicence('B12'),false);assert.equal(validLicence('B123 4567!'),false)
  assert.equal(isRental({booking_type:'RENTAL',itinerary:{rental:{days:2}}}),true);assert.equal(isRental({booking_type:'PRIVATE_HIRE',itinerary:{itinerary:{}}}),false);assert.equal(isRental({itinerary:{rental:{days:2}}}),false)
})
test('Owner steps and the renter confirmations follow the status and the recorded steps', () => {
  const b=s=>({status:s,start_at:'2030-01-01T00:00:00Z',itinerary:{rental:{}}})
  assert.deepEqual(ownerSteps(b('REQUESTED')),{accept:true,decline:true,cancel:true,handover:false,return:false})
  assert.equal(ownerSteps(b('CONFIRMED')).handover,true);assert.equal(ownerSteps(b('CONFIRMED')).cancel,true)
  assert.equal(ownerSteps({...b('IN_PROGRESS'),itinerary:{rental:{handover:{}}}}).return,true);assert.equal(ownerSteps(b('COMPLETED')).cancel,false)
  assert.deepEqual(renterConfirms({itinerary:{rental:{handover:{passenger_confirmed_at:null},return:{passenger_confirmed_at:'x'}}}}),{HANDOVER:true,RETURN:false})
  assert.deepEqual(renterConfirms(b('CONFIRMED')),{HANDOVER:false,RETURN:false})
})
