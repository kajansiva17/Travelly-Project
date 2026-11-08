import {test,expect} from '@playwright/test'
import {setup,visit} from './helpers/redesign.js'
import {accountPath} from '../../src/routes/workspaceRoutes.js'

test.setTimeout(60000)

test('Owner profile retains one header, matching evidence and dashboard return',async({page},info)=>{
 await setup(page);await visit(page,accountPath('OWNER'));await expect(page.getByRole('heading',{name:'Hello, Kasun.',exact:true})).toBeVisible()
 await page.screenshot({path:info.outputPath('owner-profile.png'),fullPage:true})
 await expect(page.locator('.site-header')).toHaveCount(1)
 await expect(page.getByRole('heading',{name:'Owner application documents',exact:true})).toBeVisible()
 await expect(page.getByRole('navigation',{name:'Document flows'})).toHaveCount(0)
 await page.getByRole('link',{name:'Back to Owner dashboard',exact:true}).click();await expect(page).toHaveURL(/\/owner\/dashboard$/)
})
test('general profile does not present both application flows',async({page},info)=>{
 await setup(page);await visit(page,'/account');await expect(page.getByRole('heading',{name:'Your private documents',exact:true})).toBeVisible();await page.screenshot({path:info.outputPath('general-profile.png'),fullPage:true})
 await expect(page.getByRole('navigation',{name:'Document flows'})).toHaveCount(0)
 await expect(page.getByRole('option',{name:'Vehicle registration',exact:true})).toHaveCount(0);await expect(page.getByRole('option',{name:'Driving licence',exact:true})).toHaveCount(0)
})
test('anonymous Admin entry returns to existing guarded Admin dashboard after login',async({page})=>{
 const visits=[];page.on('framenavigated',f=>{if(f===page.mainFrame())visits.push(new URL(f.url()).pathname)})
 await setup(page,{entry:'/admin/dashboard',destination:'/admin/dashboard'});await expect(page.locator('.overview-banner h1')).toBeVisible();expect(visits).not.toContain('/dashboard');expect(visits).not.toContain('/account')
})

for(const role of ['OWNER','DRIVER'])test(`${role} menu, settings and profile keep originating shell and evidence`,async({page},info)=>{
 await setup(page)
 await page.route('**/api/v1/documents?*',r=>r.fulfill({json:{items:[{id:'identity',document_type:'NIC',status:'APPROVED'},{id:'owner-doc',document_type:'OWNER_AUTHORISATION',status:'NEEDS_CORRECTION',rejection_reason:'Owner correction required.'},{id:'driver-doc',document_type:'DRIVING_LICENCE',status:'REJECTED',rejection_reason:'Licence correction required.'}],page:1,has_next:false}}))
 const lower=role.toLowerCase(),name=role==='OWNER'?'Owner':role==='DRIVER'?'Driver':'Admin',heading=role==='ADMIN'?'Your private documents':name+' application documents'
 await visit(page,`/${lower}/dashboard`);await expect(page.locator('.overview-banner h1')).toBeVisible();await expect(page.locator('.workspace-profile summary')).toBeVisible();await page.locator('.workspace-profile summary').click();await page.getByRole('link',{name:'Account settings',exact:true}).click();await expect(page).toHaveURL(new RegExp(`/${lower}/settings$`));await page.getByRole('link',{name:'Open profile',exact:true}).click();await expect(page.getByRole('heading',{name:heading,exact:true})).toBeVisible()
 await expect(page.locator('.workspace-shell')).toHaveAttribute('data-workspace',lower);await expect(page.locator('.site-header')).toHaveCount(1);await expect(page.getByText('Switch workspace',{exact:true})).toHaveCount(0)
 await expect(page.getByRole('heading',{name:'NIC',exact:true})).toBeVisible()
 await expect(page.getByRole('heading',{name:'OWNER AUTHORISATION',exact:true})).toHaveCount(role==='OWNER'?1:0);await expect(page.getByRole('heading',{name:'DRIVING LICENCE',exact:true})).toHaveCount(role==='DRIVER'?1:0)
 await expect(page.getByRole('option',{name:'Driving licence',exact:true})).toHaveCount(role==='DRIVER'?1:0);await expect(page.getByRole('option',{name:'Vehicle registration',exact:true})).toHaveCount(role==='OWNER'?1:0)
 await expect(page.getByRole('link',{name:'Reset password using a verified email'})).toHaveAttribute('href',role==='ADMIN'?'/forgot-password?workspace=admin':`/forgot-password?journey=${lower}`)
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await expect(page.locator('.document-checklist')).toHaveCSS('background-color','rgb(6, 36, 72)');await page.screenshot({path:info.outputPath(lower+'-profile.png'),fullPage:true})
 await page.getByRole('button',{name:'View all retained documents',exact:true}).click();await expect(page.getByRole('heading',{name:'Retained private documents',exact:true})).toBeVisible();await expect(page.getByRole('heading',{name:'OWNER AUTHORISATION',exact:true})).toBeVisible();await expect(page.getByRole('heading',{name:'DRIVING LICENCE',exact:true})).toBeVisible();await expect(page.getByRole('button',{name:'Submit private document',exact:true})).toHaveCount(0)
 await page.screenshot({path:info.outputPath(lower+'-retained-documents.png'),fullPage:true})
 if(role!=='DRIVER'){await page.getByRole('link',{name:'Manage Driver evidence',exact:true}).click();await expect(page.locator('.workspace-shell')).toHaveAttribute('data-workspace','driver');await expect(page.getByRole('heading',{name:'Driver application documents',exact:true})).toBeVisible()}
 await visit(page,accountPath(role));await page.getByRole('link',{name:`Back to ${name} dashboard`,exact:true}).click();await expect(page).toHaveURL(new RegExp(`/${lower}/dashboard$`))
})

