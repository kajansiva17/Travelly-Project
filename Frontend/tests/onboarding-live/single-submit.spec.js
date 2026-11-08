import {test,expect} from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'
import {randomUUID,randomInt} from 'node:crypto'

const fixture=JSON.parse(fs.readFileSync(process.env.TRAVELLY_PRICING_FIXTURE_PATH,'utf8'))
const base='http://127.0.0.1:5186',password='BrowserTravelly1!'
async function ok(response){expect(response.ok(),`${new URL(response.url()).pathname}: HTTP ${response.status()}`).toBe(true);return response.json()}
for(const role of ['OWNER','DRIVER'])test(`real ${role} single application and Admin approval`,async({page,request},info)=>{
 const lower=role.toLowerCase(),name=role==='OWNER'?'Owner':'Driver',email=randomUUID()+'@example.com',phone='+9477'+String(randomInt(0,10000000)).padStart(7,'0')
 const applicant=await ok(await request.post(base+'/api/v1/auth/register',{data:{full_name:'Onboarding Test Applicant',email,password,phone_e164:phone,preferred_language:'en',accept_terms:true}}))
 const mailRoot=path.join(path.dirname(fixture.image_path),'mail')
 const mail=fs.readdirSync(mailRoot).map(n=>fs.readFileSync(path.join(mailRoot,n),'utf8')).find(text=>text.includes(email))
 const token=mail.replace(/=\r?\n/g,'').replace(/=3D/g,'=').match(/#token=([A-Za-z0-9_-]+)/)[1]
 await ok(await request.post(base+'/api/v1/auth/email/verify',{data:{token}}))
 const admin=await ok(await request.post(base+'/api/v1/auth/login',{data:{identifier:'vehicle-admin@example.com',password}})),headers={Authorization:'Bearer '+admin.access_token}
 await page.goto(base+(role==='OWNER'?'/for-owners':'/drive-with-us'));await page.locator('.hero-actions .button').first().click()
 await page.getByLabel('Email address',{exact:true}).fill(email);await page.getByLabel('Password',{exact:true}).fill(password);await page.getByRole('button',{name:'Log in',exact:true}).click()
 await expect(page).toHaveURL(new RegExp(`/${lower}/onboarding$`))
 if(role==='OWNER')await page.getByLabel('Whose name is on the vehicle registration?').selectOption('SELF')
 const other=role==='OWNER'?'VEHICLE_REGISTRATION':'DRIVING_LICENCE'
 for(const type of ['NIC',other])await page.locator('#'+type+'-file').setInputFiles({name:'evidence.png',mimeType:'image/png',buffer:fs.readFileSync(fixture.image_path)})
 if(role==='DRIVER')await page.locator('#DRIVING_LICENCE-expiry_date').fill('2090-12-31')
 await page.screenshot({path:info.outputPath(lower+'-application-real.png'),fullPage:true})
 await page.getByRole('button',{name:`Submit ${name} application`,exact:true}).click()
 await expect(page.getByRole('heading',{name:`${name} application submitted — waiting for Admin approval`})).toBeVisible()
 const queue=await ok(await request.get(base+'/api/v1/admin/role-requests?role_code='+role,{headers})),application=queue.items.find(r=>r.applicant.id===applicant.id)
 expect(application).toBeTruthy()
 const detail=await ok(await request.get(base+'/api/v1/admin/role-requests/'+application.id,{headers}));expect(detail.documents.map(d=>d.document_type).sort()).toEqual(['NIC',other].sort())
 for(const doc of detail.documents){const reviewing=await ok(await request.patch(base+`/api/v1/admin/documents/${doc.id}/review`,{headers,data:{decision:'UNDER_REVIEW',version:doc.version}}));await ok(await request.patch(base+`/api/v1/admin/documents/${doc.id}/review`,{headers,data:{decision:'APPROVED',version:reviewing.version}}))}
 await page.screenshot({path:info.outputPath(lower+'-waiting-real.png'),fullPage:true})
 await ok(await request.patch(base+`/api/v1/admin/role-requests/${application.id}/review`,{headers,data:{decision:'APPROVED',version:detail.application.version}}))
 await expect(page).toHaveURL(new RegExp(`/${lower}/dashboard$`))
})
