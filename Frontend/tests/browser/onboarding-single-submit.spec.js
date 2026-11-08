import {test,expect} from '@playwright/test'

const uid='12222222-2222-4222-8222-222222222222'
const image=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=','base64')
async function setup(page){
 const state={roles:{},documents:[],writes:[],failUpload:false}
 await page.route('**/api/v1/**',async route=>{
  const req=route.request(),path=new URL(req.url()).pathname.replace('/api/v1','');let result={items:[]},status=200
  if(req.method()!=='GET')state.writes.push({path,body:req.postData()})
  if(path==='/auth/login')result={access_token:'test',refresh_token:'test'}
  else if(path==='/users/me')result={id:uid,full_name:'Journey Applicant',email:'journey@example.com',email_verified_at:'2026-11-01T00:00:00Z',account_status:'ACTIVE',approved_roles:['PASSENGER',...Object.keys(state.roles).filter(k=>state.roles[k]==='APPROVED')]}
  else if(path==='/users/me/roles')result={items:[{role_code:'PASSENGER',approval_status:'APPROVED'},...Object.entries(state.roles).map(([role_code,approval_status])=>({role_code,approval_status}))]}
  else if(path==='/documents'&&req.method()==='POST'){
   if(state.failUpload&&state.documents.length===1){state.failUpload=false;return route.fulfill({status:422,json:{message:'Evidence could not be accepted.',field_errors:[{field:'file',message:'Choose a readable evidence file.'}]}})}
   const body=req.postData(),type=body.match(/name="document_type"\r\n\r\n([^\r]+)/)?.[1];result={id:'doc-'+state.documents.length,document_type:type,status:'SUBMITTED',issuing_country:body.match(/name="issuing_country"\r\n\r\n([^\r]+)/)?.[1],expiry_date:body.match(/name="expiry_date"\r\n\r\n([^\r]+)/)?.[1],superseded_document_id:state.documents.find(doc=>doc.document_type===type)?.id};state.documents.unshift(result);status=201
  }else if(path==='/documents')result={items:state.documents,has_next:false,page:1}
  else if(path==='/users/me/role-requests'){const body=req.postDataJSON();state.roles[body.role_code]='PENDING';status=201;result={role_code:body.role_code,approval_status:'PENDING'}}
  else if(path==='/auth/google/challenge')return route.fulfill({status:503,json:{code:'GOOGLE_NOT_CONFIGURED',message:'Not configured'}})
  await route.fulfill({status,json:result})
 })
 return state
}
async function login(page,role){await page.goto(role==='owner'?'/for-owners':'/drive-with-us');await page.locator('.hero-actions .button').first().click();await page.getByLabel('Email address',{exact:true}).fill('journey@example.com');await page.getByLabel('Password',{exact:true}).fill('ExistingPassword1!');await page.getByRole('button',{name:'Log in',exact:true}).click()}
for(const role of ['owner','driver'])test(`${role} single application validates evidence, retains uploads on error and waits for approval`,async({page},info)=>{
 const state=await setup(page),name=role==='owner'?'Owner':'Driver',type=role==='owner'?'VEHICLE_REGISTRATION':'DRIVING_LICENCE'
 await login(page,role);await expect(page).toHaveURL(new RegExp('/'+role+'/onboarding$'))
 const submit=page.getByRole('button',{name:`Submit ${name} application`,exact:true});await expect(submit).toHaveCount(1)
 await expect(page.getByText('Manage your '+name+' application documents')).toHaveCount(0);await expect(page.getByRole('button',{name:/Previous|Next|Submit private document/})).toHaveCount(0)
 await submit.click();await expect(page.getByText('Choose a non-empty PDF, JPG or PNG file.').first()).toBeVisible();expect(state.writes.filter(w=>w.path==='/users/me/role-requests')).toHaveLength(0)
 if(role==='owner')await page.getByLabel('Whose name is on the vehicle registration?').selectOption('SELF')
 await page.locator('#NIC-file').setInputFiles({name:'identity.png',mimeType:'image/png',buffer:image});await page.locator('#'+type+'-file').setInputFiles({name:'evidence.png',mimeType:'image/png',buffer:image})
 await page.screenshot({path:info.outputPath(role+'-application.png'),fullPage:true})
 if(role==='driver')await page.locator('#DRIVING_LICENCE-expiry_date').fill('2030-12-31')
 state.failUpload=true;await submit.click();await expect(page.getByText('Evidence could not be accepted.')).toBeVisible();await expect(page.getByText('Choose a readable evidence file.')).toBeVisible();expect(state.writes.filter(w=>w.path==='/users/me/role-requests')).toHaveLength(0)
 expect(await page.locator('#'+type+'-file').evaluate(el=>el.files[0]?.name)).toBe('evidence.png');await submit.click()
 await expect(page.getByRole('heading',{name:`${name} application submitted — waiting for Admin approval`})).toBeVisible()
 expect(state.writes.filter(w=>w.path==='/documents')).toHaveLength(3);expect(state.writes.filter(w=>w.path==='/users/me/role-requests').map(w=>JSON.parse(w.body))).toEqual([{role_code:role.toUpperCase()}])
 await expect(page.getByRole('button',{name:`Submit ${name} application`})).toHaveCount(0);await expect(page.getByText('Manage your '+name+' application documents')).toHaveCount(0)
 await page.screenshot({path:info.outputPath(role+'-waiting.png'),fullPage:true})
 state.roles[role.toUpperCase()]='APPROVED';await page.getByRole('button',{name:'Refresh application status'}).click();await expect(page).toHaveURL(new RegExp('/'+role+'/dashboard$'))
})

