import {test,expect} from '@playwright/test'

const desktopViewports=[[1366,768],[1440,900],[1536,864],[1920,1080]]
const mobileViewports=[[375,812],[390,844]]

test('login and registration fit desktop viewports without page scrolling',async({page})=>{
 await page.emulateMedia({reducedMotion:'reduce'})
 await page.route('**/api/v1/**',route=>route.fulfill({status:503,json:{code:'GOOGLE_NOT_CONFIGURED',message:'Google sign-in is not configured yet.'}}))

 for(const [width,height] of desktopViewports){
  await page.setViewportSize({width,height})
  for(const [path,title,accountLink] of [['/login','Welcome back','Create an account'],['/register','Create your account','Log in']]){
   await page.goto(path)
   await page.evaluate(()=>document.fonts.ready)
   await expect(page.getByRole('heading',{name:title,exact:true})).toBeVisible()
   await expect(page.getByRole('link',{name:accountLink,exact:true}).last()).toBeVisible()
   await expect(page.getByRole('button',{name:'Continue with Google',exact:true})).toBeDisabled()
   const layout=await page.evaluate(()=>({
    viewport:[innerWidth,innerHeight],
    document:[document.documentElement.scrollWidth,document.documentElement.scrollHeight],
    registerColumns:getComputedStyle(document.querySelector('.auth-credentials-form')).gridTemplateColumns,
    labels:[...document.querySelectorAll('.register-page .auth-field>label')].map(label=>getComputedStyle(label).position),
    controls:[...document.querySelectorAll('.auth-form-panel input,.auth-form-panel button,.auth-form-panel a,.auth-form-panel small')]
     .filter(element=>element.getBoundingClientRect().height>0)
     .map(element=>{const rect=element.getBoundingClientRect();return [rect.left,rect.right,rect.top,rect.bottom]})
   }))
   expect(layout.viewport).toEqual([width,height])
   expect(layout.document[0]).toBeLessThanOrEqual(width)
   expect(layout.document[1],`${path} at ${width}x${height}: ${JSON.stringify(layout)}`).toBeLessThanOrEqual(height)
   expect(layout.controls.every(([left,right,top,bottom])=>left>=0&&right<=width+1&&top>=0&&bottom<=height+1),`${path} controls extend outside ${width}x${height}`).toBe(true)
   if(path==='/register'){
    expect(layout.registerColumns.trim().split(/\s+/)).toHaveLength(2)
    expect(layout.labels.every(position=>position==='static')).toBe(true)
    if(height<=864){
     await expect(page.getByRole('progressbar',{name:'Registration progress'})).toHaveAttribute('aria-valuenow','1')
     await page.getByLabel('Full name',{exact:true}).fill('Viewport User')
     await page.getByLabel('Email address',{exact:true}).fill('viewport@example.com')
     await page.getByLabel('Mobile number',{exact:true}).fill('0771234567')
     await page.getByRole('button',{name:'Continue',exact:true}).click()
     await expect(page.getByRole('progressbar',{name:'Registration progress'})).toHaveAttribute('aria-valuenow','2')
     await expect(page.getByRole('button',{name:'Create account',exact:true})).toBeVisible()
     const secondStep=await page.evaluate(()=>({height:document.documentElement.scrollHeight,viewport:innerHeight,controls:[...document.querySelectorAll('.auth-form-panel input,.auth-form-panel button,.auth-form-panel a,.auth-form-panel small')].filter(element=>element.getBoundingClientRect().height>0).map(element=>{const rect=element.getBoundingClientRect();return [rect.left,rect.right,rect.top,rect.bottom]})}))
     expect(secondStep.height).toBeLessThanOrEqual(height)
     expect(secondStep.controls.every(([left,right,top,bottom])=>left>=0&&right<=width+1&&top>=0&&bottom<=height+1)).toBe(true)
     await page.getByRole('button',{name:'Back',exact:true}).click()
     await expect(page.getByLabel('Full name',{exact:true})).toHaveValue('Viewport User')
     await expect(page.getByLabel('Email address',{exact:true})).toHaveValue('viewport@example.com')
     await expect(page.getByLabel('Mobile number',{exact:true})).toHaveValue('0771234567')
     await page.getByRole('button',{name:'Continue',exact:true}).click()
    }
   }
  }
 }
})

