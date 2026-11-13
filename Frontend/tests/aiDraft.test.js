import test from 'node:test'
import assert from 'node:assert/strict'
import {missingFor,ticketQuery,buildDraft,writeDraft,isHire,DRAFT_KEY} from '../src/features/ai/aiDraft.js'
import {topicRows,aiErrorText} from '../src/features/ai/aiApi.js'

const services=[{id:'s-local',pricing_scope:'LOCAL'},{id:'s-air',pricing_scope:'AIRPORT'},{id:'s-long',pricing_scope:'LONG_DISTANCE'}]
const place=label=>({label,latitude:'7.2',longitude:'80.6',token:'t'})
test('filters map onto the existing booking draft (03AI table)',()=>{
 const filters={service:'local',pickup:'Kandy',destination:'Colombo',date:'2026-11-20',time:'08:00',journey:'RETURN',return_date:'2026-11-21',return_time:'17:30',passengers:5,large_luggage:2,small_luggage:1}
 const d=buildDraft(filters,{services,places:{pickup:place('Kandy City'),destination:place('Colombo Fort')}})
 assert.equal(d.service,'local');assert.equal(d.serviceTypeId,'s-local');assert.equal(d.services,services)
 assert.deepEqual(d.detail,{kind:'local',journey:'RETURN',pickup:'Kandy',destination:'Colombo',date:'2026-11-20',time:'08:00',pickupPlace:place('Kandy City'),destinationPlace:place('Colombo Fort'),returnDate:'2026-11-21',returnTime:'17:30'})
 assert.deepEqual(d.requirements,{passengers:5,largeLuggage:2,smallLuggage:1})
})
test('airport keeps the optional flight number; long distance keeps duration and hours; journey defaults to ONE_WAY',()=>{
 const a=buildDraft({service:'airport',pickup:'A',destination:'B',date:'2026-11-20',time:'05:00',passengers:2,flight:'UL 225'},{services})
 assert.equal(a.serviceTypeId,'s-air');assert.equal(a.detail.flight,'UL 225');assert.equal(a.detail.journey,'ONE_WAY');assert.equal(a.requirements.largeLuggage,0)
 const l=buildDraft({service:'long-distance',pickup:'A',destination:'B',date:'2026-11-20',time:'05:00',passengers:4,hours:8,duration:'MULTI_DAY',return_date:'2026-11-23'},{services})
 assert.equal(l.serviceTypeId,'s-long');assert.equal(l.detail.duration,'MULTI_DAY');assert.equal(l.detail.hours,8);assert.equal(l.detail.returnDate,'2026-11-23')
 assert.equal(buildDraft({service:'long-distance'},{services}).detail.duration,'ONE_DAY')
})
test('an unknown or missing service never gets a serviceTypeId',()=>{
 assert.equal(buildDraft({service:'local'},{services:[]}).serviceTypeId,null)
 assert.equal(isHire('local'),true);assert.equal(isHire('ticket'),false);assert.equal(isHire(undefined),false)
})
test('hire search needs verified places, date, time and passengers; return and long distance need their extras',()=>{
 const base={service:'local',pickup:'Kandy',destination:'Colombo',date:'2026-11-20',time:'08:00',passengers:3}
 assert.deepEqual(missingFor(base,{}),['pickup','destination'])
 assert.deepEqual(missingFor(base,{pickup:place('a'),destination:place('b')}),[])
 const places={pickup:place('a'),destination:place('b')}
 assert.deepEqual(missingFor({...base,journey:'RETURN'},places),['return_date','return_time'])
 assert.deepEqual(missingFor({...base,service:'long-distance'},places),['hours'])
 assert.deepEqual(missingFor({...base,service:'long-distance',hours:6,duration:'MULTI_DAY'},places),['return_date'])
 assert.deepEqual(missingFor({...base,passengers:0},places),['passengers'])
 assert.deepEqual(missingFor({},{}),['service'])
})
test('ticket search: origin = pickup, destination, date, travellers = passengers; no places needed',()=>{
 assert.equal(ticketQuery({service:'ticket',pickup:'Kandy',destination:'Colombo',date:'2026-11-20',passengers:5}),'origin=Kandy&destination=Colombo&date=2026-11-20&travellers=5')
 assert.equal(ticketQuery({service:'ticket',destination:'Colombo'}),'destination=Colombo&travellers=1')
 assert.deepEqual(missingFor({service:'ticket',pickup:'Kandy',passengers:2},{}),[])
 assert.deepEqual(missingFor({service:'ticket',passengers:2},{}),['pickup'])
})
test('the draft is written under the booking draft key',()=>{
 const store=new Map();writeDraft({service:'local'},{setItem:(k,v)=>store.set(k,v)})
 assert.equal(DRAFT_KEY,'travelly.passenger.booking-draft.v2');assert.equal(store.get(DRAFT_KEY),'{"service":"local"}')
})
test('help topics are read from items or a bare list; errors become friendly lines, never raw text',()=>{
 assert.deepEqual(topicRows({items:[{topic_id:'cancel',title:'Cancel a booking',path:'/bookings'},{title:'Pay'}]}),[{id:'cancel',title:'Cancel a booking',path:'/bookings'},{id:'Pay',title:'Pay',path:null}])
 assert.deepEqual(topicRows([{id:'x',title:'X'}]),[{id:'x',title:'X',path:null}]);assert.deepEqual(topicRows(null),[])
 assert.equal(aiErrorText(new TypeError('Failed to fetch')),'We could not reach Travelly. Please try again.')
 const limited=Object.assign(new Error('raw server text'),{status:429,code:'RATE_LIMITED'})
 assert.match(aiErrorText(limited),/Too many questions/);assert.doesNotMatch(aiErrorText(limited),/raw server text/)
 assert.doesNotMatch(aiErrorText(Object.assign(new Error('Traceback ...'),{status:500})),/Traceback/)
})
