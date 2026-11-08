import { test, expect } from '@playwright/test'
import fs from 'node:fs/promises'

const fixture=JSON.parse(await fs.readFile(process.env.TRAVELLY_PRICING_FIXTURE_PATH || new URL('../../../.tools/pricing-browser-fixture.json',import.meta.url),'utf8'))
async function login(page,email){await page.goto('/login');await page.getByLabel('Email address',{exact:true}).fill(email);await page.getByLabel('Password',{exact:true}).fill('BrowserTravelly1!');await page.getByRole('button',{name:'Log in',exact:true}).click();await expect(page).toHaveURL(/\/dashboard$/)}
async function navigate(page,path){await page.evaluate(path=>{history.pushState({},'',path);dispatchEvent(new PopStateEvent('popstate'))},path)}
async function place(page,label,text){const input=page.getByLabel(label+' (Required)',{exact:true});await input.fill(text);const box=input.locator('..').locator('..');await box.getByRole('button',{name:'Find location',exact:true}).click();await box.getByRole('button',{name:text,exact:true}).click()}

for(const role of ['owner','driver'])test(`real API: ${role} personal detail refreshes after Driver accepts`,async({page,browser},info)=>{
 await login(page,'pricing-owner@example.com');await navigate(page,'/owner/rates')
 await page.getByLabel('Vehicle (Required)',{exact:true}).selectOption(fixture.vehicle_id);await page.getByLabel('Private-hire service (Required)',{exact:true}).selectOption(fixture.service_id)
 await expect(page.getByRole('form',{name:'Reusable vehicle rate form'})).toBeVisible()
 await page.getByLabel('Rate name (Required)',{exact:true}).fill('Refresh test route');await page.getByLabel('Effective from (Required)',{exact:true}).fill('2026-10-27')
 if(await page.getByLabel('Operating / pickup area centre (Required)',{exact:true}).count()){
  await place(page,'Operating / pickup area centre','Test Pickup');await page.getByLabel('Distance from centre to each edge (Required)',{exact:true}).fill('30')
  await place(page,'Route pickup','Test Pickup');await place(page,'Route destination','Test Destination')
 }
 for(const [label,value] of [['Base charge','1000'],['Included distance','10'],['Extra distance rate','50'],['Night distance surcharge','10'],['Free waiting allowance','20'],['Extra waiting rate','300'],['Maximum additional route distance','20'],['Maximum additional service time','2'],['Maximum additional waiting','30'],['Maximum added charge','2000']])await page.getByLabel(label+' (Required)',{exact:true}).fill(value)
 await page.getByLabel('Return-to-base charge (Required)',{exact:true}).selectOption('INCLUDED');await page.getByLabel('Return-to-base terms (Required)',{exact:true}).fill('Return included.')
 await page.getByLabel('Tolls (Required)',{exact:true}).selectOption('SEPARATE_AT_COST');await page.getByLabel('Parking (Required)',{exact:true}).selectOption('INCLUDED')
 await page.getByRole('button',{name:'Save reusable rates',exact:true}).click();await expect(page.getByText('Reusable rates saved.',{exact:false})).toBeVisible()
 const passengerContext=await browser.newContext({viewport:page.viewportSize()}),passenger=await passengerContext.newPage()
 await login(passenger,'pricing-passenger@example.com');await navigate(passenger,`/${role}/personal/hire`)
 await place(passenger,'Pickup','Test Pickup');await place(passenger,'Destination','Test Destination')
 const day=(info.project.name==='desktop'?10:12)+(role==='driver'?1:0)
 await passenger.getByLabel('Pickup date and time (Required)',{exact:true}).fill(`2031-01-${day}T08:00`)
 await passenger.getByLabel('Service hours by day (Required)',{exact:true}).fill('3');await passenger.getByLabel('Service (Required)',{exact:true}).selectOption(fixture.service_id);await passenger.getByLabel('Passengers (Required)',{exact:true}).fill('2')
 await passenger.getByRole('button',{name:'Find priced vehicles',exact:true}).click();await passenger.getByRole('button',{name:'Request this priced trip',exact:true}).click()
 await expect(passenger).toHaveURL(new RegExp('/'+role+'/personal/bookings/[a-f0-9-]+$'));const bookingId=passenger.url().split('/').at(-1)
 await passenger.getByRole('button',{name:'Accept this itinerary and price'}).click();await expect(passenger.getByRole('heading',{name:'Agreed price'})).toBeVisible()
 await navigate(page,'/bookings/'+bookingId+'?workspace=owner');await page.getByLabel('Driver public reference (Required)',{exact:true}).fill(fixture.driver_reference)
 await page.getByRole('button',{name:'Commit vehicle and offer assignment',exact:true}).click();await expect(page.getByText('AWAITING DRIVER',{exact:true})).toBeVisible()
 await passenger.getByRole('button',{name:'Refresh status'}).click();await expect(passenger.getByText('AWAITING DRIVER',{exact:true})).toBeVisible()
 const driverContext=await browser.newContext({viewport:page.viewportSize()}),driver=await driverContext.newPage()
 await login(driver,'pricing-driver@example.com');await navigate(driver,'/bookings/'+bookingId+'?workspace=driver')
 await driver.getByRole('button',{name:'Accept assignment',exact:true}).click();await expect(driver.getByText('CONFIRMED',{exact:true})).toBeVisible()
 await passenger.getByRole('button',{name:'Refresh status'}).click();await expect(passenger.getByText('CONFIRMED',{exact:true})).toBeVisible()
 await expect(passenger.getByText('Status updated: CONFIRMED.')).toBeVisible();await expect(passenger.locator(`.workspace-shell[data-workspace="${role}"]`)).toBeVisible()
 await passenger.screenshot({path:`../.tools/personal-booking-refresh-2026-11-04/${role}-${info.project.name}-real-confirmed.png`,fullPage:true})
 await driverContext.close();await passengerContext.close()
})
