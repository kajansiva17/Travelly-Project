export const workspaceRoles={PASSENGER:{label:'Passenger',home:'/dashboard',prefix:'/passenger'},OWNER:{label:'Vehicle Owner',home:'/owner/dashboard',prefix:'/owner'},DRIVER:{label:'Driver',home:'/driver/dashboard',prefix:'/driver'},ADMIN:{label:'Super Admin',home:'/admin/dashboard',prefix:'/admin'}}
const item=(label,path,icon='grid',options={})=>({label,path,icon,...options})
export function eligibleWorkspaces(user,roles){
 if(!user||!['ACTIVE','PENDING_VERIFICATION'].includes(user.account_status))return []
 return Object.keys(workspaceRoles).filter(code=>user.approved_roles?.includes(code)&&roles.some(r=>r.role_code===code&&r.approval_status==='APPROVED'))
}
export function loginDestination(user,roles,journey){
 const allowed=eligibleWorkspaces(user,roles)
 if(journey==='ADMIN')return '/admin/dashboard'
 if(['OWNER','DRIVER'].includes(journey))return allowed.includes(journey)?workspaceRoles[journey].home:`/${journey.toLowerCase()}/onboarding`
 const preferred=['ADMIN','OWNER','DRIVER'].find(role=>allowed.includes(role))
 return preferred?workspaceRoles[preferred].home:'/dashboard'
}
export function accountPath(role,documents){const q=new URLSearchParams({workspace:role.toLowerCase()});if(documents)q.set('documents',documents);return '/account?'+q}
export function withWorkspace(path,role){const [url,hash]=path.split('#'),[base,search]=url.split('?'),q=new URLSearchParams(search);q.set('workspace',role.toLowerCase());return base+'?'+q+(hash?'#'+hash:'')}
export function personalHirePath(role){return workspaceRoles[role].prefix+'/personal/hire'}
export function personalBookingsPath(role){return workspaceRoles[role].prefix+'/personal/bookings'}
export function personalBookingPath(role,bookingId){return personalBookingsPath(role)+'/'+bookingId}
export function personalVehiclePath(role,vehicleId){return workspaceRoles[role].prefix+'/personal/vehicles/'+vehicleId}
export function requestedWorkspace(search){const code=new URLSearchParams(search).get('workspace')?.toUpperCase();return workspaceRoles[code]?code:'PASSENGER'}
export function workspaceMenu(role){
 if(role==='PASSENGER')return []
 const p=workspaceRoles[role].prefix
 const bottom=[item('Profile',accountPath(role),'user',{bottom:true}),item('Settings',p+'/settings','settings',{bottom:true})]
 const menus={
  PASSENGER:[],
  OWNER:[item('Dashboard','/owner/dashboard'),item('My Vehicles','/owner/vehicles','car'),item('Services','/owner/rates','settings'),item('Ticket Departures',p+'/ticket-departures','ticket'),item('Seat Inventory',p+'/seat-inventory','seat'),item('Driver Assignments',p+'/assignments','users'),item('Bookings',p+'/bookings','calendar'),item('Documents',accountPath(role,'owner'),'document'),item('Earnings',p+'/earnings','wallet'),item('Reels & Promotions',p+'/reels','video'),item('Reviews',p+'/reviews','star'),item('Reports',p+'/reports','chart')],
  DRIVER:[item('Dashboard',p+'/dashboard'),item('Assignments',p+'/assignments','calendar'),item('Operate Trip',p+'/operate-trip','car'),item('Road Alerts',p+'/road-alerts','alert'),item('My Reels',p+'/reels','video'),item('Feed',p+'/feed','globe'),item('Earnings',p+'/earnings','wallet'),item('Availability',p+'/availability','clock'),item('Trip History',p+'/trip-history','clock'),item('Support',p+'/support','headset')],
  ADMIN:[item('Dashboard',p+'/dashboard'),item('Users & Roles','/admin/applications','users'),item('Documents',p+'/documents','document'),item('Vehicles','/admin/vehicles','car'),item('Services & Routes',p+'/services-routes','route'),item('Bookings',p+'/bookings','calendar'),item('Payments',p+'/payments','wallet'),item('Social & Reviews',p+'/social-reviews','star'),item('Road Alerts',p+'/road-alerts','alert'),item('Manual Fulfilment',p+'/manual-fulfilment','headset'),item('Reports',p+'/reports','chart')]
 }
 const personal=['OWNER','DRIVER'].includes(role)?[item('Book a ride for myself',personalHirePath(role),'car'),item('My personal trips',personalBookingsPath(role),'calendar')]:[]
 return [...menus[role],...personal,...(role==='ADMIN'?[bottom[1],bottom[0]]:bottom)]
}
export function menuActive(item,pathname,search){
 const [path,query]=item.path.split('?')
 if(path==='/account')return pathname==='/account'&&(new URLSearchParams(search).get('documents')||'')===(new URLSearchParams(query).get('documents')||'')
 if(path.endsWith('/dashboard')||path==='/dashboard')return pathname===path
 return pathname===path||pathname.startsWith(path+'/')
}
