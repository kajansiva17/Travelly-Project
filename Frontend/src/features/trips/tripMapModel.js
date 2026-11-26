import { BRAND_RED } from '../../components/brandColor.js'
/* Live trip map data (contract 03O, sections 5 and C): points, the road line and the vehicle position, as the map draws them.
   The API sends latitude and longitude as strings and the road line as [lng, lat] pairs; Leaflet wants numbers and [lat, lng]. */
const num=value=>{const n=Number(value);return value===null||value===undefined||value===''||!Number.isFinite(n)?null:n}
export const pointLatLng=point=>{const lat=num(point?.latitude),lng=num(point?.longitude);return lat===null||lng===null?null:[lat,lng]}
// The route points that have a usable position, with their kind (START, STOP, END) and label.
export const routePoints=data=>(Array.isArray(data?.points)?data.points:[]).map(point=>({kind:point.kind,label:point.label||'',latlng:pointLatLng(point)})).filter(point=>point.latlng)
// The line that follows the roads; when it is null the map draws straight lines between the points.
export function routeLine(data){
  const line=Array.isArray(data?.line)?data.line.filter(pair=>Array.isArray(pair)&&pair.length>=2).map(([lng,lat])=>[num(lat),num(lng)]).filter(pair=>pair[0]!==null&&pair[1]!==null):[]
  if(line.length>=2)return {latlngs:line,straight:false}
  return {latlngs:routePoints(data).map(point=>point.latlng),straight:true}
}
export const POINT_COLORS={START:'#1a9d4a',END:BRAND_RED,STOP:'#7b8499'}
export const pointColor=kind=>POINT_COLORS[kind]||POINT_COLORS.STOP
export const positionLatLng=position=>position?pointLatLng(position):null
// Polling GET /trips/{id} stops once the trip has ended.
export const tripFinished=status=>status==='COMPLETED'||status==='CANCELLED'
/* GET /trips/{id} gives the status and `location` {latitude, longitude, updated_at} (null until the first update and once
   tracking is off or the trip ended). It replaces the map's status and position; a null location drops the marker (03O). */
export function withTripRead(data,trip){
  if(!trip)return data
  const location=trip.location&&pointLatLng(trip.location)?{latitude:trip.location.latitude,longitude:trip.location.longitude,updated_at:trip.location.updated_at}:null
  return {...data,status:trip.status||data?.status,position:location}
}
// [[south, west], [north, east]] around the given places, or null with none.
export function boundsOf(latlngs){
  const list=(latlngs||[]).filter(Boolean)
  if(!list.length)return null
  const lats=list.map(p=>p[0]),lngs=list.map(p=>p[1])
  return [[Math.min(...lats),Math.min(...lngs)],[Math.max(...lats),Math.max(...lngs)]]
}
// Alerts on the map: only those with a usable position.
export const alertMarkers=items=>(items||[]).map(item=>({id:item.id,type:item.alert_type,status:item.status,latlng:pointLatLng(item)})).filter(item=>item.id&&item.latlng)
export const ALERT_COLORS={POLICE_PRESENCE:'#2f6fe4',SPEED_CHECK:'#7c4dff',ACCIDENT:BRAND_RED,ROADBLOCK:'#e07b00',ROAD_HAZARD:'#c9a100'}
export const alertColor=type=>ALERT_COLORS[type]||'#e07b00'
// The route as text for the fallback when the map pictures cannot be loaded: first and last point.
export function routeText(data){
  const points=routePoints(data)
  if(!points.length)return ''
  const first=points[0].label,last=points[points.length-1].label
  return first&&last&&points.length>1?`${first} → ${last}`:(first||last||'')
}
/* Direction of travel in degrees from north between two [lat, lng] spots; null when they are less than ~5 m apart (GPS jitter). */
export function bearing(from,to){
  const rad=Math.PI/180,dy=(to[0]-from[0])*111320,dx=(to[1]-from[1])*111320*Math.cos(from[0]*rad)
  if(Math.hypot(dx,dy)<5)return null
  return (Math.atan2(dx,dy)/rad+360)%360
}
