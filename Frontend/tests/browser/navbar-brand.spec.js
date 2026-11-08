import {test,expect} from '@playwright/test'
test.setTimeout(90000)

const uid='12222222-2222-4222-8222-222222222222'
const roles=['PASSENGER','OWNER','DRIVER','ADMIN']
async function visit(page,path){await page.evaluate(path=>new Promise(resolve=>{history.pushState({},'',path);dispatchEvent(new PopStateEvent('popstate'));requestAnimationFrame(()=>requestAnimationFrame(resolve))}),path)}
async function setup(page){
 let logout=0
 await page.route('**/api/v1/**',async route=>{
  const path=new URL(route.request().url()).pathname
  let body={items:[]}
  if(path.endsWith('/auth/login'))body={access_token:'navbar-test-access',refresh_token:'navbar-test-refresh',expires_in:900}
  else if(path.endsWith('/auth/logout')){logout++;return route.fulfill({status:204})}
  else if(path.endsWith('/users/me'))body={id:uid,full_name:'Alexandra Travelly Passenger',account_status:'ACTIVE',approved_roles:roles,email:'navbar@example.com',email_verified_at:'2026-10-27T00:00:00Z'}
  else if(path.endsWith('/users/me/roles'))body={items:roles.map(role_code=>({role_code,approval_status:'APPROVED'}))}
  else if(path.endsWith('/auth/config'))body={google_enabled:false}
  return route.fulfill({json:body})
 })
 return ()=>logout
}
async function assertBrand(page){
 const brand=page.getByRole('link',{name:'Travelly home',exact:true}),logo=brand.locator('.brand-wordmark-art')
 await expect(logo).toBeVisible();await expect(logo).toHaveJSProperty('complete',true);await logo.evaluate(i=>i.decode())
 expect(await logo.evaluate(e=>e.naturalWidth)).toBeGreaterThan(0)
 const within=await logo.evaluate(el=>{const r=el.getBoundingClientRect(),h=el.closest('header').getBoundingClientRect();return r.top>=h.top-.5&&r.bottom<=h.bottom+.5&&Math.abs((r.width/r.height)/(Number(el.getAttribute('width'))/Number(el.getAttribute('height')))-1)<.015})
 await expect(brand.locator('.brand-speedometer-dial')).toHaveAttribute('src','/images/travelly/branding/nav-speedometer-dial.png')
 await expect(brand.locator('.brand-gauge-needle')).toHaveAttribute('src','/images/travelly/branding/nav-speedometer-needle.png')
 await expect(brand.locator('.brand-speedometer-dial')).toHaveCount(1)
 await expect(brand.locator('.brand-gauge-needle')).toHaveCount(1)
 expect(await logo.evaluate(el=>getComputedStyle(el).clipPath)).toContain('32%')
 expect(within).toBe(true);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
}

for(const width of [1920,1440,1024,768,390,360,320])test(`shared navbar brand and existing navigation at ${width}px`,async({page},info)=>{
 await page.setViewportSize({width,height:900});await page.emulateMedia({reducedMotion:'reduce'})
 const logouts=await setup(page)
 // Public Passenger, Owner and Driver landing variants, and authentication.
 for(const path of ['/','/for-owners','/drive-with-us','/login']){
  await page.goto(path);await assertBrand(page)
  await page.locator('.site-header').screenshot({path:info.outputPath(path==='/'?'public.png':path.slice(1)+'.png')})
 }
 await page.getByLabel('Email address',{exact:true}).fill('navbar@example.com');await page.getByLabel('Password',{exact:true}).fill('BrowserTravelly1!');await page.getByRole('button',{name:'Log in',exact:true}).click()
 await expect(page.locator('.passenger-dashboard h1')).toBeVisible()
 await assertBrand(page)
 await page.locator('.site-header').screenshot({path:info.outputPath('passenger.png')})
 const toggle=page.getByRole('button',{name:'Open navigation',exact:true});if(await toggle.isVisible())await toggle.click()
 const nav=page.getByRole('navigation',{name:'Main navigation'})
 await expect(nav.getByRole('link',{name:'My Trips',exact:true})).toHaveAttribute('href','/bookings')
 await expect(nav.getByRole('link',{name:'Passenger dashboard',exact:true})).toHaveCount(0)
 await visit(page,'/driver/dashboard');await expect(page.getByRole('heading',{name:'Ready for the road, Alexandra?',exact:true})).toBeVisible();await assertBrand(page)
 const summary=page.locator('.workspace-profile summary');await summary.focus();await page.keyboard.press('Enter');await expect(page.locator('.dashboard-profile-dropdown').getByRole('link')).toHaveCount(2);await page.keyboard.press('Escape');await expect(summary).toBeFocused()
 for(const path of ['/owner/vehicles','/owner/rates','/admin/applications','/admin/vehicles','/account']){await visit(page,path);await assertBrand(page);await page.locator('.site-header').screenshot({path:info.outputPath(path.slice(1).replaceAll('/','-')+'.png')})}
 await visit(page,'/');await expect(page.locator('.passenger-hero h1')).toBeVisible();const menuToggle=page.getByRole('button',{name:'Open navigation',exact:true});if(await menuToggle.isVisible())await menuToggle.click();await page.getByLabel('Your account menu',{exact:true}).click();await page.getByRole('navigation',{name:'Main navigation'}).getByRole('button',{name:'Sign out',exact:true}).click();await expect(page).toHaveURL(/\/login$/);expect(logouts()).toBe(1)
})
