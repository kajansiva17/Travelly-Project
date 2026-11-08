import {test,expect} from '@playwright/test'

test.use({video:'on'})

async function setup(page,width=1440){
 await page.setViewportSize({width,height:900})
 await page.emulateMedia({reducedMotion:'no-preference'})
 await page.route('**/api/v1/**',route=>route.fulfill({status:503,json:{code:'GOOGLE_NOT_CONFIGURED',message:'Google sign-in is not configured yet.'}}))
 await page.goto('/')
 const brand=page.getByRole('link',{name:'Travelly home',exact:true})
 const dial=brand.locator('.brand-speedometer-dial')
 const needle=brand.locator('.brand-gauge-needle')
 await expect(dial).toBeVisible()
 await expect(needle).toBeVisible()
 await expect(brand.locator('.brand-speedometer-dial')).toHaveCount(1)
 await expect(brand.locator('.brand-gauge-needle')).toHaveCount(1)
 return {brand,dial,needle}
}

async function expectRev(page,brand,needle){
 await expect(brand.locator('.brand-mark')).toHaveClass(/is-revving/)
 const state=await needle.evaluate(async element=>{
  await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))
  const animation=element.getAnimations().find(item=>item.animationName==='travelly-navbar-speed-rev')
  const matrix=new DOMMatrixReadOnly(getComputedStyle(element).transform)
  return{duration:animation?.effect?.getTiming().duration,angle:Math.round(Math.atan2(matrix.b,matrix.a)*180/Math.PI)}
 })
 expect(state.duration).toBe(800)
 expect(state.angle).toBeGreaterThan(-132)
 expect(state.angle).toBeLessThanOrEqual(0)
}

async function expectResting(needle){
 await expect.poll(()=>needle.evaluate(element=>{
  const matrix=new DOMMatrixReadOnly(getComputedStyle(element).transform)
  return Math.round(Math.atan2(matrix.b,matrix.a)*180/Math.PI)
 })).toBe(-132)
}

test('navbar hover and keyboard focus rev the single logo needle',async({page})=>{
 const {brand,needle}=await setup(page)
 await expect(needle).not.toHaveCSS('animation-name','travelly-navbar-speed-rev')
 const home=page.getByRole('navigation',{name:'Main navigation'}).getByRole('link',{name:'Home',exact:true})
 await home.hover()
 await expectRev(page,brand,needle)
 await expect(brand).toBeVisible()
 await page.mouse.move(0,0)
 await expectResting(needle)
 await expect(brand.locator('.brand-mark')).not.toHaveClass(/is-revving/)
 await page.keyboard.press('Tab')
 await expect(page.getByRole('link',{name:'Skip to content'})).toBeFocused()
 await page.keyboard.press('Tab')
 await page.keyboard.press('Tab')
 await expect(home).toBeFocused()
 await expectRev(page,brand,needle)
})

test('navbar click and touch tap trigger the needle without changing navigation',async({page})=>{
 const {brand,needle}=await setup(page)
 const action=page.getByRole('navigation',{name:'Main navigation'}).getByRole('link',{name:'Find a ride',exact:true})
 await action.click()
 await expectRev(page,brand,needle)
 await expect(page).toHaveURL(/\/#search$/)

 const context=await page.context().browser().newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true})
 try{
  const mobile=await context.newPage()
  await mobile.route('**/api/v1/**',route=>route.fulfill({status:503,json:{code:'GOOGLE_NOT_CONFIGURED',message:'Google sign-in is not configured yet.'}}))
  await mobile.goto('http://127.0.0.1:5180/')
  const toggle=mobile.getByRole('button',{name:'Open navigation',exact:true})
  await toggle.click()
  const ride=mobile.getByRole('navigation',{name:'Main navigation'}).getByRole('link',{name:'Find a ride',exact:true})
  await ride.tap()
  await expectRev(mobile,mobile.getByRole('link',{name:'Travelly home',exact:true}),mobile.locator('.brand-gauge-needle'))
  await expect(mobile).toHaveURL(/\/#search$/)
 }finally{
  await context.close()
 }
})

test('reduced motion keeps the dial and needle static across navigation focus',async({page})=>{
 const {needle}=await setup(page)
 await page.emulateMedia({reducedMotion:'reduce'})
 await page.getByRole('navigation',{name:'Main navigation'}).getByRole('link',{name:'Home',exact:true}).focus()
 await page.getByRole('navigation',{name:'Main navigation'}).getByRole('link',{name:'Find a ride',exact:true}).click()
 await page.waitForTimeout(900)
 const state=await needle.evaluate(element=>({animations:element.getAnimations().length,transform:getComputedStyle(element).transform}))
 expect(state.animations).toBe(0)
 expect(state.transform).toBe('matrix(-0.669131, -0.743145, 0.743145, -0.669131, 0, 0)')
})

test('navbar logo fits without changing header geometry on desktop and mobile',async({page})=>{
 for(const width of [1920,1440,1024,768,390,360]){
  const {brand,needle}=await setup(page,width)
  await expect(needle).not.toHaveCSS('animation-name','travelly-navbar-speed-rev')
  const geometry=await page.evaluate(()=>{
   const header=document.querySelector('.site-header').getBoundingClientRect()
   const mark=document.querySelector('.site-header .brand-mark').getBoundingClientRect()
   const navigation=document.querySelector('.site-header .navigation').getBoundingClientRect()
   const toggle=document.querySelector('.site-header .menu-toggle')
   const navTarget=toggle&&getComputedStyle(toggle).display!=='none'?toggle:document.querySelector('.site-header .navigation')
   const navTargetRect=navTarget.getBoundingClientRect()
   const wordmark=document.querySelector('.brand-wordmark-art').getBoundingClientRect()
   return{viewport:innerWidth,scrollWidth:document.documentElement.scrollWidth,headerHeight:header.height,markHeight:mark.height,brandRight:mark.right,navLeft:navTargetRect.left,wordmark:wordmark.toJSON(),navigation:navigation.toJSON()}
  })
  expect(geometry.viewport).toBe(width)
  expect(geometry.scrollWidth).toBeLessThanOrEqual(width)
  expect(geometry.markHeight).toBeLessThanOrEqual(54)
  expect(geometry.brandRight).toBeLessThanOrEqual(geometry.navLeft+1)
  await expect(brand.locator('.brand-speedometer-dial')).toHaveCount(1)
 }
})

test('captures desktop, mobile, reduced-motion and needle animation proof',async({page},testInfo)=>{
 const {needle}=await setup(page,1440)
 await page.locator('.site-header').screenshot({path:testInfo.outputPath('navbar-desktop.png')})
 await page.getByRole('navigation',{name:'Main navigation'}).getByRole('link',{name:'Home',exact:true}).hover()
 await expectRev(page,page.getByRole('link',{name:'Travelly home',exact:true}),needle)
 await page.waitForTimeout(300)
 await page.locator('.site-header').screenshot({path:testInfo.outputPath('navbar-revving.png'),animations:'allow'})
 await page.waitForTimeout(600)
 await expectResting(needle)
 await page.emulateMedia({reducedMotion:'reduce'})
 await page.evaluate(()=>document.activeElement?.blur())
 await page.mouse.move(0,0)
 await page.waitForTimeout(900)
 await page.locator('.site-header').screenshot({path:testInfo.outputPath('navbar-reduced-motion.png')})
 await page.setViewportSize({width:390,height:844})
 await page.locator('.site-header').screenshot({path:testInfo.outputPath('navbar-mobile.png')})
})
