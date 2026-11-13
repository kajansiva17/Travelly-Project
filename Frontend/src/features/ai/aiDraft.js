/* From the AI's filters to the existing booking draft (contract 03AI, mapping table). The AI only fills the form: the person picks the
   verified places, presses Search, chooses a vehicle and books by hand. */
export const DRAFT_KEY='travelly.passenger.booking-draft.v2'
export const HIRE_SCOPE={local:'LOCAL',airport:'AIRPORT','long-distance':'LONG_DISTANCE'}
export const isHire=service=>Boolean(HIRE_SCOPE[service])
const count=value=>Math.max(0,Math.floor(Number(value)||0))

// Fields still missing before the search can run (hire needs verified places; ticket needs something to search for).
export function missingFor(filters,places={}){
  const f=filters||{},missing=[]
  if(!f.service)return ['service']
  if(f.service==='ticket'){
    if(!(f.pickup||f.destination||f.date))missing.push('pickup')
    if(count(f.passengers)<1)missing.push('passengers')
    return missing
  }
  if(!places.pickup)missing.push('pickup')
  if(!places.destination)missing.push('destination')
  if(!f.date)missing.push('date')
  if(!f.time)missing.push('time')
  if(f.journey==='RETURN'&&f.service!=='long-distance'){if(!f.return_date)missing.push('return_date');if(!f.return_time)missing.push('return_time')}
  if(f.service==='long-distance'){if(!f.hours)missing.push('hours');if(f.duration==='MULTI_DAY'&&!f.return_date)missing.push('return_date')}
  if(count(f.passengers)<1)missing.push('passengers')
  return missing
}

// Ticket search: origin = pickup, destination, date, travellers = passengers.
export function ticketQuery(filters){
  const f=filters||{},q=new URLSearchParams()
  if(f.pickup)q.set('origin',String(f.pickup).trim())
  if(f.destination)q.set('destination',String(f.destination).trim())
  if(f.date)q.set('date',f.date)
  q.set('travellers',String(Math.max(1,count(f.passengers))))
  return q.toString()
}

// The draft for a hire search. `services` is GET /service-types; the service is matched by pricing_scope, as PassengerServiceSelection does.
export function buildDraft(filters,{services=[],places={}}={}){
  const f=filters||{},row=services.find(s=>s.pricing_scope===HIRE_SCOPE[f.service])
  const detail={kind:f.service,journey:f.journey||'ONE_WAY',pickup:f.pickup||'',destination:f.destination||'',date:f.date||'',time:f.time||''}
  if(places.pickup)detail.pickupPlace=places.pickup
  if(places.destination)detail.destinationPlace=places.destination
  if(f.return_date)detail.returnDate=f.return_date
  if(f.return_time)detail.returnTime=f.return_time
  if(f.service==='long-distance'){detail.duration=f.duration||'ONE_DAY';if(f.hours)detail.hours=f.hours}
  if(f.flight)detail.flight=f.flight
  const requirements={passengers:count(f.passengers)||undefined,largeLuggage:count(f.large_luggage),smallLuggage:count(f.small_luggage)}
  return {service:f.service,serviceTypeId:row?.id||null,services,unavailableService:null,detail,requirements}
}
export function writeDraft(draft,storage=globalThis.sessionStorage){storage.setItem(DRAFT_KEY,JSON.stringify(draft))}
