import {test,expect} from '@playwright/test'
const vid='12222222-2222-4222-8222-222222222222'
test('incomplete calendar and failed mutation disable availability decisions until refresh',async({page})=>{
 let failed=true
 await page.route('**/api/v1/**',async route=>{
  const path=new URL(route.request().url()).pathname
  if(path.endsWith('/auth/login'))return route.fulfill({json:{access_token:'test-access',refresh_token:'test-refresh'}})
  if(path.endsWith('/users/me'))return route.fulfill({json:{id:vid,full_name:'Calendar Owner',approved_roles:['PASSENGER','OWNER'],account_status:'ACTIVE'}})
  if(path.endsWith('/users/me/roles'))return route.fulfill({json:{items:['PASSENGER','OWNER'].map(role_code=>({role_code,approval_status:'APPROVED'}))}})
  if(path.endsWith('/calendar'))return route.fulfill(failed?{status:503,json:{code:'AVAILABILITY_INCOMPLETE',message:'Departure occupancy source unavailable.'}}:{json:{complete:true,checked_at:new Date().toISOString(),availability_status:'ACTIVE',verification_status:'APPROVED',events:[]}})
  if(path.endsWith('/availability-blocks'))return route.fulfill({status:503,json:{code:'AVAILABILITY_INCOMPLETE',message:'Trip occupancy source unavailable.'}})
  return route.fulfill({json:{enabled:false}})
 })
 await page.goto('/login');await page.getByLabel('Email address',{exact:true}).fill('calendar@example.com');await page.getByLabel('Password',{exact:true}).fill('BrowserTravelly1!');await page.getByRole('button',{name:'Log in',exact:true}).click();await expect(page).toHaveURL(/\/dashboard$/)
 await page.evaluate(path=>{history.pushState({},'',path);dispatchEvent(new PopStateEvent('popstate'))},`/owner/vehicles/${vid}/calendar`)
 await expect(page.getByText('Availability is incomplete.',{exact:false})).toBeVisible();await expect(page.getByRole('button',{name:'Create block',exact:true})).toBeDisabled();await expect(page.getByText('No dated entries in this week.',{exact:false})).toHaveCount(0)
 failed=false;await page.getByRole('button',{name:'Refresh calendar',exact:true}).click();await expect(page.getByRole('button',{name:'Create block',exact:true})).toBeEnabled()
 await page.getByLabel('Start (Sri Lanka time) (Required)',{exact:true}).fill('2031-02-10T09:00');await page.getByLabel('End (Sri Lanka time) (Required)',{exact:true}).fill('2031-02-10T10:00');await page.getByLabel('Block reason (Required)',{exact:true}).fill('Planned maintenance');await page.getByRole('button',{name:'Create block',exact:true}).click()
 await expect(page.getByText('Trip occupancy source unavailable.',{exact:true})).toBeVisible();await expect(page.getByText('Availability is incomplete.',{exact:false})).toBeVisible();await expect(page.getByRole('button',{name:'Create block',exact:true})).toBeDisabled()
 await page.getByRole('button',{name:'Refresh calendar',exact:true}).click();await expect(page.getByRole('button',{name:'Create block',exact:true})).toBeEnabled()
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
})
