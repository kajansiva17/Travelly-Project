/* One way to read `field_errors` (backend confirmed: always a LIST of {field, message}, never a dict). api.js puts it on `error.fields`.
   Most of the time the list names inputs. A few codes use the list for data, not for inputs:
   - 409 PAYMENT_IN_PROGRESS      fields[0].message = the waiting payment id
   - 422 PAYMENT_AMOUNT_MISMATCH  fields[0].message = the correct amount, e.g. "3000.00 LKR"
   - 422 PAYER_DETAILS_REQUIRED   field names like payer.address, payer.city = what the payer still has to give
   - 409 SETTLEMENT_NOT_ALLOWED   the list holds payment ids
   - 422 REFUND_AMOUNT_INVALID / PAYMENT_SETTINGS_INVALID  fields[0].message = the limit or the rule */
export const fieldErrors=error=>(Array.isArray(error?.fields)?error.fields:[]).filter(item=>item&&typeof item==='object').map(item=>({field:String(item.field??''),message:String(item.message??'')}))

// Messages for inputs, keyed by field. A dotted name (payer.address, rules.0.price) also answers to its last part (address, price),
// so the message lands under the input that is named by it.
export function fieldErrorMap(error){
  const map={}
  for(const {field,message} of fieldErrors(error)){
    if(!field)continue
    map[field]=message
    const last=field.split('.').at(-1)
    if(last&&!(last in map))map[last]=message
  }
  return map
}
// When the list is empty, the response message is what the person sees.
export function fieldErrorText(error,fallback=''){
  const messages=fieldErrors(error).map(item=>item.message).filter(Boolean)
  return messages.length?messages.join(' '):(error?.message||fallback)
}
export const firstFieldMessage=error=>fieldErrors(error)[0]?.message||''
export const waitingPaymentId=error=>error?.code==='PAYMENT_IN_PROGRESS'?firstFieldMessage(error):''
export const correctAmount=error=>error?.code==='PAYMENT_AMOUNT_MISMATCH'?firstFieldMessage(error):''
// The payer fields still needed, without the "payer." prefix (address, city, ...), each once.
export const payerFieldNames=error=>[...new Set(fieldErrors(error).map(item=>item.field.replace(/^payer\./,'')).filter(Boolean))]
// The payment ids a settlement refused: they may come in field or in message, so both are read.
export const settlementIds=error=>new Set(fieldErrors(error).flatMap(item=>[item.field,item.message]).filter(Boolean))
