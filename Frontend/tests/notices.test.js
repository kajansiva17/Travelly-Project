import test from 'node:test'
import assert from 'node:assert/strict'
import {noticeBookingId,isReplacementAction,isReplacementInfo,isRefundNotice,isRoadAlertNotice,isExpired} from '../src/features/notifications/notices.js'

const n=(type,o={})=>({id:'n1',notification_type:type,title:'Any title',body:'Any body',action_required:false,action_payload:{},booking_id:null,expires_at:null,...o})
test('the booking comes from booking_id, otherwise action_payload.booking_id',()=>{
 assert.equal(noticeBookingId(n('REFUND',{booking_id:'b1'})),'b1')
 assert.equal(noticeBookingId(n('REFUND',{action_payload:{booking_id:'b2',scheduled_trip_id:'s1'}})),'b2')
 assert.equal(noticeBookingId(n('REFUND')),null);assert.equal(noticeBookingId(null),null)
})
test('replacement vehicle notice: REPLACEMENT with action_required and a booking, whatever the title says',()=>{
 assert.equal(isReplacementAction(n('REPLACEMENT',{action_required:true,booking_id:'b1',title:'Something else entirely'})),true)
 assert.equal(isReplacementAction(n('REPLACEMENT',{action_required:true,action_payload:{booking_id:'b1'}})),true)
 assert.equal(isReplacementAction(n('REPLACEMENT',{action_required:true})),false)            // no booking to open
 assert.equal(isReplacementAction(n('REPLACEMENT',{action_required:false,booking_id:'b1'})),false)
 assert.equal(isReplacementAction(n('REFUND',{action_required:true,booking_id:'b1',title:'Your journey has a replacement vehicle'})),false)
})
test('information notices: REPLACEMENT without an answer to give, and REFUND, by type',()=>{
 assert.equal(isReplacementInfo(n('REPLACEMENT',{booking_id:'b1',title:'We are arranging your journey'})),true)
 assert.equal(isReplacementInfo(n('REPLACEMENT',{action_required:true})),false)
 assert.equal(isRefundNotice(n('REFUND',{title:'Anything'})),true)
 assert.equal(isRefundNotice(n('REPLACEMENT',{title:'Booking cancelled - full refund'})),false)
 assert.equal(isRoadAlertNotice(n('ROAD_ALERT')),true);assert.equal(isRoadAlertNotice(n('PAYMENT')),false)
})
test('an expired notification is greyed: expires_at in the past',()=>{
 const now=Date.parse('2026-11-13T12:00:00Z')
 assert.equal(isExpired(n('ROAD_ALERT',{expires_at:'2026-11-13T11:00:00Z'}),now),true)
 assert.equal(isExpired(n('ROAD_ALERT',{expires_at:'2026-11-13T13:00:00Z'}),now),false)
 assert.equal(isExpired(n('ROAD_ALERT'),now),false);assert.equal(isExpired(null,now),false)
})
