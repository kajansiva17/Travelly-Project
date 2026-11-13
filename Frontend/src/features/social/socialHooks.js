import {useCallback,useEffect,useRef,useState} from 'react'
import {api} from '../../services/api'
import {fieldErrorText} from '../../services/fieldErrors.js'
import {feedQuery,visibleInTab} from './socialModel'

/* The Travel Reels feed (contract 03SO, section 2): GET /social/feed, next page with ?before=<next_before>.
   One request at a time. Signed media links (?t=) last an hour, so `reload` reads the feed again. */
export function useFeed({tab,hashtag='',author='',limit,enabled=true}){
  const [state,setState]=useState({items:[],loading:enabled,error:'',next:null,loaded:false})
  const busy=useRef(false),alive=useRef(true),run=useRef(0)
  useEffect(()=>{alive.current=true;return()=>{alive.current=false}},[])
  const load=useCallback(async(more=false)=>{
    if(busy.current||!enabled)return
    busy.current=true;const mine=++run.current
    setState(s=>({...s,loading:true,error:'',...(more?{}:{items:[],next:null,loaded:false})}))
    try{
      const before=more?stateRef.current.next:''
      const result=await api('/social/feed?'+feedQuery({tab,hashtag,author,before,limit}),{cache:'no-store'})
      if(!alive.current||mine!==run.current)return
      const fresh=(result.items||[]).filter(item=>visibleInTab(tab,item))
      setState(s=>({items:more?[...s.items,...fresh.filter(item=>!s.items.some(old=>old.id===item.id))]:fresh,loading:false,error:'',next:result.next_before||null,loaded:true}))
    }catch(error){
      if(alive.current&&mine===run.current)setState(s=>({...s,loading:false,loaded:true,error:fieldErrorText(error)}))
    }finally{busy.current=false}
  },[tab,hashtag,author,limit,enabled])
  const stateRef=useRef(state);stateRef.current=state
  useEffect(()=>{busy.current=false;load(false)},[load])
  const setItems=useCallback(update=>setState(s=>({...s,items:typeof update==='function'?update(s.items):update})),[])
  return {...state,more:()=>state.next&&load(true),reload:()=>{busy.current=false;return load(false)},hasMore:Boolean(state.next),setItems}
}
