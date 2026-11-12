export const workspaceRoles={PASSENGER:{label:'Passenger',home:'/dashboard',prefix:'/passenger'},OWNER:{label:'Vehicle Owner',home:'/owner/dashboard',prefix:'/owner'},DRIVER:{label:'Driver',home:'/driver/dashboard',prefix:'/driver'},ADMIN:{label:'Super Admin',home:'/admin/dashboard',prefix:'/admin'}}
const item=(label,path,icon='grid',options={})=>({label,path,icon,...options})
export function eligibleWorkspaces(user,roles){
 if(!user||!['ACTIVE','PENDING_VERIFICATION'].includes(user.account_status))return []
 return Object.keys(workspaceRoles).filter(code=>user.approved_roles?.includes(code)&&roles.some(r=>r.role_code===code&&r.approval_status==='APPROVED'))
}
export function loginDestination(user,roles,journey){
 const allowed=eligibleWorkspaces(user,roles)
 if(journey==='ADMIN')return allowed.includes('ADMIN')?'/admin/dashboard':'/dashboard'   // only an approved Admin enters the Admin workspace
 if(['OWNER','DRIVER'].includes(journey))return allowed.includes(journey)?workspaceRoles[journey].home:`/${journey.toLowerCase()}/onboarding`
 // Plain sign-in (home page, no Owner/Driver/Admin entry) opens the Passenger workspace; other workspaces are a switch away.
 return '/dashboard'
}
export function accountPath(role,documents){const q=new URLSearchParams({workspace:role.toLowerCase()});if(documents)q.set('documents',documents);return '/account?'+q}
export function withWorkspace(path,role){const [url,hash]=path.split('#'),[base,search]=url.split('?'),q=new URLSearchParams(search);q.set('workspace',role.toLowerCase());return base+'?'+q+(hash?'#'+hash:'')}
export function personalHirePath(role){return role==='PASSENGER'?'/travel/book/service':workspaceRoles[role].prefix+'/personal/hire'}
export function personalBookingsPath(role){return workspaceRoles[role].prefix+'/personal/bookings'}
export function personalBookingPath(role,bookingId){return personalBookingsPath(role)+'/'+bookingId}
export function personalVehiclePath(role,vehicleId){return workspaceRoles[role].prefix+'/personal/vehicles/'+vehicleId}
export function requestedWorkspace(search){const code=new URLSearchParams(search).get('workspace')?.toUpperCase();return workspaceRoles[code]?code:'PASSENGER'}
export function workspaceMenu(role){
 const p=workspaceRoles[role].prefix
 const bottom=[item('Settings',p+'/settings','settings',{bottom:true}),item('Profile',accountPath(role),'user',{bottom:true})]
 const menus={
  PASSENGER:[item('Overview','/dashboard'),item('My Trips','/bookings','calendar'),item('Bookings','/passenger/bookings','ticket'),item('Saved Places',p+'/saved-places','heart'),item('Payments',p+'/payments','wallet'),item('Support',p+'/support','headset')],
  OWNER:[item('Overview','/owner/dashboard'),item('Fleet','/owner/vehicles','car'),item('Prices','/owner/rates','chart'),item('My routes','/owner/routes','route'),item('Ticket departures','/owner/ticket-departures','ticket'),item('Bookings',p+'/bookings','calendar'),item('Operations',p+'/operations','watch'),item('Finance',p+'/earnings','wallet'),item('More',p+'/support','spark'),item('Travel & Booking',personalHirePath('OWNER'),'home')],
  DRIVER:[item('Overview',p+'/dashboard'),item('My Assignments',p+'/assignments','calendar'),item('Operate Trip',p+'/operate-trip','car'),item('My Trips',p+'/trip-history','calendar'),item('Availability',p+'/availability','clock'),item('Earnings',p+'/earnings','wallet'),item('Trip History',p+'/trip-history','clock'),item('Road Alerts',p+'/road-alerts','alert'),item('Support',p+'/support','headset')],
  ADMIN:[item('Overview',p+'/dashboard'),item('Users & Roles','/admin/applications','users'),item('Documents',p+'/documents','document'),item('Vehicles','/admin/vehicles','car'),item('Services & Routes',p+'/services-routes','route'),item('Bookings',p+'/bookings','calendar'),item('Payments',p+'/payments','wallet'),item('Reviews',p+'/social-reviews','star'),item('Road Alerts',p+'/road-alerts','alert'),item('Manual Fulfilment',p+'/manual-fulfilment','headset'),item('Reports',p+'/reports','chart')]
 }
 return [...menus[role],...bottom]
}
export function menuActive(item,pathname,search){
 const [path,query]=item.path.split('?')
 if(path==='/account')return pathname==='/account'&&(new URLSearchParams(search).get('documents')||'')===(new URLSearchParams(query).get('documents')||'')
 if(path.endsWith('/dashboard')||path==='/dashboard')return pathname===path
 return pathname===path||pathname.startsWith(path+'/')
}
/* Only one sidebar entry is current: the most specific matching path (the later entry wins a tie). */
export function activeMenuItem(items,pathname,search){
 let best=null,length=-1
 for(const item of items){if(!menuActive(item,pathname,search))continue;const size=item.path.split('?')[0].length;if(size>=length){best=item;length=size}}
 return best
}
