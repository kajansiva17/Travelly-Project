import test from 'node:test'
import assert from 'node:assert/strict'
import {bookingPriceState} from '../src/features/booking/bookingPriceState.js'

test('a saved applicable proposal price waits for Passenger acceptance without another Owner quote',()=>{
  const quote={calculation:{method:'FIXED_ROUTE',total:'5000.00'},rule:{method:'FIXED_ROUTE'}}
  assert.deepEqual(bookingPriceState({status:'REQUESTED',proposal:{kind:'QUOTE',quote},price:{},accepted_quote_digest:null}),{
    agreed:null,offered:quote,hasApplicablePrice:true,locationPending:false,revisionNeedsQuote:false,passengerAcceptancePending:true,needsInitialQuote:false,
  })
})

test('location confirmation and price entry are independent',()=>{
  const state=bookingPriceState({status:'REQUESTED',proposal:{kind:'LOCATION_CONFIRMATION_REQUIRED'},price:{},accepted_quote_digest:null})
  assert.equal(state.locationPending,true)
  assert.equal(state.needsInitialQuote,false)
  assert.equal(state.passengerAcceptancePending,false)
})

test('only genuinely unpriced requests and supported revisions need quote UI',()=>{
  assert.equal(bookingPriceState({proposal:{},price:{}}).needsInitialQuote,true)
  const revision=bookingPriceState({proposal:{kind:'CHANGE_REQUEST_UNPRICED'},price:{current:{calculation:{total:'1000'}}}})
  assert.equal(revision.revisionNeedsQuote,true)
  assert.equal(revision.hasApplicablePrice,true)
})
