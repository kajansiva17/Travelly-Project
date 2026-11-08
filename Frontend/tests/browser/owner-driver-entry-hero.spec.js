import {test,expect} from '@playwright/test'

test('public Owner and Driver entry pages use their hero assets without disturbing content or routes',async({page},testInfo)=>{
 for(const [role,path,asset,onboarding,signIn] of [
  ['owner','/for-owners','/images/travelly/heroes/owner-hero-1920.webp','/owner/onboarding','/login'],
  ['driver','/drive-with-us','/images/travelly/heroes/driver-hero-1920.webp','/driver/onboarding','/login'],
 ]){
  for(const [size,width,height] of [['desktop',1440,900],['mobile',390,844]]){
   await page.setViewportSize({width,height})
   await page.goto(path)
   await page.evaluate(()=>document.fonts.ready)

   const art=page.locator(`.${role}-hero-art`)
   const image=art.locator('img')
   await expect(image).toHaveAttribute('src',asset)
   await expect(image).toHaveJSProperty('complete',true)
   expect(await image.evaluate(node=>node.naturalWidth)).toBeGreaterThan(0)
   expect(await image.evaluate(node=>getComputedStyle(node).objectFit)).toBe('cover')
   expect(await art.evaluate(node=>getComputedStyle(node).overflow)).toBe('hidden')
   expect(await image.evaluate(node=>getComputedStyle(node).filter)).toBe('none')
   expect(await art.evaluate(node=>getComputedStyle(node,'::after').content)).toBe('none')
   expect(await art.evaluate(node=>getComputedStyle(node).clipPath)).toBe('none')
   await expect(page.locator(`.${role}-hero-art img[src*="hero-fleet.png"], .${role}-hero-art img[src*="driver-hero.png"]`)).toHaveCount(0)

   const actions=page.locator('.hero-actions')
   await expect(actions.locator('a').first()).toHaveAttribute('href',onboarding)
   await expect(actions.locator('a').nth(1)).toHaveAttribute('href',signIn)

   const layout=await page.evaluate(()=>{
    const hero=document.querySelector('.hero')
    const art=document.querySelector('[class$="-hero-art"]')
    const image=art.querySelector('img')
    const actions=document.querySelector('.hero-actions')
    const width=innerWidth
    const artRect=art.getBoundingClientRect()
    const actionRect=actions.getBoundingClientRect()
    return {scrollWidth:document.documentElement.scrollWidth,heroHeight:hero.getBoundingClientRect().height,artRect:{left:artRect.left,right:artRect.right,top:artRect.top,bottom:artRect.bottom},actionRect:{top:actionRect.top,bottom:actionRect.bottom},naturalRatio:image.naturalWidth/image.naturalHeight,renderedRatio:image.getBoundingClientRect().width/image.getBoundingClientRect().height}
   })
   expect(layout.scrollWidth).toBeLessThanOrEqual(width)
   expect(layout.heroHeight).toBeGreaterThan(0)
   expect(layout.artRect.left).toBeGreaterThanOrEqual(0)
   expect(layout.artRect.right).toBeLessThanOrEqual(width)
   expect(layout.naturalRatio).toBeGreaterThan(1)
   if(size==='desktop') {
    expect(layout.artRect.top).toBe(0)
    expect(layout.artRect.right-layout.artRect.left).toBe(width)
    expect(layout.artRect.bottom-layout.artRect.top).toBe(layout.heroHeight)
   }
   if(size==='mobile') expect(layout.artRect.top).toBeGreaterThanOrEqual(layout.actionRect.bottom)

   await page.locator('.hero').screenshot({path:testInfo.outputPath(`${role}-after-${size}.png`)})
  }
 }
})
