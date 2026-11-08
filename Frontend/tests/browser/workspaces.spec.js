import {test,expect} from '@playwright/test'
import {setup,visit} from './helpers/redesign.js'
import {workspaceRoles,workspaceMenu} from '../../src/routes/workspaceRoutes.js'
const operations=['OWNER','DRIVER','ADMIN']
async function nav(page,role){const button=page.getByRole('button',{name:'Open workspace navigation',exact:true});if(await button.isVisible())await button.click();return page.getByRole('navigation',{name:workspaceRoles[role].label+' sidebar',exact:true}).filter({visible:true})}
for(const [width,height] of [[1920,1080],[1440,900],[1100,760],[1024,900],[768,900],[390,844],[320,640],[1440,650]])test(`operational navigation fits ${width}x${height} without desktop scrolling`,async({page})=>{
 await setup(page);await page.setViewportSize({width,height})
 for(const role of operations){
  await visit(page,workspaceRoles[role].home);await expect(page.locator('.overview-banner h1')).toBeVisible()
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
  const sidebar=await nav(page,role)
  for(const item of workspaceMenu(role))await expect(sidebar.getByRole('link',{name:item.label,exact:true})).toHaveAttribute('href',item.path)
  await expect(sidebar.getByRole('link',{name:'Dashboard',exact:true})).toHaveAttribute('aria-current','page')
  await expect(page.getByText('Switch workspace',{exact:true})).toHaveCount(0)
  if(width>=768){
   await expect(page.locator('.workspace-sidebar')).toBeVisible()
   const fit=await sidebar.evaluate(el=>{const box=el.getBoundingClientRect(),last=el.querySelector('button').getBoundingClientRect();return {overflow:getComputedStyle(el.querySelector('.workspace-sidebar-main')).overflowY,bottom:last.bottom,viewport:innerHeight,top:box.top}})
   expect(fit.overflow).toBe('visible');expect(fit.bottom).toBeLessThanOrEqual(height)
  }else{await expect(page.getByRole('dialog')).toBeVisible();await page.keyboard.press('Escape');await expect(page.getByRole('button',{name:'Open workspace navigation',exact:true})).toBeFocused()}
 }
})

test('Passenger dashboard has top navigation only and My Trips remains Passenger data',async({page})=>{
 await setup(page);await visit(page,'/dashboard');await expect(page.locator('.passenger-dashboard h1')).toHaveText('Where will you go next, Kasun?')
 await expect(page.locator('.workspace-sidebar')).toHaveCount(0);await expect(page.getByText('Passenger dashboard',{exact:true})).toHaveCount(0)
 await visit(page,'/bookings');await expect(page.getByRole('heading',{name:'My Trips',exact:true}).first()).toBeVisible()
 await expect(page.getByText('TR-passenger',{exact:false})).toBeVisible()
 for(const id of ['owner','driver','complete'])await expect(page.getByText('TR-'+id,{exact:false})).toHaveCount(0)
 await expect(page.locator('.workspace-sidebar')).toHaveCount(0)
})

test('current approval checks protect all operational routes',async({page})=>{
 const state=await setup(page,{approved:['PASSENGER']})
 for(const path of ['/owner/dashboard','/driver/dashboard','/admin/dashboard','/admin/personal/hire','/admin/personal/owners/test','/admin/personal/vehicles/test','/admin/personal/bookings','/admin/personal/bookings/passenger','/admin/payments','/account?workspace=owner','/owner/personal/hire','/owner/personal/vehicles/test','/owner/personal/owners/test','/owner/personal/bookings','/owner/personal/bookings/passenger','/driver/personal/hire','/driver/personal/vehicles/test','/driver/personal/owners/test','/driver/personal/bookings','/driver/personal/bookings/passenger']){await visit(page,path);await expect(page.getByRole('heading',{name:'Workspace access denied',exact:true})).toBeVisible()}
 state.approved=['PASSENGER','OWNER'];await visit(page,'/owner/dashboard');await expect(page.locator('.overview-banner')).toBeVisible()
 state.approved=['PASSENGER'];await visit(page,'/owner/bookings');await expect(page.getByRole('heading',{name:'Workspace access denied',exact:true})).toBeVisible();await expect(page.getByText('TR-owner',{exact:false})).toHaveCount(0)
})

test('legacy application links reach matching onboarding without granting operational access',async({page})=>{
 const state=await setup(page,{approved:['PASSENGER']});await visit(page,'/account#owner-application')
 // The fixture starts memberships as pending, which must not offer duplicate submission.
 await expect(page.getByRole('article',{name:'Owner application'})).toContainText('Approval is pending')
 await expect(page.getByRole('button',{name:'Submit Owner application',exact:true})).toHaveCount(0)
 await expect(page.getByRole('button',{name:'Open Owner workspace',exact:true})).toHaveCount(0)
 expect(state.requests.filter(([method,path])=>method!=='GET'&&!path.startsWith('/auth/'))).toEqual([])
})

