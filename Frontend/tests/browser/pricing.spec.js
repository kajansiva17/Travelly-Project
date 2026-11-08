import { test, expect } from '@playwright/test'

const uid='12222222-2222-4222-8222-222222222222', vid='22222222-2222-4222-8222-222222222222', sid='32222222-2222-4222-8222-222222222222', bid='42222222-2222-4222-8222-222222222222'
const A={label:'Colombo',latitude:'6.93',longitude:'79.86',token:'a'.repeat(43)}, B={label:'Kandy',latitude:'7.29',longitude:'80.63',token:'b'.repeat(43)}
const rate={id:'52222222-2222-4222-8222-222222222222',label:'Colombo to Kandy',method:'DISTANCE',direction:'ONE_WAY',effective_from:'2026-10-27',pickup_area:{label:'Colombo operating area',south:'6',north:'8',west:'79',east:'82'},coverage:{kind:'ROUTE',places:[A,B]},base_charge:'1000',included_km:'10',extra_km_rate:'50',night_km_rate:'10',free_wait_minutes:'20',waiting_hour_rate:'300',return_to_base:'INCLUDED',return_to_base_notes:'Return included in the quoted rate.',tolls:'SEPARATE_AT_COST',parking:'INCLUDED',other_charges:[],change_limits:{added_km:'20',added_hours:'2',added_wait_minutes:'30',added_amount:'2000'}}
const price={method:'DISTANCE',currency:'LKR',total:'2050.00',exclusions:['Tolls: payable separately at actual cost; not part of this total.'],breakdown:[{code:'BASE',label:'Base charge including stated km',quantity:'1',rate:'1000',amount:'1000',kind:'CHARGE'},{code:'EXTRA_KM',label:'Distance beyond included km',quantity:'20',rate:'50',amount:'1000',kind:'CHARGE'},{code:'NIGHT_KM',label:'All planned night km',quantity:'5',rate:'10',amount:'50',kind:'CHARGE'}]}
const itinerary={start_at:'2027-01-10T02:30:00Z',direction:'ONE_WAY',method:'DISTANCE',service_hours:['3'],stops:[{place:A,wait_minutes:'0',overnight_rest:false},{place:B,wait_minutes:'0',overnight_rest:false}]}

