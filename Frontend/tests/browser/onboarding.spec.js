import {test,expect} from '@playwright/test'

const uid='12222222-2222-4222-8222-222222222222'
async function fixture(page){
 const state={roles:{},account:'ACTIVE',verified:true,verificationRequired:false,google:false,requests:[],documents:[],reads:0,fail:false,duplicate:false}
 await page.route('https://accounts.google.com/gsi/client',r=>r.fulfill({contentType:'application/javascript',body:`window.google={accounts:{id:{initialize(c){this.config=c},renderButton(host){const b=document.createElement('button');b.textContent='Continue with Google';b.onclick=()=>this.config.callback({credential:'fixture-google'});host.appendChild(b)}}}};`}))
 await page.route('**/api/v1/**',async route=>{
  const req=route.request(),path=new URL(req.url()).pathname.replace('/api/v1',''),json=req.postData()&&req.headers()['content-type']?.includes('application/json')?req.postDataJSON():null
  state.requests.push({method:req.method(),path,body:json})
  const approved=['PASSENGER',...Object.keys(state.roles).filter(k=>state.roles[k]==='APPROVED')]
  const tokens={access_token:'onboarding-access',refresh_token:'onboarding-refresh',expires_in:900}
  let body={items:[]},status=200
  if(path==='/auth/config')body={google_enabled:state.google,client_id:'fixture-client'}
  else if(path.endsWith('/challenge'))body={client_id:'fixture-client',nonce:'n'.repeat(43),challenge:'c'.repeat(43)}
  else if(path==='/auth/google')body={status:'completion_required',ticket:'t'.repeat(43),email:'new@example.com',full_name:'Journey Applicant'}
  else if(path==='/auth/google/complete'||path==='/auth/login')body=state.verificationRequired?{status:'verification_required',verification_ticket:'v'.repeat(43)}:tokens
  else if(path==='/auth/register'){status=201;body={status:'verification_required',verification_ticket:'v'.repeat(43),email_delivery:'captured'}}
  else if(path==='/auth/email/verify'){state.verificationRequired=false;body={message:'Email verified. Sign in to continue.'}}
  else if(path==='/auth/password/forgot'){status=202;body={message:'If eligible, a reset email will be sent.'}}
  else if(path==='/auth/password/reset')body={message:'Password updated. Sign in again.'}
  else if(path==='/auth/refresh')body=tokens
  else if(path==='/users/me'){
   state.reads++
   if(state.fail)return route.fulfill({status:503,json:{message:'Account source unavailable.'}})
   body={id:uid,full_name:'Journey Applicant',email:'journey@example.com',phone_e164:'+94771234567',email_verified_at:state.verified?'2026-11-01T00:00:00Z':null,account_status:state.account,approved_roles:approved}
  }else if(path==='/users/me/roles')body={items:[{id:'passenger-role',role_code:'PASSENGER',approval_status:'APPROVED'},...Object.entries(state.roles).map(([role_code,approval_status])=>({id:role_code+'-same-id',role_code,approval_status,rejection_reason:approval_status==='REJECTED'?'Correct the evidence.':null,suspension_reason:approval_status==='SUSPENDED'?'Authorized review required.':null}))]}
  else if(path==='/users/me/role-requests'){
   if(state.duplicate)return route.fulfill({status:409,json:{message:'This role is already requested.'}})
   state.roles[json.role_code]='PENDING';status=201;body={id:json.role_code+'-same-id',role_code:json.role_code,approval_status:'PENDING'}
  }else if(path==='/documents'&&req.method()==='POST'){state.documents.push(req.postDataBuffer().toString());status=201;body={id:'retained-document',status:'SUBMITTED'}}
  else if(path==='/documents')body={items:[{id:'retained-document',document_type:'NIC',status:'NEEDS_CORRECTION',rejection_reason:'Supply a readable copy.'}],page:1,has_next:false}
  else if(path==='/users/me/auth-methods')body={password:true,google:false}
  else if(path==='/bookings/active')body={id:'active',reference:'TR-ACTIVE',passenger_user_id:uid,owner_user_id:'other',status:'IN_PROGRESS',start_at:'2026-11-04T03:00:00Z',end_at:'2026-11-04T09:00:00Z',itinerary:{itinerary:{start_at:'2026-11-04T03:00:00Z',service_hours:['6'],stops:[{place:{label:'Test pickup'},wait_minutes:0},{place:{label:'Test destination'},wait_minutes:0}]}}}
  else if(path==='/auth/logout')return route.fulfill({status:204})
  await route.fulfill({status,json:body})
 })
 return state
}
async function visit(page,path){await page.evaluate(path=>{history.pushState({},'',path);dispatchEvent(new PopStateEvent('popstate'))},path)}
async function login(page,role){await page.goto('/login'+(role?'?journey='+role:''));await page.getByLabel('Email address',{exact:true}).fill('journey@example.com');await page.getByLabel('Password',{exact:true}).fill('BrowserTravelly1!');await page.getByRole('button',{name:'Log in',exact:true}).click()}

