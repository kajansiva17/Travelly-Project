export const workspaceRoles={PASSENGER:{label:'Passenger',home:'/dashboard',prefix:'/passenger'},OWNER:{label:'Vehicle Owner',home:'/owner/dashboard',prefix:'/owner'},DRIVER:{label:'Driver',home:'/driver/dashboard',prefix:'/driver'},ADMIN:{label:'Super Admin',home:'/admin/dashboard',prefix:'/admin'}}
const item=(label,path,icon='grid',options={})=>({label,path,icon,...options})
export function eligibleWorkspaces(user,roles){
 if(!user||!['ACTIVE','PENDING_VERIFICATION'].includes(user.account_status))return []
 return Object.keys(workspaceRoles).filter(code=>user.approved_roles?.includes(code)&&roles.some(r=>r.role_code===code&&r.approval_status==='APPROVED'))
}
const PRIORITY=['ADMIN','OWNER','DRIVER','PASSENGER']
/* Role workspaces (contract 03W, section 1). Highest approved role wins: Admin > Owner > Driver > Passenger.
   The Owner / Driver landing pages go to that role's dashboard, or to its application when the role is not approved yet. */
export function loginDestination(user,roles,journey){
 const allowed=eligibleWorkspaces(user,roles)
 if(['OWNER','DRIVER'].includes(journey))return allowed.includes(journey)?workspaceRoles[journey].home:`/${journey.toLowerCase()}/onboarding`
 const top=PRIORITY.find(code=>allowed.includes(code))
 return top?workspaceRoles[top].home:'/dashboard'
}
export function accountPath(role,documents){const q=new URLSearchParams({workspace:role.toLowerCase()});if(documents)q.set('documents',documents);return '/account?'+q}
export function withWorkspace(path,role){const [url,hash]=path.split('#'),[base,search]=url.split('?'),q=new URLSearchParams(search);q.set('workspace',role.toLowerCase());return base+'?'+q+(hash?'#'+hash:'')}
/* Owner, Driver and Admin workspaces hold the Passenger pages under <prefix>/travel/... (contract 03W, section 2), so Travel & booking never switches the person into the Passenger workspace. */
export const hasTravel=role=>role==='OWNER'||role==='DRIVER'||role==='ADMIN'
const personalPrefix=role=>hasTravel(role)?workspaceRoles[role].prefix+'/travel':workspaceRoles[role].prefix+'/personal'
export const travelHome=role=>hasTravel(role)?workspaceRoles[role].prefix+'/travel':'/travel/book/service'
export function personalHirePath(role){return role==='PASSENGER'?'/travel/book/service':hasTravel(role)?personalPrefix(role)+'/hire':personalPrefix(role)+'/hire'}
export function personalBookingsPath(role){return personalPrefix(role)+'/bookings'}
export function personalBookingPath(role,bookingId){return personalBookingsPath(role)+'/'+bookingId}
export function personalVehiclePath(role,vehicleId){return personalPrefix(role)+'/vehicles/'+vehicleId}
export function personalOwnerPath(role,reference){return personalPrefix(role)+'/owners/'+reference}
export const isPersonalPath=(role,pathname)=>role!=='PASSENGER'&&workspaceRoles[role]&&(pathname.startsWith(personalPrefix(role)+'/')||pathname===personalPrefix(role))
/* The Passenger pages link to each other with Passenger paths. Inside the Owner or Driver workspace the same page lives under <prefix>/travel. */
const PASSENGER_PATHS=['/bookings','/trips/','/hire','/vehicles/','/owners/','/reels','/social/']
export function travelPath(role,path){
 if(!hasTravel(role)||typeof path!=='string'||!path.startsWith('/'))return path
 const prefix=workspaceRoles[role].prefix
 if(path==='/travel'||path.startsWith('/travel/'))return prefix+path
 return PASSENGER_PATHS.some(p=>path===p||path.startsWith(p.endsWith('/')?p:p+'/')||path.startsWith(p+'?'))?prefix+'/travel'+path:path
}
export function requestedWorkspace(search){const code=new URLSearchParams(search).get('workspace')?.toUpperCase();return workspaceRoles[code]?code:'PASSENGER'}
export function workspaceMenu(role,{driving=false}={}){
 const p=workspaceRoles[role].prefix
 const bottom=[item('Settings',p+'/settings','settings',{bottom:true}),item('Profile',accountPath(role),'user',{bottom:true})]
 const menus={
  PASSENGER:[item('Overview','/dashboard'),item('My Trips','/bookings','calendar'),item('Bookings','/passenger/bookings','ticket'),item('Favourite vehicles',p+'/favourites','heart'),item('Saved Places',p+'/saved-places','pin'),item('Payments',p+'/payments','wallet'),item('Support',p+'/support','headset'),item('Travel Reels','/reels','video'),item('Travelly AI','/travelly-ai','spark',{action:'ai'})],
  // One Owner dashboard: this sidebar never changes. My driving appears only for an approved Owner who is also an approved Driver.
  OWNER:[item('Overview','/owner/dashboard'),item('My vehicles','/owner/vehicles','car'),item('Hire prices','/owner/rates','chart'),item('Ticket','/owner/ticket','ticket'),item('Rental','/owner/rental','key'),item('Maintenance','/owner/maintenance','settings'),item('Bookings for my vehicles','/owner/bookings','calendar'),item('Replacement requests','/owner/replacement-requests','clock'),item('My drivers','/owner/drivers','user'),item('Settlements','/owner/earnings','wallet'),item('Reports','/owner/reports','chart'),item('Travel & booking',travelHome('OWNER'),'plane',{travel:true}),...(driving?[item('My driving','/owner/driving','watch')]:[])],
  DRIVER:[item('Overview',p+'/dashboard'),item('My Assignments',p+'/assignments','calendar'),item('Operate Trip',p+'/operate-trip','car'),item('My Trips',p+'/trip-history','calendar'),item('My owners',p+'/owners','user'),item('Availability',p+'/availability','clock'),item('Maintenance',p+'/maintenance','settings'),item('Earnings',p+'/earnings','wallet'),item('Trip History',p+'/trip-history','clock'),item('Road Alerts',p+'/road-alerts','alert'),item('Support',p+'/support','headset')],
  ADMIN:[item('Overview',p+'/dashboard'),item('Users & Roles','/admin/applications','users'),item('Documents',p+'/documents','document'),item('Vehicles','/admin/vehicles','car'),item('Services & Routes',p+'/services-routes','route'),item('Bookings',p+'/bookings','calendar'),item('Payments',p+'/payments','wallet'),item('Reviews',p+'/social-reviews','star'),item('Road Alerts',p+'/road-alerts','alert'),item('Manual Fulfilment',p+'/manual-fulfilment','headset'),item('Reports',p+'/reports','chart'),item('Travelly AI','/travelly-ai','spark',{action:'ai'})]
 }
 return [...menus[role],...bottom]
}
export const canDriveAsOwner=user=>!!user?.approved_roles?.includes('OWNER')&&!!user?.approved_roles?.includes('DRIVER')
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