async function setup(page,{passenger=false,admin=false,change=false,departure=false}={}) {
  const mutations=[]
  let config={service_type_id:sid,version:2,enabled:true,currency:'LKR',rules:[structuredClone(rate)]}
  let booking={id:bid,reference:'BKG-TEST-JOURNEY',owner_user_id:uid,passenger_user_id:passenger?uid:'62222222-2222-4222-8222-222222222222',vehicle_id:vid,service_type_id:sid,status:change?'IN_PROGRESS':'REQUESTED',version:1,start_at:itinerary.start_at,end_at:'2027-01-10T05:30:00Z',itinerary:{itinerary},price:change?{initial:{calculation:price,rule:rate,itinerary},current:{calculation:price,rule:rate,itinerary}}:{},proposal:change?{kind:'CHANGE',old_total:'2050.00',added_charge:'750.00',new_total:'2800.00',manual_review_required:false,passenger_accepted:false,digest:'d'.repeat(64)}:{},vehicle_committed:change,accepted_quote_digest:change?'a'.repeat(64):null,trip:null}
  if(departure){
    const fixed={...structuredClone(rate),method:'FIXED_ROUTE',fixed_fare:'2050',departure:{kind:'ANY_TIME'}}
    for(const field of ['base_charge','included_km','extra_km_rate','night_km_rate'])delete fixed[field]
    const calculation={...price,method:'FIXED_ROUTE',breakdown:[{code:'FIXED',label:'Covered fixed-route fare',quantity:'1',rate:'2050',amount:'2050',kind:'CHARGE'}]}
    booking.status='CONFIRMED';booking.price={initial:{calculation,rule:fixed,itinerary},current:{calculation,rule:fixed,itinerary}};config.rules=[fixed]
    booking.proposal=passenger?{...booking.proposal,reason:'DEPARTURE_TIME_CHANGE',manual_review_required:true,old_departure:itinerary.start_at,new_departure:'2027-01-10T04:30:00Z'}:{}
  }
  await page.route('**/api/v1/**',async route=>{
    const req=route.request(),url=new URL(req.url()),path=url.pathname,method=req.method();let result,status=200
    if(method!=='GET')mutations.push({path,method,body:req.postDataJSON()})
    if(path.endsWith('/auth/login'))result={access_token:'test-access',refresh_token:'test-refresh'}
    else if(path.endsWith('/auth/google/challenge')){status=503;result={code:'GOOGLE_NOT_CONFIGURED',message:'Google sign-in is not configured yet.'}}
    else if(path.endsWith('/users/me'))result={id:uid,full_name:'Pricing Owner',email:'owner@example.com',approved_roles:passenger?['PASSENGER']:admin?['PASSENGER','OWNER','DRIVER','ADMIN']:['PASSENGER','OWNER','DRIVER'],email_verified_at:'2026-10-27T01:00:00Z',account_status:'ACTIVE'}
    else if(path.endsWith('/users/me/roles'))result={items:(passenger?['PASSENGER']:admin?['PASSENGER','OWNER','DRIVER','ADMIN']:['PASSENGER','OWNER','DRIVER']).map(role_code=>({role_code,approval_status:'APPROVED'}))}
    else if(path==='/api/v1/notifications')result={items:[]}
    else if(path.endsWith('/owners/me/vehicles'))result={items:[{id:vid,label:'Test Van AB-1234',verification_status:'APPROVED',published:true}],has_next:false}
    else if(path==='/api/v1/bookings')result={items:[booking,{...booking,id:'management-only',reference:'BKG-MANAGEMENT-ONLY',passenger_user_id:'someone-else'}]}
    else if(path==='/api/v1/service-types')result={items:[{id:sid,name:'Long-distance private hire',code:'LONG_DISTANCE'}]}
    else if(path==='/api/v1/locations')result={items:[url.searchParams.get('q').includes('Kandy')?B:A]}
    else if(path.endsWith('/services/preview'))result={...price,example_only:true,message:'Owner-entered example only. This is not a booking price or availability promise.'}
    else if(path.endsWith('/services')&&method==='GET')result={items:[config]}
    else if(path.endsWith('/services')&&method==='PUT'){const body=req.postDataJSON();config={...body,version:config.version+1,message:'Reusable rates saved. Future matching requests calculate a fresh price; accepted booking prices stay preserved.'};result=config}
    else if(path===`/api/v1/bookings/${bid}/quote`){booking={...booking,version:2,proposal:{kind:'QUOTE',quote:{calculation:price,digest:'q'.repeat(64)}}};result=booking}
    else if(path===`/api/v1/bookings/${bid}/price-acceptance`){booking={...booking,status:'AWAITING_DRIVER',version:booking.version+1,accepted_quote_digest:booking.proposal.quote.digest,proposal:{}};result=booking}
    else if(path===`/api/v1/bookings/${bid}/changes/accept`){booking={...booking,version:2,proposal:{...booking.proposal,passenger_accepted:true,manual_review_required:true,manual_review_reason:'This interval conflicts with a committed vehicle booking.'}};result=booking}
    else if(path===`/api/v1/bookings/${bid}/changes`){const body=req.postDataJSON();booking={...booking,version:2,proposal:{kind:'CHANGE_REQUEST_UNPRICED',reason:body.reason,old_total:'2050.00',itinerary:body.itinerary,old_departure:itinerary.start_at,new_departure:body.itinerary.start_at,message:'A new disclosed quote and Passenger acceptance are required.'}};result=booking}
    else if(path===`/api/v1/bookings/${bid}`)result=booking
    else if(path==='/api/v1/search/vehicles')result={items:[{id:vid,reference:'VEH-TEST',make:'Test',model:'Van',passenger_seats:4,large_luggage:2,owner_reference:'USR-0000000000000001',owner_name:'Real fixture Owner',price,reserved_end_at:'2027-01-10T05:30:00Z'}],message:'Only complete matching rates are priced.'}
    else if(path===`/api/v1/vehicles/${vid}`)result={id:vid,reference:'VEH-TEST',make:'Test',model:'Van',vehicle_type_code:'VAN',manufacture_year:2020,colour:'White',passenger_seats:4,large_luggage:2,owner_reference:'USR-0000000000000001',photos:[]}
    else if(path==='/api/v1/vehicles')result={items:[{id:vid,reference:'VEH-TEST',make:'Test',model:'Van',passenger_seats:4,large_luggage:2,owner_reference:'USR-0000000000000001',owner_name:'Real fixture Owner'}]}
    else if(path==='/api/v1/bookings/private-hires'){status=201;booking={...booking,passenger_user_id:uid,owner_user_id:'another-owner',proposal:{kind:'QUOTE',quote:{calculation:price,rule:rate,digest:'q'.repeat(64)}}};result=booking}
    else {status=404;result={message:'Unexpected test endpoint.'}}
    return route.fulfill({status,json:result})
  })
  await page.goto('/login');await page.getByLabel('Email address',{exact:true}).fill('owner@example.com');await page.getByLabel('Password',{exact:true}).fill('Existing password');await page.getByRole('button',{name:'Log in',exact:true}).click();await expect(page).toHaveURL(/\/dashboard$/)
  return mutations
}

