import {test,expect} from '@playwright/test'
import {visit} from './helpers/redesign.js'

async function fixture(page,roles={}){
 const state={roles,requirements:[{label:'Identity document (NIC or Passport)',ready:false,message:'NIC: UNDER_REVIEW. The issue date is in the future. Ask Super Admin to request a correction.'}],reason:'Please provide a readable licence.',fail:false,writes:[]}
 await page.route('**/api/v1/**',route=>{
  const request=route.request(),path=new URL(request.url()).pathname.replace('/api/v1','')
  if(request.method()!=='GET')state.writes.push(path)
  if(state.fail&&path==='/users/me')return route.fulfill({status:503,json:{code:'AUTH_DEPENDENCY_UNAVAILABLE',message:'Access cannot be checked.'}})
  if(state.failStatus&&path.endsWith('/status'))return route.fulfill({status:503,json:{code:'AUTH_DEPENDENCY_UNAVAILABLE',message:'Application status could not be checked.'}})
  let result={items:[]}
  if(path==='/auth/login')result={access_token:'approval-test',refresh_token:'approval-refresh'}
  if(path==='/users/me')result={id:'12222222-2222-4222-8222-222222222222',full_name:'Role Applicant',email:'applicant@example.com',account_status:'ACTIVE',email_verified_at:'2026-11-01T00:00:00Z',approved_roles:['PASSENGER',...Object.keys(state.roles).filter(role=>state.roles[role]==='APPROVED')]}
  if(path==='/users/me/roles')result={items:[{role_code:'PASSENGER',approval_status:'APPROVED'},...Object.entries(state.roles).map(([role_code,approval_status])=>({role_code,approval_status,rejection_reason:approval_status==='REJECTED'?state.reason:null}))]}
  if(/^\/users\/me\/role-requests\/(OWNER|DRIVER)\/status$/.test(path)){const role=path.split('/')[4];result={application:{role_code:role,approval_status:state.roles[role]},approval_readiness:{ready:state.requirements.every(item=>item.ready),requirements:state.requirements},checked_at:new Date().toISOString()}}
  if(path==='/documents')result={items:[{id:'identity',document_type:'NIC',status:'SUBMITTED'},{id:'licence',document_type:'DRIVING_LICENCE',status:'SUBMITTED',issuing_country:'LK',expiry_date:'2030-12-31'}],has_next:false}
  if(path==='/auth/google/challenge')return route.fulfill({status:503,json:{code:'GOOGLE_NOT_CONFIGURED',message:'Not configured'}})
  return route.fulfill({json:result})
 })
 return state
}
async function login(page,query=''){
 await page.goto('/login'+query)
 await page.getByLabel('Email address',{exact:true}).fill('applicant@example.com')
 await page.getByLabel('Password',{exact:true}).fill('ExistingPassword1!')
 await page.getByRole('button',{name:'Log in',exact:true}).click()
}

for(const [roles,query,destination] of [
 [{OWNER:'APPROVED'},'','/owner/dashboard'],
 [{DRIVER:'APPROVED'},'','/driver/dashboard'],
 [{OWNER:'APPROVED',DRIVER:'APPROVED'},'','/owner/dashboard'],
 [{OWNER:'APPROVED',DRIVER:'APPROVED'},'?journey=driver','/driver/dashboard'],
 [{DRIVER:'PENDING'},'?journey=driver','/driver/onboarding'],
 [{OWNER:'REJECTED'},'?journey=owner','/owner/onboarding'],
])test(`login routes ${JSON.stringify(roles)} ${query} to ${destination}`,async({page})=>{
 const state=await fixture(page,roles);await login(page,query)
 await expect(page).toHaveURL(new RegExp(destination+'$'))
 if(destination.endsWith('/dashboard'))await expect(page.locator('.overview-banner h1')).toBeVisible()
 expect(state.writes.filter(path=>path==='/users/me/role-requests'||path==='/documents')).toEqual([])
 await expect(page.getByRole('heading',{name:'Sign-in and email verification',exact:true})).toHaveCount(0)
})

test('waiting applicant observes approval in existing session without reapplying',async({page})=>{
 const state=await fixture(page,{DRIVER:'PENDING'});await login(page,'?journey=driver')
 await expect(page.getByRole('heading',{name:'Driver application submitted — waiting for Admin approval',exact:true})).toBeVisible()
 state.roles.DRIVER='APPROVED';await page.getByRole('button',{name:'Refresh application status'}).click()
 await expect(page).toHaveURL(/\/driver\/dashboard$/)
 await expect(page.locator('.overview-banner h1')).toBeVisible()
 expect(state.writes.filter(path=>path==='/users/me/role-requests')).toEqual([])
})

