import {travelPath,workspaceRoles} from '../../routes/workspaceRoutes.js'

/* Help paths are Passenger paths (contract 03AI, clarification 1). The button opens the person's own workspace copy:
   - /passenger/support (found: false) -> /owner/support or /driver/support inside those workspaces;
   - /travel/..., /bookings, /trips/... -> travelPath; /dashboard -> the workspace's dashboard;
   - /owner/... and /driver/... topics -> only for people with that approved role (no button for anyone else);
   - /account, /forgot-password, /reels and the two onboarding pages are used as given.
   Returns null when there should be no button. */
const AS_GIVEN=['/account','/forgot-password','/reels','/owner/onboarding','/driver/onboarding']
export function helpTarget(path,{role='PASSENGER',allowed=[]}={}){
  if(!path||typeof path!=='string'||!path.startsWith('/'))return null
  const base=path.split(/[?#]/)[0]
  if(AS_GIVEN.includes(base))return path
  if(base==='/passenger/support')return role==='OWNER'?'/owner/support':role==='DRIVER'?'/driver/support':path
  if(base==='/dashboard')return workspaceRoles[role]?.home||path
  if(base.startsWith('/owner/'))return allowed.includes('OWNER')?path:null
  if(base.startsWith('/driver/'))return allowed.includes('DRIVER')?path:null
  return travelPath(role,path)
}