async function navigate(page,path){await page.evaluate(path=>{history.pushState({},'',path);dispatchEvent(new PopStateEvent('popstate'))},path)}
async function rates(page){await navigate(page,'/owner/rates');await page.getByLabel('Vehicle (Required)',{exact:true}).selectOption(vid);await page.getByLabel('Private-hire service (Required)',{exact:true}).selectOption(sid);await expect(page.getByRole('form',{name:'Reusable vehicle rate form'})).toBeVisible()}

for(const role of ['admin','owner','driver','passenger'])test(`${role} personal hire retains its workspace through search, quote acceptance and booking detail`,async({page},info)=>{
 test.setTimeout(60000)
 const personal=role!=='passenger',writes=await setup(page,{admin:role==='admin',passenger:!personal})
 const prefix=personal?'/'+role+'/personal':''
 if(personal){
  await navigate(page,'/'+role+'/dashboard')
  const trigger=page.getByRole('button',{name:'Open workspace navigation',exact:true});if(await trigger.isVisible())await trigger.click()
  await page.getByRole('navigation',{name:role==='admin'?'Super Admin sidebar':role==='owner'?'Vehicle Owner sidebar':'Driver sidebar',exact:true}).filter({visible:true}).getByRole('link',{name:'Travel & Booking',exact:true}).click()
 }else await navigate(page,'/hire')
 await expect(page.getByRole('heading',{name:personal?'Book a ride for myself':'Plan your long-distance trip',exact:true})).toBeVisible()
 const shell=()=>page.locator(personal?'.workspace-shell[data-workspace="'+role+'"]':'.customer-shell')
 async function retained(){await expect(shell()).toBeVisible();await expect(shell().locator('.site-header')).toHaveCount(1);await expect(page.locator('.passenger-dashboard')).toHaveCount(0);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)}
 await retained()
 if(personal)for(const name of ['Home','Vehicles','Tickets','Rentals','For Owners','For Drivers','Travel Reels'])await expect(page.getByRole('navigation',{name:'Main navigation',exact:true}).getByRole('link',{name,exact:true})).toHaveCount(0)
 await page.getByLabel('Service (Required)',{exact:true}).selectOption(sid)
 await page.getByLabel('Passengers (Required)',{exact:true}).fill('2')
 await page.getByLabel('Pickup date and time (Required)',{exact:true}).fill('2027-01-10T09:00')
 await page.getByLabel('Service hours by day (Required)',{exact:true}).fill('3')
 for(const [label,place] of [['Pickup','Colombo'],['Destination','Kandy']]){
  const input=page.getByRole('searchbox',{name:new RegExp('^'+label)})
  await input.fill(place);await input.press('Enter')
  await page.getByRole('button',{name:place,exact:true}).click()
 }
 await page.getByRole('button',{name:'Find priced vehicles',exact:true}).click()
 await page.getByRole('link',{name:'Vehicle details',exact:true}).click()
 await expect(page).toHaveURL(new RegExp(prefix+'/vehicles/'+vid+'$'));await retained()
 await page.goBack();await expect(page).toHaveURL(new RegExp(prefix+'/hire$'));await retained()
 await page.goForward();await expect(page).toHaveURL(new RegExp(prefix+'/vehicles/'+vid+'$'));await retained()
 await page.getByRole('link',{name:'Browse vehicles',exact:true}).click()
 await expect(page).toHaveURL(new RegExp(prefix+'/hire$'))
 await page.getByRole('button',{name:'Request this priced trip',exact:true}).click()
 await expect(page).toHaveURL(new RegExp(prefix+'/bookings/'+bid+'$'));await retained()
 await expect(page.getByRole('heading',{name:'Trip quote for your itinerary',exact:true})).toBeVisible()
 await page.getByRole('button',{name:'Accept this itinerary and price',exact:true}).click()
 await expect(page.getByText('AWAITING DRIVER',{exact:true})).toBeVisible()
 await page.screenshot({path:info.outputPath(role+'-booking-detail.png'),fullPage:true})
 await page.getByRole('link',{name:'My journeys and requests',exact:true}).click()
 await expect(page).toHaveURL(new RegExp(prefix+'/bookings$'))
 await expect(page.locator('h1')).toHaveText(personal?'My personal trips':'My Trips')
 await expect(page.getByText('BKG-MANAGEMENT-ONLY',{exact:true})).toHaveCount(0)
 await page.getByRole('link').filter({hasText:'BKG-TEST-JOURNEY'}).first().click()
 await expect(page).toHaveURL(new RegExp(prefix+'/bookings/'+bid));await retained()
 const deepLink=page.url();await page.reload();await expect(page.getByRole('button',{name:'Log in',exact:true})).toBeVisible()
 await page.getByLabel('Email address',{exact:true}).fill('owner@example.com');await page.getByLabel('Password',{exact:true}).fill('Existing password');await page.getByRole('button',{name:'Log in',exact:true}).click();await expect(page).toHaveURL(/dashboard$/)
 await navigate(page,new URL(deepLink).pathname+new URL(deepLink).search);await expect(page.getByText('AWAITING DRIVER',{exact:true})).toBeVisible();await retained()
 const created=writes.filter(x=>x.path==='/api/v1/bookings/private-hires');expect(created).toHaveLength(1)
 for(const field of ['role','owner_user_id','driver_user_id'])expect(created[0].body).not.toHaveProperty(field)
 expect(writes.filter(x=>!x.path.startsWith('/api/v1/auth/')&&!x.path.startsWith('/api/v1/bookings/')&&!x.path.startsWith('/api/v1/search/'))).toEqual([])
})

