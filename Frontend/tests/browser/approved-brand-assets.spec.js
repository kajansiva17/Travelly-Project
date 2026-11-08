import { test, expect } from '@playwright/test'
import { setup, visit } from './helpers/redesign.js'

const files='/images/travelly/branding/approved-2026-11-07/'
for(const [role,path] of [['Passenger','/dashboard'],['Owner','/owner/dashboard'],['Driver','/driver/dashboard'],['Admin','/admin/dashboard']]){
 for(const width of [1366,390])test(`${role} shared supplied brand fits ${width}px without changing navigation`,async({page},testInfo)=>{
  await page.setViewportSize({width,height:900})
  await page.emulateMedia({reducedMotion:'reduce'})
  await setup(page)
  await visit(page,path)
  await expect(page.locator(role==='Passenger'?'.passenger-dashboard h1':'.overview-banner h1')).toBeVisible()
  await page.evaluate(()=>document.fonts.ready)
  const brand=page.locator('.site-header .travelly-brand')
  await expect(brand).toBeVisible()
  for(const [selector,file]of [['.brand-wordmark-art','wordmark.png'],['.brand-speedometer-dial','meter-dial.png'],['.brand-gauge-needle','meter-needle.png']]){
   const image=brand.locator(selector)
   await expect(image).toHaveAttribute('src',files+file)
   await expect.poll(()=>image.evaluate(el=>el.complete&&el.naturalWidth>0)).toBe(true)
  }
  const bounds=await brand.evaluate(el=>{
   const header=el.closest('header').getBoundingClientRect(),box=el.getBoundingClientRect(),mark=el.querySelector('.brand-mark').getBoundingClientRect()
   const gauge=el.querySelector('.brand-speedometer'),needle=el.querySelector('.brand-gauge-needle'),hub=el.querySelector('.brand-gauge-hub')
   const origin=getComputedStyle(needle).transformOrigin.split(' ').map(parseFloat),g=gauge.getBoundingClientRect(),h=hub.getBoundingClientRect()
   return{overflow:document.documentElement.scrollWidth>innerWidth,markHeight:mark.height,inside:box.left>=0&&box.right<=innerWidth&&mark.top>=header.top&&mark.bottom<=header.bottom,pivotX:Math.abs(g.left+needle.offsetLeft+origin[0]-(h.left+h.width/2)),pivotY:Math.abs(g.top+needle.offsetTop+origin[1]-(h.top+h.height/2))}
  })
  expect(bounds.overflow).toBe(false)
  expect(bounds.inside).toBe(true)
  expect(bounds.markHeight).toBeLessThanOrEqual(54)
  expect(bounds.pivotX).toBeLessThan(1)
  expect(bounds.pivotY).toBeLessThan(1)
  await page.locator('.site-header').screenshot({path:testInfo.outputPath(`${role.toLowerCase()}-brand-${width}.png`)})
  await expect(page.locator(role==='Passenger'?'.passenger-dashboard':'.workspace-shell')).toBeVisible()
 })
}

test('public role icons and transparent brand artwork use the supplied files',async({page})=>{
 for(const [path,logo]of [['/','standard'],['/for-owners','standard'],['/drive-with-us','driver']]){
  await page.goto(path)
  await expect(page.locator('.lr-logo img')).toHaveAttribute('src',`${files}${logo}-logo.png`)
  await expect(page.locator('.lr-footer img')).toHaveAttribute('src',`${files}${logo}-logo.png`)
  for(const name of ['drivers','owners'])await expect(page.locator(`.lr-role-icon[src$="${name}-icon.png"]`)).toHaveCount(1)
  await expect(page.locator('.lr-logo img')).toHaveCSS('filter','none')
  await expect(page.locator('.lr-logo img')).toHaveCSS('mix-blend-mode','normal')
  await expect(page.locator('.lr-hero-scene')).toHaveCount(1)
  await expect(page.locator('.lr-hero-regions')).toHaveCount(0)
  await expect(page.locator('.lr-hero-scene')).toHaveCSS('object-fit','cover')
  await expect(page.locator('.lr-hero-scene')).toHaveCSS('filter','none')
  await expect(page.locator('.lr-hero-copy')).toHaveCSS('background-color','rgba(0, 0, 0, 0)')
  await expect(page.locator('.lr-hero-copy')).toHaveCSS('backdrop-filter','none')
  const coverage=await page.locator('.lr-hero-art').evaluate(el=>{const r=el.getBoundingClientRect();return Math.abs(r.left)<1&&Math.abs(r.width-innerWidth)<1})
  expect(coverage).toBe(true)
 }
})

test('supplied glossy needle keeps existing hover and reduced-motion behavior',async({page})=>{
 await setup(page)
 await visit(page,'/dashboard')
 await expect(page.locator('.passenger-dashboard h1')).toBeVisible()
 await page.emulateMedia({reducedMotion:'no-preference'})
 const needle=page.locator('.site-header .brand-gauge-needle')
 const angle=()=>needle.evaluate(el=>{const m=new DOMMatrixReadOnly(getComputedStyle(el).transform);return Math.atan2(m.b,m.a)*180/Math.PI})
 await page.locator('.site-header .language select').hover()
 await expect.poll(angle).toBeGreaterThan(-100)
 await page.mouse.move(0,300)
 await expect.poll(async()=>Math.abs(await angle()+132)).toBeLessThan(1)
 await page.emulateMedia({reducedMotion:'reduce'})
 await page.locator('.site-header .language select').hover()
 await expect.poll(async()=>Math.abs(await angle()+132)).toBeLessThan(.1)
})
