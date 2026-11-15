import test from 'node:test'
import assert from 'node:assert/strict'
import {eligibleWorkspaces,workspaceMenu,requestedWorkspace,withWorkspace,menuActive,activeMenuItem,loginDestination,accountPath,travelPath,canDriveAsOwner,isPersonalPath} from '../src/routes/workspaceRoutes.js'

test('workspace eligibility requires current account and both approved role representations',()=>{
 const user={account_status:'ACTIVE',approved_roles:['PASSENGER','OWNER','ADMIN']},roles=[{role_code:'PASSENGER',approval_status:'APPROVED'},{role_code:'OWNER',approval_status:'PENDING'},{role_code:'DRIVER',approval_status:'APPROVED'},{role_code:'ADMIN',approval_status:'SUSPENDED'}]
 assert.deepEqual(eligibleWorkspaces(user,roles),['PASSENGER'])
 assert.deepEqual(eligibleWorkspaces({...user,account_status:'SUSPENDED'},roles),[])
 assert.deepEqual(eligibleWorkspaces({...user,account_status:'PENDING_VERIFICATION'},roles),['PASSENGER'])
 assert.deepEqual(eligibleWorkspaces(null,roles),[])
})
test('role menus retain every required destination and bottom account controls',()=>{
 const expected={PASSENGER:11,OWNER:13,DRIVER:12,ADMIN:13}
 for(const [role,length] of Object.entries(expected)){const menu=workspaceMenu(role);assert.equal(menu.length,length);assert.equal(new Set(menu.map(m=>m.label)).size,length);assert.deepEqual(new Set(menu.filter(m=>m.bottom).map(m=>m.label)),new Set(['Profile','Settings']));assert.ok(menu.every(m=>m.path.startsWith('/')))}
})
test('workspace query is an allowlisted UI selection and preserves existing URL parts',()=>{
 assert.equal(requestedWorkspace('?workspace=admin'),'ADMIN');assert.equal(requestedWorkspace('?workspace=SUPER_ADMIN'),'PASSENGER')
 assert.equal(withWorkspace('/bookings/123?tab=details#price','OWNER'),'/bookings/123?tab=details&workspace=owner#price')
 const documents={label:'Documents',path:accountPath('OWNER','owner')},profile=workspaceMenu('OWNER').find(i=>i.label==='Profile')
 assert.equal(menuActive(documents,'/account','?workspace=owner&documents=owner'),true)
 assert.equal(menuActive(profile,'/account','?workspace=owner&documents=owner'),false)
})
test('login goes to the highest approved role, or the landing page role (role workspaces contract 03W)',()=>{
 const route=(codes,journey,status='ACTIVE',rows)=>loginDestination({account_status:status,approved_roles:codes},rows||codes.map(role_code=>({role_code,approval_status:'APPROVED'})),journey)
 // Home page / plain login / registration: Admin > Owner > Driver > Passenger.
 assert.equal(route(['PASSENGER']),'/dashboard')
 assert.equal(route(['PASSENGER','OWNER']),'/owner/dashboard')
 assert.equal(route(['PASSENGER','DRIVER']),'/driver/dashboard')
 assert.equal(route(['PASSENGER','OWNER','DRIVER']),'/owner/dashboard')
 assert.equal(route(['PASSENGER','ADMIN','OWNER']),'/admin/dashboard')
 assert.equal(route(['PASSENGER','OWNER'],null),'/owner/dashboard')
 // Owner / Driver landing pages: that role's dashboard, otherwise its application.
 assert.equal(route(['PASSENGER','OWNER'],'OWNER'),'/owner/dashboard')
 assert.equal(route(['PASSENGER','OWNER','DRIVER'],'OWNER'),'/owner/dashboard')
 assert.equal(route(['PASSENGER','OWNER','DRIVER'],'DRIVER'),'/driver/dashboard')
 assert.equal(route(['PASSENGER','DRIVER'],'OWNER'),'/owner/onboarding')
 assert.equal(route(['PASSENGER','OWNER'],'DRIVER'),'/driver/onboarding')
 assert.equal(route(['PASSENGER'],'OWNER'),'/owner/onboarding')
 assert.equal(route(['PASSENGER'],'DRIVER'),'/driver/onboarding')
 // A pending, rejected or suspended role is not approved: it never wins, and the landing page sends to the application.
 for(const approval_status of ['PENDING','REJECTED','SUSPENDED']){
  const rows=[{role_code:'PASSENGER',approval_status:'APPROVED'},{role_code:'OWNER',approval_status}]
  assert.equal(route(['PASSENGER','OWNER'],null,'ACTIVE',rows),'/dashboard')
  assert.equal(route(['PASSENGER','OWNER'],'OWNER','ACTIVE',rows),'/owner/onboarding')
 }
 assert.equal(route(['PASSENGER','OWNER'],null,'BLOCKED'),'/dashboard')
 assert.equal(route(['PASSENGER','OWNER'],'ADMIN'),'/owner/dashboard')
})
test('Owner sidebar follows the contract order; My driving only for an approved Owner who is also a Driver',()=>{
 const labels=menu=>menu.filter(i=>!i.bottom).map(i=>i.label)
 assert.deepEqual(labels(workspaceMenu('OWNER')),['Overview','My vehicles','Hire prices','Ticket','Rental','Maintenance','Bookings for my vehicles','Replacement requests','Settlements','Reports','Travel & booking'])
 assert.deepEqual(labels(workspaceMenu('OWNER',{driving:true})),['Overview','My vehicles','Hire prices','Ticket','Rental','Maintenance','Bookings for my vehicles','Replacement requests','Settlements','Reports','Travel & booking','My driving'])
 assert.deepEqual(workspaceMenu('OWNER',{driving:true}).filter(i=>i.bottom).map(i=>i.label),['Settings','Profile'])
 assert.equal(canDriveAsOwner({approved_roles:['PASSENGER','OWNER','DRIVER']}),true)
 assert.equal(canDriveAsOwner({approved_roles:['PASSENGER','OWNER']}),false)
 assert.equal(canDriveAsOwner({approved_roles:['PASSENGER','DRIVER']}),false)
})
test('Passenger pages run inside the Owner and Driver workspaces under /travel without leaving the shell',()=>{
 assert.equal(travelPath('OWNER','/travel/book/tickets?booking=1'),'/owner/travel/book/tickets?booking=1')
 assert.equal(travelPath('DRIVER','/travel/book/service'),'/driver/travel/book/service')
 assert.equal(travelPath('OWNER','/bookings'),'/owner/travel/bookings')
 assert.equal(travelPath('OWNER','/bookings/b1'),'/owner/travel/bookings/b1')
 assert.equal(travelPath('OWNER','/trips/t1/request-status'),'/owner/travel/trips/t1/request-status')
 assert.equal(travelPath('OWNER','/hire'),'/owner/travel/hire')
 assert.equal(travelPath('OWNER','/vehicles/v1'),'/owner/travel/vehicles/v1')
 assert.equal(travelPath('OWNER','/owners/OWN-1'),'/owner/travel/owners/OWN-1')
 assert.equal(travelPath('OWNER','/login'),'/login')
 assert.equal(travelPath('OWNER','/owner/vehicles'),'/owner/vehicles')
 assert.equal(travelPath('OWNER','/bookingsx'),'/bookingsx')
 for(const role of ['PASSENGER','ADMIN',undefined])assert.equal(travelPath(role,'/bookings'),'/bookings')
 assert.equal(isPersonalPath('OWNER','/owner/travel/bookings/b1'),true)
 assert.equal(isPersonalPath('OWNER','/owner/bookings/b1'),false)
 assert.equal(isPersonalPath('ADMIN','/admin/personal/hire'),true)
})
test('only one sidebar entry is current, including entries that share a path',()=>{
 const driver=workspaceMenu('DRIVER'),current=activeMenuItem(driver,'/driver/trip-history','')
 assert.equal(driver.filter(item=>item===current).length,1)
 assert.equal(current.label,'Trip History')
 assert.equal(activeMenuItem(driver,'/driver/dashboard','').label,'Overview')
 assert.equal(activeMenuItem(workspaceMenu('OWNER'),'/owner/vehicles/abc','?workspace=owner').label,'My vehicles')
 assert.equal(activeMenuItem(workspaceMenu('OWNER'),'/nowhere','?workspace=owner'),null)
})