for(const role of ['owner','driver'])test(`${role} approved applicants do not reapply`,async({page})=>{
 const state=await setup(page);state.roles[role.toUpperCase()]='APPROVED';await login(page,role)
 await expect(page).toHaveURL(new RegExp('/'+role+'/dashboard$'))
 expect(state.writes.filter(w=>w.path==='/users/me/role-requests'||w.path==='/documents')).toHaveLength(0)
})

test('pending application exposes only a focused reviewed-document correction',async({page})=>{
 const state=await setup(page);state.roles.DRIVER='PENDING';state.documents=[{id:'identity',document_type:'NIC',status:'APPROVED'},{id:'licence',document_type:'DRIVING_LICENCE',status:'UNDER_REVIEW'}]
 await login(page,'driver');await expect(page.getByRole('heading',{name:'Driver application submitted — waiting for Admin approval'})).toBeVisible()
 state.documents[1].status='NEEDS_CORRECTION';state.documents[1].rejection_reason='Please provide a readable licence.'
 await page.evaluate(()=>window.dispatchEvent(new Event('focus')));await expect(page.getByRole('heading',{name:'Correction requested: DRIVING LICENCE'})).toBeVisible()
 await expect(page.getByRole('button',{name:'Correct requested evidence'})).toHaveCount(1)
 await expect(page.getByRole('button',{name:'Submit Driver application'})).toHaveCount(0)
 await page.getByRole('button',{name:'Correct requested evidence'}).click()
 await expect(page.getByLabel('Document type (Required)')).toHaveValue('DRIVING_LICENCE')
 await expect(page.getByRole('option',{name:'Vehicle registration'})).toHaveCount(0)
})

test('Owner evidence follows registered-owner case without adding a Driver licence',async({page})=>{
 const state=await setup(page);await login(page,'owner')
 for(const value of ['INDIVIDUAL','COMPANY']){
  await page.getByLabel('Whose name is on the vehicle registration?').selectOption(value)
  await expect(page.locator('#OWNER_AUTHORISATION-file')).toBeVisible()
  await expect(page.locator('#VEHICLE_REGISTRATION-file')).toHaveCount(0)
  await expect(page.locator('#DRIVING_LICENCE-file')).toHaveCount(0)
 }
 expect(state.writes.filter(w=>w.path==='/documents'||w.path==='/users/me/role-requests')).toHaveLength(0)
})


