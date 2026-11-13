import {useCallback,useEffect,useRef,useState} from 'react'
import {api} from '../../services/api'
import {fieldErrorText} from '../../services/fieldErrors.js'
import {usePoll} from './usePoll'

export const MAP_POLL_MS=20000      // a Passenger's read-only map follows the vehicle
export const ACTIVE_POLL_MS=30000   // contract 03O: the dashboard list, about every 30 s while it is open

/* GET /trips/{id}/map: the route points, the road line and the current position. With `poll` it is read again every 20 s
   (a Passenger watching the vehicle); the Driver's own map reads it once and takes its position from its own location updates. */
export function useTripMap(tripId,{poll=false,enabled=true}={}){
  const [state,setState]=useState({data:null,error:'',loaded:false}),inFlight=useRef(false)
  const load=useCallback(async()=>{
    if(inFlight.current)return
    inFlight.current=true
    try{setState({data:await api(`/trips/${encodeURIComponent(tripId)}/map`,{cache:'no-store'}),error:'',loaded:true})}
    catch(error){setState(current=>({...current,error:fieldErrorText(error,''),loaded:true}))}
    finally{inFlight.current=false}
  },[tripId])
  useEffect(()=>{if(!enabled)return;setState({data:null,error:'',loaded:false});load()},[load,enabled])
  usePoll(load,poll&&enabled,MAP_POLL_MS)
  return {...state,reload:load}
}

/* GET /trips/active: the trips running now for this person (IN_PROGRESS). Read when the dashboard opens and about every 30 s
   while it is open, one request at a time, paused while the tab is hidden. An empty list means no card. */
export function useActiveTrips(){
  const [state,setState]=useState({items:[],loaded:false}),inFlight=useRef(false)
  const load=useCallback(async()=>{
    if(inFlight.current)return
    inFlight.current=true
    try{const result=await api('/trips/active',{cache:'no-store'});setState({items:Array.isArray(result?.items)?result.items:[],loaded:true})}
    catch{setState(current=>({...current,loaded:true}))}   // a failed read keeps what is shown; the next poll tries again
    finally{inFlight.current=false}
  },[])
  usePoll(load,true,ACTIVE_POLL_MS)
  return state
}
