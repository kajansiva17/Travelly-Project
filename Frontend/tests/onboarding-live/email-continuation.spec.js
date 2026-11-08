import {test,expect} from '@playwright/test'
import fs from 'node:fs/promises'
import path from 'node:path'
import {randomUUID,randomInt} from 'node:crypto'

const fixture=JSON.parse(await fs.readFile(process.env.TRAVELLY_PRICING_FIXTURE_PATH,'utf8'))
const base='http://127.0.0.1:5186',password='BrowserTravelly1!'
for(const role of ['PASSENGER','OWNER','DRIVER'])test(`real email link continues ${role} registration in a fresh tab`,async({page,context},info)=>{
 const email=randomUUID()+'@example.com',phone='77'+String(randomInt(0,10000000)).padStart(7,'0')
 await page.goto(base+(role==='OWNER'?'/for-owners':role==='DRIVER'?'/drive-with-us':'/'))
 if(role!=='PASSENGER'){await page.locator('.hero-actions .button').first().click();await page.locator('.auth-switch a').click()}
 else {await page.getByRole('link',{name:'Log in',exact:true}).first().click();await page.locator('.auth-switch a').click()}
 await page.getByLabel('Full name',{exact:true}).fill('Verification Applicant');await page.getByLabel('Email address',{exact:true}).fill(email);await page.getByLabel('Mobile number',{exact:true}).fill(phone)
 if(await page.getByRole('button',{name:'Continue',exact:true}).count())await page.getByRole('button',{name:'Continue',exact:true}).click()
 await page.getByLabel('Password',{exact:true}).fill(password);await page.getByLabel('Confirm password',{exact:true}).fill(password);await page.getByRole('checkbox').check();await page.getByRole('button',{name:'Create account',exact:true}).click()
 await expect(page).toHaveURL(/\/check-email/)
 const mailRoot=path.join(path.dirname(fixture.image_path),'mail');let mail=''
 for(const file of await fs.readdir(mailRoot)){const content=await fs.readFile(path.join(mailRoot,file),'utf8');if(content.includes(email)){mail=content;break}}
 expect(mail).toBeTruthy();const token=mail.replace(/=\r?\n/g,'').replace(/=3D/g,'=').match(/#token=([A-Za-z0-9_-]+)/)[1]
 const verify=await context.newPage(),tampered=role==='DRIVER'?'owner':'driver'
 await verify.goto(`${base}/verify-email?journey=${tampered}#token=${token}`)
 await verify.getByRole('button',{name:'Verify email',exact:true}).click()
 await expect(verify).toHaveURL(new RegExp(role==='PASSENGER'?'/dashboard$':`/${role.toLowerCase()}/onboarding$`))
 if(role==='PASSENGER'){await expect(verify.getByRole('heading',{name:/Where will you go next/})).toBeVisible();await expect(verify.locator('.workspace-sidebar')).toHaveCount(0)}
 else {await expect(verify.getByRole('heading',{name:`${role==='OWNER'?'Owner':'Driver'} application`,exact:true}).first()).toBeVisible();await expect(verify.getByRole('button',{name:`Submit ${role==='OWNER'?'Owner':'Driver'} application`,exact:true})).toBeVisible()}
 await verify.screenshot({path:info.outputPath(role.toLowerCase()+'-continued.png'),fullPage:true})
 const replay=await context.newPage();await replay.goto(`${base}/verify-email?journey=${tampered}#token=${token}`);await replay.getByRole('button',{name:'Verify email',exact:true}).click();await expect(replay.getByRole('alert')).toContainText('invalid, expired or already used');await expect(replay.getByRole('link',{name:'Sign in or request another verification link'})).toHaveAttribute('href','/login');await replay.close();await verify.close()
})
