import { t } from '../../i18n/language.js'
import React,{useCallback,useEffect,useRef,useState} from 'react'
import {useParams} from 'react-router-dom'
import {Link} from '../passenger/travelRouter'
import {api} from '../../services/api'
import {Header,Icon} from '../../components/components'
import Chip from '../../components/ui/Chip'
import EmptyState from '../../components/ui/EmptyState'
import {fieldErrorText} from '../../services/fieldErrors.js'
import {useFeed} from './socialHooks'
import {TABS,ratingOf,replaceItem,sharePath,viewsOf,withFollow} from './socialModel'
import {src} from './mediaSrc'
import {CommentsPanel,EditPanel,MenuPanel,RemovePanel,ReportPanel} from './ReelPanels'

/* Travel Reels viewing page (contract 03SO, Screens): a vertical full-height player. Only the visible reel plays (it autoplays muted,
   tap for sound) and only the next one is preloaded. Swipe, wheel or arrow keys move to the next reel; a view is counted once
   per reel per visit when playback starts. Side buttons: like, comments, save, share, the author (follow) and ⋯. */
const stars=n=>'★'.repeat(n)+'☆'.repeat(5-n)

function Media({post,muted,onSound,onPlaying}){
  const video=useRef(null)
  useEffect(()=>{const v=video.current;if(v){v.muted=muted}},[muted,post.id])
  useEffect(()=>{
    const v=video.current;if(!v)return undefined
    const sync=()=>{if(document.hidden)v.pause();else v.play?.().catch(()=>{})}
    document.addEventListener('visibilitychange',sync);v.play?.().catch(()=>{})
    return()=>document.removeEventListener('visibilitychange',sync)
  },[post.id])
  if(post.post_type==='REEL')return <button type="button" className="rl-media" onClick={onSound} aria-label={muted?t('Tap for sound'):t('Sound on')}>
    <video ref={video} key={post.id} src={src(post.media_url)} poster={src(post.thumbnail_url)||undefined} autoPlay muted loop playsInline preload="auto" onPlaying={onPlaying}/>
    <span className="rl-sound" aria-hidden="true"><Icon name={muted?'mute':'volume'} size={20}/></span></button>
  if(post.media_url)return <div className="rl-media"><img src={src(post.media_url)} alt={post.caption||t('Photo')}/></div>
  return <div className="rl-media rl-text"/>
}