test('profile queries cannot bypass approval or account restrictions; legacy evidence resumes correct journey',async({page})=>{
 const state=await setup(page,{approved:['PASSENGER']});await visit(page,'/account?workspace=admin');await expect(page.getByRole('heading',{name:'Workspace access denied',exact:true})).toBeVisible()
 await visit(page,'/account?workspace=owner');await expect(page.getByRole('heading',{name:'Workspace access denied',exact:true})).toBeVisible()
 await visit(page,'/account?documents=owner');await expect(page).toHaveURL(/\/owner\/onboarding$/);await expect(page.getByRole('heading',{name:'Waiting for Admin Approval',exact:true})).toBeVisible()
 await visit(page,'/account?documents=driver');await expect(page).toHaveURL(/\/driver\/onboarding$/)
 state.status='BLOCKED';await visit(page,'/account');await expect(page.getByRole('heading',{name:'Account access unavailable',exact:true})).toBeVisible();await expect(page.getByRole('button',{name:'View all retained documents'})).toHaveCount(0)
})

test('existing Admin authentication never grants Admin to a Passenger',async({page})=>{
 await setup(page,{approved:['PASSENGER'],entry:'/admin/dashboard',destination:'/admin/dashboard'});await expect(page.getByRole('heading',{name:'Workspace access denied',exact:true})).toBeVisible();await expect(page.getByRole('link',{name:'Users & Roles',exact:true})).toHaveCount(0)
})

test('anonymous legacy document links retain matching login intent',async({page})=>{
 for(const role of ['owner','driver']){await page.goto('/account?documents='+role);await expect(page).toHaveURL(new RegExp('/login\\?journey='+role+'$'))}
})

test('Admin Google entry uses existing accounts and general registration remains Passenger',async({page})=>{
 const state=await setup(page);let completion=true;const mutations=[]
 page.on('request',r=>{if(r.method()==='POST')mutations.push(new URL(r.url()).pathname)})
 await page.route('https://accounts.google.com/gsi/client',r=>r.fulfill({contentType:'application/javascript',body:`window.google={accounts:{id:{initialize(c){this.config=c},renderButton(host){const b=document.createElement('button');b.textContent='Continue with Google';b.onclick=()=>this.config.callback({credential:'test-google'});host.appendChild(b)}}}};`}))
 await page.route('**/api/v1/auth/google/challenge',r=>r.fulfill({json:{client_id:'test-client',nonce:'n'.repeat(43),challenge:'c'.repeat(43)}}))
 await page.route('**/api/v1/auth/google',r=>r.fulfill({json:completion?{status:'completion_required',ticket:'t'.repeat(43),full_name:'New identity',email:'new@example.com'}:{access_token:'workspace-access',refresh_token:'workspace-refresh',expires_in:900}}))
 await page.goto('/login?workspace=admin');await expect(page.getByRole('link',{name:/Create account|Create an account/})).toHaveCount(0);await page.getByRole('button',{name:'Continue with Google',exact:true}).click();await expect(page.getByRole('alert')).toContainText('existing approved Admin account');await expect(page).toHaveURL(/\/login\?workspace=admin$/)
 completion=false;await page.getByRole('button',{name:'Continue with Google',exact:true}).click();await expect(page).toHaveURL(/\/admin\/dashboard$/);await expect(page.locator('.overview-banner h1')).toBeVisible();expect(mutations).not.toContain('/api/v1/auth/google/complete');expect(mutations).not.toContain('/api/v1/auth/register')
 await visit(page,'/register?workspace=admin');await expect(page).toHaveURL(/\/dashboard$/);await expect(page.locator('.workspace-sidebar')).toHaveCount(0);expect(state.requests.some(([method,path])=>method==='POST'&&path==='/users/me/role-requests')).toBe(false)
})

