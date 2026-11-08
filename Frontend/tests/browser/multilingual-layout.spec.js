import { test, expect } from '@playwright/test'
import { translate } from '../../src/i18n/language.js'

const sizes = [[1920,1080],[1536,864],[1366,768],[1280,800],[1024,768],[768,1024],[375,812],[390,844]]

async function stubGoogle(page) {
  await page.route('**/api/v1/**', route => route.fulfill({ status:503, json:{code:'AUTH_DEPENDENCY_UNAVAILABLE',message:'Service temporarily unavailable.'} }))
}

async function bounds(page, selector) {
  return page.locator(selector).evaluateAll(nodes => nodes.filter(n => n.getClientRects().length).map(n => {
    const r=n.getBoundingClientRect()
    return {text:n.textContent.slice(0,80),left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:n.clientWidth,scroll:n.scrollWidth}
  }))
}

for (const code of ['en','ta','si']) for (const [width,height] of sizes) {
  test(`${code} navigation, cards and auth fit ${width}x${height}`, async ({page},info) => {
    await page.setViewportSize({width,height})
    await page.emulateMedia({reducedMotion:'reduce'})
    await page.addInitScript(code => localStorage.setItem('travelly-language',code), code)
    await stubGoogle(page)
    for (const path of ['/','/login','/register']) {
      await page.goto(path)
      await page.evaluate(() => document.fonts.ready)
      await expect(page.locator('html')).toHaveAttribute('lang',code)
      if(path!=='/') await expect(page.locator('.google-sign-in .google-button-unavailable')).toBeVisible()
      const desktop=path==='/'?width>=1280:width>=1024
      await expect(page.locator('.menu-toggle'))[desktop?'toBeHidden':'toBeVisible']()
      if (!desktop) await page.locator('.menu-toggle').click()
      await expect(page.locator('.navigation')).toBeVisible()
      const controls=await bounds(page,'.navigation > a,.navigation > button,.navigation > .language')
      const nav=await page.locator('.navigation').boundingBox()
      expect(controls.filter(r=>r.left<nav.x-1||r.right>nav.x+nav.width+1),JSON.stringify(controls)).toEqual([])
      expect(controls.filter(r=>r.scroll>r.width+2),JSON.stringify(controls)).toEqual([])
      // No pair of visible navigation controls may overlap.
      for(let i=0;i<controls.length;i++) for(let j=i+1;j<controls.length;j++) {
        const a=controls[i],b=controls[j]
        expect(a.left<b.right-1&&a.right>b.left+1&&a.top<b.bottom-1&&a.bottom>b.top+1,JSON.stringify([a,b])).toBe(false)
      }
      if(!desktop) {
        const background=await page.locator('.navigation').evaluate(n=>getComputedStyle(n).backgroundImage+' '+getComputedStyle(n).backgroundColor)
        expect(background).not.toContain('252, 242, 229')
        await page.keyboard.press('Escape')
        if(await page.locator('.navigation').isVisible())await page.locator('.menu-toggle').click()
      }
      const dimensions=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,height:innerHeight,scrollHeight:document.documentElement.scrollHeight}))
      expect(dimensions.scroll,JSON.stringify(dimensions)).toBeLessThanOrEqual(width+1)
      if(path!=='/'&&width>=1366) expect(dimensions.scrollHeight,JSON.stringify(dimensions)).toBeLessThanOrEqual(height+1)
      const cards=await bounds(page,'.service-card,.benefit-card,.service-card>div,.benefit-card>div,.auth-form-panel')
      expect(cards.filter(r=>r.left<0||r.right>width+1||r.scroll>r.width+2),JSON.stringify(cards)).toEqual([])
      if(width===1366||width===390)await page.screenshot({path:info.outputPath(`${code}-${path==='/'?'home':path.slice(1)}-${width}.png`),fullPage:true})
    }
  })
}

test('language changes preserve login fields, checkbox, password visibility and translated errors',async({page})=>{
  await page.setViewportSize({width:1366,height:768});await stubGoogle(page);await page.goto('/login')
  await page.locator('#identifier').fill('language@example.com');await page.locator('#password').fill('typed-password')
  await page.locator('.visibility').click();await page.locator('.login-options input').check()
  await page.locator('.auth-submit').click();await expect(page.locator('.notice.error')).toBeVisible()
  for(const code of ['ta','si','en']) {
    await page.locator('.language select').selectOption(code)
    await expect(page.locator('#identifier')).toHaveValue('language@example.com')
    await expect(page.locator('#password')).toHaveValue('typed-password')
    await expect(page.locator('#password')).toHaveAttribute('type','text')
    await expect(page.locator('.login-options input')).toBeChecked()
    await expect(page.locator('.notice.error')).toHaveText(translate('Service temporarily unavailable.',code))
    await expect(page.locator('.visibility')).toHaveAttribute('aria-label',translate('Hide password',code))
  }
})

test('compact registration retains both steps and translates each password requirement after switching',async({page})=>{
  await page.setViewportSize({width:1366,height:768});await stubGoogle(page);await page.goto('/register')
  await page.locator('#full_name').fill('Language Fixture');await page.locator('#email').fill('fixture@example.com')
  await page.locator('#national_phone').fill('0771234567');await page.locator('.auth-submit').click()
  await page.locator('#password').fill('weak');await page.locator('#confirm_password').fill('different')
  await page.locator('.auth-submit').click()
  for(const code of ['ta','si','en']){
    await page.locator('.language select').selectOption(code)
    await expect(page.locator('#password-error')).toContainText(translate('Use at least 12 characters.',code))
    await expect(page.locator('#password-error')).toContainText(translate('Add an uppercase letter.',code))
    await expect(page.locator('#confirm_password-error')).toHaveText(translate('Your passwords do not match.',code))
    await expect(page.locator('#password')).toHaveValue('weak')
    await expect(page.locator('.registration-progress-track')).toHaveAttribute('aria-valuenow','2')
  }
  await page.locator('.registration-back').click()
  await expect(page.locator('#full_name')).toHaveValue('Language Fixture')
  await expect(page.locator('#email')).toHaveValue('fixture@example.com')
  await expect(page.locator('#national_phone')).toHaveValue('0771234567')
})