for(const role of ['admin','owner','driver'])test(`${role} personal pages do not display management bookings or operations`,async({page})=>{
 await setup(page,{admin:role==='admin'})
 await navigate(page,`/${role}/personal/bookings/${bid}`)
 await expect(page.getByRole('alert')).toContainText('This booking is not one of your personal journeys')
 await expect(page.getByRole('heading',{name:'BKG-TEST-JOURNEY',exact:true})).toHaveCount(0)
 for(const name of ['Accept assignment','Accept & Self-drive','Commit vehicle and offer assignment'])await expect(page.getByRole('button',{name,exact:true})).toHaveCount(0)
 await expect(page.locator('.workspace-shell[data-workspace="'+role+'"]')).toBeVisible()
})

for(const role of ['owner','driver'])test(`${role} personal confirmed booking re-enters its matching workspace after driver acceptance`,async({page})=>{
 await setup(page)
 const confirmed={id:bid,reference:'BKG-PERSONAL-CONFIRMED',owner_user_id:'other-owner',passenger_user_id:uid,vehicle_id:vid,service_type_id:sid,status:'CONFIRMED',version:3,start_at:itinerary.start_at,end_at:'2027-01-10T05:30:00Z',itinerary:{itinerary},price:{initial:{calculation:price,rule:rate,itinerary},current:{calculation:price,rule:rate,itinerary}},proposal:{},vehicle_committed:true,accepted_quote_digest:'q'.repeat(64),trip:{id:'external-trip',driver_user_id:'other-driver',assignment_status:'ACCEPTED',status:'READY',version:2}}
 await page.route('**/api/v1/bookings/'+bid,route=>route.fulfill({json:confirmed}))
 await navigate(page,`/${role}/personal/bookings/${bid}`)
 await expect(page.locator('.workspace-shell[data-workspace="'+role+'"]').locator('.site-header')).toHaveCount(1)
 await expect(page.getByText('CONFIRMED',{exact:true})).toBeVisible()
 await expect(page.getByRole('button',{name:'Accept assignment',exact:true})).toHaveCount(0)
 await page.getByRole('link',{name:'My journeys and requests',exact:true}).click()
 await expect(page).toHaveURL(new RegExp('/'+role+'/personal/bookings$'))
})

