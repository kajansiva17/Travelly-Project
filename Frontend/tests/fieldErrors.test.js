import test from 'node:test'
import assert from 'node:assert/strict'
import {fieldErrors,fieldErrorMap,fieldErrorText,firstFieldMessage,waitingPaymentId,correctAmount,payerFieldNames,settlementIds} from '../src/services/fieldErrors.js'

const err=(code,fields,message='Server message')=>Object.assign(new Error(message),{code,fields})
test('field_errors is read as a list of {field, message}; anything else is an empty list',()=>{
 assert.deepEqual(fieldErrors(err('X',[{field:'a',message:'A bad'},{field:'b',message:'B bad'}])),[{field:'a',message:'A bad'},{field:'b',message:'B bad'}])
 for(const bad of [undefined,null,{a:'x'},'text',[null,5,'x']])assert.deepEqual(fieldErrors({fields:bad}),[])
 assert.deepEqual(fieldErrors(null),[])
 assert.deepEqual(fieldErrors(err('X',[{field:'a'}])),[{field:'a',message:''}])
})
test('messages land under the input named by field; a dotted name also answers to its last part',()=>{
 const map=fieldErrorMap(err('VALIDATION_ERROR',[{field:'password',message:'Too short'},{field:'payer.address',message:'Enter the address'},{field:'payer.city',message:'Enter the city'},{field:'rules.2.price',message:'Price must be above 0'}]))
 assert.equal(map.password,'Too short')
 assert.equal(map['payer.address'],'Enter the address');assert.equal(map.address,'Enter the address')
 assert.equal(map['payer.city'],'Enter the city');assert.equal(map.city,'Enter the city')
 assert.equal(map['rules.2.price'],'Price must be above 0');assert.equal(map.price,'Price must be above 0')
 assert.deepEqual(fieldErrorMap(err('X',[])),{});assert.deepEqual(fieldErrorMap(err('X',[{field:'',message:'orphan'}])),{})
})
test('the first message of a full name is not overwritten by a later short one',()=>{
 const map=fieldErrorMap(err('VALIDATION_ERROR',[{field:'city',message:'Top-level city'},{field:'payer.city',message:'Payer city'}]))
 assert.equal(map.city,'Top-level city');assert.equal(map['payer.city'],'Payer city')
})
test('an empty list shows the response message; a filled list shows its messages',()=>{
 assert.equal(fieldErrorText(err('X',[],'Plain response message'),'fallback'),'Plain response message')
 assert.equal(fieldErrorText(err('X',undefined,''),'fallback'),'fallback')
 assert.equal(fieldErrorText(err('VALIDATION_ERROR',[{field:'a',message:'One.'},{field:'b',message:'Two.'}],'Validation failed'),'fallback'),'One. Two.')
})
test('409 PAYMENT_IN_PROGRESS: the list holds the waiting payment id, and only for that code',()=>{
 assert.equal(waitingPaymentId(err('PAYMENT_IN_PROGRESS',[{field:'payment_id',message:'pay-123'}])),'pay-123')
 assert.equal(waitingPaymentId(err('PAYMENT_IN_PROGRESS',[])),'')
 assert.equal(waitingPaymentId(err('SOMETHING_ELSE',[{field:'payment_id',message:'pay-123'}])),'')
})
test('422 PAYMENT_AMOUNT_MISMATCH: the list holds the correct amount',()=>{
 assert.equal(correctAmount(err('PAYMENT_AMOUNT_MISMATCH',[{field:'amount',message:'3000.00 LKR'}])),'3000.00 LKR')
 assert.equal(correctAmount(err('PAYMENT_AMOUNT_MISMATCH',[])),'')
 assert.equal(correctAmount(err('VALIDATION_ERROR',[{field:'amount',message:'3000.00 LKR'}])),'')
 assert.equal(firstFieldMessage(err('REFUND_AMOUNT_INVALID',[{field:'amount',message:'1500.00 LKR'}])),'1500.00 LKR')
})
test('422 PAYER_DETAILS_REQUIRED: payer.* names without the prefix, each once',()=>{
 assert.deepEqual(payerFieldNames(err('PAYER_DETAILS_REQUIRED',[{field:'payer.address',message:'Required'},{field:'payer.city',message:'Required'},{field:'payer.address',message:'Required'}])),['address','city'])
 assert.deepEqual(payerFieldNames(err('PAYER_DETAILS_REQUIRED',[])),[])
})
test('409 SETTLEMENT_NOT_ALLOWED: the payment ids are read from field or message',()=>{
 assert.deepEqual([...settlementIds(err('SETTLEMENT_NOT_ALLOWED',[{field:'p1',message:'not OWNER_PAYABLE'},{field:'payment_ids',message:'p2'}]))].sort(),['not OWNER_PAYABLE','p1','p2','payment_ids'].sort())
 assert.equal(settlementIds(err('SETTLEMENT_NOT_ALLOWED',[])).size,0)
 assert.equal(settlementIds(err('SETTLEMENT_NOT_ALLOWED',[{field:'p1',message:'x'}])).has('p1'),true)
})
