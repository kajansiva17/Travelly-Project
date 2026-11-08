import {test,expect} from '@playwright/test'
import {setup,visit} from './helpers/redesign.js'
import {workspaceRoles,workspaceMenu} from '../../src/routes/workspaceRoutes.js'

for(const [width,height] of [[1672,941],[1366,768],[1024,900],[768,900],[390,844],[320,640],[844,390],[640,360]]) {
 test(`reference dashboards and non-scrolling navigation at ${width}x${height}`,async({page},info)=>{
  await page.setViewportSize({width,height});await setup(page)
  for(const role of ['ADMIN','OWNER','DRIVER']) {
   await visit(page,workspaceRoles[role].home)
   await expect(page.locator('.overview-banner h1')).toContainText(role==='ADMIN'?'Kasun':role==='OWNER'?'Grow every journey':'Ready for the road')
   expect(await page.evaluate(()=>[...document.querySelectorAll('body *')].filter(el=>{const b=el.getBoundingClientRect();return b.width>0&&b.right>innerWidth+1}).map(el=>({tag:el.tagName,cls:el.className,right:el.getBoundingClientRect().right})).slice(0,20))).toEqual([])
   await expect(page.locator('.workspace-loading')).toHaveCount(0)
   await page.screenshot({path:info.outputPath(`${role.toLowerCase()}-${width}.png`),fullPage:false})
   const trigger=page.getByRole('button',{name:'Open workspace navigation',exact:true})
   const mobile=await trigger.isVisible();expect(mobile).toBe(width<768);if(mobile)await trigger.click()
   const surface=page.locator(mobile?'.workspace-drawer-panel':'.workspace-sidebar')
   for(const item of workspaceMenu(role))await expect(surface.getByRole('link',{name:item.label,exact:true})).toBeInViewport()
   await expect(surface.getByRole('button',{name:'Logout',exact:true})).toBeInViewport()
   const rows=await surface.locator('.workspace-sidebar-link').evaluateAll(els=>els.map(el=>{const label=el.querySelector('span'),box=el.getBoundingClientRect(),text=label.getBoundingClientRect();return {left:box.left,top:box.top,bottom:box.bottom,whiteSpace:getComputedStyle(label).whiteSpace,full:label.scrollWidth<=label.clientWidth+1,fits:text.right<=box.right+1}}))
   for(const row of rows){expect(row.whiteSpace).toBe('nowrap');expect(row.full).toBe(true);expect(row.fits).toBe(true);expect(Math.abs(row.left-rows[0].left)).toBeLessThanOrEqual(1)}
   for(let i=1;i<rows.length;i++)expect(rows[i].top).toBeGreaterThanOrEqual(rows[i-1].bottom-1)
   const fit=await surface.evaluate(el=>({client:el.clientHeight,scroll:el.scrollHeight,top:el.scrollTop}))
   expect(fit.scroll).toBeLessThanOrEqual(fit.client+1);expect(fit.top).toBe(0)
   await surface.evaluate(el=>{el.scrollTop=100})
   expect(await surface.evaluate(el=>el.scrollTop)).toBe(0)
   if(mobile)await page.keyboard.press('Escape')
  }
 })
}

