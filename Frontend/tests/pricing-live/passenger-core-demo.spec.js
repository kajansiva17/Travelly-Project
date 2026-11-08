import {test,expect} from '@playwright/test'
import fs from 'node:fs/promises'
import path from 'node:path'
import {randomUUID,randomInt} from 'node:crypto'

const fixture=JSON.parse(await fs.readFile(process.env.TRAVELLY_PRICING_FIXTURE_PATH,'utf8'))
const password='BrowserTravelly1!',root='../.tools/passenger-core-demo-2026-11-05'
async function login(page,email){await page.goto('/login');await page.getByLabel('Email address',{exact:true}).fill(email);await page.getByLabel('Password',{exact:true}).fill(password);await page.getByRole('button',{name:'Log in',exact:true}).click();await expect(page).toHaveURL(/\/dashboard$/)}
async function navigate(page,url){await page.evaluate(url=>{history.pushState({},'',url);dispatchEvent(new PopStateEvent('popstate'))},url)}
async function place(page,label,text){const input=page.getByLabel(label+' (Required)',{exact:true});await input.fill(text);const box=input.locator('..').locator('..');await box.getByRole('button',{name:'Find location',exact:true}).click();await box.getByRole('button',{name:text,exact:true}).click()}
async function ok(response){expect(response.ok(),`${new URL(response.url()).pathname}: HTTP ${response.status()}`).toBeTruthy();return response.json()}

