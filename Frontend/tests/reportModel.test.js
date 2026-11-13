import test from 'node:test'
import assert from 'node:assert/strict'
import {attentionTone,bookingsMade,isLoss,monthKey,pdfName,previousMonth,thisMonth,validPeriod} from '../src/features/reports/reportModel.js'

test('the default month is the finished month before now (Sri Lanka time), across a year end', () => {
  assert.equal(previousMonth(new Date('2026-11-13T06:00:00Z')),'2026-10');assert.equal(previousMonth(new Date('2026-01-05T06:00:00Z')),'2025-12')
  assert.equal(thisMonth(new Date('2026-11-13T06:00:00Z')),'2026-11')
})
test('near midnight on the first of a month the Sri Lanka month decides, not the device clock', () => {
  // 2026-11-30 19:00 UTC is 2026-12-01 00:30 in Sri Lanka (UTC+5:30): a device in UTC or the Americas is still in November.
  const lk=new Date('2026-11-30T19:00:00Z')
  assert.equal(monthKey(lk),'2026-12');assert.equal(thisMonth(lk),'2026-12');assert.equal(previousMonth(lk),'2026-11')
  assert.equal(validPeriod('2026-12',lk),true);assert.equal(validPeriod('2027-01',lk),false)
  // 30 Nov 2026 23:59 in Sri Lanka (18:29 UTC) is still November: December is refused.
  const before=new Date('2026-11-30T18:29:00Z')
  assert.equal(thisMonth(before),'2026-11');assert.equal(previousMonth(before),'2026-10');assert.equal(validPeriod('2026-12',before),false)
  // New year: 1 Jan 2027 00:10 in Sri Lanka is 31 Dec 2026 18:40 UTC.
  const ny=new Date('2026-12-31T18:40:00Z')
  assert.equal(thisMonth(ny),'2027-01');assert.equal(previousMonth(ny),'2026-12')
})
test('a period must be YYYY-MM, from 2020 up to this month', () => {
  const now=new Date('2026-11-13T06:00:00Z')
  assert.equal(validPeriod('2026-11',now),true);assert.equal(validPeriod('2020-01',now),true)
  assert.equal(validPeriod('2026-12',now),false);assert.equal(validPeriod('2019-12',now),false);assert.equal(validPeriod('2026-13',now),false);assert.equal(validPeriod('',now),false)
})
test('file names and result rules', () => {
  assert.equal(pdfName('2026-11'),'travelly-report-2026-11.pdf');assert.equal(pdfName('2026-11',true),'travelly-admin-report-2026-11.pdf')
  assert.equal(isLoss({is_loss:true,profit:'5'}),true);assert.equal(isLoss({is_loss:false,profit:'-5'}),false);assert.equal(isLoss({profit:'-5.00'}),true);assert.equal(isLoss({profit:'0.00'}),false)
  assert.equal(attentionTone(0),'muted');assert.equal(attentionTone(3),'danger')
  assert.equal(bookingsMade({private_hire_bookings:4,ticket_bookings:6}),10);assert.equal(bookingsMade({private_hire_bookings:4,ticket_bookings:6,rental_bookings:3}),13)
})
