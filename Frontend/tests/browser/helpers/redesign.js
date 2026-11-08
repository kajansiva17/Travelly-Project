import {expect} from '@playwright/test'
const uid='12222222-2222-4222-8222-222222222222',roles=['PASSENGER','OWNER','DRIVER','ADMIN']
const vehicle={id:'vehicle-one',reference:'VH-001',label:'Toyota Hiace',vehicle_type_code:'VAN',registration_number:'NC-1234',verification_status:'APPROVED',availability_status:'ACTIVE'}
const booking=(id,extra={})=>({id,reference:'TR-'+id,passenger_user_id:uid,owner_user_id:'other',status:'CONFIRMED',start_at:'2026-11-20T03:30:00Z',end_at:'2026-11-20T09:30:00Z',passenger_count:6,itinerary:{itinerary:{stops:[{place:{label:'Colombo'}},{place:{label:'Kandy'}}]}},...extra})
export async function visit(page,path){await page.evaluate(path=>new Promise(resolve=>{if(path===location.pathname+location.search){resolve();return}history.pushState({},'',path);dispatchEvent(new PopStateEvent('popstate'));requestAnimationFrame(()=>requestAnimationFrame(resolve))}),path)}
export async function setup(page,{approved=roles,status='ACTIVE',empty=false,entry='/login',destination='/dashboard'}={}){
 const state={approved,status,roleStatuses:{},applications:[],requests:[],bookingError:false,calendarIncomplete:false,logoutFailure:false,logout:0}
 const list=empty?[]:[booking('passenger'),booking('owner',{passenger_user_id:'another',owner_user_id:uid,status:'AWAITING_DRIVER'}),booking('driver',{passenger_user_id:'another',trip:{id:'trip-1',driver_user_id:uid,assignment_status:'ACCEPTED',status:'SCHEDULED'}}),booking('complete',{passenger_user_id:'another',status:'COMPLETED',trip:{id:'trip-2',driver_user_id:uid,assignment_status:'ACCEPTED',status:'COMPLETED'}})]
 await page.route('**/api/v1/**',async route=>{
  const req=route.request(),url=new URL(req.url()),path=url.pathname.replace('/api/v1','');state.requests.push([req.method(),path]);let body={items:[]}
  if(path==='/auth/login')body={access_token:'workspace-access',refresh_token:'workspace-refresh',expires_in:900}
  else if(path==='/auth/config')body={google_enabled:false}
  else if(path==='/users/me')body={id:uid,full_name:'Kasun Perera',account_status:state.status,email:'workspace@example.com',email_verified_at:'2026-10-27T00:00:00Z',approved_roles:state.approved}
  else if(path==='/users/me/role-requests'){const code=req.postDataJSON().role_code;state.approved=state.approved.filter(r=>r!==code);state.roleStatuses[code]='PENDING';state.applications.push(req.postDataJSON());body={role_code:code,approval_status:'PENDING'}}
  else if(path==='/users/me/roles')body={items:roles.map(role_code=>({role_code,approval_status:state.roleStatuses[role_code]||(state.approved.includes(role_code)?'APPROVED':'PENDING')}))}
  else if(path==='/auth/logout'){state.logout++;return state.logoutFailure?route.fulfill({status:503,json:{message:'Sign out unavailable. Try again.'}}):route.fulfill({status:204})}
  else if(path==='/bookings'){if(state.bookingError)return route.fulfill({status:503,json:{message:'Booking source unavailable.'}});body={items:list}}
  else if(path.startsWith('/bookings/'))body=list.find(b=>b.id===path.split('/')[2])||{}
  else if(path==='/owners/me/vehicles')body={items:empty?[]:[vehicle],total:empty?0:1,page:1,has_next:false}
  else if(path.includes('/calendar'))body={complete:!state.calendarIncomplete,checked_at:'2026-10-29T06:00:00Z',availability_status:'ACTIVE',verification_status:'APPROVED',events:[{id:'block-1',source:'BLOCK',kind:'EMERGENCY_MAINTENANCE',status:'ACTIVE',restricts:true,start_at:'2026-10-29T10:00:00Z',end_at:'2026-10-30T10:00:00Z',affected_commitments:[{id:'owner'}]}]}
  else if(path==='/admin/role-requests')body={items:empty?[]:[{id:'request-1',role_code:'DRIVER',approval_status:'PENDING',requested_at:'2026-10-29T04:00:00Z',applicant:{full_name:'Nimal Silva'}}],total:empty?0:1}
  else if(path==='/admin/vehicles')body={items:empty?[]:[{...vehicle,verification_status:'SUBMITTED'}],total:empty?0:1}
  else if(path==='/users/me/auth-methods')body={password:true,google:true}
  await route.fulfill({json:body})
 })
 await page.goto(entry);await page.getByLabel('Email address',{exact:true}).fill('workspace@example.com');await page.getByLabel('Password',{exact:true}).fill('BrowserTravelly1!');await page.getByRole('button',{name:'Log in',exact:true}).click()
 await expect(page).toHaveURL(new RegExp(destination+'$'));if(destination==='/dashboard'){
  // General login now opens the eligible operational workspace. Tests of shared
  // Passenger screens explicitly navigate there after authentication.
  if(new URL(page.url()).pathname!=='/dashboard')await visit(page,'/dashboard')
  await expect(page.locator('.passenger-dashboard h1')).toBeVisible()
 }
 return state
}