for(const role of ['owner','driver'])test(`${role} personal booking status refresh handles focus, unchanged and unavailable responses`,async({page},info)=>{
 await setup(page)
 let mode='waiting', reads=0, release
 const row={id:bid,reference:'BKG-REFRESH',owner_user_id:'other-owner',passenger_user_id:uid,vehicle_id:vid,service_type_id:sid,status:'AWAITING_DRIVER',version:2,start_at:itinerary.start_at,end_at:'2027-01-10T05:30:00Z',itinerary:{itinerary},price:{initial:{calculation:price,rule:rate,itinerary},current:{calculation:price,rule:rate,itinerary}},proposal:{},vehicle_committed:true,accepted_quote_digest:'q'.repeat(64),trip:null}
 await page.route('**/api/v1/bookings/'+bid,async route=>{
  reads++
  if(mode==='error')return route.fulfill({status:503,json:{message:'Booking service unavailable'}})
  if(mode==='denied')return route.fulfill({status:403,json:{message:'Access unavailable'}})
  if(mode==='delayed')await new Promise(resolve=>{release=resolve})
  await route.fulfill({json:mode==='confirmed'?{...row,status:'CONFIRMED',version:3}:row})
 })
 await navigate(page,`/${role}/personal/bookings/${bid}`)
 await expect(page.getByText('AWAITING DRIVER',{exact:true})).toBeVisible()
 mode='delayed';await page.getByRole('button',{name:'Refresh status',exact:true}).click()
 await expect(page.getByRole('button',{name:'Checking status…'})).toBeDisabled()
 await expect(page.getByText('Checking the latest booking status…')).toBeVisible()
 await expect.poll(()=>Boolean(release)).toBe(true);release();mode='waiting'
 await expect(page.getByText('Status checked: no change.')).toBeVisible()
 mode='error';await page.getByRole('button',{name:'Refresh status',exact:true}).click()
 await expect(page.getByRole('alert')).toContainText('Booking service unavailable')
 await expect(page.getByText('Status could not be updated. The last retrieved booking is shown.')).toBeVisible()
 await expect(page.getByText('AWAITING DRIVER',{exact:true})).toBeVisible()
 mode='confirmed';const previousReads=reads
 await page.evaluate(()=>window.dispatchEvent(new Event('focus')))
 await expect.poll(()=>reads).toBeGreaterThan(previousReads)
 await expect(page.getByText('CONFIRMED',{exact:true})).toBeVisible()
 await expect(page.getByText('Status updated: CONFIRMED.')).toBeVisible()
 await expect(page.locator('.workspace-shell[data-workspace="'+role+'"]').locator('.site-header')).toHaveCount(1)
 await expect(page).toHaveURL(new RegExp('/'+role+'/personal/bookings/'+bid+'$'))
 await page.screenshot({path:`../.tools/personal-booking-refresh-2026-11-04/${role}-${info.project.name}-confirmed.png`,fullPage:true})
 mode='denied';await page.getByRole('button',{name:'Refresh status',exact:true}).click()
 await expect(page.getByRole('alert')).toContainText('Access unavailable')
 await expect(page.getByRole('heading',{name:'BKG-REFRESH'})).toHaveCount(0)
})

test('Owner self-drive and contextual Driver Mode stay within the Owner trip',async({page})=>{
 await setup(page)
 let row={id:bid,reference:'SELF-DRIVE',owner_user_id:uid,passenger_user_id:'other',status:'REQUESTED',version:1,accepted_quote_digest:'accepted',itinerary:{itinerary},price:{},proposal:{},start_at:itinerary.start_at,end_at:'2027-01-10T05:30:00Z'}
 const writes=[]
 await page.route('**/api/v1/bookings/'+bid+'**',async route=>{
  if(route.request().method()==='POST'){
   writes.push(new URL(route.request().url()).pathname)
   row={...row,status:'CONFIRMED',version:2,trip:{id:'self-trip',driver_user_id:uid,assignment_status:'ACCEPTED',status:'READY',version:1}}
  }
  await route.fulfill({json:row})
 })
 await navigate(page,'/bookings/'+bid+'?workspace=owner')
 await page.getByRole('button',{name:'Accept & Self-drive',exact:true}).click()
 await expect(page.getByRole('region',{name:'Driver Mode',exact:true})).toContainText('accepted')
 await expect(page.getByRole('button',{name:'Start trip after eligibility recheck'})).toBeVisible()
 await expect(page).toHaveURL(/workspace=owner$/)
 expect(writes).toEqual(['/api/v1/bookings/'+bid+'/self-drive'])
})