test('rejection reason is visible on waiting journey and Passenger status',async({page})=>{
 const state=await fixture(page,{DRIVER:'PENDING'});await login(page,'?journey=driver')
 await expect(page.getByRole('button',{name:'Refresh application status'})).toBeVisible()
 state.roles.DRIVER='REJECTED';await page.getByRole('button',{name:'Refresh application status'}).click()
 await expect(page.getByRole('status').filter({hasText:'Application rejected:'})).toContainText(state.reason)
 await visit(page,'/dashboard')
 await expect(page.locator('.application-status-notice')).toContainText(state.reason)
 await expect(page.locator('.application-status-notice').getByRole('link',{name:'View application'})).toHaveAttribute('href','/driver/onboarding')
})

test('focus refresh updates roles without displacing the current page and denies failed access checks',async({page})=>{
 const state=await fixture(page);await login(page)
 await expect(page.locator('.passenger-dashboard h1')).toBeVisible()
 state.roles.OWNER='APPROVED';await page.evaluate(()=>window.dispatchEvent(new Event('focus')))
 await expect(page.locator('.application-status-notice').getByRole('link',{name:'Open dashboard'})).toHaveAttribute('href','/owner/dashboard')
 await expect(page).toHaveURL(/\/dashboard$/)
 state.fail=true;await page.evaluate(()=>window.dispatchEvent(new Event('focus')))
 await expect(page.getByRole('heading',{name:'Account unavailable',exact:true})).toBeVisible()
 await expect(page.locator('.application-status-notice')).toHaveCount(0)
})

test('an approved Owner also sees the reason for a rejected Driver application',async({page})=>{
 const state=await fixture(page,{OWNER:'APPROVED',DRIVER:'REJECTED'});await login(page)
 await expect(page).toHaveURL(/\/owner\/dashboard$/)
 await expect(page.locator('.application-status-notice')).toContainText(state.reason)
 await expect(page.locator('.application-status-notice').getByRole('link',{name:'View application'})).toHaveAttribute('href','/driver/onboarding')
})

test('Admin sees the relevant document checklist with no account linking forms',async({page})=>{
 await fixture(page,{ADMIN:'APPROVED'})
 let ready=false
 await page.route('**/api/v1/admin/role-requests/application',route=>route.fulfill({json:{application:{id:'application',role_code:'DRIVER',approval_status:'PENDING',version:1},applicant:{full_name:'Role Applicant',email:'applicant@example.com'},documents:[],approval_readiness:{ready,requirements:[{label:'Identity document (NIC or Passport)',ready,message:ready?'Reviewed and approved.':'Review the submitted document below; it must be approved, current and valid for this application.'}]}}}))
 await login(page);await expect(page).toHaveURL(/\/admin\/dashboard$/)
 await visit(page,'/admin/applications/application')
 await expect(page.getByRole('region',{name:'Application review checklist'})).toBeVisible()
 await expect(page.getByRole('button',{name:'Approve Driver',exact:true})).toBeDisabled()
 await expect(page.getByRole('button',{name:'Reject Driver',exact:true})).toBeEnabled()
 await expect(page.getByLabel('Current password',{exact:true})).toHaveCount(0)
 ready=true;await visit(page,'/admin/dashboard');await visit(page,'/admin/applications/application')
 await expect(page.getByRole('button',{name:'Approve Driver',exact:true})).toBeEnabled()
})


test('pending Owner refresh shows exact saved blockers and distinguishes verified documents from role approval',async({page})=>{
 const state=await fixture(page,{OWNER:'PENDING'});await login(page,'?journey=owner')
 await expect(page.getByRole('region',{name:'Pending approval requirements'})).toContainText('issue date is in the future')
 state.requirements=[{label:'Identity document (NIC or Passport)',ready:true,message:'Required evidence has been verified. The final role decision is still awaiting Super Admin approval.'}]
 await page.getByRole('button',{name:'Refresh application status'}).click()
 await expect(page.getByRole('heading',{name:'Documents verified ? final role approval pending',exact:true})).toBeVisible()
 await expect(page).toHaveURL(/\/owner\/onboarding$/)
 state.roles.OWNER='APPROVED';await page.getByRole('button',{name:'Refresh application status'}).click()
 await expect(page).toHaveURL(/\/owner\/dashboard$/)
 expect(state.writes.filter(path=>path==='/users/me/role-requests')).toEqual([])
})


test('failed status refresh clears stale access until a successful authenticated retry',async({page})=>{
 const state=await fixture(page,{OWNER:'PENDING'});await login(page,'?journey=owner')
 await expect(page.getByRole('region',{name:'Pending approval requirements'})).toBeVisible()
 state.failStatus=true;state.roles.OWNER='APPROVED'
 await page.getByRole('button',{name:'Refresh application status'}).click()
 await expect(page.getByRole('alert')).toContainText('Application status could not be checked.')
 await expect(page.getByRole('region',{name:'Pending approval requirements'})).toHaveCount(0)
 await expect(page).toHaveURL(/\/owner\/onboarding$/)
 state.failStatus=false;await page.getByRole('button',{name:'Try again',exact:true}).click()
 await expect(page).toHaveURL(/\/owner\/dashboard$/)
})
