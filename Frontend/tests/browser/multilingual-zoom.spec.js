import {test,expect,chromium} from '@playwright/test'
import {mkdtemp,rm} from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'

test('all languages retain usable navigation and auth at actual Chrome 90, 100, 110 and 125 percent zoom',async({},info)=>{
  test.setTimeout(180000)
  const profilePath=await mkdtemp(path.join(os.tmpdir(),'travelly-language-zoom-'))
  let context
  try {
    context=await chromium.launchPersistentContext(profilePath,{channel:'chrome',headless:true,viewport:{width:1366,height:768},reducedMotion:'reduce'})
    await context.route('**/api/v1/**',r=>r.fulfill({status:503,json:{code:'GOOGLE_NOT_CONFIGURED'}}))
    const settings=await context.newPage(),page=await context.newPage()
    await settings.goto('chrome://settings/appearance')
    const results=[]
    for(const zoom of [0.9,1,1.1,1.25]) {
      await settings.locator('#zoomLevel').selectOption(String(zoom))
      for(const language of ['en','ta','si']) for(const route of ['/','/login','/register']) {
        await page.goto('http://127.0.0.1:5180'+route)
        await page.evaluate(code=>{localStorage.setItem('travelly-language',code)},language)
        await page.reload();await page.evaluate(()=>document.fonts.ready)
        await expect(page.locator('html')).toHaveAttribute('lang',language)
        if(route!=='/')await expect(page.locator('.google-sign-in .google-button-unavailable')).toBeVisible()
        const dimensions=await page.evaluate(()=>({width:innerWidth,dpr:devicePixelRatio,scroll:document.documentElement.scrollWidth,cssZoom:getComputedStyle(document.documentElement).zoom}))
        expect(dimensions.dpr).toBeCloseTo(zoom,2)
        expect(dimensions.cssZoom).toBe('1')
        expect(dimensions.scroll).toBeLessThanOrEqual(dimensions.width+1)
        const desktop=dimensions.width>=(route==='/'?1280:1024)
        await expect(page.locator('.menu-toggle'))[desktop?'toBeHidden':'toBeVisible']()
        if(!desktop)await page.locator('.menu-toggle').click()
        await expect(page.locator('.language select')).toBeVisible()
        const overflow=await page.locator('.navigation > a,.navigation > button,.navigation > .language').evaluateAll(nodes=>nodes.filter(n=>{const r=n.getBoundingClientRect();return r.width&&(r.left<0||r.right>innerWidth+1||n.scrollWidth>n.clientWidth+2)}).map(n=>n.textContent))
        expect(overflow).toEqual([])
        if(!desktop)await page.keyboard.press('Escape')
        if(route!=='/'){
          await page.locator('.auth-submit').scrollIntoViewIfNeeded()
          await expect(page.locator('.auth-submit')).toBeInViewport()
          await page.locator('.google-sign-in').scrollIntoViewIfNeeded()
          await expect(page.locator('.google-sign-in button').first()).toBeInViewport()
        }
        results.push({zoom,language,route,...dimensions})
      }
    }
    await info.attach('actual-zoom-matrix',{body:JSON.stringify(results,null,2),contentType:'application/json'})
  } finally {
    if(context)await context.close()
    // Only the fresh random profile created above is removed, never a user profile.
    if(path.dirname(path.resolve(profilePath))!==path.resolve(os.tmpdir())||!path.basename(profilePath).startsWith('travelly-language-zoom-'))throw new Error('Unexpected temporary profile path')
    await rm(profilePath,{recursive:true,force:true})
  }
})