test('Passenger books, assigned Driver accepts and Passenger refreshes to confirmed',async({page,browser,request})=>{
 const email=randomUUID()+'@example.com',phone='+9477'+String(randomInt(0,10000000)).padStart(7,'0')
 await ok(await request.post('/api/v1/auth/register',{data:{full_name:'Demo Passenger',email,password,phone_e164:phone,preferred_language:'en',accept_terms:true}}))
 const mailRoot=path.join(path.dirname(fixture.image_path),'mail');const names=await fs.readdir(mailRoot);let mail=''
 for(const name of names){const text=await fs.readFile(path.join(mailRoot,name),'utf8');if(text.includes(email)){mail=text;break}}
 const token=mail.replace(/=\r?\n/g,'').replace(/=3D/g,'=').match(/#token=([A-Za-z0-9_-]+)/)[1]
 await ok(await request.post('/api/v1/auth/email/verify',{data:{token}}))
 await login(page,'pricing-owner@example.com');await navigate(page,'/owner/rates')
 await page.getByLabel('Vehicle (Required)',{exact:true}).selectOption(fixture.vehicle_id);await page.getByLabel('Private-hire service (Required)',{exact:true}).selectOption(fixture.service_id)
 await page.getByLabel('Rate name (Required)',{exact:true}).fill('Demo route');await page.getByLabel('Effective from (Required)',{exact:true}).fill('2026-10-27')
 await place(page,'Operating / pickup area centre','Test Pickup');await page.getByLabel('Distance from centre to each edge (Required)',{exact:true}).fill('30');await place(page,'Route pickup','Test Pickup');await place(page,'Route destination','Test Destination')
 for(const [label,value] of [['Base charge','1000'],['Included distance','10'],['Extra distance rate','50'],['Night distance surcharge','10'],['Free waiting allowance','20'],['Extra waiting rate','300'],['Maximum additional route distance','20'],['Maximum additional service time','2'],['Maximum additional waiting','30'],['Maximum added charge','2000']])await page.getByLabel(label+' (Required)',{exact:true}).fill(value)
 await page.getByLabel('Return-to-base charge (Required)',{exact:true}).selectOption('INCLUDED');await page.getByLabel('Return-to-base terms (Required)',{exact:true}).fill('Return included.')
 await page.getByLabel('Tolls (Required)',{exact:true}).selectOption('SEPARATE_AT_COST');await page.getByLabel('Parking (Required)',{exact:true}).selectOption('INCLUDED');await page.getByRole('button',{name:'Save reusable rates',exact:true}).click();await expect(page.getByText('Reusable rates saved.',{exact:false})).toBeVisible()
 const passengerContext=await browser.newContext({viewport:{width:1366,height:900}}),passenger=await passengerContext.newPage()
 await passenger.goto('/');await passenger.getByRole('link',{name:'Log in',exact:true}).first().click();await expect(passenger).toHaveURL(/\/login$/);await passenger.screenshot({path:`${root}/01-login.png`,fullPage:true})
 await passenger.getByLabel('Email address',{exact:true}).fill(email);await passenger.getByLabel('Password',{exact:true}).fill(password);await passenger.getByRole('button',{name:'Log in',exact:true}).click();await expect(passenger).toHaveURL(/\/dashboard$/)
 await expect(passenger.getByRole('heading',{name:/Where will you go next/})).toBeVisible();await passenger.screenshot({path:`${root}/02-passenger-dashboard.png`,fullPage:true})
 for(const role of ['owner','driver']){await navigate(passenger,`/${role}/dashboard`);await expect(passenger.getByRole('heading',{name:'Workspace access denied'})).toBeVisible()}
 await navigate(passenger,'/dashboard');const planner=passenger.getByRole('region',{name:'Plan your journey'});await planner.getByLabel('Pickup location').fill('Test Pickup');await planner.getByLabel('Destination').fill('Test Destination');await planner.getByLabel('Travel date').fill('2031-01-10T08:00');await planner.getByRole('button',{name:'Find a ride'}).click();await expect(passenger).toHaveURL(/\/hire$/)
 await place(passenger,'Pickup','Test Pickup');await place(passenger,'Destination','Test Destination');await passenger.getByLabel('Service hours by day (Required)',{exact:true}).fill('3');await passenger.getByLabel('Service (Required)',{exact:true}).selectOption(fixture.service_id);await passenger.getByLabel('Passengers (Required)',{exact:true}).fill('2')
 await passenger.getByRole('button',{name:'Find priced vehicles',exact:true}).click();await expect(passenger.getByRole('button',{name:'Request this priced trip'})).toBeVisible();await passenger.screenshot({path:`${root}/03-vehicle-search.png`,fullPage:true})
 await passenger.getByRole('button',{name:'Request this priced trip'}).click();await expect(passenger).toHaveURL(/\/bookings\/[a-f0-9-]+$/);const bookingId=passenger.url().split('/').at(-1)
 await expect(passenger.getByRole('heading',{name:'Trip quote for your itinerary'})).toBeVisible();await passenger.screenshot({path:`${root}/04-booking-quote.png`,fullPage:true});await passenger.getByRole('button',{name:'Accept this itinerary and price'}).click();await expect(passenger.getByRole('heading',{name:'Agreed price'})).toBeVisible()
 await navigate(page,'/bookings/'+bookingId+'?workspace=owner');await page.getByLabel('Driver public reference (Required)',{exact:true}).fill(fixture.driver_reference);await page.getByRole('button',{name:'Commit vehicle and offer assignment'}).click();await expect(page.getByText('AWAITING DRIVER',{exact:true})).toBeVisible()
 await passenger.getByRole('button',{name:'Refresh status'}).click();await expect(passenger.getByText('AWAITING DRIVER',{exact:true})).toBeVisible();await passenger.screenshot({path:`${root}/05-awaiting-driver.png`,fullPage:true})
 const driverContext=await browser.newContext({viewport:{width:1366,height:900}}),driver=await driverContext.newPage();await login(driver,'pricing-driver@example.com');await navigate(driver,'/bookings/'+bookingId+'?workspace=driver');await driver.getByRole('button',{name:'Accept assignment'}).click();await expect(driver.getByText('CONFIRMED',{exact:true})).toBeVisible();await driver.screenshot({path:`${root}/06-driver-accepted.png`,fullPage:true})
 await passenger.getByRole('button',{name:'Refresh status'}).click();await expect(passenger.getByText('CONFIRMED',{exact:true})).toBeVisible();await expect(passenger.getByText('Status updated: CONFIRMED.')).toBeVisible();await passenger.screenshot({path:`${root}/07-passenger-confirmed.png`,fullPage:true})
 await driverContext.close();await passengerContext.close()
})
