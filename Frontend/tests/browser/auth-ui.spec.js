import {test,expect} from '@playwright/test'

for(const width of [1440,1024,768,390,320])test(`redesigned auth controls stay accessible at ${width}px`,async({page})=>{
 await page.setViewportSize({width,height:900});await page.emulateMedia({reducedMotion:'reduce'})
 const writes=[]
 await page.route('**/api/v1/**',route=>{
  const path=new URL(route.request().url()).pathname
  if(path.endsWith('/auth/register')){writes.push(route.request().postDataJSON());return route.fulfill({status:201,json:{status:'verification_required',verification_ticket:'v'.repeat(43),email_delivery:'captured'}})}
  return route.fulfill({status:503,json:{code:'GOOGLE_NOT_CONFIGURED',message:'Google sign-in is not configured yet.'}})
 })
 await page.goto('/register')
 await expect(page.getByRole('heading',{name:'Create your account',exact:true})).toBeVisible()
 const contrast=await page.locator('.auth-submit').evaluate(el=>{
  const lum=rgb=>rgb.map(c=>c/255).map(c=>c<=.04045?c/12.92:((c+.055)/1.055)**2.4).reduce((a,c,i)=>a+c*[.2126,.7152,.0722][i],0)
  const style=getComputedStyle(el),text=lum(style.color.match(/[\d.]+/g).slice(0,3).map(Number))
  return style.backgroundImage.match(/rgb\([^)]+\)/g).map(c=>{const bg=lum(c.match(/[\d.]+/g).map(Number));return (Math.max(text,bg)+.05)/(Math.min(text,bg)+.05)})
 })
 expect(Math.min(...contrast)).toBeGreaterThanOrEqual(4.5)
 await page.getByLabel('Full name',{exact:true}).fill('Visual Passenger')
 await page.getByLabel('Email address',{exact:true}).fill('visual@example.com')
 await page.getByRole('button',{name:'Country code:',exact:false}).click()
 await page.getByRole('combobox',{name:'Search country or calling code',exact:true}).fill('United Kingdom');await page.keyboard.press('Enter')
 await page.getByLabel('Mobile number',{exact:true}).fill('07400 123456')
 await page.getByLabel('Password',{exact:true}).fill('TravellyStrong1!')
 await page.getByLabel('Confirm password',{exact:true}).fill('DifferentPassword1!')
 await page.getByRole('checkbox').check()
 await page.getByRole('button',{name:'Create account',exact:true}).click()
 await expect(page.getByText('Your passwords do not match.',{exact:true})).toBeVisible();expect(writes).toHaveLength(0)
 await page.getByLabel('Confirm password',{exact:true}).fill('TravellyStrong1!')
 await page.getByRole('button',{name:'Show confirm password',exact:true}).click()
 await expect(page.getByLabel('Confirm password',{exact:true})).toHaveAttribute('type','text')
 await page.getByRole('button',{name:'Hide confirm password',exact:true}).click()
 await page.getByRole('button',{name:'Privacy Policy',exact:true}).click();await expect(page.getByRole('dialog')).toContainText('Privacy Policy');await page.keyboard.press('Escape')
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
 const outside=await page.locator('.auth-form-panel input,.auth-form-panel button').evaluateAll(els=>els.filter(e=>{const r=e.getBoundingClientRect();return r.width&&(r.left<0||r.right>innerWidth+1)}).length)
 expect(outside).toBe(0)
 await page.getByRole('button',{name:'Create account',exact:true}).click();await expect(page).toHaveURL(/\/check-email$/)
 expect(writes[0].phone_e164).toBe('+447400123456');expect(writes[0]).not.toHaveProperty('confirm_password')
})

test('login retains password visibility, remembered identifier guidance and recovery links',async({page})=>{
 await page.route('**/api/v1/**',r=>r.fulfill({status:503,json:{code:'GOOGLE_NOT_CONFIGURED',message:'Google sign-in is not configured yet.'}}));await page.goto('/login')
 await page.getByRole('checkbox',{name:'Remember me',exact:true}).check();await expect(page.getByText('Remember your email on this device. Your password and session are never saved.',{exact:true})).toBeVisible()
 await page.getByLabel('Password',{exact:true}).fill('TravellyStrong1!');await page.getByRole('button',{name:'Show password',exact:true}).click();await expect(page.getByLabel('Password',{exact:true})).toHaveAttribute('type','text')
 await page.getByRole('link',{name:'Forgot password?',exact:true}).click();await expect(page).toHaveURL(/\/forgot-password$/)
})

test('login submits the current API contract and enters Passenger dashboard',async({page})=>{
 const requests=[]
 await page.route('**/api/v1/**',async route=>{
  const path=new URL(route.request().url()).pathname
  if(path.endsWith('/auth/login')){
   requests.push(route.request().postDataJSON())
   return route.fulfill({json:{access_token:'login-test-access',refresh_token:'login-test-refresh',expires_in:900}})
  }
  if(path.endsWith('/users/me'))return route.fulfill({json:{id:'12222222-2222-4222-8222-222222222222',full_name:'Login Passenger',account_status:'ACTIVE',email:'passenger@example.com',phone_e164:'+94771234567',approved_roles:['PASSENGER'],email_verified_at:'2026-11-05T00:00:00Z'}})
  if(path.endsWith('/users/me/roles'))return route.fulfill({json:{items:[{role_code:'PASSENGER',approval_status:'APPROVED'}]}})
  return route.fulfill({json:{items:[]}})
 })
 await page.goto('/login')
 await page.getByLabel('Email address',{exact:true}).fill(' Passenger@Example.com ')
 await page.getByLabel('Password',{exact:true}).fill('ExistingPassword1!')
 await page.getByRole('button',{name:'Log in',exact:true}).click()
 await expect(page).toHaveURL(/\/dashboard$/)
 expect(requests).toEqual([{identifier:' Passenger@Example.com ',password:'ExistingPassword1!'}])
})
