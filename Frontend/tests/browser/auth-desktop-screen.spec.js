import {test,expect} from '@playwright/test'

const cases=[['desktop-1080',1920,1080],['desktop-screen',1920,880],['scaled-desktop',1536,704],['laptop',1366,640],['mobile',390,844],['narrow-tablet',768,900]]
const stage=process.env.TRAVELLY_AUTH_CAPTURE_STAGE || 'after'

test('login and registration remain accessible at actual browser viewport heights',async({page})=>{
 await page.emulateMedia({reducedMotion:'reduce'})
 for(const [name,width,height] of cases){
  await page.setViewportSize({width,height})
  for(const [path,heading] of [['login','Welcome back'],['register','Create your account']]){
   await page.goto('http://127.0.0.1:5173/'+path)
   await page.evaluate(()=>document.fonts.ready)
   await expect(page.getByRole('heading',{name:heading,exact:true})).toBeVisible()
   await page.screenshot({path:`../.tools/auth-desktop-screen-2026-11-04/${stage}-${name}-${path}.png`,fullPage:true})
   const measure=async()=>page.evaluate(()=>({viewport:[innerWidth,innerHeight],document:[document.documentElement.scrollWidth,document.documentElement.scrollHeight],card:document.querySelector('.auth-form-panel').getBoundingClientRect().toJSON(),ticket:document.querySelector('.journey-pass-frame').getBoundingClientRect().toJSON(),controls:[...document.querySelectorAll('.auth-form-panel input,.auth-form-panel button,.auth-form-panel a,.auth-form-panel small')].filter(el=>el.getClientRects().length).map(el=>{const r=el.getBoundingClientRect();return {name:el.getAttribute('aria-label')||el.textContent?.trim()||el.id,rect:[r.left,r.right,r.top,r.bottom]}})}))
   const first=await measure();console.log(stage,name,path,JSON.stringify(first))
   if(stage==='after'){
    expect(first.document[0]).toBeLessThanOrEqual(width)
    if(width>=1024){expect(first.document[1]).toBeLessThanOrEqual(height);expect(first.card.top).toBeGreaterThanOrEqual(0);expect(first.card.bottom).toBeLessThanOrEqual(height);expect(first.ticket.bottom).toBeLessThanOrEqual(height);expect(first.controls.every(c=>c.rect[2]>=0&&c.rect[3]<=height+1)).toBe(true)}
    else for(const control of await page.locator('.auth-form-panel input,.auth-form-panel button,.auth-form-panel a').all()){if(await control.isVisible()){await control.scrollIntoViewIfNeeded();await expect(control).toBeInViewport()}}
   }
   if(path==='register'&&await page.getByRole('button',{name:'Continue',exact:true}).count()){
    await page.getByLabel('Full name',{exact:true}).fill('Test Traveller');await page.getByLabel('Email address',{exact:true}).fill('layout@example.com');await page.getByLabel('Mobile number',{exact:true}).fill('0771234567');await page.getByRole('button',{name:'Continue',exact:true}).click()
    await expect(page.getByRole('button',{name:'Create account',exact:true})).toBeVisible()
    const second=await measure();console.log(stage,name,'register-step-2',JSON.stringify(second))
    if(stage==='after'&&width>=1024){expect(second.document[1]).toBeLessThanOrEqual(height);expect(second.controls.every(c=>c.rect[2]>=0&&c.rect[3]<=height+1)).toBe(true)}
    await page.screenshot({path:`../.tools/auth-desktop-screen-2026-11-04/${stage}-${name}-register-step-2.png`,fullPage:true})
   }
  }
 }
})