test('role records and existing calendar and trip links stay scoped',async({page})=>{
 await setup(page);await visit(page,'/owner/dashboard');await expect(page.getByText('TR-owner',{exact:false})).toBeVisible();await expect(page.getByRole('link',{name:'Open calendar',exact:false})).toHaveAttribute('href','/owner/vehicles/vehicle-one/calendar')
 await expect(page.getByText('Admin support required. Affected commitments remain protected.',{exact:true})).toBeVisible()
 await visit(page,'/driver/dashboard');await expect(page.getByRole('link',{name:'Open Trip',exact:true})).toHaveAttribute('href','/bookings/driver?workspace=driver');await expect(page.getByText('TR-owner',{exact:false})).toHaveCount(0)
 await visit(page,'/admin/dashboard');await expect(page.getByText('Nimal Silva',{exact:false})).toBeVisible()
})
for(const role of ['owner','driver'])test(`${role} personal trips remain Passenger records`,async({page})=>{
 await setup(page);await visit(page,`/${role}/personal/bookings`);await expect(page.getByText('TR-passenger',{exact:false})).toBeVisible()
 for(const id of ['owner','driver','complete'])await expect(page.getByText('TR-'+id,{exact:false})).toHaveCount(0)
})

test('failed sources recover and incomplete occupancy never appears as empty availability',async({page})=>{
 const state=await setup(page);state.bookingError=true;await visit(page,'/owner/dashboard');await expect(page.getByRole('alert')).toHaveText('Booking source unavailable.')
 await expect(page.getByRole('button',{name:'Try again',exact:true})).toHaveCount(1)
 await expect(page.getByRole('heading',{name:'Booking activity',exact:true})).toHaveCount(0)
 state.bookingError=false;await page.getByRole('button',{name:'Try again',exact:true}).click();await expect(page.getByRole('alert')).toHaveCount(0)
 await expect(page.getByRole('heading',{name:'Booking activity',exact:true})).toBeVisible()
 state.calendarIncomplete=true;await visit(page,'/driver/dashboard');await visit(page,'/owner/dashboard');await expect(page.getByRole('alert')).toHaveText('Availability is incomplete. Do not use this preview for new availability decisions.')
})

test('empty assignments and logout failure remain actionable',async({page})=>{
 const state=await setup(page,{empty:true});await visit(page,'/driver/dashboard');await expect(page.getByRole('heading',{name:'No upcoming assignment',exact:true})).toBeVisible()
 await page.setViewportSize({width:390,height:844});let sidebar=await nav(page,'DRIVER');state.logoutFailure=true;await sidebar.getByRole('button',{name:'Logout',exact:true}).click();await page.keyboard.press('Escape');await expect(page.getByRole('alert')).toHaveText('Sign out unavailable. Try again.')
 state.logoutFailure=false;sidebar=await nav(page,'DRIVER');await sidebar.getByRole('button',{name:'Logout',exact:true}).click();await expect(page).toHaveURL(/\/login$/)
})


test('rejected membership resubmits in matching onboarding and stays pending',async({page})=>{
 const state=await setup(page,{approved:['PASSENGER']});state.roleStatuses.OWNER='REJECTED';await visit(page,'/account#owner-application')
 await page.getByRole('button',{name:'Resubmit Owner application',exact:true}).click()
 await expect(page.getByRole('status')).toContainText('Owner application submitted. Approval is pending.')
 expect(state.applications).toEqual([{role_code:'OWNER'}]);await expect(page).toHaveURL(/\/owner\/onboarding$/)
 await expect(page.getByRole('button',{name:'Open Owner workspace',exact:true})).toHaveCount(0)
})

for(const width of [1440,1024,768,390,320])test(`Passenger dashboard booking controls and no sidebar at ${width}px`,async({page})=>{
 await page.setViewportSize({width,height:900});await setup(page)
 await expect(page.locator('.workspace-sidebar')).toHaveCount(0)
 for(const title of ['Your next trip','Quickly pick up where you left off','Smart journeys for you','Travel Reels'])await expect(page.getByRole('heading',{name:title,exact:true})).toBeVisible()
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
 await page.getByLabel('Pickup location',{exact:true}).fill('Colombo');await page.getByLabel('Destination',{exact:true}).fill('Kandy');await page.getByLabel('Travel date',{exact:true}).fill('2027-01-10T09:30')
 await page.getByRole('button',{name:'Find a ride',exact:true}).click();await expect(page).toHaveURL(/\/hire$/)
 await expect(page.getByRole('searchbox',{name:/^Pickup/})).toHaveValue('Colombo')
 await expect(page.getByLabel('Pickup date and time (Required)',{exact:true})).toHaveValue('2027-01-10T09:30')
})
