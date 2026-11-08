import {test,expect,chromium} from '@playwright/test'
import {mkdtemp,rm,writeFile} from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'

test('Login and Register remain usable at actual Chrome zoom levels',async({},info)=>{
 test.skip(info.project.name!=='desktop','Browser zoom is checked once in an isolated desktop Chrome profile.')
 test.setTimeout(90000)
 // Chrome's real Page zoom setting changes CSS viewport size and pixel ratio.
 // Use a fresh profile for each run so saved browser zoom cannot affect settings changes.
 const profilePath=await mkdtemp(path.join(os.tmpdir(),'travelly-auth-zoom-'))
 let context
 const errors=[]
 try{
  context=await chromium.launchPersistentContext(profilePath,{channel:'chrome',headless:true,viewport:{width:1366,height:768},reducedMotion:'reduce'})
  await context.route('**/api/v1/**',route=>route.fulfill({status:503,json:{code:'GOOGLE_NOT_CONFIGURED',message:'Google sign-in is not configured yet.'}}))
  const settings=await context.newPage(),page=await context.newPage()
  const surface=await context.newCDPSession(page)
  const capture=async name=>{
   await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))))
   const shot=await surface.send('Page.captureScreenshot',{format:'png',fromSurface:true,captureBeyondViewport:false})
   await writeFile(info.outputPath(name),Buffer.from(shot.data,'base64'))
  }
  page.on('pageerror',error=>errors.push(error.message))
  await settings.goto('chrome://settings/appearance')
  const results=[]
  for(const zoom of [1,1.25,2]){
   await settings.locator('#zoomLevel').selectOption(String(zoom))
   for(const path of ['login','register']){
    await page.goto('http://127.0.0.1:5180/'+path);await page.evaluate(()=>document.fonts.ready)
    await expect(page.getByRole('button',{name:'Continue with Google',exact:true})).toBeDisabled()
    const metrics=await page.evaluate(()=>({width:innerWidth,height:innerHeight,dpr:devicePixelRatio,documentHeight:document.documentElement.scrollHeight,documentWidth:document.documentElement.scrollWidth,cssZoom:getComputedStyle(document.documentElement).zoom,transform:getComputedStyle(document.querySelector('.auth-layout')).transform}))
    expect(metrics.dpr).toBeCloseTo(zoom,2)
    expect(metrics.width).toBeCloseTo(1366/zoom,0)
    expect(metrics.documentWidth).toBeLessThanOrEqual(metrics.width+1)
    expect(metrics.cssZoom).toBe('1');expect(metrics.transform).toBe('none')
    // Registration may grow the document; controls must stay reachable at every zoom.
    const outside=await page.locator('.auth-form-panel input,.auth-form-panel button,.auth-form-panel small').evaluateAll(els=>els.filter(e=>{const r=e.getBoundingClientRect();return r.width&&(r.left<0||r.right>innerWidth+1)}).length)
    expect(outside).toBe(0)
    await expect(page.locator('.journey-pass-card-image')).toBeVisible()
    // Chromium's full-page clip uses different CSS/DIP coordinates at browser
    // zoom. Viewport captures record what the real window actually displays.
    await page.evaluate(()=>window.scrollTo({top:0,behavior:'instant'}))
    await capture(`${path}-${zoom*100}-percent-top.png`)
    if(path==='register'&&zoom<=1.25){
     await page.getByLabel('Full name',{exact:true}).fill('Zoom Test Passenger')
     await page.getByLabel('Email address',{exact:true}).fill('zoom@example.com')
     await page.getByRole('button',{name:'Country code:',exact:false}).click()
     await page.getByRole('combobox',{name:'Search country or calling code',exact:true}).fill('Sri Lanka');await page.keyboard.press('Enter')
     await expect(page.getByRole('button',{name:'Country code: Sri Lanka (+94)',exact:true})).toBeFocused()
     await page.getByLabel('Mobile number',{exact:true}).fill('0771234567')
     await page.getByRole('button',{name:'Continue',exact:true}).click()
     await expect(page.getByRole('progressbar',{name:'Registration progress'})).toHaveAttribute('aria-valuenow','2')
    }
    const password=page.getByLabel('Password',{exact:true});await password.scrollIntoViewIfNeeded();await password.focus();await password.fill('TravellyStrong1!')
    await page.getByRole('button',{name:'Show password',exact:true}).click();await expect(password).toHaveAttribute('type','text')
    await page.getByRole('button',{name:'Hide password',exact:true}).click()
    if(path==='register'){
     if(zoom>1.25){
      await page.getByRole('button',{name:'Country code:',exact:false}).click()
      await page.getByRole('combobox',{name:'Search country or calling code',exact:true}).fill('Sri Lanka');await page.keyboard.press('Enter')
      await expect(page.getByRole('button',{name:'Country code: Sri Lanka (+94)',exact:true})).toBeFocused()
     }
     await page.getByRole('checkbox').check();await page.getByRole('button',{name:'Terms',exact:true}).click()
     await expect(page.getByRole('dialog').getByRole('heading',{name:'Terms',exact:true})).toBeVisible();await page.keyboard.press('Escape')
    }
    const nav=page.getByRole('link',{name:path==='login'?'Create an account':'Log in',exact:true}).last();await nav.scrollIntoViewIfNeeded();await nav.focus();await expect(nav).toBeFocused();await expect(nav).toBeInViewport()
    await capture(`${path}-${zoom*100}-percent-actions.png`)
    await page.locator('.journey-pass-card-image').evaluate(e=>e.scrollIntoView({block:'center',behavior:'instant'}))
    await expect(page.locator('.journey-pass-card-image')).toBeInViewport()
    await capture(`${path}-${zoom*100}-percent-promo-card.png`)
    results.push({page:path,zoom:zoom*100,...metrics})
   }
  }
  expect(errors).toEqual([]);await info.attach('actual-browser-zoom',{body:JSON.stringify(results,null,2),contentType:'application/json'})
 }finally{
  try{if(context)await context.close()}finally{await rm(profilePath,{recursive:true,force:true})}
 }
})
