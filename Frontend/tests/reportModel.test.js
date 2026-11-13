import test from 'node:test'
import assert from 'node:assert/strict'
import {attentionTone,bookingsMade,isLoss,pdfName,previousMonth,thisMonth,validPeriod} from '../src/features/reports/reportModel.js'

test('the default month is the finished month before now, across a year end', () => {
  assert.equal(previousMonth(new Date(2026,10,13)),'2026-10');assert.equal(previousMonth(new Date(2026,0,5)),'2025-12')
  assert.equal(thisMonth(new Date(2026,10,13)),'2026-11')
})
test('a period must be YYYY-MM, from 2020 up to this month', () => {
  const now=new Date(2026,10,13)
  assert.equal(validPeriod('2026-11',now),true);assert.equal(validPeriod('2020-01',now),true)
  assert.equal(validPeriod('2026-12',now),false);assert.equal(validPeriod('2019-12',now),false);assert.equal(validPeriod('2026-13',now),false);assert.equal(validPeriod('',now),false)
})
test('file names and result rules', () => {
  assert.equal(pdfName('2026-11'),'travelly-report-2026-11.pdf');assert.equal(pdfName('2026-11',true),'travelly-admin-report-2026-11.pdf')
  assert.equal(isLoss({is_loss:true,profit:'5'}),true);assert.equal(isLoss({is_loss:false,profit:'-5'}),false);assert.equal(isLoss({profit:'-5.00'}),true);assert.equal(isLoss({profit:'0.00'}),false)
  assert.equal(attentionTone(0),'muted');assert.equal(attentionTone(3),'danger')
  assert.equal(bookingsMade({private_hire_bookings:4,ticket_bookings:6}),10)
})
