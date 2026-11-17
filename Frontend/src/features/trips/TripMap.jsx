import { BRAND_RED } from '../../components/brandColor.js'
import { t } from '../../i18n/language.js'
import {useEffect,useRef,useState} from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import {alertColor,alertMarkers,boundsOf,pointColor,positionLatLng,routeLine,routePoints,routeText} from './tripMapModel'

/* The live trip map (contract 03O, C): Leaflet with OpenStreetMap tiles (free, no key; the attribution stays on the map).
   It draws the route points (START green, END red, STOP grey), the road line (straight lines between the points when there is
   none), the vehicle's position and the nearby road alerts. If the map pictures cannot be loaded, the route and position are
   still drawn and a text line says so. */
const TILES='https://tile.openstreetmap.org/{z}/{x}/{y}.png'
const ATTRIBUTION='&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors'

export default function TripMap({data,position,alerts,selectedId,onSelect,follow,onFollow}){
  const holder=useRef(null),map=useRef(null),layers=useRef({}),fitted=useRef(false),loaded=useRef(0),errors=useRef(0)
  const [tilesFailed,setTilesFailed]=useState(false)
  useEffect(()=>{
    const instance=L.map(holder.current,{zoomControl:true,attributionControl:true,zoomSnap:0.5}).setView([7.8731,80.7718],7)
    const tiles=L.tileLayer(TILES,{maxZoom:19,attribution:ATTRIBUTION,referrerPolicy:'strict-origin-when-cross-origin'}).addTo(instance)
    tiles.on('tileload',()=>{loaded.current+=1;setTilesFailed(false)})
    tiles.on('tileerror',()=>{errors.current+=1;if(!loaded.current&&errors.current>=2)setTilesFailed(true)})
    layers.current={route:L.layerGroup().addTo(instance),alerts:L.layerGroup().addTo(instance),vehicle:L.layerGroup().addTo(instance)}
    map.current=instance
    // Keep the map sized to its box (the side column and the window change size).
    const watch=typeof ResizeObserver!=='undefined'?new ResizeObserver(()=>instance.invalidateSize()):null
    watch?.observe(holder.current)
    // A new map (React may mount twice) is fitted to the route again; stop() ends a running pan before the map goes away.
    return()=>{watch?.disconnect();instance.stop();instance.remove();map.current=null;layers.current={};fitted.current=false}
  },[])

  // The route: points and the road line. The map is fitted to it once.
  useEffect(()=>{
    const instance=map.current;if(!instance)return
    layers.current.route.clearLayers()
    const {latlngs,straight}=routeLine(data)
    if(latlngs.length>=2)L.polyline(latlngs,{color:'#2f6fe4',weight:5,opacity:.85,dashArray:straight?'8 8':undefined}).addTo(layers.current.route)
    for(const point of routePoints(data)){
      const marker=L.circleMarker(point.latlng,{radius:point.kind==='STOP'?7:10,color:'#fff',weight:3,fillColor:pointColor(point.kind),fillOpacity:1}).addTo(layers.current.route)
      if(point.label)marker.bindTooltip(point.label,{direction:'top'})
    }
    const bounds=boundsOf(latlngs)
    // No zoom animation here: its end timer would run after the map is removed when the page changes quickly.
    if(bounds&&!fitted.current){fitted.current=true;instance.fitBounds(bounds,{padding:[28,28],maxZoom:16,animate:false})}
  },[data])

  // The vehicle: a marker, and the map follows it when "Follow me" is on.
  useEffect(()=>{
    const instance=map.current;if(!instance)return
    layers.current.vehicle.clearLayers()
    const spot=positionLatLng(position)
    if(!spot)return
    L.circleMarker(spot,{radius:11,color:'#fff',weight:4,fillColor:BRAND_RED,fillOpacity:1}).addTo(layers.current.vehicle).bindTooltip(t('Vehicle'),{direction:'top'})
    // Zoom in without animation (same reason as the fit), then pan smoothly; stop() can end a pan.
    if(follow){if(instance.getZoom()<15)instance.setView(spot,15,{animate:false});else instance.panTo(spot,{animate:true})}
  },[position,follow])

  // Alert markers; the selected one is larger.
  useEffect(()=>{
    const instance=map.current;if(!instance)return
    layers.current.alerts.clearLayers()
    for(const alert of alertMarkers(alerts)){
      const marker=L.circleMarker(alert.latlng,{radius:alert.id===selectedId?13:9,color:'#fff',weight:3,fillColor:alertColor(alert.type),fillOpacity:alert.status==='UNCONFIRMED'?.6:1}).addTo(layers.current.alerts)
      marker.on('click',()=>onSelect&&onSelect(alert.id))
    }
  },[alerts,selectedId,onSelect])

  // Dragging the map by hand ends "Follow me".
  useEffect(()=>{
    const instance=map.current;if(!instance||!onFollow)return undefined
    const stop=()=>onFollow(false)
    instance.on('dragstart',stop)
    return()=>{instance.off('dragstart',stop)}
  },[onFollow])

  return <div className="tm-wrap">
    <div ref={holder} className="tm-map" role="application" aria-label={t('Live trip map')}/>
    {onFollow&&<button type="button" className={'tm-follow'+(follow?' is-on':'')} aria-pressed={follow} onClick={()=>onFollow(!follow)}>{t('Follow me')}</button>}
    {tilesFailed&&<p className="tm-fallback" role="status">{t('The map pictures could not be loaded.')} {routeText(data)}</p>}
  </div>
}
