import {test,expect} from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'
import {randomUUID} from 'node:crypto'
const fixture=JSON.parse(fs.readFileSync(new URL('../../../.tools/pricing-browser-fixture.json',import.meta.url),'utf8'))
const password='BrowserTravelly1!'
async function ok(response){expect(response.ok(),`${new URL(response.url()).pathname}: HTTP ${response.status()}`).toBe(true);return response.json()}
async function visit(page,url){await page.evaluate(url=>{history.pushState({},'',url);dispatchEvent(new PopStateEvent('popstate'))},url)}
for(const role of ['OWNER','DRIVER'])test(`real API ${role} application, evidence, rejection, same-record resubmission and Admin approval`,async({page,request},info)=>{
 const email=`${randomUUID()}@example.com`,prefix='/api/v1',lower=role.toLowerCase(),name=role==='OWNER'?'Owner':'Driver'
 const person=await ok(await request.post(prefix+'/auth/register',{data:{full_name:'Onboarding Test Applicant',email,password,phone_e164:'+9477'+String(Date.now()).slice(-7),preferred_language:'en',accept_terms:true}}))
 const mailRoot=path.join(path.dirname(fixture.image_path),'mail')
 const mail=fs.readdirSync(mailRoot).map(n=>fs.readFileSync(path.join(mailRoot,n),'utf8')).find(text=>text.includes(email))
 const token=mail.replace(/=\r?\n/g,'').replace(/=3D/g,'=').match(/#token=([A-Za-z0-9_-]+)/)[1]
 await ok(await request.post(prefix+'/auth/email/verify',{data:{token}}))
 const admin=await ok(await request.post(prefix+'/auth/login',{data:{identifier:'vehicle-admin@example.com',password}})),headers={Authorization:'Bearer '+admin.access_token}
 await page.goto('/login?journey='+lower);await page.getByLabel('Email address',{exact:true}).fill(email);await page.getByLabel('Password',{exact:true}).fill(password);await page.getByRole('button',{name:'Log in',exact:true}).click()
 await expect(page).toHaveURL(new RegExp(`/${lower}/onboarding$`));await page.getByRole('button',{name:`Submit ${name} application`,exact:true}).click();await expect(page.getByRole('heading',{name:'Waiting for Admin Approval',exact:true})).toBeVisible()
 let queue=await ok(await request.get(prefix+'/admin/role-requests?role_code='+role,{headers}));let application=queue.items.find(r=>r.applicant.id===person.id);expect(application).toBeTruthy();const id=application.id
 const early=await request.patch(prefix+`/admin/role-requests/${id}/review`,{headers,data:{decision:'APPROVED',version:application.version}});expect(early.status()).toBe(409)
 application=await ok(await request.patch(prefix+`/admin/role-requests/${id}/review`,{headers,data:{decision:'REJECTED',version:application.version,reason:'Provide required readable evidence.'}}))
 await page.getByRole('button',{name:'Refresh application status'}).click();await page.getByRole('button',{name:`Resubmit ${name} application`,exact:true}).click();await expect(page.getByRole('heading',{name:'Waiting for Admin Approval',exact:true})).toBeVisible()
 for(const kind of ['NIC',role==='OWNER'?'OWNER_AUTHORISATION':'DRIVING_LICENCE']){
  await page.getByLabel('Document type',{exact:false}).selectOption(kind)
  if(kind==='DRIVING_LICENCE'){await page.getByLabel('Issuing country',{exact:false}).selectOption('LK');await page.getByLabel('Expiry date',{exact:false}).fill('2030-12-31')}
  await page.getByLabel('Document file',{exact:false}).setInputFiles({name:'evidence.png',mimeType:'image/png',buffer:fs.readFileSync(fixture.image_path)})
  const uploaded=page.waitForResponse(r=>new URL(r.url()).pathname===prefix+'/documents'&&r.request().method()==='POST');await page.getByRole('button',{name:'Submit private document',exact:true}).click();await ok(await uploaded);await expect(page.getByText('Your private document was submitted for review.',{exact:false})).toBeVisible()
 }
 const detail=await ok(await request.get(prefix+`/admin/role-requests/${id}`,{headers}));expect(detail.application.id).toBe(id);expect(detail.application.approval_status).toBe('PENDING')
 for(const doc of detail.documents){let reviewed=await ok(await request.patch(prefix+`/admin/documents/${doc.id}/review`,{headers,data:{decision:'UNDER_REVIEW',version:doc.version}}));await ok(await request.patch(prefix+`/admin/documents/${doc.id}/review`,{headers,data:{decision:'APPROVED',version:reviewed.version}}))}
 await page.screenshot({path:info.outputPath(lower+'-waiting-real-api.png'),fullPage:true})
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
 await ok(await request.patch(prefix+`/admin/role-requests/${id}/review`,{headers,data:{decision:'APPROVED',version:detail.application.version}}))
 await expect(page).toHaveURL(new RegExp(`/${lower}/dashboard$`));await page.screenshot({path:info.outputPath(lower+'-approved-real-api.png'),fullPage:true})
 await visit(page,'/account#'+lower+'-application');await expect(page).toHaveURL(new RegExp(`/${lower}/dashboard$`))
 await page.locator('.workspace-profile summary').click();await page.getByRole('link',{name:'Account settings',exact:true}).click();await expect(page).toHaveURL(new RegExp(`/${lower}/settings$`));await page.getByRole('link',{name:'Open profile',exact:true}).click()
 await expect(page.getByRole('heading',{name:name+' application documents',exact:true})).toBeVisible();await expect(page.locator('.workspace-shell')).toHaveAttribute('data-workspace',lower);await expect(page.locator('.site-header')).toHaveCount(1)
 await expect(page.getByRole('option',{name:role==='OWNER'?'Driving licence':'Vehicle registration',exact:true})).toHaveCount(0)
 await page.getByRole('button',{name:'View all retained documents',exact:true}).click();await expect(page.getByRole('heading',{name:'Retained private documents',exact:true})).toBeVisible();await expect(page.getByRole('button',{name:'Submit private document'})).toHaveCount(0)
 await page.getByRole('button',{name:'View private document',exact:true}).first().click();await expect(page.getByRole('img',{name:'Private application evidence',exact:true})).toBeVisible();await page.getByRole('button',{name:'Close preview',exact:true}).click()
 await page.screenshot({path:info.outputPath(lower+'-profile-retained-real-api.png'),fullPage:true});await page.getByRole('link',{name:`Back to ${name} dashboard`,exact:true}).click();await expect(page).toHaveURL(new RegExp(`/${lower}/dashboard$`))
})

test('real API direct Admin entry, profile/settings return and Passenger authorization denial',async({page,request},info)=>{
 const prefix='/api/v1',password='BrowserTravelly1!',passenger=await ok(await request.post(prefix+'/auth/login',{data:{identifier:'pricing-passenger@example.com',password}}))
 const denied=await request.get(prefix+'/admin/role-requests',{headers:{Authorization:'Bearer '+passenger.access_token}});expect(denied.status()).toBe(403)
 const visits=[];page.on('framenavigated',frame=>{if(frame===page.mainFrame())visits.push(new URL(frame.url()).pathname)})
 await page.goto('/admin/dashboard');await expect(page).toHaveURL(/\/login\?workspace=admin$/);await expect(page.getByRole('link',{name:'Create account',exact:true})).toHaveCount(0)
 await page.getByLabel('Email address',{exact:true}).fill('vehicle-admin@example.com');await page.getByLabel('Password',{exact:true}).fill(password);await page.getByRole('button',{name:'Log in',exact:true}).click();await expect(page).toHaveURL(/\/admin\/dashboard$/);await expect(page.locator('.overview-banner h1')).toBeVisible();expect(visits).not.toContain('/dashboard');expect(visits).not.toContain('/account')
 await page.locator('.workspace-profile summary').click();await page.getByRole('link',{name:'Account settings',exact:true}).click();await page.getByRole('link',{name:'Open profile',exact:true}).click();await expect(page.locator('.workspace-shell')).toHaveAttribute('data-workspace','admin');await expect(page.getByRole('heading',{name:'Your private documents',exact:true})).toBeVisible();await expect(page.locator('.site-header')).toHaveCount(1)
 await expect(page.getByRole('option',{name:'Driving licence',exact:true})).toHaveCount(0);await expect(page.getByRole('option',{name:'Vehicle registration',exact:true})).toHaveCount(0);await page.screenshot({path:info.outputPath('admin-profile-real-api.png'),fullPage:true});await page.getByRole('link',{name:'Back to Admin dashboard',exact:true}).click();await expect(page).toHaveURL(/\/admin\/dashboard$/)
})
