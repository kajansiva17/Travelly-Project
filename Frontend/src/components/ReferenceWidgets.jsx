import { t } from '../i18n/language.js'
import React from 'react'
import {Link} from 'react-router-dom'
import {Icon,useNotice} from './components'
import {TravellyAsset} from './TravellyVisuals'

export function UnavailableFeature({icon='clock',children,compact=false}){
 return <div className={'reference-unavailable'+(compact?' compact':'')}><span className="reference-orb"><Icon name={icon} size={28}/></span><strong>{t("Not available yet")}</strong><p>{children}</p></div>
}
export function DestinationTiles({compact=false}){
 return <div className={compact?'reference-destinations compact':'reference-destinations'}>{[['ella','Ella','Scenic trains and misty mountains.'],['kandy','Kandy','Culture, lakes and timeless beauty.'],['galle','Galle','Coastal charm and golden sunsets.']].map(([name,title,copy])=><Link key={name} to="/hire"><TravellyAsset name={'destinations/destination-'+name+'.png'} alt={'Illustrated '+title+' destination'}/><div><h3>{t(title)}</h3>{!compact&&<p>{t(copy)}</p>}<span><Icon name="pin" size={14}/>{t(" Explore ")}{t(title)}<Icon name="arrow" size={14}/></span></div></Link>)}</div>
}
export function ReelsPreview(){return <><DestinationTiles compact/><p className="workspace-note">{t("Destination inspiration · illustrative artwork. Video reels and viewing counts are not available yet.")}</p></>}
export function ItineraryPreview({booking}){
 const stops=booking?.itinerary?.itinerary?.stops||[]
 return <div className="reference-route"><ol>{stops.length?stops.map((stop,i)=><li key={i}><Icon name="pin" size={16}/><div><strong>{t(stop.place?.label)||t('Unreported stop')}</strong><small>{i===0?t('Pickup'):i===stops.length-1?t('Destination'):t('Planned stop')}</small></div></li>):<li><Icon name="route"/><div><strong>{t("No itinerary to preview")}</strong><small>{t("Choose an assigned journey to review its stops.")}</small></div></li>}</ol></div>
}
export function PlatformMapPlaceholder(){return <div className="reference-platform-map"><svg viewBox="0 0 240 390" aria-hidden="true"><path d="M107 18C85 53 116 65 87 108C52 156 36 205 43 249C47 293 69 344 110 366C145 381 190 353 198 319C213 258 177 208 164 168C151 128 145 98 126 77C117 65 127 38 107 18Z"/></svg><div><Icon name="pin" size={30}/><strong>{t("Live trip positions are unavailable")}</strong><p>{t("Current APIs do not supply vehicle locations. No live markers or trip totals are shown.")}</p></div><small>{t("Illustrative island outline · no live tracking")}</small></div>}
export function TravellyHelp(){
 const notice=useNotice()
 return <button className="reference-help" aria-label={t("Travelly help")} onClick={()=>notice({title:'Travelly help',message:'Review your journeys in My Trips and your documents in Profile. Owner and Driver applications are reviewed independently. Automated chat and voice assistance are not available yet.'})}><Icon name="headset" size={25}/><span>{t("Help")}</span></button>
}
