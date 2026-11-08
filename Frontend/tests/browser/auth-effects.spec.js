import {test,expect} from '@playwright/test'

test('Google retry and responsive auth content remain reachable with reduced motion',async({page})=>{
 await page.emulateMedia({reducedMotion:'reduce'})
 await page.route('**/api/v1/**',r=>r.fulfill({status:503,json:{code:'GOOGLE_UNAVAILABLE',message:'Google sign-in is temporarily unavailable. Use email or try again.'}}))
 for(const width of [1440,768,320])for(const path of ['login','register']){
  await page.setViewportSize({width,height:740});await page.goto('/'+path)
  const retry=page.getByRole('button',{name:'Retry Google sign-in',exact:true});await retry.scrollIntoViewIfNeeded();await expect(retry).toBeInViewport()
  const submit=page.getByRole('button',{name:path==='login'?'Log in':width>=1024?'Continue':'Create account',exact:true});await submit.scrollIntoViewIfNeeded();await expect(submit).toBeInViewport()
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
  await expect(page.locator('.journey-pass-card-image')).toHaveAttribute('src','/images/travelly/auth/journey-pass-card.png')
  await expect(page.locator('.journey-pass-frame')).toHaveCount(1)
  await expect(page.locator('.journey-pass-frame img')).toHaveCount(1)
  await expect(page.locator('.journey-pass-frame :is(.journey-ticket,.ticket-vehicles,.ticket-steps,.ticket-light,.ticket-services,.ticket-tagline,.ticket-perimeter)')).toHaveCount(0)
  expect(await page.locator('.journey-pass-frame').evaluate(e=>e.textContent.trim())).toBe('')
  expect(await page.locator('.journey-pass-frame').evaluate(e=>e.getAnimations().length)).toBe(0)
  expect(await page.locator('.auth-form-panel').evaluate(e=>getComputedStyle(e).overflowY)).toBe('visible')
 }
})

test('the local promotional image has a slow alpha-masked glow and fits desktop auth viewports',async({page})=>{
 await page.emulateMedia({reducedMotion:'no-preference'})
 for(const height of [1080,880]){
  await page.setViewportSize({width:1920,height})
  for(const path of ['login','register']){
   await page.goto('/'+path)
   const card=page.locator('.journey-pass-card-image')
   await expect(card).toHaveAttribute('src','/images/travelly/auth/journey-pass-card.png')
   await expect(card).toBeVisible()
   const metrics=await page.evaluate(()=>{
    const image=document.querySelector('.journey-pass-card-image'),frame=image.parentElement,form=document.querySelector('.auth-form-panel')
    const imageRect=image.getBoundingClientRect(),formRect=form.getBoundingClientRect()
    const shimmer=getComputedStyle(frame,'::after'),glow=getComputedStyle(image)
    return {
     natural:[image.naturalWidth,image.naturalHeight],
     objectFit:glow.objectFit,
     imageAnimation:glow.animationName,
     shimmerAnimation:shimmer.animationName,
     shimmerDuration:shimmer.animationDuration,
     mask:shimmer.maskImage,
     document:[document.documentElement.scrollWidth,document.documentElement.scrollHeight],
     overlap:imageRect.right>formRect.left&&imageRect.left<formRect.right&&imageRect.bottom>formRect.top&&imageRect.top<formRect.bottom
    }
   })
   expect(metrics.natural).toEqual([1605,980])
   expect(metrics.objectFit).toBe('contain')
   expect(metrics.imageAnimation).toBe('journey-pass-glow-pulse')
   expect(metrics.shimmerAnimation).toBe('journey-pass-border-glint')
   expect(metrics.shimmerDuration).toBe('10s')
   expect(metrics.mask).toContain('journey-pass-card.png')
   expect(metrics.document).toEqual([1920,height])
   expect(metrics.overlap).toBe(false)
  }
 }
})

test('reduced motion keeps the ticket glow static without the traveling shimmer',async({page})=>{
 await page.emulateMedia({reducedMotion:'reduce'})
 await page.setViewportSize({width:1920,height:880})
 await page.goto('/login')
 const motion=await page.evaluate(()=>{
  const image=document.querySelector('.journey-pass-card-image'),frame=image.parentElement
  return {
   imageAnimation:getComputedStyle(image).animationName,
   shimmerAnimation:getComputedStyle(frame,'::after').animationName,
   shimmerOpacity:getComputedStyle(frame,'::after').opacity,
   staticGlow:getComputedStyle(image).filter
  }
 })
 expect(motion.imageAnimation).toBe('none')
 expect(motion.shimmerAnimation).toBe('none')
 expect(motion.shimmerOpacity).toBe('0')
 expect(motion.staticGlow).toContain('drop-shadow')
})