for(const role of ['owner','driver'])test(`${role} resubmission cannot silently reuse future-dated retained documents`,async({page})=>{
 const state=await setup(page),code=role.toUpperCase(),name=role==='owner'?'Owner':'Driver',other=role==='owner'?'VEHICLE_REGISTRATION':'DRIVING_LICENCE'
 state.roles[code]='REJECTED';state.documents=[{id:'old-identity',document_type:'NIC',status:'SUBMITTED',issue_date:'2099-01-01'},{id:'old-other',document_type:other,status:'REJECTED'}]
 await login(page,role)
 await expect(page.getByRole('button',{name:`Resubmit ${name} application`,exact:true})).toBeVisible()
 await expect(page.locator('.single-application')).toContainText('cannot be reused')
 if(role==='owner')await page.getByLabel('Whose name is on the vehicle registration?').selectOption('SELF')
 await page.locator('#NIC-file').setInputFiles({name:'corrected.png',mimeType:'image/png',buffer:image})
 await page.locator('#'+other+'-file').setInputFiles({name:'corrected.png',mimeType:'image/png',buffer:image})
 await page.locator('#NIC-issue_date').fill('2099-01-01')
 if(role==='driver')await page.locator('#DRIVING_LICENCE-expiry_date').fill('2030-12-31')
 await page.getByRole('button',{name:`Resubmit ${name} application`,exact:true}).click()
 await expect(page.getByText('The issue date is in the future. Enter the date printed on the corrected document.',{exact:true})).toBeVisible()
 expect(state.writes.filter(w=>w.path==='/documents'||w.path==='/users/me/role-requests')).toHaveLength(0)
 await page.locator('#NIC-issue_date').fill('2020-01-01')
 await page.getByRole('button',{name:`Resubmit ${name} application`,exact:true}).click()
 await expect(page.getByRole('heading',{name:`${name} application submitted — waiting for Admin approval`,exact:true})).toBeVisible()
 expect(state.writes.filter(w=>w.path==='/documents')).toHaveLength(2)
 expect(state.writes.filter(w=>w.path==='/users/me/role-requests')).toHaveLength(1)
})


for(const expiry of [null,'2020-01-01'])test(`approved Driver licence with ${expiry||'missing'} expiry can be replaced without another application`,async({page})=>{
 const state=await setup(page);state.roles.DRIVER='PENDING'
 state.documents=[{id:'identity',document_type:'NIC',status:'APPROVED'},{id:'legacy-licence',document_type:'DRIVING_LICENCE',status:'APPROVED',issuing_country:'LK',expiry_date:expiry}]
 await login(page,'driver')
 const repair=page.getByRole('region',{name:'Correct driving licence details'})
 await expect(repair).toContainText('saved document is APPROVED')
 await repair.getByRole('button',{name:'Correct driving licence',exact:true}).click()
 await expect(repair.getByLabel('Expiry date (Required)',{exact:true})).toBeVisible()
 await repair.getByLabel('Document file (Required)',{exact:true}).setInputFiles({name:'corrected-licence.png',mimeType:'image/png',buffer:image})
 await repair.getByRole('button',{name:'Submit private document',exact:true}).click()
 await expect(repair.getByText('A current expiry date is required for role approval.',{exact:true})).toBeVisible()
 expect(state.writes.filter(w=>w.path==='/documents')).toHaveLength(0)
 await repair.getByLabel('Expiry date (Required)',{exact:true}).fill('2020-01-01')
 await repair.getByRole('button',{name:'Submit private document',exact:true}).click()
 await expect(repair.getByText('This document has expired. Upload current replacement evidence.',{exact:true})).toBeVisible()
 await repair.getByLabel('Expiry date (Required)',{exact:true}).fill('2031-12-31')
 await repair.getByRole('button',{name:'Submit private document',exact:true}).click()
 await expect(repair).toHaveCount(0)
 const writes=state.writes.filter(w=>w.path==='/documents');expect(writes).toHaveLength(1);expect(writes[0].body).toContain('2031-12-31')
 expect(state.writes.filter(w=>w.path==='/users/me/role-requests')).toHaveLength(0)
 expect(state.documents.find(doc=>doc.id==='identity').status).toBe('APPROVED')
 state.roles.DRIVER='APPROVED';await page.getByRole('button',{name:'Refresh application status'}).click();await expect(page).toHaveURL(/\/driver\/dashboard$/)
})