test('external assignment remains pending until the assigned Driver accepts',async({page})=>{
 await setup(page)
 let driverView=false,row={id:bid,reference:'EXTERNAL',owner_user_id:uid,passenger_user_id:'other',status:'REQUESTED',version:1,accepted_quote_digest:'accepted',itinerary:{itinerary},price:{},proposal:{},start_at:itinerary.start_at,end_at:'2027-01-10T05:30:00Z'}
 const writes=[]
 await page.route('**/api/v1/bookings/'+bid+'**',async route=>{
  if(route.request().method()==='POST'){
   writes.push(new URL(route.request().url()).pathname)
   row={...row,status:'AWAITING_DRIVER',version:2,trip:{id:'external-trip',driver_user_id:'external',assignment_status:'PENDING',status:'READY',version:1}}
  }
  await route.fulfill({json:driverView?{...row,owner_user_id:'other-owner',trip:{...row.trip,driver_user_id:uid}}:row})
 })
 await navigate(page,'/bookings/'+bid+'?workspace=owner')
 await page.getByLabel('Driver public reference (Required)',{exact:true}).fill('USR-1234567890ABCDEF')
 await page.getByRole('button',{name:'Commit vehicle and offer assignment',exact:true}).click()
 await expect(page.getByText('AWAITING DRIVER',{exact:true})).toBeVisible()
 await expect(page.getByRole('button',{name:'Accept assignment',exact:true})).toHaveCount(0)
 await expect(page.getByRole('region',{name:'Driver Mode'})).toHaveCount(0)
 driverView=true
 await navigate(page,'/bookings/'+bid+'?workspace=driver')
 await expect(page.getByRole('button',{name:'Accept assignment',exact:true})).toBeVisible()
 await expect(page.getByRole('button',{name:'Decline assignment',exact:true})).toBeVisible()
 expect(writes).toEqual(['/api/v1/bookings/'+bid+'/driver-assignments'])
 await page.route('**/api/v1/trips/external-trip/assignment-accept',async route=>{writes.push(new URL(route.request().url()).pathname);row={...row,status:'CONFIRMED',trip:{...row.trip,assignment_status:'ACCEPTED'}};await route.fulfill({json:row})})
 await page.getByRole('button',{name:'Accept assignment',exact:true}).click()
 await expect(page.getByText('CONFIRMED',{exact:true})).toBeVisible()
 expect(writes).toHaveLength(2)
})

test('fixed-fare departure applicability is explicit, responsive and saved in the shared form',async({page},info)=>{
  const viewport=page.viewportSize()
  const writes=await setup(page);await rates(page)
  await page.getByLabel('Pricing method (Required)',{exact:true}).selectOption('FIXED_ROUTE')
  await page.getByLabel('Fixed route fare (Required)',{exact:true}).fill('1700')
  await expect(page.getByLabel('Applicable departures (Required)',{exact:true})).toHaveValue('')
  await page.getByLabel('Applicable departures (Required)',{exact:true}).selectOption('WEEKLY_WINDOW')
  await page.getByLabel('Departure window starts (Required)',{exact:true}).fill('22:00')
  await page.getByLabel('Departure window ends (Required)',{exact:true}).fill('05:00')
  await page.getByRole('button',{name:'Save reusable rates',exact:true}).click()
  await expect(page.getByLabel('Applicable departures (Required)',{exact:true})).toHaveAttribute('aria-invalid','true')
  expect(writes.filter(x=>x.method==='PUT')).toHaveLength(0)
  await page.getByLabel('Monday',{exact:true}).check()
  await page.getByRole('button',{name:'Save reusable rates',exact:true}).click()
  await expect(page.getByText('Reusable rates saved.',{exact:false})).toBeVisible()
  const saved=writes.find(x=>x.method==='PUT').body.rules[0]
  expect(saved.departure).toEqual({kind:'WEEKLY_WINDOW',weekdays:[0],from_time:'22:00',until_time:'05:00'})
  expect(saved.base_charge).toBeUndefined();expect(saved.night_km_rate).toBeUndefined()
  await expect(page.getByLabel('Included waiting (Required)',{exact:true})).toHaveValue('20')
  for(const width of [360,768,1366]){await page.setViewportSize({width,height:900});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)}
  await page.setViewportSize(viewport)
  await page.getByRole('group',{name:'Fixed-fare departure applicability',exact:true}).screenshot({path:info.outputPath('departure-applicability.png'),style:'.site-header,.site-header *,.skip-link{visibility:hidden!important}'})
})

