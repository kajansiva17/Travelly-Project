const priceFields = {
  DISTANCE: ['base_charge','included_km','extra_km_rate','night_km_rate'],
  DAY_HIRE: ['day_charge','included_km_per_day','included_hours_per_day','extra_km_rate','extra_hour_rate','night_km_rate','overnight_driver_cost'],
  FIXED_ROUTE: ['fixed_fare'],
}
const allPrices = [...new Set(Object.values(priceFields).flat())]
const decimal = value => typeof value === 'string' && /^[0-9]{1,10}(\.[0-9]{1,10})?$/.test(value)
const inBox = (a,p) => Number(p.latitude)>=Number(a.south)&&Number(p.latitude)<=Number(a.north)&&Number(p.longitude)>=Number(a.west)&&Number(p.longitude)<=Number(a.east)
const boxesOverlap = (a,b) => Number(a.south)<=Number(b.north)&&Number(a.north)>=Number(b.south)&&Number(a.west)<=Number(b.east)&&Number(a.east)>=Number(b.west)
const week = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
export function departureDescription(value){
  if(!value)return 'Legacy agreed departure; see the accepted itinerary.'
  if(value.kind==='ANY_TIME')return 'Any departure time, subject to the effective dates and availability.'
  return `${value.weekdays.map(d=>week[d]).join(', ')}: ${value.from_time} to ${value.until_time}, Sri Lanka time; end excluded. Overnight windows start on the selected weekday.`
}
function intervals(d){
  if(!d||d.kind==='ANY_TIME')return [[0,10080]]
  const minute=s=>Number(s.slice(0,2))*60+Number(s.slice(3)),from=minute(d.from_time),until=minute(d.until_time),out=[]
  for(const day of d.weekdays){const a=day*1440+from,b=day*1440+until+(until<from?1440:0);if(b>10080)out.push([a,10080],[0,b-10080]);else out.push([a,b])}
  return out
}
export function departureMatches(d,iso){
  if(!d)return false
  const local=new Date(new Date(iso).getTime()+330*60000),m=((local.getUTCDay()+6)%7)*1440+local.getUTCHours()*60+local.getUTCMinutes()+local.getUTCSeconds()/60
  return intervals(d).some(([a,b])=>a<=m&&m<b)
}
function validDeparture(d){
  if(d?.kind==='ANY_TIME')return d.weekdays==null&&d.from_time==null&&d.until_time==null
  return d?.kind==='WEEKLY_WINDOW'&&Array.isArray(d.weekdays)&&d.weekdays.length>0&&d.weekdays.length<=7&&new Set(d.weekdays).size===d.weekdays.length&&d.weekdays.every(v=>Number.isInteger(v)&&v>=0&&v<=6)&&[d.from_time,d.until_time].every(t=>typeof t==='string'&&/^(?:[01][0-9]|2[0-3]):[0-5][0-9]$/.test(t))&&d.from_time!==d.until_time
}
function conflict(a,b){
  if((a.method==='DAY_HIRE')!==(b.method==='DAY_HIRE')||a.direction!==b.direction||a.effective_from>(b.effective_until||'9999-12-31')||b.effective_from>(a.effective_until||'9999-12-31')||!boxesOverlap(a.pickup_area,b.pickup_area))return false
  if(new Set([a.method,b.method]).size===2&&[a.method,b.method].every(m=>['DISTANCE','FIXED_ROUTE'].includes(m))&&a.direction==='ONE_WAY')return false
  if(a.method===b.method&&a.method==='FIXED_ROUTE'&&!intervals(a.departure).some(([x,y])=>intervals(b.departure).some(([u,v])=>x<v&&y>u)))return false
  if(a.coverage.kind===b.coverage.kind)return a.coverage.kind==='AREA'?boxesOverlap(a.coverage.area,b.coverage.area):JSON.stringify(a.coverage.places.map(p=>[Number(p.latitude),Number(p.longitude)]))===JSON.stringify(b.coverage.places.map(p=>[Number(p.latitude),Number(p.longitude)]))
  const area=a.coverage.kind==='AREA'?a.coverage.area:b.coverage.area,places=a.coverage.kind==='ROUTE'?a.coverage.places:b.coverage.places
  return places.every(p=>inBox(area,p))
}
export function validateRateRules(rules){
  const errors=[]
  for(const [index,r] of rules.entries()){
    const add=(field,message)=>errors.push({index,field,message})
    const required=priceFields[r.method]||[]
    for(const field of [...required,'free_wait_minutes','waiting_hour_rate'])if(!decimal(r[field]))add(field,'Enter a nonnegative decimal value; use 0 only when you mean zero.')
    for(const field of allPrices)if(r[field]!=null&&!required.includes(field))add(field,'Remove charges that do not belong to the selected pricing method.')
    if(r.method==='DAY_HIRE'&&!(Number(r.included_hours_per_day)>0&&Number(r.included_hours_per_day)<=24))add('included_hours_per_day','Included service hours must be greater than zero and at most 24.')
    for(const field of ['added_km','added_hours','added_wait_minutes','added_amount'])if(!decimal(r.change_limits[field]))add(field,'Enter an explicit nonnegative change limit.')
    if(r.return_to_base==='SEPARATE_FIXED'&&!decimal(r.return_to_base_charge))add('return_to_base_charge','Enter the disclosed nonnegative return-to-base charge.')
    if(!r.label.trim())add('label','Enter a name for this rate.')
    if(!r.effective_from)add('effective_from','Choose the effective date.')
    if(r.effective_until&&r.effective_until<r.effective_from)add('effective_until','Effective end must not precede the start.')
    if(r.method==='FIXED_ROUTE'&&r.coverage.kind!=='ROUTE')add('coverage','A fixed fare requires an exact route.')
    if(r.method==='FIXED_ROUTE'&&!validDeparture(r.departure))add('departure','Choose explicit departure applicability with valid weekdays and a nonempty time window.')
    if(r.method!=='FIXED_ROUTE'&&r.departure!=null)add('departure','Remove departure applicability from non-fixed pricing.')
  }
  if(!errors.length)for(let i=0;i<rules.length;i++)for(let j=i+1;j<rules.length;j++)if(conflict(rules[i],rules[j]))errors.push({index:j,field:'coverage',message:'Rate coverage and effective dates overlap for the same trip type and direction.'})
  return errors
}
