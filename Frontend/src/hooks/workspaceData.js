import { getLocale } from '../i18n/language.js'
import {useCallback,useEffect,useRef,useState} from 'react'
import {api} from '../services/api'

// Every result belongs to the current workspace, not to an earlier request.
export function useWorkspaceData(loader,dependencies=[]){
 const [state,setState]=useState({loading:true,data:null,error:null}),[revision,setRevision]=useState(0),generation=useRef(0)
 useEffect(()=>{let active=true;const id=++generation.current;setState({loading:true,data:null,error:null});Promise.resolve().then(loader).then(data=>{if(active&&id===generation.current)setState({loading:false,data,error:null})}).catch(error=>{if(active&&id===generation.current)setState({loading:false,data:null,error})});return()=>{active=false}},[...dependencies,revision])
 const reload=useCallback(()=>setRevision(n=>n+1),[])
 return {...state,reload}
}
export const words=value=>(value||'Not reported').replaceAll('_',' ')
export const displayTime=value=>value?new Date(value).toLocaleString(getLocale(),{timeZone:'Asia/Colombo',dateStyle:'medium',timeStyle:'short'}):'Time not reported'
export const tripRoute=booking=>(booking.itinerary?.itinerary?.stops||[]).map(stop=>stop.place?.label).filter(Boolean).join(' → ')||booking.reference
export const pendingBooking=booking=>!['COMPLETED','CANCELLED','REJECTED'].includes(booking.status)
// Contract 03W: every booking carries viewer_roles and GET /bookings takes ?as=passenger|owner|driver, so the server decides
// which list a booking belongs to (My trips, Bookings for my vehicles, My driving).
export async function loadBookings(userId,role){
 if(role==='ADMIN')throw new Error('Global Admin bookings are not available. Use My Trips for your personal journeys.')
 const result=await api('/bookings?as='+role.toLowerCase()),items=result.items||[]
 if(role==='OWNER'||role==='PASSENGER')return items
 // The Driver list needs each booking's trip record (assignment and trip ids). Bound concurrency.
 const details=new Array(items.length);let next=0
 await Promise.all(Array.from({length:Math.min(4,items.length)},async()=>{while(next<items.length){const i=next++;details[i]=await api('/bookings/'+items[i].id)}}))
 return details.filter(b=>b.trip?.driver_user_id===userId)
}
