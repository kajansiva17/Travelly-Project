import {useEffect,useRef,useState} from 'react'
import {BRAND_RED} from '../../components/brandColor.js'
import {t} from '../../i18n/language.js'
import {loadGoogleMaps} from './googleMaps'
import {alertColor,alertMarkers,bearing,boundsOf,pointColor,positionLatLng,routeLine,routePoints,routeText} from './tripMapModel'

/* The live trip map drawn with Google Maps (used when VITE_GOOGLE_MAPS_KEY is set; TripMap falls back to OpenStreetMap otherwise or
   when Google refuses the key). Same props and same drawing as the OpenStreetMap map: route points, the road line, the vehicle arrow turned
   the way it moves, the nearby road alerts, "Follow me", and Google's live traffic layer. */
const ll=([lat,lng])=>({lat,lng})
const phone=()=>typeof window!=='undefined'&&Boolean(window.matchMedia?.('(max-width: 767px)').matches)

export default function GoogleTripMap({data,position,alerts,selectedId,onSelect,follow,onFollow,onFail}){
  const holder=useRef(null),api=useRef(null),map=useRef(null),layers=useRef({route:[],alerts:[],vehicle:null,traffic:null})
  const fitted=useRef(false),lastSpot=useRef(null),heading=useRef(null),failRef=useRef(onFail)
  const [ready,setReady]=useState(false)
  useEffect(()=>{failRef.current=onFail},[onFail])

  useEffect(()=>{
    let gone=false
    window.gm_authFailure=()=>failRef.current&&failRef.current()   // key refused: use the OpenStreetMap map instead
    loadGoogleMaps().then(maps=>{
      if(gone||!holder.current)return
      api.current=maps
      map.current=new maps.Map(holder.current,{center:{lat:7.8731,lng:80.7718},zoom:7,disableDefaultUI:true,zoomControl:!phone(),
        gestureHandling:'greedy',clickableIcons:false,mapTypeControl:false,streetViewControl:false,fullscreenControl:false})
      layers.current.traffic=new maps.TrafficLayer();layers.current.traffic.setMap(map.current)
      map.current.addListener('dragstart',()=>{dragRef.current&&dragRef.current()})
      setReady(true)
    }).catch(()=>failRef.current&&failRef.current())
    return()=>{gone=true;for(const key of ['route','alerts'])for(const item of layers.current[key])item.setMap(null);layers.current={route:[],alerts:[],vehicle:null,traffic:null};map.current=null;fitted.current=false}
  },[])
  const dragRef=useRef(null);useEffect(()=>{dragRef.current=onFollow?()=>onFollow(false):null},[onFollow])

  // The route: the road line and the points. The map is fitted to it once.
  useEffect(()=>{
    if(!ready)return
    const maps=api.current;for(const item of layers.current.route)item.setMap(null);layers.current.route=[]
    const {latlngs,straight}=routeLine(data)
    if(latlngs.length>=2)layers.current.route.push(new maps.Polyline({map:map.current,path:latlngs.map(ll),strokeColor:'#2f6fe4',strokeOpacity:straight?0:.9,strokeWeight:6,
      icons:straight?[{icon:{path:'M 0,-1 0,1',strokeOpacity:1,scale:3},offset:'0',repeat:'16px'}]:undefined}))
    for(const point of routePoints(data))layers.current.route.push(new maps.Marker({map:map.current,position:ll(point.latlng),title:point.label||undefined,clickable:false,
      icon:{path:maps.SymbolPath.CIRCLE,scale:point.kind==='STOP'?7:10,fillColor:pointColor(point.kind),fillOpacity:1,strokeColor:'#fff',strokeWeight:3}}))
    const bounds=boundsOf(latlngs)
    if(bounds&&!fitted.current){fitted.current=true;map.current.fitBounds({south:bounds[0][0],west:bounds[0][1],north:bounds[1][0],east:bounds[1][1]},28)}
  },[data,ready])

  // The vehicle: an arrow turned the way it moves (from the last two positions; before it moves, towards the next route point).
  useEffect(()=>{
    if(!ready)return
    const maps=api.current;layers.current.vehicle?.setMap(null);layers.current.vehicle=null
    const spot=positionLatLng(position)
    if(!spot)return
    const moved=lastSpot.current?bearing(lastSpot.current,spot):null
    if(moved!==null)heading.current=moved
    else if(heading.current===null){const {latlngs}=routeLine(data);const ahead=latlngs.find(p=>bearing(spot,p)!==null);if(ahead)heading.current=bearing(spot,ahead)}
    if(moved!==null||!lastSpot.current)lastSpot.current=spot
    layers.current.vehicle=new maps.Marker({map:map.current,position:ll(spot),title:t('Vehicle'),zIndex:1000,clickable:false,
      icon:{path:maps.SymbolPath.FORWARD_CLOSED_ARROW,rotation:heading.current??0,scale:7,fillColor:BRAND_RED,fillOpacity:1,strokeColor:'#fff',strokeWeight:3}})
    if(follow){if(map.current.getZoom()<15)map.current.setZoom(15);map.current.panTo(ll(spot))}
  },[position,follow,data,ready])

  // Alert markers; the selected one is larger.
  useEffect(()=>{
    if(!ready)return
    const maps=api.current;for(const item of layers.current.alerts)item.setMap(null);layers.current.alerts=[]
    for(const alert of alertMarkers(alerts)){
      const marker=new maps.Marker({map:map.current,position:ll(alert.latlng),zIndex:alert.id===selectedId?500:100,
        icon:{path:maps.SymbolPath.CIRCLE,scale:alert.id===selectedId?13:9,fillColor:alertColor(alert.type),fillOpacity:alert.status==='UNCONFIRMED'?.6:1,strokeColor:'#fff',strokeWeight:3}})
      marker.addListener('click',()=>onSelect&&onSelect(alert.id))
      layers.current.alerts.push(marker)
    }
  },[alerts,selectedId,onSelect,ready])

  return <div className="tm-wrap tm-google">
    <div ref={holder} className="tm-map" role="application" aria-label={t('Live trip map')}/>
    {onFollow&&<button type="button" className={'tm-follow'+(follow?' is-on':'')} aria-pressed={follow} aria-label={t('Follow me')} title={t('Follow me')} onClick={()=>onFollow(!follow)}><svg className="tm-follow-icon" viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true"><circle cx="12" cy="12" r="3.5"/><circle cx="12" cy="12" r="8"/><path d="M12 1v3M12 20v3M1 12h3M20 12h3"/></svg><span className="tm-follow-label">{t('Follow me')}</span></button>}
    <p className="tm-fallback" hidden>{routeText(data)}</p>
  </div>
}