test('auth pages retain natural scrolling on mobile without horizontal overflow',async({page})=>{
 await page.emulateMedia({reducedMotion:'reduce'})
 await page.route('**/api/v1/**',route=>route.fulfill({status:503,json:{code:'GOOGLE_NOT_CONFIGURED',message:'Google sign-in is not configured yet.'}}))

 for(const [width,height] of mobileViewports){
  await page.setViewportSize({width,height})
  for(const [path,submitName] of [['/login','Log in'],['/register','Create account']]){
   await page.goto(path)
   await expect(page.getByRole('button',{name:submitName,exact:false})).toBeVisible()
   await page.locator('.auth-submit').scrollIntoViewIfNeeded()
   const bounds=await page.evaluate(()=>({
    viewport:[innerWidth,innerHeight],
    documentWidth:document.documentElement.scrollWidth,
    controls:[...document.querySelectorAll('.auth-form-panel input,.auth-form-panel button,.auth-form-panel a')]
     .map(element=>{const rect=element.getBoundingClientRect();return [rect.left,rect.right]})
   }))
   expect(bounds.viewport[0]).toBe(width)
   expect(bounds.documentWidth).toBeLessThanOrEqual(width)
   expect(bounds.controls.every(([left,right])=>left>=0&&right<=width+1)).toBe(true)
  }
 }
})

test('registration validation messages remain readable in the desktop viewport',async({page})=>{
 await page.setViewportSize({width:1366,height:768})
 await page.emulateMedia({reducedMotion:'reduce'})
 await page.route('**/api/v1/**',route=>route.fulfill({status:503,json:{code:'GOOGLE_NOT_CONFIGURED',message:'Google sign-in is not configured yet.'}}))
 await page.goto('/register')
 await expect(page.getByRole('button',{name:'Continue with Google',exact:true})).toBeDisabled()
 await page.getByRole('button',{name:'Continue',exact:true}).click()
 for(const message of ['Enter your full name.','Enter a valid public email address, such as name@example.com, without spaces inside it.']){
  await expect(page.getByText(message,{exact:true})).toBeVisible()
 }
 let layout=await page.evaluate(()=>({height:document.documentElement.scrollHeight,errors:[...document.querySelectorAll('.field-error')].map(error=>{const rect=error.getBoundingClientRect();return [rect.left,rect.right,rect.top,rect.bottom]})}))
 expect(layout.height).toBeLessThanOrEqual(768)
 expect(layout.errors.every(([left,right,top,bottom])=>left>=0&&right<=1367&&top>=0&&bottom<=768)).toBe(true)

 await page.getByLabel('Full name',{exact:true}).fill('Viewport User')
 await page.getByLabel('Email address',{exact:true}).fill('viewport@example.com')
 await page.getByLabel('Mobile number',{exact:true}).fill('0771234567')
 await page.getByRole('button',{name:'Continue',exact:true}).click()
 await page.getByLabel('Password',{exact:true}).fill('weak')
 await page.getByLabel('Confirm password',{exact:true}).fill('different')
 await page.getByRole('button',{name:'Create account',exact:true}).click()

 for(const message of ['Your passwords do not match.','Agree to the Terms and Privacy Policy to continue.']){
  await expect(page.getByText(message,{exact:true})).toBeVisible()
 }
 await expect(page.locator('.auth-field .field-error').filter({hasText:'Use at least 12 characters.'})).toBeVisible()
 layout=await page.evaluate(()=>({
  viewport:[innerWidth,innerHeight],
  document:[document.documentElement.scrollWidth,document.documentElement.scrollHeight],
  errors:[...document.querySelectorAll('.field-error')].map(error=>{const rect=error.getBoundingClientRect();return [rect.left,rect.right,rect.top,rect.bottom]})
 }))
 expect(layout.document[0]).toBeLessThanOrEqual(1366)
 expect(layout.document[1]).toBeLessThanOrEqual(768)
 expect(layout.errors.every(([left,right,top,bottom])=>left>=0&&right<=1367&&top>=0&&bottom<=768)).toBe(true)
})

