import test from 'node:test'
import assert from 'node:assert/strict'
import {eligibleWorkspaces,workspaceMenu,requestedWorkspace,withWorkspace,menuActive,activeMenuItem,loginDestination,accountPath} from '../src/routes/workspaceRoutes.js'

test('workspace eligibility requires current account and both approved role representations',()=>{
 const user={account_status:'ACTIVE',approved_roles:['PASSENGER','OWNER','ADMIN']},roles=[{role_code:'PASSENGER',approval_status:'APPROVED'},{role_code:'OWNER',approval_status:'PENDING'},{role_code:'DRIVER',approval_status:'APPROVED'},{role_code:'ADMIN',approval_status:'SUSPENDED'}]
 assert.deepEqual(eligibleWorkspaces(user,roles),['PASSENGER'])
 assert.deepEqual(eligibleWorkspaces({...user,account_status:'SUSPENDED'},roles),[])
 assert.deepEqual(eligibleWorkspaces({...user,account_status:'PENDING_VERIFICATION'},roles),['PASSENGER'])
 assert.deepEqual(eligibleWorkspaces(null,roles),[])
})
test('role menus retain every required destination and bottom account controls',()=>{
 const expected={PASSENGER:8,OWNER:9,DRIVER:11,ADMIN:13}
 for(const [role,length] of Object.entries(expected)){const menu=workspaceMenu(role);assert.equal(menu.length,length);assert.equal(new Set(menu.map(m=>m.label)).size,length);assert.deepEqual(new Set(menu.filter(m=>m.bottom).map(m=>m.label)),new Set(['Profile','Settings']));assert.ok(menu.every(m=>m.path.startsWith('/')))}
})
test('workspace query is an allowlisted UI selection and preserves existing URL parts',()=>{
 assert.equal(requestedWorkspace('?workspace=admin'),'ADMIN');assert.equal(requestedWorkspace('?workspace=SUPER_ADMIN'),'PASSENGER')
 assert.equal(withWorkspace('/bookings/123?tab=details#price','OWNER'),'/bookings/123?tab=details&workspace=owner#price')
 const documents={label:'Documents',path:accountPath('OWNER','owner')},profile=workspaceMenu('OWNER').find(i=>i.label==='Profile')
 assert.equal(menuActive(documents,'/account','?workspace=owner&documents=owner'),true)
 assert.equal(menuActive(profile,'/account','?workspace=owner&documents=owner'),false)
})
test('login uses current approval, Owner priority for dual roles and explicit journey intent',()=>{
 const route=(codes,journey,status='ACTIVE',rows)=>loginDestination({account_status:status,approved_roles:codes},rows||codes.map(role_code=>({role_code,approval_status:'APPROVED'})),journey)
 assert.equal(route(['PASSENGER','OWNER']),'/owner/dashboard')
 assert.equal(route(['PASSENGER','DRIVER']),'/driver/dashboard')
 assert.equal(route(['PASSENGER','OWNER','DRIVER']),'/owner/dashboard')
 assert.equal(route(['PASSENGER','OWNER','DRIVER'],'DRIVER'),'/driver/dashboard')
 assert.equal(route(['PASSENGER','ADMIN','OWNER']),'/admin/dashboard')
 assert.equal(route(['PASSENGER'],'OWNER'),'/owner/onboarding')
 assert.equal(route(['PASSENGER'],'DRIVER'),'/driver/onboarding')
 assert.equal(route(['PASSENGER','OWNER'],null,'BLOCKED'),'/dashboard')
 for(const approval_status of ['PENDING','REJECTED','SUSPENDED'])assert.equal(route(['PASSENGER','OWNER'],null,'ACTIVE',[{role_code:'PASSENGER',approval_status:'APPROVED'},{role_code:'OWNER',approval_status}]),'/dashboard')
})
test('only one sidebar entry is current, including entries that share a path',()=>{
 const driver=workspaceMenu('DRIVER'),current=activeMenuItem(driver,'/driver/trip-history','')
 assert.equal(driver.filter(item=>item===current).length,1)
 assert.equal(current.label,'Trip History')
 assert.equal(activeMenuItem(driver,'/driver/dashboard','').label,'Overview')
 assert.equal(activeMenuItem(workspaceMenu('OWNER'),'/owner/vehicles/abc','?workspace=owner').label,'Fleet')
 assert.equal(activeMenuItem(workspaceMenu('OWNER'),'/nowhere','?workspace=owner'),null)
})
