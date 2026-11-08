import {test,expect} from '@playwright/test'
import {setup,visit} from './helpers/redesign.js'

test('the seven redesigned pages use production artwork and responsive real controls',async({page},info)=>{
 test.setTimeout(90000)
 const errors=[];page.on('pageerror',e=>errors.push(e.message))
 await page.emulateMedia({reducedMotion:'reduce'})
 await page.setViewportSize({width:info.project.name==='desktop'?1440:390,height:1000})
 await page.route('**/api/v1/**',route=>route.fulfill({status:503,json:{code:'GOOGLE_NOT_CONFIGURED',message:'Google sign-in is not configured yet.'}}))
 for(const [path,name] of [['/','landing'],['/login','login'],['/register','register']]){
  await page.goto(path);await page.evaluate(()=>document.fonts.ready)
  await expect(page.locator('main h1')).toBeVisible()
  if(path==='/')await expect(page.locator('.passenger-hero .hero-copy')).toHaveCSS('background-color','rgba(0, 0, 0, 0)')
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
  const production=page.locator('img[src*="/images/travelly/"]')
  expect(await production.count()).toBeGreaterThan(0)
  await production.evaluateAll(images=>images.forEach(i=>i.loading='eager'))
  await expect.poll(()=>production.evaluateAll(images=>images.filter(i=>!i.complete||!i.naturalWidth).length)).toBe(0)
  await production.evaluateAll(images=>Promise.all(images.map(i=>i.decode())))
  expect(await page.locator('img[src*="references/"]').count()).toBe(0)
  await page.locator('main h1').click()
  await page.screenshot({path:info.outputPath(name+'.png'),fullPage:true})
 }
 await page.unroute('**/api/v1/**');await setup(page)
 await expect(page.locator('.passenger-dashboard h1')).toHaveText('Where will you go next, Kasun?')
 await expect(page.locator('.workspace-sidebar')).toHaveCount(0)
 await expect(page.locator('.passenger-customer-shell>.site-header')).toBeVisible()
 await page.locator('img').evaluateAll(images=>images.forEach(i=>i.loading='eager'))
 await expect.poll(()=>page.locator('img').evaluateAll(images=>images.filter(i=>!i.complete||!i.naturalWidth).length)).toBe(0)
 await page.locator('img').evaluateAll(images=>Promise.all(images.map(i=>i.decode())))
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
 await page.screenshot({path:info.outputPath('passenger.png'),fullPage:true})
 for(const [path,name,title] of [['/owner/dashboard','owner','Grow every journey, Kasun.'],['/driver/dashboard','driver','Ready for the road, Kasun?'],['/admin/dashboard','admin',/Good (morning|afternoon|evening), Kasun/]]){
  await visit(page,path);await expect(page.locator('.workspace-content main h1')).toHaveText(title)
  await expect(page.locator('.workspace-loading')).toHaveCount(0)
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
  if(name==='admin'){await expect(page.locator('.admin-profile-link')).toHaveAttribute('href','/account?workspace=admin');await expect(page.locator('.dashboard-profile-dropdown')).toHaveCount(0)}
  else {await page.locator('.workspace-profile summary').click();await expect(page.locator('.dashboard-profile-dropdown').getByRole('link')).toHaveCount(2)}
  await expect(page.getByText('Switch workspace',{exact:true})).toHaveCount(0)
  await page.keyboard.press('Escape')
  await expect(page.locator('.workspace-sidebar-main').first()).toHaveCSS('overflow-y','visible')
  await page.locator('img').evaluateAll(images=>images.forEach(i=>i.loading='eager'))
  await expect.poll(()=>page.locator('img').evaluateAll(images=>images.filter(i=>!i.complete||!i.naturalWidth).length)).toBe(0)
  await page.locator('main h1').click()
  await page.screenshot({path:info.outputPath(name+'.png'),fullPage:true})
 }
 expect(errors).toEqual([])
})

test('landing search transfers real itinerary seeds and unsupported services are explicit',async({page})=>{
 await page.route('**/api/v1/**',route=>route.fulfill({json:{items:[]}}));await page.goto('/')
 await page.getByLabel('Pickup location',{exact:true}).fill('Colombo')
 await page.getByLabel('Destination',{exact:true}).fill('Kandy')
 await page.getByLabel('Travel date',{exact:true}).fill('2027-01-10T09:30')
 await page.getByRole('button',{name:'Find a ride',exact:true}).click()
 await expect(page).toHaveURL(/\/hire$/)
 await expect(page.getByLabel('Pickup date and time (Required)',{exact:true})).toHaveValue('2027-01-10T09:30')
 await expect(page.getByRole('searchbox',{name:/^Pickup/})).toHaveValue('Colombo')
 await page.goto('/');await page.getByRole('tab',{name:'Book tickets',exact:true}).click()
 await page.getByLabel('From',{exact:true}).fill('Colombo');await page.getByLabel('Destination',{exact:true}).fill('Kandy');await page.getByLabel('Travel date',{exact:true}).fill('2027-01-10T09:30')
 await page.getByRole('button',{name:'Find tickets',exact:true}).click()
 await expect(page.getByRole('dialog')).toContainText('not available yet')
})
