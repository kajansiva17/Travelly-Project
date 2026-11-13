/* Self-drive rental (contract 03RN): checks, the price preview and small helpers. Pure, so it can be tested. */
export const RENTAL_LIMITS={maxDaysTop:30,extras:10,notes:500,extraName:80,licenceMin:5,licenceMax:30}
const decimals=text=>{const m=String(text).trim().match(/^\d+(?:\.(\d+))?$/);return m?(m[1]||'').length:-1}
const money=(text,{positive=false,max=9999999.99}={})=>{
  if(String(text??'').trim()==='')return 'REQUIRED'
  const n=Number(text),d=decimals(text)
  if(!Number.isFinite(n)||d<0||d>2||n>max||n<0||(positive&&!(n>0)))return 'AMOUNT'
  return ''
}
export function checkExtra(extra){
  const e={},name=String(extra.name||'').trim()
  if(!name||name.length>RENTAL_LIMITS.extraName)e.name='NAME'
  if(money(extra.price,{positive:true}))e.price='PRICE'
  if(!['DAY','ONCE'].includes(extra.per))e.per='PER'
  return e
}
// Errors of the rental rates form: { field: code }, {} when it can be saved.
export function checkRates(r){
  const e={}
  if(money(r.day_rate,{positive:true}))e.day_rate='AMOUNT'
  for(const key of ['free_km_per_day','extra_km_rate','late_hour_rate'])if(money(r[key]))e[key]='AMOUNT'
  const days=Number(r.max_days)
  if(!Number.isInteger(days)||days<1||days>RENTAL_LIMITS.maxDaysTop)e.max_days='DAYS'
  if(String(r.notes||'').length>RENTAL_LIMITS.notes)e.notes='NOTES'
  if((r.extras||[]).length>RENTAL_LIMITS.extras)e.extras='EXTRAS'
  if((r.extras||[]).some(x=>Object.keys(checkExtra(x)).length))e.extras='EXTRA'
  return e
}
export const newExtraId=()=>globalThis.crypto?.randomUUID?globalThis.crypto.randomUUID():'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g,c=>{const r=Math.random()*16|0;return (c==='x'?r:(r&3|8)).toString(16)})
const two=value=>Number(value).toFixed(2)
// The PUT body: money as strings with two decimals, free km as typed, max_days a whole number, extras with the ids kept.
export function toRatesBody({version,enabled,rates,extras,cashAccepted}){
  const notes=String(rates.notes||'').trim()
  return {expected_version:version,enabled:Boolean(enabled),day_rate:two(rates.day_rate),free_km_per_day:String(rates.free_km_per_day).trim(),extra_km_rate:two(rates.extra_km_rate),late_hour_rate:two(rates.late_hour_rate),
    max_days:Number(rates.max_days),...(notes?{notes}:{}),...(typeof cashAccepted==='boolean'?{cash_accepted:cashAccepted}:{}),
    extras:extras.map(x=>({id:x.id,name:String(x.name).trim(),price:two(x.price),per:x.per}))}
}
// GET /vehicles/{id}/rental, or the first-time answer { version: 0, enabled: false }.
export function readRates(data){
  const d=data||{}
  return {version:d.version??0,enabled:(d.version??0)===0?true:Boolean(d.enabled),cashAccepted:Boolean(d.cash_accepted),
    rates:{day_rate:d.day_rate??'',free_km_per_day:d.free_km_per_day??'',extra_km_rate:d.extra_km_rate??'',late_hour_rate:d.late_hour_rate??'',max_days:d.max_days??7,notes:d.notes||''},
    extras:(d.extras||[]).map(x=>({id:x.id,name:x.name,price:String(x.price),per:x.per}))}
}
// What an extra costs for `days` booked days: price x days when per = DAY, once when per = ONCE (contract formula).
export const extraAmount=(extra,days)=>Math.round(Number(extra.price)*(extra.per==='DAY'?Number(days):1)*100)/100
export const extrasTotal=(extras,days)=>extras.reduce((sum,x)=>sum+extraAmount(x,days),0)
// Search item -> price preview with the chosen extras: day rate x days + extras.
export function previewTotal(rental,days,chosen){
  const base=Math.round(Number(rental?.day_rate||0)*Number(days)*100)/100
  return Math.round((base+extrasTotal(chosen||[],days))*100)/100
}
export const validDays=(value,max=RENTAL_LIMITS.maxDaysTop)=>{const n=Number(value);return Number.isInteger(n)&&n>=1&&n<=max}
export const validLicence=text=>{const v=String(text||'');return v.trim().length>=RENTAL_LIMITS.licenceMin&&v.length<=RENTAL_LIMITS.licenceMax&&/^[A-Za-z0-9 /-]+$/.test(v)}
// A rental booking carries itinerary.rental (and no itinerary.itinerary).
export const isRental=booking=>Boolean(booking&&booking.itinerary&&booking.itinerary.rental)
export const rentalOf=booking=>booking?.itinerary?.rental||null
// The Owner's next steps and the renter's confirmations from the booking status and the recorded steps.
export function ownerSteps(booking,now=new Date()){
  const r=rentalOf(booking)||{},s=booking?.status
  return {accept:s==='REQUESTED',decline:s==='REQUESTED',cancel:s==='REQUESTED'||s==='CONFIRMED',
    handover:s==='CONFIRMED',
    return:s==='IN_PROGRESS'&&Boolean(r.handover)}
}
export function renterConfirms(booking){
  const r=rentalOf(booking)||{}
  return {HANDOVER:Boolean(r.handover&&!r.handover.passenger_confirmed_at),RETURN:Boolean(r.return&&!r.return.passenger_confirmed_at)}
}
export const STATUS_CHIP={REQUESTED:['info','Requested'],CONFIRMED:['success','Confirmed'],IN_PROGRESS:['info','In progress'],COMPLETED:['success','Completed'],REJECTED:['danger','Rejected'],CANCELLED:['muted','Cancelled']}
