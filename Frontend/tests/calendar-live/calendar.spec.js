import {test,expect} from '@playwright/test'
import fs from 'node:fs'
const fixture=JSON.parse(fs.readFileSync(new URL('../../../.tools/pricing-browser-fixture.json',import.meta.url),'utf8'))
const backend='http://127.0.0.1:8002/api/v1'
async function login(page,email){await page.goto('/login');await page.getByLabel('Email address',{exact:true}).fill(email);await page.getByLabel('Password',{exact:true}).fill('BrowserTravelly1!');await page.getByRole('button',{name:'Log in',exact:true}).click();await expect(page).toHaveURL(/\/dashboard$/)}
async function navigate(page,path){await page.evaluate(path=>{history.pushState({},'',path);dispatchEvent(new PopStateEvent('popstate'))},path)}
async function auth(request,email){const r=await request.post(backend+'/auth/login',{data:{identifier:email,password:'BrowserTravelly1!'}});expect(r.ok()).toBeTruthy();return {Authorization:'Bearer '+(await r.json()).access_token}}
async function call(request,headers,method,path,data){const r=await request[method](backend+path,{headers,data});expect(r.ok(),await r.text()).toBeTruthy();return r.json()}

test('real calendar: dates, edit conflict, ordinary protection, emergency support and retained withdrawal',async({page,request,browser},info)=>{
 const owner=await auth(request,'pricing-owner@example.com'),passenger=await auth(request,'pricing-passenger@example.com')
 const vid=fixture.vehicle_id,sid=fixture.service_id,day=info.project.name==='desktop'?'2031-02-10':'2031-02-11'
 const rates=await call(request,owner,'get',`/vehicles/${vid}/services`)
 const area={label:'Test coverage',south:'6',north:'9',west:'79',east:'82'}
 const rule={id:crypto.randomUUID(),label:'Calendar fixture rate',pickup_area:area,coverage:{kind:'AREA',area},direction:'ONE_WAY',effective_from:'2026-10-27',method:'DISTANCE',base_charge:'1000',included_km:'10',extra_km_rate:'50',night_km_rate:'10',free_wait_minutes:'20',waiting_hour_rate:'300',return_to_base:'INCLUDED',return_to_base_notes:'Test return included',tolls:'SEPARATE_AT_COST',parking:'INCLUDED',other_charges:[],change_limits:{added_km:'20',added_hours:'2',added_wait_minutes:'30',added_amount:'2000'}}
 await call(request,owner,'put',`/vehicles/${vid}/services`,{service_type_id:sid,expected_version:rates.items.find(r=>r.service_type_id===sid)?.version||0,enabled:true,currency:'LKR',rules:[rule]})
 const a=await call(request,owner,'get','/locations?q=Test%20Pickup'),b=await call(request,owner,'get','/locations?q=Test%20Destination')
 const itinerary={start_at:day+'T09:00:00+05:30',direction:'ONE_WAY',method:'DISTANCE',service_hours:['3'],stops:[{place:a.items[0],wait_minutes:'0',overnight_rest:false},{place:b.items[0],wait_minutes:'0',overnight_rest:false}]}
 let booking=await call(request,passenger,'post','/bookings/private-hires',{vehicle_id:vid,service_type_id:sid,itinerary,passenger_count:2,large_luggage_count:0,small_luggage_count:0,idempotency_key:crypto.randomUUID()})
 booking=await call(request,passenger,'post',`/bookings/${booking.id}/price-acceptance`,{expected_version:booking.version,digest:booking.proposal.quote.digest})
 booking=await call(request,owner,'post',`/bookings/${booking.id}/self-drive`,{expected_version:booking.version})
 const price=booking.price
 await login(page,'pricing-owner@example.com');await navigate(page,`/owner/vehicles/${vid}`);await page.getByRole('link',{name:'Availability calendar',exact:true}).click()
 await page.getByLabel('Week starting (Required)',{exact:true}).fill(day)
 await expect(page.getByText(booking.reference,{exact:true})).toBeVisible()
 const start=page.getByLabel('Start (Sri Lanka time) (Required)',{exact:true}),end=page.getByLabel('End (Sri Lanka time) (Required)',{exact:true}),reason=page.getByLabel('Block reason (Required)',{exact:true})
 await start.fill(day+'T10:00');await end.fill(day+'T11:00');await reason.fill('Test ordinary overlap');await page.getByRole('button',{name:'Create block',exact:true}).click()
 await expect(page.getByText('Resolve overlapping commitments before saving this ordinary block.',{exact:false})).toBeVisible()
 await page.getByLabel('Block type (Required)',{exact:true}).selectOption('EMERGENCY');await reason.fill('Test emergency repair');await page.getByRole('button',{name:'Create block',exact:true}).click()
 await expect(page.getByText('Admin support required — commitments retained',{exact:true})).toBeVisible()
 const emergency=page.locator('.calendar-entry').filter({has:page.getByRole('heading',{name:'EMERGENCY',exact:true})})
 await emergency.getByRole('button',{name:'Withdraw block',exact:true}).click();await page.getByLabel('Withdrawal reason (Required)',{exact:true}).fill('Test repair resolved');await page.getByRole('button',{name:'Confirm withdrawal',exact:true}).click()
 await expect(page.getByText('WITHDRAWN EMERGENCY',{exact:true})).toBeVisible();await expect(page.getByText(booking.reference,{exact:true})).toBeVisible()
 const retained=await call(request,owner,'get',`/bookings/${booking.id}`);expect(retained.vehicle_committed).toBe(true);expect(retained.price).toEqual(price);expect(retained.status).toBe('CONFIRMED')
 await page.getByLabel('Block type (Required)',{exact:true}).selectOption('PERSONAL');await start.fill(day+'T14:00');await end.fill(day+'T16:00');await reason.fill('Test personal plans');await page.getByRole('button',{name:'Create block',exact:true}).click()
 let personal=page.locator('.calendar-entry').filter({has:page.getByRole('heading',{name:'PERSONAL',exact:true})})
 await personal.getByRole('button',{name:'Edit block',exact:true}).click();await end.fill(day+'T17:00');await reason.fill('Test changed plans');await page.getByRole('button',{name:'Save block changes',exact:true}).click();await expect(personal.getByText('Test changed plans',{exact:true})).toBeVisible()
 // A competing real API edit must produce a visible stale-version error, never overwrite it.
 await personal.getByRole('button',{name:'Edit block',exact:true}).click()
 let records=await call(request,owner,'get',`/vehicles/${vid}/calendar?${new URLSearchParams({start_at:day+'T00:00:00+05:30',end_at:day+'T23:59:00+05:30'})}`)
 const record=records.events.find(e=>e.kind==='PERSONAL')
 await call(request,owner,'patch',`/vehicles/${vid}/availability-blocks/${record.id}`,{expected_version:record.version,kind:'PERSONAL',start_at:record.start_at,end_at:record.end_at,reason:'Changed in another session'})
 await reason.fill('Stale browser change');await page.getByRole('button',{name:'Save block changes',exact:true}).click();await expect(page.getByText('Block changed. Refresh the calendar before retrying.',{exact:true})).toBeVisible()
 await page.getByRole('button',{name:'Cancel edit',exact:true}).click();await page.getByRole('button',{name:'Refresh calendar',exact:true}).click();await expect(personal.getByText('Changed in another session',{exact:true})).toBeVisible()
 await personal.getByRole('button',{name:'Withdraw block',exact:true}).click();await page.getByLabel('Withdrawal reason (Required)',{exact:true}).fill('Plans no longer needed');await page.getByRole('button',{name:'Confirm withdrawal',exact:true}).click();await expect(page.getByText('WITHDRAWN PERSONAL',{exact:true})).toBeVisible()
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
 await page.locator('.calendar-week').screenshot({path:info.outputPath('calendar-week.png')})
 await page.locator('#calendar-entries').screenshot({path:info.outputPath('calendar-entries.png'),style:'.site-header{visibility:hidden!important}'})
 const context=await browser.newContext({viewport:page.viewportSize()}),admin=await context.newPage()
 await login(admin,'vehicle-admin@example.com');await navigate(admin,'/bookings');await admin.getByRole('link',{name:'Review affected vehicle commitments',exact:true}).first().click();await admin.getByLabel('Week starting (Required)',{exact:true}).fill(day);await expect(admin.getByText(booking.reference,{exact:true})).toBeVisible();await expect(admin.getByRole('form',{name:'Availability block'})).toHaveCount(0)
 await context.close()
})
