import test from 'node:test'
import assert from 'node:assert/strict'
import {alertMarkers,boundsOf,routeLine,routePoints,routeText,positionLatLng,tripFinished,withTripRead} from '../src/features/trips/tripMapModel.js'
import {drivesTrip,tripLink} from '../src/features/trips/tripLinks.js'

const data={points:[{kind:'START',label:'Kandy',latitude:'7.29',longitude:'80.63'},{kind:'STOP',label:'Mid',latitude:null,longitude:null},{kind:'END',label:'Colombo',latitude:'6.93',longitude:'79.85'}],
  line:[[80.63,7.29],[80.2,7.1],[79.85,6.93]],position:{latitude:'7.1',longitude:'80.2'}}

test('route points keep only usable positions, as numbers', () => {
  assert.deepEqual(routePoints(data).map(p=>p.kind),['START','END'])
  assert.deepEqual(routePoints(data)[0].latlng,[7.29,80.63])
})
test('the road line turns [lng, lat] into [lat, lng]', () => {
  const r=routeLine(data)
  assert.equal(r.straight,false);assert.deepEqual(r.latlngs[1],[7.1,80.2])
})
test('a null line draws straight lines between the points', () => {
  const r=routeLine({...data,line:null})
  assert.equal(r.straight,true);assert.deepEqual(r.latlngs,[[7.29,80.63],[6.93,79.85]])
})
test('bounds, position, alert markers and route text', () => {
  assert.deepEqual(boundsOf([[7,80],[6,81]]),[[6,80],[7,81]]);assert.equal(boundsOf([]),null)
  assert.deepEqual(positionLatLng(data.position),[7.1,80.2]);assert.equal(positionLatLng(null),null)
  assert.equal(alertMarkers([{id:'a',alert_type:'ACCIDENT',latitude:'7',longitude:'80'},{id:'b',latitude:null,longitude:null}]).length,1)
  assert.equal(routeText(data),'Kandy → Colombo');assert.equal(routeText({}),'')
})
test('trip cards open the right map per workspace', () => {
  const rider={trip_id:'t1',viewer_roles:['PASSENGER']},driver={trip_id:'t2',viewer_roles:['DRIVER']},both={trip_id:'t3',viewer_roles:['OWNER','DRIVER']}
  assert.equal(drivesTrip(rider),false);assert.equal(drivesTrip(both),true)
  assert.equal(tripLink(rider,'PASSENGER'),'/trips/t1/map')
  assert.equal(tripLink(rider,'OWNER'),'/owner/travel/trips/t1/map')
  assert.equal(tripLink(driver,'DRIVER'),'/driver/trips/t2/live')
  assert.equal(tripLink(both,'OWNER'),'/owner/driving/trips/t3')
})

test('the map is read once; GET /trips/{id} then gives status and location, and polling stops when the trip ends', () => {
  const map={trip_id:'t1',status:'IN_PROGRESS',points:[{kind:'START',label:'A',latitude:'7',longitude:'80'}],line:null,position:null}
  // no position until the first update: the "not shared yet" line stays
  assert.equal(withTripRead(map,{status:'IN_PROGRESS',location:null}).position,null)
  const seen=withTripRead(map,{status:'IN_PROGRESS',location:{latitude:'7.1',longitude:'80.1',accuracy_m:'5',updated_at:'2026-11-14T08:00:00Z'}})
  assert.deepEqual(seen.position,{latitude:'7.1',longitude:'80.1',updated_at:'2026-11-14T08:00:00Z'})
  assert.deepEqual(seen.points,map.points)
  // tracking ended (location null): keep the last position shown, take the new status
  const done=withTripRead(seen,{status:'COMPLETED',location:null})
  assert.equal(done.status,'COMPLETED'); assert.equal(done.position.updated_at,'2026-11-14T08:00:00Z')
  assert.equal(tripFinished('COMPLETED'),true); assert.equal(tripFinished('CANCELLED'),true); assert.equal(tripFinished('IN_PROGRESS'),false)
  assert.equal(withTripRead(map,null),map)
})
