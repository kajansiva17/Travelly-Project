import {test,expect} from '@playwright/test'
import {setup,visit} from './helpers/redesign.js'

async function prepare(page){
 const state=await setup(page)
 let user={id:'12222222-2222-4222-8222-222222222222',full_name:'Sample Admin',email:'admin@example.com',phone_e164:'+94771234567',profile_image_url:null,version:1,account_status:'ACTIVE',email_verified_at:'2026-10-27T00:00:00Z',approved_roles:['PASSENGER','ADMIN']}
 const updates=[]
 await page.route('**/api/v1/users/me',route=>{
  if(route.request().method()==='PATCH'){
   const body=route.request().postDataJSON();updates.push(body);user={...user,...body,version:user.version+1}
  }
  return route.fulfill({json:user})
 })
 await visit(page,'/admin/dashboard')
 await expect(page.getByRole('link',{name:'Sample Admin, Super Admin profile',exact:true})).toBeVisible()
 return {state,updates}
}

async function sidebar(page){
 const trigger=page.getByRole('button',{name:'Open workspace navigation',exact:true})
 if(await trigger.isVisible())await trigger.click()
 return page.getByRole('navigation',{name:'Super Admin sidebar',exact:true}).filter({visible:true})
}

test('Admin navbar and sidebar share one clean profile and keep Settings and Logout',async({page})=>{
 const {state}=await prepare(page)
 await expect(page.locator('.workspace-profile summary,.dashboard-profile-dropdown')).toHaveCount(0)
 await page.getByRole('link',{name:'Sample Admin, Super Admin profile',exact:true}).click()
 await expect(page).toHaveURL(/\/account\?workspace=admin$/)
 await expect(page.getByRole('heading',{name:'Profile',exact:true})).toBeVisible()
 await expect(page.locator('.site-header')).toHaveCount(1)
 for(const text of ['Sign-in and email verification','Your private documents','View all retained documents','Admin dashboard','Back to Admin dashboard','Sign out'])await expect(page.locator('main').getByText(text,{exact:true})).toHaveCount(0)
 await expect(page.getByLabel('Current password',{exact:true})).toHaveCount(0)
 await expect(page.getByRole('checkbox')).toHaveCount(0)
 await expect(page.getByRole('button',{name:'Save Changes',exact:true})).toBeDisabled()
 let nav=await sidebar(page);await nav.getByRole('link',{name:'Settings',exact:true}).click()
 await expect(page).toHaveURL(/\/admin\/settings$/)
 await expect(page.getByRole('heading',{name:'Sign-in and email verification',exact:true})).toBeVisible()
 nav=await sidebar(page);await nav.getByRole('link',{name:'Profile',exact:true}).click()
 await expect(page).toHaveURL(/\/account\?workspace=admin$/)
 await expect(page.getByRole('heading',{name:'Profile',exact:true})).toBeVisible()
 nav=await sidebar(page);await nav.getByRole('link',{name:'Dashboard',exact:true}).click()
 await expect(page).toHaveURL(/\/admin\/dashboard$/)
 nav=await sidebar(page);await nav.getByRole('button',{name:'Logout',exact:true}).click()
 await expect(page).toHaveURL(/\/login$/);expect(state.logout).toBe(1)
})

