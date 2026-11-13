import test from 'node:test'
import assert from 'node:assert/strict'
import {eventPackageOf} from '../src/features/booking/eventPackage.js'
import {isRentalTrip,tripLink} from '../src/features/trips/tripLinks.js'
import {RENTAL_STAGES,isRentalReminder} from '../src/features/notifications/notices.js'
import {isRentalBooking,rentalLabel} from '../src/features/rental/rentalLabel.js'
import {vehicleTabFromSearch} from '../src/features/notifications/reminders.js'

const pkg={id:'p1',name:'Wedding car 6 hours',hours:'6'}
test('the package is read from the quote, the agreed price or the Admin list, in that order of availability', () => {
  assert.deepEqual(eventPackageOf({proposal:{quote:{calculation:{package:pkg}}}}),pkg)
  assert.deepEqual(eventPackageOf({price:{current:{calculation:{package:pkg}}},proposal:null}),pkg)
  assert.deepEqual(eventPackageOf({event_package:pkg}),pkg)
  assert.equal(eventPackageOf({event_package:null}),null);assert.equal(eventPackageOf({price:{current:null},proposal:null}),null);assert.equal(eventPackageOf(undefined),null)
})
test('a rental in progress opens its booking page, not a map', () => {
  const rental={trip_id:'t1',kind:'RENTAL',booking_id:'b1',viewer_roles:['PASSENGER']},owned={...rental,viewer_roles:['OWNER']}
  assert.equal(isRentalTrip(rental),true)
  assert.equal(tripLink(rental,'PASSENGER'),'/bookings/b1')
  assert.equal(tripLink(rental,'OWNER'),'/owner/travel/bookings/b1')
  assert.equal(tripLink(owned,'OWNER'),'/bookings/b1?workspace=owner')
  assert.equal(tripLink({trip_id:'t2',kind:'TICKET',viewer_roles:['PASSENGER']},'PASSENGER'),'/trips/t2/map')
  assert.equal(tripLink({trip_id:'t3',kind:'PRIVATE_HIRE',viewer_roles:['DRIVER']},'DRIVER'),'/driver/trips/t3/live')
})
test('rental reminders are RECONFIRMATION notices with a rental stage, matched by type, not wording', () => {
  assert.equal(RENTAL_STAGES.length,5)
  for(const stage of RENTAL_STAGES)assert.equal(isRentalReminder({notification_type:'RECONFIRMATION',title:'anything',action_payload:{stage,booking_id:'b1',booking_reference:'BKG-1'}}),true)
  assert.equal(isRentalReminder({notification_type:'RECONFIRMATION',action_payload:{booking_id:'b1'}}),false)
  assert.equal(isRentalReminder({notification_type:'PAYMENT',action_payload:{stage:'OVERDUE',booking_id:'b1'}}),false)
  assert.equal(isRentalReminder({notification_type:'RECONFIRMATION',action_payload:{stage:'OVERDUE'}}),false)
})
test('vehicle page tabs from the address', () => {
  assert.equal(vehicleTabFromSearch('?tab=event-packages'),6);assert.equal(vehicleTabFromSearch('?tab=rental-rates'),7);assert.equal(vehicleTabFromSearch('?tab=documents'),1)
})
test('rental label comes from booking_type RENTAL, with the days', () => {
  assert.equal(isRentalBooking({booking_type:'RENTAL'}),true);assert.equal(isRentalBooking({booking_type:'PRIVATE_HIRE',itinerary:{rental:{days:2}}}),false)
  assert.match(rentalLabel({booking_type:'RENTAL',itinerary:{rental:{days:2}}}),/Self-drive rental · 2 days|Self-drive rental · \{value0\} days/)
  assert.match(rentalLabel({booking_type:'RENTAL',rental_days:1}),/Self-drive rental · 1 day/)
  assert.equal(rentalLabel({booking_type:'RENTAL'}),'Self-drive rental')
})