test('Admin recovery and verification preserve authorized continuation without a Passenger detour',async({page})=>{
 await setup(page);let verification=true
 await page.route('**/api/v1/auth/login',r=>verification?r.fulfill({json:{status:'verification_required',verification_ticket:'v'.repeat(43)}}):r.fallback())
 await page.route('**/api/v1/auth/password/forgot',r=>r.fulfill({status:202,json:{message:'Check your verified email.'}}));await page.route('**/api/v1/auth/password/reset',r=>r.fulfill({json:{message:'Password updated.'}}))
 await page.route('**/api/v1/auth/email/verify',r=>{verification=false;return r.fulfill({json:{message:'Email verified.'}})})
 await page.goto('/admin/dashboard');await page.getByRole('link',{name:'Forgot password?',exact:true}).click();await expect(page).toHaveURL(/\/forgot-password\?workspace=admin$/);await page.getByLabel('Email address',{exact:true}).fill('workspace@example.com');await page.getByRole('button',{name:'Request reset link'}).click()
 await visit(page,`/reset-password#token=${'r'.repeat(43)}`);await page.getByLabel('New password',{exact:true}).fill('BrowserTravelly2!');await page.getByRole('button',{name:'Save new password'}).click();await page.getByRole('link',{name:'Back to sign in'}).click();await expect(page).toHaveURL(/\/login\?workspace=admin$/)
 const login=async()=>{await page.getByLabel('Email address',{exact:true}).fill('workspace@example.com');await page.getByLabel('Password',{exact:true}).fill('BrowserTravelly2!');await page.getByRole('button',{name:'Log in',exact:true}).click()};await login();await expect(page).toHaveURL(/\/check-email\?workspace=admin$/)
 await visit(page,`/verify-email#token=${'v'.repeat(43)}`);await page.getByRole('button',{name:'Verify email',exact:true}).click();await page.getByRole('link',{name:'Sign in or request another verification link'}).click();await expect(page).toHaveURL(/\/login\?workspace=admin$/);await login();await expect(page).toHaveURL(/\/admin\/dashboard$/)
})

test('general recovery clears an earlier Admin continuation',async({page})=>{
 await setup(page);await page.route('**/api/v1/auth/password/forgot',r=>r.fulfill({status:202,json:{message:'Check your email.'}}))
 for(const url of ['/forgot-password?workspace=admin','/forgot-password']){await visit(page,url);await page.getByLabel('Email address',{exact:true}).fill('workspace@example.com');await page.getByRole('button',{name:'Request reset link'}).click();await expect(page.getByRole('status')).toContainText('Check your email.')}
 await visit(page,`/reset-password#token=${'r'.repeat(43)}`);await expect(page.getByRole('link',{name:'Back to sign in',exact:true})).toHaveAttribute('href','/login')
})

test('expired profile access preserves matching login context without exposing documents',async({page})=>{
 for(const role of ['OWNER','DRIVER','ADMIN']){
  await setup(page);await visit(page,accountPath(role));await expect(page.getByRole('heading',{name:role==='ADMIN'?'Profile':'Hello, Kasun.',exact:true})).toBeVisible()
  await page.route('**/api/v1/users/me',r=>r.fulfill({status:401,json:{message:'Session expired.'}}));await page.route('**/api/v1/auth/refresh',r=>r.fulfill({status:401,json:{message:'Sign in again.'}}))
  await visit(page,`/${role.toLowerCase()}/settings`);await expect(page).toHaveURL(role==='ADMIN'?/\/login\?workspace=admin$/:new RegExp('/login\\?journey='+role.toLowerCase()+'$'));await expect(page.getByRole('button',{name:'View all retained documents'})).toHaveCount(0)
 }
})