test('Owner departure proposal enables date entry and preserves the existing agreement',async({page})=>{
  const writes=await setup(page,{change:true,departure:true});await navigate(page,'/bookings/'+bid)
  await page.getByRole('button',{name:'Propose a trip change'}).click()
  await page.getByLabel('Reason for change (Required)',{exact:true}).selectOption('DEPARTURE_TIME_CHANGE')
  await expect(page.getByLabel('Pickup date and time (Required)',{exact:true})).toBeEnabled()
  await page.getByLabel('Pickup date and time (Required)',{exact:true}).fill('2027-01-10T10:00')
  await page.getByRole('button',{name:'Calculate and propose change'}).click()
  await expect(page.getByText('Added charge and new total are not yet known',{exact:false})).toBeVisible()
  await expect(page.getByRole('button',{name:'Save reusable rates and send quote'})).toBeVisible()
  expect(writes.find(x=>x.path.endsWith('/changes')).body.reason).toBe('DEPARTURE_TIME_CHANGE')
  await expect(page.getByText('LKR 2050.00',{exact:true})).toBeVisible()
})

test('Passenger sees departure changes and old/add/new charges before explicit consent',async({page})=>{
  const writes=await setup(page,{passenger:true,change:true,departure:true});await navigate(page,'/bookings/'+bid)
  await expect(page.getByText('Your existing departure stays agreed until this change is accepted and confirmed.',{exact:false})).toBeVisible()
  await expect(page.getByText('LKR 750.00',{exact:true})).toBeVisible()
  expect(writes.filter(x=>x.path.endsWith('/changes/accept'))).toHaveLength(0)
  await page.getByRole('button',{name:'Accept proposed change and charge'}).click()
  await expect(page.getByText('This interval conflicts with a committed vehicle booking.')).toBeVisible()
  await expect(page.locator('.trip-price').getByText('LKR 2050.00',{exact:true})).toBeVisible()
})

test('shared Owner rate form preserves explicit values, conditional sections and mobile/tablet layout',async({page},info)=>{
  const writes=await setup(page);await rates(page)
  await expect(page.getByText('Each future matching itinerary gets a new calculation.',{exact:false})).toBeVisible()
  await expect(page.getByLabel('Base charge (Required)',{exact:true})).toHaveValue('1000')
  await page.getByLabel('Base charge (Required)',{exact:true}).fill('-1');await page.getByRole('button',{name:'Save reusable rates',exact:true}).click()
  expect(writes.filter(r=>r.method==='PUT')).toHaveLength(0)
  await page.getByLabel('Base charge (Required)',{exact:true}).fill('1200');await page.getByRole('button',{name:'Save reusable rates',exact:true}).click()
  await expect(page.getByText('Reusable rates saved.',{exact:false})).toBeVisible();expect(writes.find(r=>r.method==='PUT').body.rules[0].base_charge).toBe('1200')
  await page.getByLabel('Pricing method (Required)',{exact:true}).selectOption('DAY_HIRE')
  await expect(page.getByLabel('Base charge (Required)',{exact:true})).toHaveCount(0)
  for(const label of ['Day package charge','Included distance per day','Included service hours per day','Extra distance rate','Extra service-hour rate','Night distance surcharge','Overnight Driver cost'])await expect(page.getByLabel(`${label} (Required)`,{exact:true})).toHaveValue('')
  await expect(page.locator('.rate-policy').getByText('22:00–05:00 Sri Lanka time.',{exact:false})).toBeVisible()
  for(const width of [360,768,1366]){await page.setViewportSize({width,height:900});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.getByRole('group',{name:'Day and multi-day hire',exact:true}).screenshot({path:info.outputPath(`day-rates-${width}.png`),style:'.site-header,.skip-link{visibility:hidden!important}'})}
  await page.getByLabel('Pricing method (Required)',{exact:true}).selectOption('FIXED_ROUTE');await expect(page.getByLabel('Fixed route fare (Required)',{exact:true})).toBeVisible();await expect(page.getByLabel('Night distance surcharge (Required)',{exact:true})).toHaveCount(0)
  await page.getByRole('button',{name:'Add rate',exact:true}).click();await expect(page.getByLabel('Free waiting allowance (Required)',{exact:true})).toHaveValue('')
})

