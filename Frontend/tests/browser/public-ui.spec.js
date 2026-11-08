import {test,expect} from '@playwright/test'
for(const width of [1920,1440,1024,768,390,360])test(`public typography and hero actions remain clear at ${width}px`,async({page},info)=>{
 await page.setViewportSize({width,height:900});await page.emulateMedia({reducedMotion:'reduce'})
 for(const path of ['/','/for-owners','/drive-with-us']){
  await page.goto(path);await page.evaluate(()=>document.fonts.ready)
  await expect(page.locator('.hero h1')).toBeVisible()
  expect(await page.locator('.hero h1').evaluate(el=>getComputedStyle(el).fontWeight)).toBe(path==='/'?'800':'600')
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
  for(const button of await page.locator('.hero-actions a').all()){
   await button.scrollIntoViewIfNeeded()
   const clear=await button.evaluate(el=>{const r=el.getBoundingClientRect();return [[r.left+5,r.top+5],[r.right-5,r.bottom-5]].every(([x,y])=>el.contains(document.elementFromPoint(x,y)))})
   expect(clear,'The complete hero action must remain clear of later sections.').toBe(true)
  }
  await page.locator('.hero').screenshot({path:info.outputPath((path==='/'?'passenger':path.slice(1))+'.png')})
 }
})