test('Admin can save personal details, cancel edits, change and remove a photo',async({page})=>{
 const {updates}=await prepare(page)
 await page.getByRole('link',{name:'Sample Admin, Super Admin profile',exact:true}).click()
 await expect(page.getByLabel('Full name',{exact:true})).toHaveAttribute('readonly','')
 await page.getByRole('button',{name:'Edit full name',exact:true}).click()
 await page.getByLabel('Full name',{exact:true}).fill('Discarded name')
 await page.getByRole('button',{name:'Cancel',exact:true}).click()
 await expect(page.getByLabel('Full name',{exact:true})).toHaveValue('Sample Admin');expect(updates).toHaveLength(0)
 await page.getByRole('button',{name:'Edit full name',exact:true}).click()
 await page.getByLabel('Full name',{exact:true}).fill('Updated Admin')
 await page.getByRole('button',{name:'Edit mobile number',exact:true}).click()
 await page.getByLabel('Mobile number',{exact:true}).fill('+94771234568')
 const image=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aK1cAAAAASUVORK5CYII=','base64')
 await page.getByLabel('Upload profile picture',{exact:true}).setInputFiles({name:'avatar.png',mimeType:'image/png',buffer:image})
 await expect(page.getByRole('button',{name:'Change photo',exact:true})).toBeVisible()
 await page.getByRole('button',{name:'Save Changes',exact:true}).click()
 await expect(page.getByRole('status')).toHaveText('Your profile has been updated.')
 expect(updates[0]).toMatchObject({full_name:'Updated Admin',phone_e164:'+94771234568',version:1})
 expect(Object.keys(updates[0]).sort()).toEqual(['full_name','phone_e164','profile_image_url','version'])
 await expect(page.getByRole('link',{name:'Updated Admin, Super Admin profile',exact:true})).toBeVisible()
 await expect(page.locator('.admin-profile-link img')).toHaveCount(1)
 await page.getByRole('button',{name:'Remove photo',exact:true}).click()
 await page.getByRole('button',{name:'Cancel',exact:true}).click()
 await expect(page.getByRole('img',{name:'Your profile',exact:true})).toBeVisible()
 await page.getByRole('button',{name:'Remove photo',exact:true}).click()
 await page.getByRole('button',{name:'Save Changes',exact:true}).click()
 await expect(page.getByRole('status')).toHaveText('Your profile has been updated.')
 expect(updates[1].profile_image_url).toBeNull()
 await visit(page,'/admin/dashboard');await page.getByRole('link',{name:'Updated Admin, Super Admin profile',exact:true}).click()
 await expect(page.getByLabel('Full name',{exact:true})).toHaveValue('Updated Admin')
})

test('profile save errors retain edits and allow correction',async({page})=>{
 await prepare(page);await visit(page,'/account?workspace=admin')
 await page.getByRole('button',{name:'Edit full name',exact:true}).click()
 await page.getByLabel('Full name',{exact:true}).fill('Keep my edit')
 await page.route('**/api/v1/users/me',route=>route.request().method()==='PATCH'?route.fulfill({status:409,json:{code:'PROFILE_CHANGED',message:'Your profile changed. Reload your profile before saving again.'}}):route.fallback())
 await page.getByRole('button',{name:'Save Changes',exact:true}).click()
 await expect(page.getByRole('alert')).toContainText('Your profile changed.')
 await expect(page.getByLabel('Full name',{exact:true})).toHaveValue('Keep my edit')
 await expect(page.getByRole('button',{name:'Save Changes',exact:true})).toBeEnabled()
})

test('profile fits desktop tablet and mobile at normal browser zoom',async({page},info)=>{
 await prepare(page)
 await page.emulateMedia({reducedMotion:'reduce'})
 for(const [width,height] of [[1920,1080],[1366,768],[768,1024],[390,844],[320,640]]){
  await page.setViewportSize({width,height});await visit(page,'/account?workspace=admin')
  await expect(page.getByRole('heading',{name:'Profile',exact:true})).toBeVisible()
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
  await expect(page.locator('.admin-profile-link .workspace-profile-name')).toBeVisible()
  await page.getByRole('button',{name:'Save Changes',exact:true}).scrollIntoViewIfNeeded()
  const controls=await page.locator('.admin-profile-card').evaluate(card=>[...card.querySelectorAll('input:not([hidden]),button')].map(el=>{const r=el.getBoundingClientRect();return {left:r.left,right:r.right}}))
  expect(controls.every(r=>r.left>=0&&r.right<=width)).toBe(true)
  await page.screenshot({path:info.outputPath(`admin-profile-${width}.png`),fullPage:true})
 }
})
