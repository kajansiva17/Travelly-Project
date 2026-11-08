import {test,expect} from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'
import {randomUUID} from 'node:crypto'
const fixture=JSON.parse(fs.readFileSync(new URL('../../../.tools/owner-approval-browser-fixture.json',import.meta.url),'utf8'))
const password='BrowserTravelly1!',prefix='/api/v1'
async function ok(response){expect(response.ok(),`${new URL(response.url()).pathname}: HTTP ${response.status()}`).toBe(true);return response.json()}
async function visit(page,url){await page.evaluate(url=>{history.pushState({},'',url);dispatchEvent(new PopStateEvent('popstate'))},url)}
async function login(page,email){await page.goto('/login');await page.getByLabel('Email address',{exact:true}).fill(email);await page.getByLabel('Password',{exact:true}).fill(password);await page.getByRole('button',{name:'Log in',exact:true}).click()}
async function applicant(request,roleCode='OWNER'){
 const email=`${randomUUID()}@example.com`
 const person=await ok(await request.post(prefix+'/auth/register',{data:{full_name:'Owner Approval Test',email,password,phone_e164:'+9477'+String(Date.now()).slice(-7),preferred_language:'en',accept_terms:true}}))
 const mailRoot=path.join(path.dirname(fixture.image_path),'mail')
 const mail=fs.readdirSync(mailRoot).map(n=>fs.readFileSync(path.join(mailRoot,n),'utf8')).find(text=>text.includes(email))
 const token=mail.replace(/=\r?\n/g,'').replace(/=3D/g,'=').match(/#token=([A-Za-z0-9_-]+)/)[1]
 await ok(await request.post(prefix+'/auth/email/verify',{data:{token}}))
 const tokens=await ok(await request.post(prefix+'/auth/login',{data:{identifier:email,password}})),headers={Authorization:'Bearer '+tokens.access_token}
 const role=await ok(await request.post(prefix+'/users/me/role-requests',{headers,data:{role_code:roleCode}}))
 return {email,person,headers,role}
}
async function confirm(page){await page.getByRole('button',{name:'Review confirmation',exact:true}).click();await page.getByRole('button',{name:'Confirm decision',exact:true}).click();await expect(page.getByRole('region',{name:'Decision confirmation'})).toHaveCount(0)}

for(const roleCode of ['OWNER','DRIVER'])test(`real ${roleCode} review, manual status refresh and fresh login open its dashboard`,async({page,request,browser},info)=>{
 const lower=roleCode.toLowerCase(),name=roleCode==='OWNER'?'Owner':'Driver',other=roleCode==='OWNER'?'VEHICLE_REGISTRATION':'DRIVING_LICENCE'
 const c=await applicant(request,roleCode)
 for(const kind of ['NIC',other])await ok(await request.post(prefix+'/documents',{headers:c.headers,multipart:{owner_type:'USER',owner_id:c.person.id,document_type:kind,...(kind==='DRIVING_LICENCE'?{issuing_country:'LK',expiry_date:'2030-12-31'}:{}),file:{name:'test-evidence.png',mimeType:'image/png',buffer:fs.readFileSync(fixture.image_path)}}}))
 expect((await ok(await request.get(prefix+'/users/me',{headers:c.headers}))).approved_roles).not.toContain(roleCode)
 // A second signed-in session waits while the Super Admin reviews the same application.
 const context=await browser.newContext({baseURL:'http://127.0.0.1:5182'}),waiting=await context.newPage()
 try {
  await login(waiting,c.email);await expect(waiting).toHaveURL(/\/dashboard$/);await visit(waiting,`/${lower}/onboarding`)
  await expect(waiting.getByRole('button',{name:'Refresh application status'})).toBeVisible()
  await expect(waiting.getByRole('region',{name:'Pending approval requirements'})).toContainText('Awaiting Super Admin document verification.')
  await waiting.evaluate(()=>{const latest=setInterval(()=>{},100000);for(let id=1;id<=latest;id++)clearInterval(id)})
  await login(page,'vehicle-admin@example.com');await expect(page).toHaveURL(/\/admin\/dashboard$/);await visit(page,`/admin/applications/${c.role.id}`)
  await expect(page.getByRole('button',{name:`Approve ${name}`,exact:true})).toBeDisabled();await expect(page.getByRole('button',{name:`Reject ${name}`,exact:true})).toBeEnabled()
  await expect(page.getByRole('region',{name:'Application review checklist'})).toContainText('SUBMITTED. Open the private document, select Start review')
  await page.screenshot({path:info.outputPath('owner-documents-submitted.png'),fullPage:true})
  for(const [index,kind] of ['NIC',other.replaceAll('_',' ')].entries()){
   await page.getByRole('link',{name:`Go to ${kind} review`,exact:true}).click()
   const doc=page.locator('.review-document').filter({has:page.getByRole('heading',{name:kind,exact:true})})
   await doc.getByRole('button',{name:'View private document',exact:true}).click();await expect(page.getByAltText('Private application evidence')).toBeVisible();await page.getByRole('button',{name:'Close preview',exact:true}).click()
   await doc.getByRole('button',{name:'Start review',exact:true}).click();await expect(page.getByRole('heading',{name:`Start review ${kind}`,exact:true})).toBeFocused();await confirm(page)
   await expect(page.getByRole('region',{name:'Application review checklist'})).toContainText(`${kind}: UNDER_REVIEW`)
   await expect(page.getByRole('button',{name:`Approve ${name}`,exact:true})).toBeDisabled()
   await doc.getByRole('button',{name:'Approve',exact:true}).click();await confirm(page)
   if(index===0)await expect(page.getByRole('button',{name:`Approve ${name}`,exact:true})).toBeDisabled()
  }
  await expect(page.getByRole('button',{name:`Approve ${name}`,exact:true})).toBeEnabled();await expect(page.getByRole('region',{name:'Application review checklist'})).toContainText('Ready for your decision')
  await page.screenshot({path:info.outputPath('owner-ready-to-approve.png'),fullPage:true})
  await waiting.getByRole('button',{name:'Refresh application status'}).click();await expect(waiting.getByRole('region',{name:'Pending approval requirements'})).toContainText('Documents verified ? final role approval pending')
  await page.getByRole('button',{name:`Approve ${name}`,exact:true}).click();await confirm(page);await expect(page.getByRole('status').filter({hasText:'Application approved.'})).toBeVisible()
  const me=await ok(await request.get(prefix+'/users/me',{headers:c.headers}));expect(me.approved_roles).toEqual([roleCode,'PASSENGER'].sort())
  if(roleCode==='OWNER')await ok(await request.get(prefix+'/owners/me/vehicles',{headers:c.headers}))
  await waiting.evaluate(()=>{window.__statusRequests=[];const original=window.fetch;window.fetch=(input,options)=>{window.__statusRequests.push({url:String(input),cache:options?.cache,method:options?.method||'GET'});return original(input,options)}})
  await waiting.getByRole('button',{name:'Refresh application status'}).click();await expect(waiting).toHaveURL(new RegExp(`/${lower}/dashboard$`))
  const statusRequests=await waiting.evaluate(()=>window.__statusRequests);expect(statusRequests.some(r=>r.url.endsWith(`/role-requests/${roleCode}/status`)&&r.cache==='no-store')).toBe(true);expect(statusRequests.filter(r=>r.method==='POST'&&r.url.endsWith('/role-requests'))).toEqual([])
  await waiting.screenshot({path:info.outputPath('approved-owner-dashboard.png'),fullPage:true})
  // A fresh general login uses the database's approved Owner membership.
  const fresh=await context.newPage();await login(fresh,c.email);await expect(fresh).toHaveURL(new RegExp(`/${lower}/dashboard$`));await expect(fresh.locator('.overview-banner h1')).toBeVisible()
  const roles=await ok(await request.get(prefix+'/users/me/roles',{headers:c.headers}));expect(roles.items.find(r=>r.role_code===roleCode).id).toBe(c.role.id)
 }finally{await context.close()}
})

test('real Owner rejection requires a reason, preserves Passenger access and shows applicant notification',async({page,request,browser})=>{
 const c=await applicant(request)
 await login(page,'vehicle-admin@example.com');await expect(page).toHaveURL(/\/admin\/dashboard$/);await visit(page,`/admin/applications/${c.role.id}`)
 await expect(page.getByRole('button',{name:'Approve Owner',exact:true})).toBeDisabled()
 await expect(page.getByRole('region',{name:'Application review checklist'})).toContainText('Ask the applicant to upload the missing evidence to their existing application.')
 await page.getByRole('button',{name:'Reject Owner',exact:true}).click();await expect(page.getByRole('button',{name:'Review confirmation'})).toBeDisabled()
 await page.getByLabel('Applicant-visible reason').fill('Please supply readable ownership evidence.');await confirm(page)
 const context=await browser.newContext({baseURL:'http://127.0.0.1:5182'})
 try{const applicantPage=await context.newPage();await login(applicantPage,c.email);await expect(applicantPage).toHaveURL(/\/dashboard$/);await expect(applicantPage.locator('.application-status-notice')).toContainText('Please supply readable ownership evidence.');expect((await request.get(prefix+'/owners/me/vehicles',{headers:c.headers})).status()).toBe(403)}finally{await context.close()}
})
for(const roleCode of ['OWNER','DRIVER'])test(`real ${roleCode} rejection and resubmission preserves its role and activates dashboard automatically`,async({page,request,browser},info)=>{
 const name=roleCode==='OWNER'?'Owner':'Driver',lower=roleCode.toLowerCase(),other=roleCode==='OWNER'?'VEHICLE_REGISTRATION':'DRIVING_LICENCE',c=await applicant(request,roleCode)
 const old=[]
 for(const kind of ['NIC',other])old.push(await ok(await request.post(prefix+'/documents',{headers:c.headers,multipart:{owner_type:'USER',owner_id:c.person.id,document_type:kind,issue_date:'2099-01-01',...(kind==='DRIVING_LICENCE'?{issuing_country:'LK',expiry_date:'2100-01-01'}:{}),file:{name:'old-test.png',mimeType:'image/png',buffer:fs.readFileSync(fixture.image_path)}}})))
 await login(page,'vehicle-admin@example.com');await expect(page).toHaveURL(/\/admin\/dashboard$/);await visit(page,`/admin/applications/${c.role.id}`)
 const oldNic=page.locator('.review-document').filter({has:page.getByRole('heading',{name:'NIC',exact:true})})
 await oldNic.getByRole('button',{name:'Start review',exact:true}).click();await confirm(page)
 await oldNic.getByRole('button',{name:'Reject',exact:true}).click();await page.getByLabel('Applicant-visible reason').fill('Replace the unreadable identity document.');await confirm(page)
 await page.getByRole('button',{name:`Reject ${name}`,exact:true}).click();await page.getByLabel('Applicant-visible reason').fill('Correct the documents and their issue dates.');await confirm(page)
 const context=await browser.newContext({baseURL:'http://127.0.0.1:5182'})
 try{
  const owner=await context.newPage();await login(owner,c.email);await expect(owner).toHaveURL(/\/dashboard$/);await visit(owner,`/${lower}/onboarding`)
  await expect(owner.getByRole('status').filter({hasText:'Application rejected:'})).toContainText('Correct the documents and their issue dates.')
  await expect(owner.getByRole('button',{name:`Resubmit ${name} application`,exact:true})).toBeVisible()
  if(roleCode==='OWNER')await owner.getByLabel('Whose name is on the vehicle registration?').selectOption('SELF')
  for(const kind of ['NIC',other]){
   await owner.locator(`#${kind}-file`).setInputFiles(fixture.image_path)
   await owner.locator(`#${kind}-issue_date`).fill('2020-01-01')
  }
  if(roleCode==='DRIVER')await owner.locator('#DRIVING_LICENCE-expiry_date').fill('2030-12-31')
  await owner.getByRole('button',{name:`Resubmit ${name} application`,exact:true}).click()
  await expect(owner.getByRole('heading',{name:`${name} application submitted \u2014 waiting for Admin approval`,exact:true})).toBeVisible()
  const ownStatus=await ok(await request.get(prefix+`/users/me/role-requests/${roleCode}/status`,{headers:c.headers}))
  expect(ownStatus.application.id).toBe(c.role.id);expect(ownStatus.application.version).toBeGreaterThan(c.role.version);expect(ownStatus.application.approval_status).toBe('PENDING')
  await page.getByRole('button',{name:'Refresh application',exact:true}).click()
  await expect(page.locator('.dashboard-role-status')).toHaveText('Pending Review')
  await expect(page.getByRole('button',{name:`Approve ${name}`,exact:true})).toBeDisabled()
  await expect(page.getByRole('region',{name:'Application review checklist'})).not.toContainText('in the future')
  await expect(page.getByRole('region',{name:'Application review checklist'})).toContainText('SUBMITTED')
  await page.screenshot({path:info.outputPath('resubmitted-pending-latest-evidence.png'),fullPage:true})
  for(const kind of ['NIC',other.replaceAll('_',' ')]){
   const doc=page.locator('.review-document').filter({has:page.getByRole('heading',{name:kind,exact:true})})
   await doc.getByRole('button',{name:'View private document',exact:true}).click();await expect(page.getByAltText('Private application evidence')).toBeVisible();await page.getByRole('button',{name:'Close preview',exact:true}).click()
   await doc.getByRole('button',{name:'Start review',exact:true}).click();await confirm(page)
   await doc.getByRole('button',{name:'Approve',exact:true}).click();await confirm(page)
  }
  await expect(page.getByRole('button',{name:`Approve ${name}`,exact:true})).toBeEnabled()
  await page.getByRole('button',{name:`Approve ${name}`,exact:true}).click();await confirm(page)
  // The existing waiting page polls current authenticated membership; no new application or login.
  await expect(owner).toHaveURL(new RegExp(`/${lower}/dashboard$`))
  await owner.screenshot({path:info.outputPath('resubmission-approved-dashboard.png'),fullPage:true})
  const ownRoles=await ok(await request.get(prefix+'/users/me/roles',{headers:c.headers})),role=ownRoles.items.find(r=>r.role_code===roleCode)
  expect(role.id).toBe(c.role.id);expect(role.approval_status).toBe('APPROVED')
  const me=await ok(await request.get(prefix+'/users/me',{headers:c.headers}));expect(me.approved_roles).toEqual([roleCode,'PASSENGER'].sort())
  const retained=await ok(await request.get(prefix+'/documents/'+old[0].id,{headers:c.headers}));expect(retained.rejection_reason).toBe('Replace the unreadable identity document.')
  const fresh=await context.newPage();await login(fresh,c.email);await expect(fresh).toHaveURL(new RegExp(`/${lower}/dashboard$`))
 }finally{await context.close()}
})
test('Driver missing-expiry correction stores metadata, requires verification and opens Driver Dashboard',async({page,request},info)=>{
 const c=await applicant(request,'DRIVER')
 const admin=await ok(await request.post(prefix+'/auth/login',{data:{identifier:'vehicle-admin@example.com',password}})),adminHeaders={Authorization:'Bearer '+admin.access_token}
 const initial=[]
 for(const kind of ['NIC','DRIVING_LICENCE'])initial.push(await ok(await request.post(prefix+'/documents',{headers:c.headers,multipart:{owner_type:'USER',owner_id:c.person.id,document_type:kind,...(kind==='DRIVING_LICENCE'?{issuing_country:'LK'}:{}),file:{name:'initial.png',mimeType:'image/png',buffer:fs.readFileSync(fixture.image_path)}}})))
 for(const doc of initial){const reviewing=await ok(await request.patch(prefix+`/admin/documents/${doc.id}/review`,{headers:adminHeaders,data:{decision:'UNDER_REVIEW',version:doc.version}}));const result=await request.patch(prefix+`/admin/documents/${doc.id}/review`,{headers:adminHeaders,data:{decision:'APPROVED',version:reviewing.version}});if(doc.document_type==='NIC')await ok(result);else{expect(result.status()).toBe(422);expect((await result.json()).code).toBe('INVALID_DRIVING_LICENCE_EVIDENCE')}}
 await login(page,c.email);await expect(page).toHaveURL(/\/dashboard$/);await visit(page,'/driver/onboarding')
 const repair=page.getByRole('region',{name:'Correct driving licence details'})
 await expect(repair).toContainText('expiry date is required')
 await repair.getByRole('button',{name:'Correct driving licence',exact:true}).click()
 await repair.getByLabel('Document file (Required)',{exact:true}).setInputFiles(fixture.image_path)
 await repair.getByRole('button',{name:'Submit private document',exact:true}).click()
 await expect(repair.getByText('A current expiry date is required for role approval.',{exact:true})).toBeVisible()
 await repair.getByLabel('Expiry date (Required)',{exact:true}).fill('2031-12-31')
 await repair.getByRole('button',{name:'Submit private document',exact:true}).click();await expect(repair).toHaveCount(0)
 const detail=await ok(await request.get(prefix+`/admin/role-requests/${c.role.id}`,{headers:adminHeaders})),licence=detail.documents.find(doc=>doc.document_type==='DRIVING_LICENCE')
 expect(licence.id).not.toBe(initial[1].id);expect(licence.expiry_date).toBe('2031-12-31');expect(licence.status).toBe('SUBMITTED');expect(licence.verified_at).toBeNull();expect(detail.approval_readiness.ready).toBe(false)
 const denied=await request.patch(prefix+`/admin/role-requests/${c.role.id}/review`,{headers:adminHeaders,data:{decision:'APPROVED',version:detail.application.version}});expect(denied.status()).toBe(409)
 const context=await page.context().browser().newContext({baseURL:'http://127.0.0.1:5182'})
 try{
  const adminPage=await context.newPage();await login(adminPage,'vehicle-admin@example.com');await expect(adminPage).toHaveURL(/\/admin\/dashboard$/);await visit(adminPage,`/admin/applications/${c.role.id}`)
  await expect(adminPage.getByRole('button',{name:'Approve Driver',exact:true})).toBeDisabled()
  const doc=adminPage.locator('.review-document').filter({has:adminPage.getByRole('heading',{name:'DRIVING LICENCE',exact:true})})
  await doc.getByRole('button',{name:'View private document',exact:true}).click();await expect(adminPage.getByAltText('Private application evidence')).toBeVisible();await adminPage.getByRole('button',{name:'Close preview',exact:true}).click()
  await doc.getByRole('button',{name:'Start review',exact:true}).click();await confirm(adminPage)
  await doc.getByRole('button',{name:'Approve',exact:true}).click();await confirm(adminPage)
  await expect(adminPage.getByRole('button',{name:'Approve Driver',exact:true})).toBeEnabled()
  await adminPage.getByRole('button',{name:'Approve Driver',exact:true}).click();await confirm(adminPage)
  await expect(page).toHaveURL(/\/driver\/dashboard$/)
  await page.screenshot({path:info.outputPath('corrected-driver-dashboard.png'),fullPage:true})
  const roles=await ok(await request.get(prefix+'/users/me/roles',{headers:c.headers}));expect(roles.items.find(row=>row.role_code==='DRIVER').id).toBe(c.role.id)
  const user=await ok(await request.get(prefix+'/users/me',{headers:c.headers}));expect(user.approved_roles).toEqual(['DRIVER','PASSENGER'])
  const fresh=await context.newPage();await login(fresh,c.email);await expect(fresh).toHaveURL(/\/driver\/dashboard$/)
 }finally{await context.close()}
})
