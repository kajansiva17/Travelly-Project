import {test,expect} from '@playwright/test'

for(const role of ['OWNER','DRIVER'])for(const status of ['APPROVED','PENDING','CORRECTION'])test(`${role} ${status} follows authoritative state after verification`,async({page})=>{
 const uid='12222222-2222-4222-8222-222222222222',name=role==='OWNER'?'Owner':'Driver'
 await page.route('**/api/v1/**',async route=>{
  const path=new URL(route.request().url()).pathname;let result={items:[]}
  if(path.endsWith('/auth/email/verify'))result={status:'verified',journey:role,verified_user_id:uid,access_token:'access',refresh_token:'refresh'}
  else if(path.endsWith('/users/me/roles'))result={items:[{role_code:'PASSENGER',approval_status:'APPROVED'},{role_code:role,approval_status:status==='CORRECTION'?'PENDING':status}]}
  else if(path.endsWith('/users/me'))result={id:uid,full_name:'Test Applicant',account_status:'ACTIVE',email_verified_at:'2026-11-05T00:00:00Z',approved_roles:status==='APPROVED'?['PASSENGER',role]:['PASSENGER']}
  else if(path.endsWith('/documents'))result={items:[{id:'identity',document_type:'NIC',status:'APPROVED'},{id:'evidence',document_type:role==='OWNER'?'VEHICLE_REGISTRATION':'DRIVING_LICENCE',status:status==='CORRECTION'?'NEEDS_CORRECTION':'APPROVED',rejection_reason:'A clearer document is required.'}],has_next:false}
  return route.fulfill({json:result})
 })
 await page.goto('/verify-email?journey='+ (role==='OWNER'?'driver':'owner')+'#token='+ 'a'.repeat(43))
 await page.getByRole('button',{name:'Verify email'}).click()
 await expect(page).toHaveURL(new RegExp('/'+role.toLowerCase()+'/'+(status==='APPROVED'?'dashboard':'onboarding')+'$'))
 if(status!=='APPROVED')await expect(page.getByRole('heading',{name:`${name} application submitted — waiting for Admin approval`})).toBeVisible()
 if(status==='CORRECTION')await expect(page.getByRole('button',{name:'Correct requested evidence'})).toBeVisible()
 await expect(page.getByRole('button',{name:`Submit ${name} application`})).toHaveCount(0)
})

test('verification does not replace a different signed-in account',async({page})=>{
 const uid='12222222-2222-4222-8222-222222222222',profileTokens=[]
 await page.route('**/api/v1/**',async route=>{
  const path=new URL(route.request().url()).pathname;let result={items:[]}
  if(path.endsWith('/auth/login'))result={access_token:'existing',refresh_token:'existing-refresh'}
  else if(path.endsWith('/auth/email/verify'))result={status:'verified',journey:'OWNER',verified_user_id:'different-user',access_token:'new',refresh_token:'new-refresh'}
  else if(path.endsWith('/users/me/roles'))result={items:[{role_code:'PASSENGER',approval_status:'APPROVED'}]}
  else if(path.endsWith('/users/me')){profileTokens.push(route.request().headers().authorization);result={id:uid,full_name:'Existing Passenger',account_status:'ACTIVE',approved_roles:['PASSENGER']}}
  else if(path.endsWith('/auth/google/challenge'))return route.fulfill({status:503,json:{code:'GOOGLE_NOT_CONFIGURED',message:'Not configured'}})
  return route.fulfill({json:result})
 })
 await page.goto('/login');await page.getByLabel('Email address',{exact:true}).fill('existing@example.com');await page.getByLabel('Password',{exact:true}).fill('ExistingPassword1!');await page.getByRole('button',{name:'Log in',exact:true}).click();await expect(page).toHaveURL(/\/dashboard$/)
 await page.evaluate(()=>{history.pushState({},'','/verify-email#token='+ 'a'.repeat(43));dispatchEvent(new PopStateEvent('popstate'))})
 await page.getByRole('button',{name:'Verify email'}).click();await expect(page.getByText('Email verified. You are signed in to another account; sign out before continuing with this account.')).toBeVisible()
 await expect(page).toHaveURL(/\/verify-email$/)
 await page.getByRole('link',{name:'Sign in or request another verification link'}).click();await expect(page).toHaveURL(/\/dashboard$/)
 expect(profileTokens.length).toBeGreaterThan(0);expect(profileTokens.every(value=>value==='Bearer existing')).toBe(true)
})
