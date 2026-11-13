import { t } from '../../i18n/language.js'
import {useEffect,useState} from 'react'
import {Link} from '../passenger/travelRouter'
import {api} from '../../services/api'
import {Icon} from '../../components/components'
import {viewsOf} from './socialModel'
import {src} from './mediaSrc'

/* Dashboard "Travel Reels" card (contract 03SO, Screens): GET /social/feed?type=REEL&limit=8, thumbnails with the place and view_count views.
   See all opens /reels in the current workspace (travelRouter Link). */
export function useReelsPreview(){
  const [state,setState]=useState({items:[],loading:true,error:false})
  useEffect(()=>{let alive=true;api('/social/feed?type=REEL&limit=8',{cache:'no-store'}).then(r=>alive&&setState({items:r.items||[],loading:false,error:false})).catch(()=>alive&&setState({items:[],loading:false,error:true}));return()=>{alive=false}},[])
  return state
}
export default function ReelsCard({className='',state}){
  return <section className={'dash-tile reels-card '+className}>
    <header><h3><Icon name="video" size={18}/>{t('Travel Reels')}</h3><Link to="/reels">{t('See all')}</Link></header>
    <div className="dash-tile-body">{state.loading?<p className="dash-soft">{t(' Loading…')}</p>:state.error?<p className="dash-soft">{t('Unable to load this information')}</p>
      :state.items.length?<div className="reels-strip">{state.items.map(post=><Link key={post.id} className="reels-thumb" to={`/reels/${post.id}`} title={post.caption||''}>
        {post.thumbnail_url?<img src={src(post.thumbnail_url)} alt="" loading="lazy"/>:<span className="reels-noimg"><Icon name="video" size={18}/></span>}
        <span className="reels-text"><strong>{post.location_name||post.author?.name||t('Travel Reels')}</strong><small>{t('{value0} views',{value0:viewsOf(post)})}</small></span></Link>)}</div>
      :<p className="dash-soft">{t('No reels yet.')}</p>}</div></section>
}
