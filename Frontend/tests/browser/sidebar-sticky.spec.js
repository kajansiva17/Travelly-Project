import {test,expect} from '@playwright/test'
import {setup,visit} from './helpers/redesign.js'
import {workspaceRoles,workspaceMenu} from '../../src/routes/workspaceRoutes.js'

for(const role of ['OWNER','DRIVER','ADMIN'])test(`${role} sidebar stays in place while the dashboard scrolls`,async({page},info)=>{
 await page.setViewportSize({width:1366,height:768});await setup(page);await visit(page,workspaceRoles[role].home)
 const sidebar=page.locator('aside.workspace-sidebar'),nav=sidebar.getByRole('navigation',{name:workspaceRoles[role].label+' sidebar',exact:true})
 await expect(sidebar).toBeVisible()
 for(const item of workspaceMenu(role))await expect(nav.getByRole('link',{name:item.label,exact:true})).toBeInViewport()
 await expect(nav.getByRole('button',{name:'Logout',exact:true})).toBeInViewport()
 const before=await sidebar.boundingBox()
 const fit=await sidebar.evaluate(el=>({height:el.clientHeight,scrollHeight:el.scrollHeight,overflow:getComputedStyle(el).overflowY}))
 expect(fit.scrollHeight).toBeLessThanOrEqual(fit.height+1)
 expect(fit.overflow).toBe('visible')
 await page.screenshot({path:info.outputPath(role.toLowerCase()+'-sidebar-desktop.png'),fullPage:false})
 await page.evaluate(()=>window.scrollTo(0,500))
 await expect.poll(()=>page.evaluate(()=>scrollY)).toBeGreaterThan(0)
 const after=await sidebar.boundingBox()
 expect(Math.abs(after.y-before.y)).toBeLessThanOrEqual(1)
 await expect(nav.getByRole('link',{name:'Profile',exact:true})).toBeInViewport()
 await expect(nav.getByRole('button',{name:'Logout',exact:true})).toBeInViewport()
 expect(await sidebar.evaluate(el=>el.scrollTop)).toBe(0)
})