test('compact registration submits the unchanged account payload',async({page})=>{
 await page.setViewportSize({width:1366,height:768})
 let registration
 await page.route('**/api/v1/**',route=>{
  if(new URL(route.request().url()).pathname.endsWith('/auth/register')){
   registration=route.request().postDataJSON()
   return route.fulfill({status:201,json:{status:'verification_required',verification_ticket:'v'.repeat(43),email_delivery:'captured'}})
  }
  return route.fulfill({status:503,json:{code:'GOOGLE_NOT_CONFIGURED',message:'Google sign-in is not configured yet.'}})
 })
 await page.goto('/register')
 await page.getByLabel('Full name',{exact:true}).fill('Viewport User')
 await page.getByLabel('Email address',{exact:true}).fill('viewport@example.com')
 await page.getByLabel('Mobile number',{exact:true}).fill('0771234567')
 await page.getByRole('button',{name:'Continue',exact:true}).click()
 await page.getByLabel('Password',{exact:true}).fill('TravellyStrong1!')
 await page.getByLabel('Confirm password',{exact:true}).fill('TravellyStrong1!')
 await page.getByRole('checkbox').check()
 await page.getByRole('button',{name:'Create account',exact:true}).click()
 await expect(page).toHaveURL(/\/check-email$/)
 expect(registration).toMatchObject({
  full_name:'Viewport User',
  email:'viewport@example.com',
  phone_e164:'+94771234567',
  password:'TravellyStrong1!',
  preferred_language:'en',
  accept_terms:true
 })
 expect(registration).not.toHaveProperty('confirm_password')
})

test('landing booking panel follows the hero and stays usable after scrolling',async({page})=>{
 await page.emulateMedia({reducedMotion:'reduce'})
 for(const [width,height] of [...desktopViewports,...mobileViewports]){
  await page.setViewportSize({width,height})
  await page.goto('/')
  await page.evaluate(()=>document.fonts.ready)
  await expect(page.getByRole('heading',{name:'One account. Every way to travel.',exact:true})).toBeVisible()
  await expect(page.getByRole('region',{name:'Plan your journey'})).toBeVisible()
  const boundary=await page.evaluate(()=>({
   heroBottom:document.querySelector('.passenger-hero').getBoundingClientRect().bottom,
   searchTop:document.querySelector('.search-panel').getBoundingClientRect().top
  }))
  // The current public layout keeps the search card below the full-height hero.
  expect(boundary.searchTop).toBeGreaterThanOrEqual(boundary.heroBottom)
  await page.getByRole('region',{name:'Plan your journey'}).scrollIntoViewIfNeeded()
  const layout=await page.evaluate(()=>({
   viewport:[innerWidth,innerHeight],
   documentWidth:document.documentElement.scrollWidth,
   search:document.querySelector('.search-panel').getBoundingClientRect().toJSON(),
   controls:[...document.querySelectorAll('.search-panel button,.search-panel input,.search-panel select')]
    .map(element=>{const rect=element.getBoundingClientRect();return [rect.left,rect.right,rect.top,rect.bottom]})
  }))
  expect(layout.viewport).toEqual([width,height])
  expect(layout.documentWidth).toBeLessThanOrEqual(width)
  expect(layout.search.left).toBeGreaterThanOrEqual(0)
  expect(layout.search.right).toBeLessThanOrEqual(width+1)
  expect(layout.search.bottom).toBeLessThanOrEqual(height+1)
  expect(layout.controls.every(([left,right,top,bottom])=>left>=0&&right<=width+1&&top>=0&&bottom<=height+1)).toBe(true)
 }
})