for(const role of ['owner','driver']){
 const name=role==='owner'?'Owner':'Driver',code=role.toUpperCase()
 test(`${name} public entry and registration verify then continue without Passenger or Account detour`,async({page},info)=>{
  const state=await fixture(page),visits=[];page.on('framenavigated',f=>{if(f===page.mainFrame())visits.push(new URL(f.url()).pathname)})
  await page.goto(role==='owner'?'/for-owners':'/drive-with-us');await page.locator('.hero-actions .button').first().click()
  await expect(page).toHaveURL(new RegExp('/login\\?journey='+role+'$'))
  await page.locator('.auth-switch a').click();await expect(page).toHaveURL(new RegExp('/register\\?journey='+role+'$'))
  await page.getByLabel('Full name',{exact:true}).fill('Journey Applicant');await page.getByLabel('Email address',{exact:true}).fill('new@example.com');await page.getByLabel('Mobile number',{exact:true}).fill('771234567');await page.getByLabel('Password',{exact:true}).fill('BrowserTravelly1!');await page.getByLabel('Confirm password',{exact:true}).fill('BrowserTravelly1!');await page.getByRole('checkbox').check();await page.getByRole('button',{name:'Create account',exact:true}).click()
  await expect(page).toHaveURL(new RegExp('/check-email\\?journey='+role+'$'));expect(state.requests.find(r=>r.path==='/auth/register').body).not.toHaveProperty('role_code')
  await visit(page,`/verify-email?journey=${role}#token=${'v'.repeat(43)}`);await page.getByRole('button',{name:'Verify email',exact:true}).click();await page.getByRole('link',{name:'Sign in or request another verification link'}).click()
  await page.getByLabel('Email address',{exact:true}).fill('new@example.com');await page.getByLabel('Password',{exact:true}).fill('BrowserTravelly1!');await page.getByRole('button',{name:'Log in',exact:true}).click()
  await expect(page).toHaveURL(new RegExp(`/${role}/onboarding$`));await expect(page.getByRole('button',{name:`Submit ${name} application`,exact:true})).toBeVisible()
  expect(await page.locator('.site-header').evaluate(el=>el.getBoundingClientRect().bottom)).toBeLessThanOrEqual(await page.locator('main h1').evaluate(el=>el.getBoundingClientRect().top))
  await expect(page.locator('.document-checklist')).toHaveCSS('background-color','rgb(6, 36, 72)')
  expect(visits).not.toContain('/dashboard');expect(visits).not.toContain('/account');expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
  await page.screenshot({path:info.outputPath(`${role}-application.png`),fullPage:true})
 })
 test(`${name} application submission, corrections, duplicate guard and approval progression`,async({page},info)=>{
  const state=await fixture(page);await login(page,role)
  await page.getByRole('button',{name:`Submit ${name} application`,exact:true}).click();await expect(page.getByRole('heading',{name:'Waiting for Admin Approval',exact:true})).toBeVisible()
  expect(state.requests.filter(r=>r.path==='/users/me/role-requests').map(r=>r.body)).toEqual([{role_code:code}]);await expect(page.getByRole('button',{name:`Submit ${name} application`,exact:true})).toHaveCount(0)
  await expect(page.getByText('Supply a readable copy.',{exact:true})).toBeVisible()
  await page.getByLabel('Document file',{exact:false}).setInputFiles({name:'correction.png',mimeType:'image/png',buffer:Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=','base64')});await page.getByRole('button',{name:'Submit private document',exact:true}).click();await expect(page.getByText('Your private document was submitted for review.',{exact:false})).toBeVisible();expect(state.documents).toHaveLength(1)
  await page.screenshot({path:info.outputPath(`${role}-waiting.png`),fullPage:true})
  state.roles[code]='APPROVED';await page.evaluate(()=>window.dispatchEvent(new Event('focus')))
  await expect(page).toHaveURL(new RegExp(`/${role}/dashboard$`));await expect(page.locator('.workspace-content main h1')).toBeVisible()
 })
 test(`${name} rejected resubmission and suspended/account restrictions remain distinct`,async({page})=>{
  const state=await fixture(page);state.roles[code]='REJECTED';await login(page,role);await expect(page.getByText('Correct the evidence.',{exact:true})).toBeVisible()
  await page.getByRole('button',{name:`Resubmit ${name} application`,exact:true}).click();await expect(page.getByRole('heading',{name:'Waiting for Admin Approval',exact:true})).toBeVisible()
  state.roles[code]='SUSPENDED';await page.getByRole('button',{name:'Refresh application status'}).click();await expect(page.locator('.dashboard-role-status')).toHaveText('Role suspended');await expect(page.getByRole('button',{name:`Resubmit ${name} application`,exact:true})).toHaveCount(0)
  state.account='BLOCKED';await page.getByRole('button',{name:'Refresh application status'}).click();await expect(page.getByRole('heading',{name:'Account access unavailable'})).toBeVisible();await expect(page.getByRole('button',{name:'Submit private document'})).toHaveCount(0)
 })
 test(`${name} Google completion retains journey and existing request payload`,async({page})=>{
  const state=await fixture(page);state.google=true;await page.goto('/login?journey='+role);await page.getByRole('button',{name:'Continue with Google',exact:true}).click();await expect(page).toHaveURL(new RegExp('/google-complete\\?journey='+role+'$'))
  await page.getByLabel('Mobile number',{exact:true}).fill('771234567');await page.locator('[name="accept_terms"]').check();await page.getByRole('button',{name:'Create Passenger account'}).click();await expect(page).toHaveURL(new RegExp(`/${role}/onboarding$`))
  expect(state.requests.find(r=>r.path==='/auth/google/complete').body).not.toHaveProperty('journey');expect(state.requests.filter(r=>r.path==='/users/me/role-requests')).toHaveLength(0)
 })
 test(`${name} password verification and recovery keep matching continuation`,async({page})=>{
  const state=await fixture(page);state.verificationRequired=true;await login(page,role);await expect(page).toHaveURL(new RegExp('/check-email\\?journey='+role+'$'))
  await visit(page,`/verify-email#token=${'v'.repeat(43)}`);await page.getByRole('button',{name:'Verify email',exact:true}).click();await page.getByRole('link',{name:'Sign in or request another verification link'}).click();await expect(page).toHaveURL(new RegExp('/login\\?journey='+role+'$'))
  await page.getByRole('link',{name:'Forgot password?'}).click();await expect(page).toHaveURL(new RegExp('/forgot-password\\?journey='+role+'$'));await page.getByLabel('Email address',{exact:true}).fill('journey@example.com');await page.getByRole('button',{name:'Request reset link'}).click()
  await visit(page,`/reset-password#token=${'r'.repeat(43)}`);await page.getByLabel('New password',{exact:true}).fill('BrowserTravelly2!');await page.getByRole('button',{name:'Save new password'}).click();await page.getByRole('link',{name:'Back to sign in'}).click();await expect(page).toHaveURL(new RegExp('/login\\?journey='+role+'$'))
  await page.getByLabel('Email address',{exact:true}).fill('journey@example.com');await page.getByLabel('Password',{exact:true}).fill('BrowserTravelly2!');await page.getByRole('button',{name:'Log in',exact:true}).click();await expect(page).toHaveURL(new RegExp(`/${role}/onboarding$`))
 })
 test(`${name} approved entry and legacy links do not reapply; approval cannot displace another page`,async({page})=>{
  const state=await fixture(page);state.roles[code]='APPROVED';await login(page,role);await expect(page).toHaveURL(new RegExp(`/${role}/dashboard$`))
  await visit(page,`/account#${role}-application`);await expect(page).toHaveURL(new RegExp(`/${role}/dashboard$`));expect(state.requests.filter(r=>r.path==='/users/me/role-requests')).toHaveLength(0)
  state.roles[code]='PENDING';await visit(page,`/${role}/onboarding`);await expect(page.getByRole('heading',{name:'Waiting for Admin Approval'})).toBeVisible()
  state.roles[code==='OWNER'?'DRIVER':'OWNER']='APPROVED';await page.evaluate(()=>window.dispatchEvent(new Event('focus')));await expect(page).toHaveURL(new RegExp(`/${role}/onboarding$`))
  await visit(page,'/bookings/active');await expect(page.getByRole('heading',{name:'TR-ACTIVE',exact:true})).toBeVisible();state.roles[code]='APPROVED';await page.evaluate(()=>window.dispatchEvent(new Event('focus')));await page.waitForTimeout(5200);await expect(page).toHaveURL(/\/bookings\/active$/);await expect(page.getByRole('heading',{name:'TR-ACTIVE',exact:true})).toBeVisible()
 })
}
test('general auth, malformed intent, lost session and anonymous legacy entry stay safe',async({page})=>{
 await fixture(page);await page.goto('/dashboard#owner-application');await expect(page).toHaveURL(/\/login\?journey=owner$/)
 await login(page,null);await expect(page).toHaveURL(/\/dashboard$/);await expect(page.locator('.workspace-sidebar')).toHaveCount(0);await expect(page.locator('.dashboard-application')).toHaveCount(0)
 await visit(page,'/login?journey=admin&next=https://example.com');await expect(page).toHaveURL(/\/dashboard$/)
 await page.goto('/driver/onboarding');await expect(page).toHaveURL(/\/login\?journey=driver$/)
})
test('failed sources and duplicate race recover without optimistic approval',async({page})=>{
 const state=await fixture(page);await login(page,'owner');await expect(page.getByRole('button',{name:'Submit Owner application',exact:true})).toBeVisible();state.duplicate=true;state.roles.OWNER='PENDING';await page.getByRole('button',{name:'Submit Owner application',exact:true}).click();await expect(page.getByRole('alert')).toContainText('already requested');await expect(page.getByRole('heading',{name:'Waiting for Admin Approval'})).toBeVisible()
 state.fail=true;await page.getByRole('button',{name:'Refresh application status'}).click();await expect(page.getByRole('alert')).toContainText('Account source unavailable');await expect(page.getByRole('button',{name:'Submit private document'})).toHaveCount(0)
 state.fail=false;await page.getByRole('button',{name:'Try again',exact:true}).click();await expect(page.getByRole('heading',{name:'Waiting for Admin Approval'})).toBeVisible()
})