test('Owner quote uses the same prefilled reusable rate form and structured payload',async({page})=>{
  const writes=await setup(page);await navigate(page,'/bookings/'+bid)
  await expect(page.getByRole('heading',{name:'Passenger itinerary',exact:true})).toBeVisible();await expect(page.getByLabel('Route pickup (Required)',{exact:true})).toHaveValue('Colombo');await expect(page.getByLabel('Route destination (Required)',{exact:true})).toHaveValue('Kandy')
  await page.getByRole('button',{name:'Save reusable rates and send quote',exact:true}).click();await expect(page.getByRole('heading',{name:'Trip quote for your itinerary'})).toBeVisible()
  const payload=writes.find(r=>r.path.endsWith('/quote')).body;expect(payload.rates.rules[0].coverage.kind).toBe('ROUTE');expect(payload.rates.rules[0]).not.toHaveProperty('total');expect(payload.rates.expected_version).toBe(2)
})

test('changed trip shows old/add/new and preserves agreement when operational checks need review',async({page})=>{
  const writes=await setup(page,{passenger:true,change:true});await navigate(page,'/bookings/'+bid)
  await expect(page.getByText('LKR 2050.00',{exact:true}).first()).toBeVisible();await expect(page.getByText('LKR 750.00',{exact:true})).toBeVisible();await expect(page.getByText('LKR 2800.00',{exact:true})).toBeVisible()
  await page.getByRole('button',{name:'Accept proposed change and charge'}).click();await expect(page.getByText('This interval conflicts with a committed vehicle booking.')).toBeVisible();await expect(page.getByText('The agreed itinerary and price stay in place',{exact:false})).toBeVisible()
  expect(writes.filter(r=>r.path.endsWith('/changes/accept'))).toHaveLength(1)
})

test('Passenger search and Browse keep unpriced vehicles reachable for quotes',async({page})=>{
  await setup(page,{passenger:true});await navigate(page,'/hire')
  await page.getByRole('button',{name:'Browse vehicles / Request a quote'}).click();await expect(page.getByRole('button',{name:'Request a quote',exact:true})).toBeVisible();await expect(page.getByText('A price has not been calculated for this vehicle.',{exact:false})).toBeVisible()
  await page.getByLabel('Pickup (Required)',{exact:true}).fill('Colombo');await page.getByRole('button',{name:'Find location',exact:true}).first().click();await page.getByRole('button',{name:'Colombo',exact:true}).click()
  await page.getByLabel('Destination (Required)',{exact:true}).fill('Kandy');await page.getByRole('button',{name:'Find location',exact:true}).click();await page.getByRole('button',{name:'Kandy',exact:true}).click()
  await page.getByLabel('Pickup date and time (Required)',{exact:true}).fill('2027-01-10T08:00');await page.getByLabel('Service hours by day (Required)',{exact:true}).fill('3');await page.getByLabel('Service (Required)',{exact:true}).selectOption(sid);await page.getByLabel('Passengers (Required)',{exact:true}).fill('2')
  await page.getByRole('button',{name:'Find priced vehicles',exact:true}).click();await expect(page.getByRole('button',{name:'Request this priced trip'})).toBeVisible();await expect(page.getByText('LKR 2050.00',{exact:true})).toBeVisible()
  await page.getByRole('button',{name:'Request this priced trip'}).click();await expect(page).toHaveURL(new RegExp('/bookings/'+bid+'$'))
})
