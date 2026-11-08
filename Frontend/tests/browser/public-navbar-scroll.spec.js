import {test,expect} from '@playwright/test'

test('public navbar stays centered and fixed while content scrolls',async({page},info)=>{
 for(const width of [1920,1366,1024,390]){
  await page.setViewportSize({width,height:900})
  for(const path of ['/','/for-owners','/drive-with-us']){
   await page.goto(path)
   await page.emulateMedia({reducedMotion:'reduce'})
   const bar=page.locator('.public-page > .site-header .header-inner')
   const before=await bar.boundingBox()
   expect(before.width).toBeLessThanOrEqual(1440)
   expect(Math.abs(before.x-(width-before.width)/2)).toBeLessThan(2)
   await page.evaluate(()=>window.scrollTo({top:500,behavior:'instant'}))
   expect(await page.evaluate(()=>scrollY)).toBeGreaterThan(0)
   const after=await bar.boundingBox()
   expect(Math.abs(after.y-before.y)).toBeLessThan(1)
   expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(width)
   if(width<1200){
    await page.getByRole('button',{name:'Open navigation',exact:true}).click()
    await expect(page.getByRole('navigation',{name:'Main navigation'})).toBeVisible()
   }
   if(width===1920&&path==='/')await page.screenshot({path:info.outputPath('navbar-scrolled-desktop.png')})
  }
 }
})
