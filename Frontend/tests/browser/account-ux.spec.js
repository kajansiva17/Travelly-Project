import {test,expect} from '@playwright/test'
test.setTimeout(60000)
const uid='12222222-2222-4222-8222-222222222222'
async function visit(page,path){await page.evaluate(path=>new Promise(resolve=>{history.pushState({},'',path);dispatchEvent(new PopStateEvent('popstate'));requestAnimationFrame(()=>requestAnimationFrame(resolve))}),path)}
async function menu(page){const toggle=page.getByRole('button',{name:'Open navigation',exact:true});if(await toggle.isVisible())await toggle.click()}
async function setup(page){
 const reads=[]
 await page.route('**/api/v1/**',async route=>{
  const req=route.request(),url=new URL(req.url()),path=url.pathname.replace('/api/v1','');let body={}
  if(path==='/auth/login')body={access_token:'account-test-access',refresh_token:'account-test-refresh',expires_in:900}
  else if(path==='/users/me'){reads.push(req.headers().authorization);body={id:uid,full_name:'Account Passenger',account_status:'ACTIVE',email:'account@example.com',phone_e164:'+94771234567',approved_roles:['PASSENGER'],email_verified_at:'2026-10-27T00:00:00Z'}}
  else if(path==='/users/me/roles')body={items:[{role_code:'PASSENGER',approval_status:'APPROVED'}]}
  else if(path==='/users/me/auth-methods')body={password:true,google:false}
  else if(path==='/documents'){const n=Number(url.searchParams.get('page'));body={items:[{id:'doc-'+n,document_type:n===1?'NIC':'PASSPORT',status:'SUBMITTED'}],page:n,has_next:n===1}}
  else if(path==='/auth/logout')return route.fulfill({status:204})
  else body={enabled:false}
  await route.fulfill({json:body})
 })
 await page.goto('/login');await page.getByLabel('Email address',{exact:true}).fill('account@example.com');await page.getByLabel('Password',{exact:true}).fill('BrowserTravelly1!');await page.getByRole('button',{name:'Log in',exact:true}).click();await expect(page.locator('.passenger-dashboard h1')).toBeVisible()
 await visit(page,'/account');await expect(page.getByRole('heading',{name:'Account Passenger',exact:true})).toBeVisible();return reads
}
test('account navigation reflects the live session',async({page})=>{
 const reads=await setup(page)
 await expect(page.locator('.workspace-sidebar')).toHaveCount(0);await expect(page.getByRole('link',{name:'Log in',exact:true})).toHaveCount(0)
 await page.getByRole('link',{name:'Travelly home',exact:true}).click();await expect(page).toHaveURL(/\/$/);await expect(page.locator('.passenger-hero h1')).toBeVisible();await menu(page)
 await expect(page.getByRole('link',{name:'My Trips',exact:true})).toBeVisible();await expect(page.getByRole('link',{name:'Passenger dashboard',exact:true})).toHaveCount(0)
 await visit(page,'/login');await expect(page).toHaveURL(/\/dashboard$/)
 await visit(page,'/account');await expect(page.getByRole('heading',{name:'Account Passenger',exact:true})).toBeVisible();expect(reads.every(v=>v==='Bearer account-test-access')).toBe(true)
 await menu(page);await page.getByLabel('Your account menu',{exact:true}).click();await page.getByRole('navigation',{name:'Main navigation',exact:true}).getByRole('button',{name:'Sign out',exact:true}).click();await expect(page).toHaveURL(/\/login$/);await visit(page,'/account');await expect(page).toHaveURL(/\/login$/)
 await expect(page.getByRole('heading',{name:'Welcome back',exact:true})).toBeVisible();await page.getByRole('link',{name:'Travelly home',exact:true}).click();await expect(page).toHaveURL(/\/$/);await expect(page.locator('.passenger-hero h1')).toBeVisible();await menu(page);await expect(page.getByRole('link',{name:'Log in',exact:true})).toBeVisible();await expect(page.getByRole('link',{name:'Passenger dashboard',exact:true})).toHaveCount(0)
})
test('Passenger profile keeps Owner/Driver guidance contextual',async({page})=>{
 await setup(page);await expect(page.getByLabel('Whose name is on the vehicle registration?',{exact:false})).toHaveCount(0)
 await expect(page.getByRole('option',{name:'Driving licence',exact:true})).toHaveCount(0)
 await expect(page.getByRole('navigation',{name:'Document flows'})).toHaveCount(0)
 await visit(page,'/account?documents=owner');await expect(page.getByRole('heading',{name:'Owner application documents',exact:true})).toBeVisible()
 for(const value of ['SELF','INDIVIDUAL','COMPANY']){await page.getByLabel('Whose name is on the vehicle registration?',{exact:false}).selectOption(value);await expect(page.locator('.vehicle-registration-note')).toBeVisible()}
 await expect(page.getByRole('option',{name:'Driving licence',exact:true})).toHaveCount(0)
 await visit(page,'/account?documents=driver');await expect(page.getByRole('heading',{name:'Driver application documents',exact:true})).toBeVisible();await expect(page.getByLabel('Whose name is on the vehicle registration?',{exact:false})).toHaveCount(0);await expect(page.getByRole('option',{name:'Vehicle registration',exact:true})).toHaveCount(0)
 await page.getByLabel('Document type',{exact:false}).selectOption('DRIVING_LICENCE');await expect(page.getByLabel('Issuing country',{exact:false})).toHaveValue('LK')
 await visit(page,'/account');await expect(page.getByRole('heading',{name:'Your private documents',exact:true})).toBeVisible();await expect(page.getByRole('heading',{name:'NIC',exact:true})).toBeVisible()
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
})
test('document pagination uses a normal unavailable cursor',async({page})=>{
 await setup(page);const previous=page.getByRole('button',{name:'Previous',exact:true});await expect(previous).toBeDisabled();expect(await previous.evaluate(el=>getComputedStyle(el).cursor)).not.toBe('wait')
 await page.getByRole('button',{name:'Next',exact:true}).click();await expect(page.getByText('Page 2',{exact:true})).toBeVisible();await expect(page.getByRole('button',{name:'Next',exact:true})).toBeDisabled()
})