function Overlay({post,onTag}){
  return <div className="rl-overlay">
    {post.post_type==='REVIEW'&&<p className="rl-stars" role="img" aria-label={t('{value0} out of 5 stars',{value0:ratingOf(post)})}>{stars(ratingOf(post))}</p>}
    <div className="rl-author"><Link to={`/social/users/${encodeURIComponent(post.author?.reference||'')}`}>{post.author?.name}</Link>{post.location_name&&<span><Icon name="pin" size={13}/>{post.location_name}</span>}</div>
    {post.caption&&<p className="rl-caption">{post.caption}</p>}
    {(post.hashtags||[]).length>0&&<div className="rl-tags">{post.hashtags.map(tag=><button type="button" key={tag} onClick={()=>onTag(tag)}>#{tag}</button>)}</div>}
    {post.post_type==='REEL'&&<p className="rl-views">{t('{value0} views',{value0:viewsOf(post)})}</p>}
  </div>
}

function Rail({post,busy,onLike,onSave,onComments,onShare,onFollow,onMenu}){
  const btn=(icon,label,count,on,active)=><button type="button" className={'rl-btn'+(active?' is-on':'')} aria-pressed={active===undefined?undefined:active} aria-label={label} title={label} disabled={busy} onClick={on}><Icon name={icon} size={26}/>{count!=null&&<span>{count}</span>}</button>
  return <div className="rl-rail" role="group" aria-label={t('Reel actions')}>
    {btn('heart',t('Like'),post.like_count,onLike,post.liked_by_me)}
    {btn('chat',t('Comments'),post.comment_count,onComments)}
    {btn('bookmark',t('Save'),null,onSave,post.saved_by_me)}
    {btn('share',t('Share'),post.share_count,onShare)}
    {!post.is_mine&&post.author?.reference&&<button type="button" className={'rl-btn rl-follow'+(post.following_author?' is-on':'')} aria-pressed={Boolean(post.following_author)} disabled={busy} onClick={onFollow}><Icon name="user" size={24}/><span>{post.following_author?t('Following'):t('Follow')}</span></button>}
    {btn('more',t('More'),null,onMenu)}
  </div>
}

export default function ReelsPage(){
  const {postId}=useParams(),[tab,setTab]=useState('REEL'),[hashtag,setHashtag]=useState(''),[index,setIndex]=useState(0)
  const [panel,setPanel]=useState(null),[muted,setMuted]=useState(true),[busy,setBusy]=useState(false),[note,setNote]=useState({text:'',warn:false})
  const feed=useFeed({tab,hashtag,enabled:!postId})
  const [single,setSingle]=useState({post:null,error:'',loaded:false})
  const viewed=useRef(new Set()),lastMove=useRef(0),touchY=useRef(null)
  useEffect(()=>{
    if(!postId)return undefined
    let alive=true;setSingle({post:null,error:'',loaded:false})
    api(`/social/posts/${encodeURIComponent(postId)}`,{cache:'no-store'}).then(post=>alive&&setSingle({post,error:'',loaded:true})).catch(e=>alive&&setSingle({post:null,error:fieldErrorText(e),loaded:true}))
    return()=>{alive=false}
  },[postId])
  const items=postId?(single.post?[single.post]:[]):feed.items
  const loading=postId?!single.loaded:feed.loading&&!feed.items.length,error=postId?single.error:feed.error
  const post=items[Math.min(index,Math.max(0,items.length-1))],next=items[index+1]
  useEffect(()=>{setIndex(0);setPanel(null)},[tab,hashtag])
  // Read ahead: when the last two reels are near, ask for the next page. An empty Following page keeps reading until something shows.
  useEffect(()=>{if(!postId&&feed.hasMore&&!feed.loading&&(items.length-index<=2))feed.more()},[index,items.length,feed.hasMore,feed.loading,postId])
  const patch=useCallback(next=>{postId?setSingle(s=>({...s,post:s.post&&replaceItem([s.post],next)[0]})):feed.setItems(list=>replaceItem(list,next))},[postId,feed.setItems])
  const say=(text,warn=false)=>setNote({text,warn})
  useEffect(()=>{if(!note.text)return undefined;const id=setTimeout(()=>setNote({text:'',warn:false}),4000);return()=>clearTimeout(id)},[note])

  const go=useCallback(delta=>{
    const now=Date.now();if(now-lastMove.current<450)return;lastMove.current=now
    setIndex(i=>Math.max(0,Math.min(items.length-1,i+delta)));setPanel(null)
  },[items.length])
  useEffect(()=>{
    const key=e=>{
      if(['INPUT','TEXTAREA','SELECT'].includes(e.target?.tagName)||panel)return
      if(e.key==='ArrowDown'||e.key==='PageDown'){e.preventDefault();go(1)}
      else if(e.key==='ArrowUp'||e.key==='PageUp'){e.preventDefault();go(-1)}
    }
    window.addEventListener('keydown',key);return()=>window.removeEventListener('keydown',key)
  },[go,panel])
  useEffect(()=>{viewed.current.clear()},[])

  const countView=()=>{
    if(!post||viewed.current.has(post.id))return
    viewed.current.add(post.id)
    api(`/social/posts/${post.id}/views`,{method:'POST',body:JSON.stringify({})}).then(r=>{if(r&&typeof r.view_count==='number')patch({id:post.id,view_count:r.view_count})}).catch(()=>{})
  }
  async function act(fn){if(busy)return;setBusy(true);try{await fn()}catch(e){say(fieldErrorText(e),true)}finally{setBusy(false)}}
  const like=()=>act(async()=>{const r=await api(`/social/posts/${post.id}/like`,{method:'POST',body:JSON.stringify({active:!post.liked_by_me})});patch({id:post.id,liked_by_me:r.active,like_count:r.like_count})})
  const save=()=>act(async()=>{const r=await api(`/social/posts/${post.id}/save`,{method:'POST',body:JSON.stringify({active:!post.saved_by_me})});patch({id:post.id,saved_by_me:r.active});say(r.active?t('Saved'):t('Removed from saved'))})
  const follow=()=>act(async()=>{const active=!post.following_author;const r=await api(`/social/users/${encodeURIComponent(post.author.reference)}/follow`,{method:'POST',body:JSON.stringify({active})});const on=typeof r?.active==='boolean'?r.active:active
    postId?patch({id:post.id,following_author:on}):feed.setItems(list=>withFollow(list,post.author.reference,on))})
  const share=()=>act(async()=>{
    const r=await api(`/social/posts/${post.id}/share`,{method:'POST',body:JSON.stringify({})});patch({id:post.id,share_count:r.share_count})
    const url=sharePath(window.location.origin,r.share_path)
    if(navigator.share){try{await navigator.share({title:post.caption||t('Travel Reels'),url})}catch(e){if(e?.name!=='AbortError')throw e}}
    else{try{await navigator.clipboard.writeText(url);say(t('Link copied'))}catch{say(url)}}
  })
  async function conflict(){try{patch(await api(`/social/posts/${post.id}`,{cache:'no-store'}))}catch{/* the message is already shown */}}

  const tabs=<div className="rl-top" role="tablist" aria-label={t('Travel Reels')}>
    {postId?<Link className="ui-button ui-button-secondary" to="/reels">{t('More reels')}</Link>
      :TABS.map(([code,name])=><Chip key={code} tone="info" role="tab" aria-selected={tab===code} selected={tab===code} onClick={()=>setTab(code)}>{t(name)}</Chip>)}
    {hashtag&&<Chip tone="info" selected onClick={()=>setHashtag('')} aria-label={t('Clear #{value0}',{value0:hashtag})}>#{hashtag} ✕</Chip>}
  </div>
  let body
  if(loading)body=<p className="rl-state" role="status">{t('Loading…')}</p>
  else if(error&&!items.length)body=<EmptyState icon="video" title={error} action={<button type="button" className="ui-button ui-button-secondary" onClick={()=>postId?window.location.reload():feed.reload()}>{t('Try again')}</button>}>{t('Please try again.')}</EmptyState>
  else if(!post)body=<EmptyState icon="video" title={t(tab==='FOLLOWING'?'Nothing from people you follow yet.':'Nothing to watch yet.')}>{hashtag?t('Nothing has this tag yet.'):t('New posts will show here.')}</EmptyState>
  else body=<div className={'rl-wrap'+(panel?' has-panel':'')}>
    <div className="rl-frame" key={post.id}>
      <Media post={post} muted={muted} onSound={()=>setMuted(m=>!m)} onPlaying={countView}/>
      <Overlay post={post} onTag={setHashtag}/>
    </div>
    <Rail post={post} busy={busy} onLike={like} onSave={save} onComments={()=>setPanel('comments')} onShare={share} onFollow={follow} onMenu={()=>setPanel('menu')}/>
    {panel==='comments'&&<CommentsPanel post={post} onClose={()=>setPanel(null)} onCount={n=>typeof n==='number'&&n!==post.comment_count&&patch({id:post.id,comment_count:n})}/>}
    {panel==='menu'&&<MenuPanel post={post} onClose={()=>setPanel(null)} onChoose={setPanel}/>}
    {panel==='report'&&<ReportPanel post={post} onClose={()=>setPanel(null)}/>}
    {panel==='edit'&&<EditPanel post={post} onClose={()=>setPanel(null)} onSaved={saved=>{patch(saved);setPanel(null);say(t('Saved'))}} onConflict={conflict}/>}
    {panel==='remove'&&<RemovePanel post={post} onClose={()=>setPanel(null)} onRemoved={()=>{setPanel(null);if(postId){setSingle({post:null,error:'',loaded:true})}else{feed.setItems(list=>list.filter(item=>item.id!==post.id))}}}/>}
    {next?.post_type==='REEL'&&<video className="rl-preload" src={src(next.media_url)} preload="auto" muted tabIndex={-1} aria-hidden="true"/>}
    {next&&next.post_type!=='REEL'&&next.media_url&&<img className="rl-preload" src={src(next.media_url)} alt="" aria-hidden="true"/>}
  </div>
  return <><Header/><main className="rl-page" id="main">
    {tabs}
    <div className="rl-stage" onWheel={e=>{if(panel||Math.abs(e.deltaY)<20)return;go(e.deltaY>0?1:-1)}}
      onTouchStart={e=>{touchY.current=e.touches[0].clientY}} onTouchEnd={e=>{if(touchY.current==null||panel)return;const dy=touchY.current-e.changedTouches[0].clientY;touchY.current=null;if(Math.abs(dy)>50)go(dy>0?1:-1)}}>
      {body}
      {note.text&&<p className={'rl-note'+(note.warn?' is-warn':'')} role="status">{note.text}</p>}
      {post&&items.length>1&&<div className="rl-nav"><button type="button" className="rl-x" aria-label={t('Previous reel')} disabled={index<=0} onClick={()=>go(-1)}><Icon name="chevron" size={22} style={{transform:'rotate(-90deg)'}}/></button><button type="button" className="rl-x" aria-label={t('Next reel')} disabled={index>=items.length-1&&!feed.hasMore} onClick={()=>go(1)}><Icon name="chevron" size={22} style={{transform:'rotate(90deg)'}}/></button></div>}
    </div>
  </main></>
}
