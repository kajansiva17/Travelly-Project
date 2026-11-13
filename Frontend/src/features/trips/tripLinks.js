import {travelPath} from '../../routes/workspaceRoutes.js'

/* Where a "Trip in progress" card opens (contract 03O, GET /trips/active). A trip the person drives (viewer_roles has DRIVER, and an
   Owner who drives their own vehicle has both) opens the Operate trip page, whose main view is the live map with the driver controls.
   Anyone else opens the read-only map, through travelPath so it stays in the current workspace. */
export const drivesTrip=item=>Array.isArray(item?.viewer_roles)&&item.viewer_roles.includes('DRIVER')
export function tripLink(item,role){
  const id=encodeURIComponent(item.trip_id)
  if(drivesTrip(item))return role==='OWNER'?`/owner/driving/trips/${id}`:`/driver/trips/${id}/live`
  return travelPath(role,`/trips/${id}/map`)
}
