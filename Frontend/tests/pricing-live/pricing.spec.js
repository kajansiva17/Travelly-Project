import { test, expect } from '@playwright/test'
import fs from 'node:fs/promises'
const fixture=JSON.parse(await fs.readFile(new URL('../../../.tools/pricing-browser-fixture.json',import.meta.url),'utf8'))

async function login(page,email){await page.goto('/login');await page.getByLabel('Email address',{exact:true}).fill(email);await page.getByLabel('Password',{exact:true}).fill('BrowserTravelly1!');await page.getByRole('button',{name:'Log in',exact:true}).click();await expect(page).toHaveURL(/\/dashboard$/)}
async function navigate(page,path){await page.evaluate(path=>{history.pushState({},'',path);dispatchEvent(new PopStateEvent('popstate'))},path)}
async function place(page,label,text){const input=page.getByLabel(label+' (Required)',{exact:true});await input.fill(text);const box=input.locator('..').locator('..');await box.getByRole('button',{name:'Find location',exact:true}).click();await box.getByRole('button',{name:text,exact:true}).click()}

test('real API: Owner rules to Passenger price acceptance, commitment, changed stop and preserved snapshot',async({page,browser},info)=>{
  await login(page,'pricing-owner@example.com');await navigate(page,'/owner/rates')
  await page.getByLabel('Vehicle (Required)',{exact:true}).selectOption(fixture.vehicle_id);await page.getByLabel('Private-hire service (Required)',{exact:true}).selectOption(fixture.service_id)
  await expect(page.getByRole('form',{name:'Reusable vehicle rate form'})).toBeVisible()
  // One vehicle is reused sequentially by desktop/mobile; edit the saved rule if present.
  await page.getByLabel('Rate name (Required)',{exact:true}).fill('Test reusable route')
  await page.getByLabel('Effective from (Required)',{exact:true}).fill('2026-10-27')
  if(await page.getByLabel('Operating / pickup area centre (Required)',{exact:true}).count()){
    await place(page,'Operating / pickup area centre','Test Pickup');await page.getByLabel('Distance from centre to each edge (Required)',{exact:true}).fill('30')
    await place(page,'Route pickup','Test Pickup');await place(page,'Route destination','Test Destination')
  }
  for(const [label,value] of [['Base charge','1000'],['Included distance','10'],['Extra distance rate','50'],['Night distance surcharge','10'],['Free waiting allowance','20'],['Extra waiting rate','300'],['Maximum additional route distance','20'],['Maximum additional service time','2'],['Maximum additional waiting','30'],['Maximum added charge','2000']])await page.getByLabel(label+' (Required)',{exact:true}).fill(value)
  await page.getByLabel('Return-to-base charge (Required)',{exact:true}).selectOption('INCLUDED');await page.getByLabel('Return-to-base terms (Required)',{exact:true}).fill('Test route includes return to base.')
  await page.getByLabel('Tolls (Required)',{exact:true}).selectOption('SEPARATE_AT_COST');await page.getByLabel('Parking (Required)',{exact:true}).selectOption('INCLUDED')
  await page.getByRole('button',{name:'Save reusable rates',exact:true}).click();await expect(page.getByText('Reusable rates saved.',{exact:false})).toBeVisible()
  await page.getByRole('group',{name:'Distance trip',exact:true}).screenshot({path:info.outputPath('owner-rates.png'),style:'.site-header,.skip-link{visibility:hidden!important}'})
  const context=await browser.newContext({viewport:page.viewportSize()});const passenger=await context.newPage()
  await login(passenger,'pricing-passenger@example.com');await navigate(passenger,'/hire')
  await place(passenger,'Pickup','Test Pickup');await place(passenger,'Destination','Test Destination')
  const tripDate=info.project.name==='desktop'?'2030-01-10T08:00':'2030-01-11T08:00'
  await passenger.getByLabel('Pickup date and time (Required)',{exact:true}).fill(tripDate);await passenger.getByLabel('Service hours by day (Required)',{exact:true}).fill('3');await passenger.getByLabel('Service (Required)',{exact:true}).selectOption(fixture.service_id);await passenger.getByLabel('Passengers (Required)',{exact:true}).fill('2')
  await passenger.getByRole('button',{name:'Find priced vehicles',exact:true}).click();await expect(passenger.getByText('LKR 2000.00',{exact:true})).toBeVisible()
  await passenger.getByRole('button',{name:'Request this priced trip',exact:true}).click();await expect(passenger).toHaveURL(/\/bookings\/[a-f0-9-]+$/)
  const id=passenger.url().split('/').at(-1)
  await passenger.getByRole('button',{name:'Accept this itinerary and price'}).click();await expect(passenger.getByRole('heading',{name:'Agreed price',exact:true})).toBeVisible()
  await navigate(page,'/bookings/'+id);await page.getByRole('button',{name:'Accept & Self-drive'}).click();await expect(page.getByText('CONFIRMED',{exact:true})).toBeVisible()
  await passenger.getByRole('link',{name:'My journeys and requests'}).click();await passenger.getByRole('link',{name:'Review itinerary, price and actions'}).first().click()
  // Open the requested booking directly in-memory when another project already has history.
  await navigate(passenger,'/bookings/'+id)
  await passenger.getByRole('button',{name:'Propose a trip change'}).click();await passenger.getByRole('button',{name:'Add an ordered stop',exact:true}).click();await place(passenger,'Stop 1','Test Extra Stop');await passenger.getByLabel('Service hours by day (Required)',{exact:true}).fill('4')
  await passenger.getByRole('button',{name:'Calculate and propose change'}).click();await expect(passenger.getByText('LKR 750.00',{exact:true})).toBeVisible();await expect(passenger.locator('.change-totals').getByText('LKR 2750.00',{exact:true})).toBeVisible()
  await passenger.getByRole('button',{name:'Accept proposed change and charge'}).click();await expect(passenger.getByRole('heading',{name:'Proposed change',exact:true})).toHaveCount(0);await expect(passenger.getByText('LKR 2750.00',{exact:true})).toBeVisible()
  const overflow=await passenger.evaluate(()=>[...document.querySelectorAll('main *')].map(e=>({tag:e.tagName,cls:e.className,x:e.getBoundingClientRect().x,width:e.getBoundingClientRect().width})).filter(r=>r.x<0||r.x+r.width>innerWidth+1))
  await info.attach('layout-overflow.json',{body:JSON.stringify(overflow),contentType:'application/json'})
  expect(await passenger.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
  await passenger.locator('.rate-preview').first().screenshot({path:info.outputPath('agreed-price.png'),style:'.site-header,.site-header *,.skip-link{visibility:hidden!important}'})
  await navigate(page,'/owner/rates');await page.getByLabel('Vehicle (Required)',{exact:true}).selectOption(fixture.vehicle_id);await page.getByLabel('Private-hire service (Required)',{exact:true}).selectOption(fixture.service_id)
  await page.getByLabel('Extra distance rate (Required)',{exact:true}).fill('60');await page.getByRole('button',{name:'Save reusable rates',exact:true}).click();await expect(page.getByText('Reusable rates saved.',{exact:false})).toBeVisible()
  await passenger.getByRole('link',{name:'My journeys and requests'}).click();await navigate(passenger,'/bookings/'+id);await expect(passenger.getByText('LKR 2750.00',{exact:true})).toBeVisible()
  await context.close()
})