test('pagination retains results while loading and recovers without skipping a failed page',async({page})=>{
 await setup(page)
 let release,secondRequests=0,fail=true
 const gate=new Promise(resolve=>{release=resolve})
 await page.route('**/api/v1/documents?*',async route=>{
  if(new URL(route.request().url()).searchParams.get('page')!=='2')return route.fallback()
  secondRequests++;await gate
  if(fail)return route.fulfill({status:503,json:{message:'Documents temporarily unavailable.'}})
  return route.fallback()
 })
 const next=page.getByRole('button',{name:'Next',exact:true});await next.focus();await page.keyboard.press('Enter')
 await expect(page.getByText(/Loading your documents/)).toBeVisible();await expect(next).toBeDisabled();await expect(page.getByText('Page 1',{exact:true})).toBeVisible();await expect(page.getByRole('heading',{name:'NIC',exact:true})).toBeVisible()
 release();await expect(page.getByRole('alert')).toHaveText('Documents temporarily unavailable.');await expect(next).toBeEnabled();expect(secondRequests).toBe(1)
 fail=false;await next.click();await expect(page.getByText('Page 2',{exact:true})).toBeVisible();await expect(page.getByRole('heading',{name:'PASSPORT',exact:true})).toBeVisible();await expect(next).toBeDisabled()
 const previous=page.getByRole('button',{name:'Previous',exact:true});await previous.focus();await page.keyboard.press('Enter');await expect(page.getByText('Page 1',{exact:true})).toBeVisible();await expect(previous).toBeDisabled()
})
test('expired access token refresh preserves authenticated navigation',async({page})=>{
 const reads=await setup(page);let refreshes=0
 await page.route('**/api/v1/auth/refresh',route=>{refreshes++;return route.fulfill({json:{access_token:'renewed-access',refresh_token:'renewed-refresh',expires_in:900}})})
 await page.route('**/api/v1/users/me',route=>route.request().headers().authorization==='Bearer account-test-access'?route.fulfill({status:401,json:{message:'Expired access token.'}}):route.fallback())
 await page.getByRole('link',{name:'Back to booking home',exact:true}).click();await expect(page.locator('.passenger-hero h1')).toBeVisible();await expect.poll(()=>refreshes).toBe(1);await expect.poll(()=>reads.includes('Bearer renewed-access')).toBe(true)
 await visit(page,'/account');await expect(page.getByRole('heading',{name:'Account Passenger',exact:true})).toBeVisible();await expect(page.getByRole('link',{name:'Log in',exact:true})).toHaveCount(0)
})
test('full reload preserves the existing memory-only session policy',async({page})=>{
 await setup(page);await page.reload();await expect(page).toHaveURL(/\/login$/);await expect(page.getByRole('button',{name:'Log in',exact:true})).toBeVisible()
})
