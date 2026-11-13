import { t } from '../../i18n/language.js'
import {useEffect,useState} from 'react'
import {useParams} from 'react-router-dom'
import {Link} from '../passenger/travelRouter'
import {api} from '../../services/api'
import {Header,Icon} from '../../components/components'
import Chip from '../../components/ui/Chip'
import EmptyState from '../../components/ui/EmptyState'
import {FlowShell,usePaged,useRowCount} from '../booking/flow/FlowParts'
import {fieldErrorText} from '../../services/fieldErrors.js'
import {viewsOf} from './socialModel'
import {src} from './mediaSrc'

/* A profile (contract 03SO, section 4): GET /social/users/{reference}, posts grid, followers and following counts, Follow button.
   On the signed-in person's own profile the Saved tab (GET /social/me/saved) is added. */
function Grid({items,empty}){
  const size=Math.max(4,useRowCount(96)*4),paged=usePaged(items,size)
  if(!items.length)return <EmptyState icon="video" title={empty}>{''}</EmptyState>
  return <><div className="sp-grid">{paged.slice.map(post=><Link key={post.id} className="sp-post" to={`/reels/${post.id}`} title={post.caption||''}>
    {post.thumbnail_url||post.post_type==='PHOTO'?<img src={src(post.thumbnail_url||post.media_url)} alt={post.caption||t('Post')} loading="lazy"/>:<span className="sp-noimg"><Icon name={post.post_type==='REVIEW'?'star':'video'} size={22}/></span>}
    {post.post_type==='REEL'&&<small>{t('{value0} views',{value0:viewsOf(post)})}</small>}</Link>)}</div>
    <div className="flow-actions">{paged.pages>1?paged.pager:<span/>}<span/></div></>
}
export default function SocialProfile(){
  const {reference}=useParams(),[data,setData]=useState(null),[error,setError]=useState(''),[tab,setTab]=useState('posts'),[saved,setSaved]=useState(null),[busy,setBusy]=useState(false)
  useEffect(()=>{let alive=true;setData(null);setError('');setTab('posts');setSaved(null)
    api(`/social/users/${encodeURIComponent(reference)}`,{cache:'no-store'}).then(r=>alive&&setData(r)).catch(e=>alive&&setError(fieldErrorText(e)));return()=>{alive=false}},[reference])
  useEffect(()=>{if(tab!=='saved'||saved)return;api('/social/me/saved',{cache:'no-store'}).then(r=>setSaved(r.items||[])).catch(e=>setError(fieldErrorText(e)))},[tab])
  async function follow(){
    setBusy(true);setError('')
    try{const active=!data.followed_by_me;const r=await api(`/social/users/${encodeURIComponent(reference)}/follow`,{method:'POST',body:JSON.stringify({active})});const on=typeof r?.active==='boolean'?r.active:active
      setData(d=>({...d,followed_by_me:on,followers:Math.max(0,Number(d.followers||0)+(on?1:-1))}))}
    catch(e){setError(fieldErrorText(e))}finally{setBusy(false)}
  }
  const tabs=data?.is_me?[['posts','Posts'],['saved','Saved']].map(([code,name])=>({label:t(name),icon:code==='saved'?'star':'video',active:tab===code,onClick:()=>setTab(code)})):undefined
  return <><Header/><FlowShell heading={t('Travel Reels')} icon="video" title={data?.name||t('Profile')} tabs={tabs}>
    {error&&<p className="tk-line is-warn" role="alert">{error}</p>}
    {!data&&!error?<p role="status">{t('Loading…')}</p>:data&&<div className="tk-pane">
      <div className="tk-bar sp-head">
        {data.profile_image_url?<img className="sp-avatar" src={src(data.profile_image_url)} alt=""/>:<span className="sp-avatar"><Icon name="user" size={26}/></span>}
        <Chip tone="muted">{t('{value0} posts',{value0:data.post_count??(data.posts||[]).length})}</Chip><Chip tone="muted">{t('{value0} followers',{value0:data.followers??0})}</Chip><Chip tone="muted">{t('{value0} following',{value0:data.following??0})}</Chip>
        {!data.is_me&&<button type="button" className={'ui-button '+(data.followed_by_me?'ui-button-secondary':'ui-button-primary')} aria-pressed={Boolean(data.followed_by_me)} disabled={busy} onClick={follow}>{data.followed_by_me?t('Following'):t('Follow')}</button>}</div>
      {tab==='saved'?(saved?<Grid items={saved} empty={t('You have not saved anything yet.')}/>:!error&&<p role="status">{t('Loading…')}</p>):<Grid items={data.posts||[]} empty={t('No posts yet.')}/>}
    </div>}
  </FlowShell></>
}
