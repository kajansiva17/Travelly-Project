import { t } from '../../i18n/language.js'
import {useEffect,useState} from 'react'
import {Link as PlainLink} from 'react-router-dom'
import {Link,useNavigate} from '../passenger/travelRouter'
import {Icon,useSession} from '../../components/components'
import {useWorkspace} from '../../context/workspaceContext'
import {workspaceRoles} from '../../routes/workspaceRoutes'
import {api} from '../../services/api'
import {fieldErrorText} from '../../services/fieldErrors.js'
import {src} from './mediaSrc'
import {PanelShell} from './ReelPanels'

/* Travel Reels on a phone (up to 767 px) looks like a short-video app: Following / For you and a search icon over the video,
   a bottom bar with Home, Add (+) and Profile. The same feed, panels and gestures as the desktop page are used underneath. */
const QUERY='(max-width: 767px)'
export function usePhone(){
  const [phone,setPhone]=useState(()=>Boolean(window.matchMedia?.(QUERY).matches))
  useEffect(()=>{
    const list=window.matchMedia?.(QUERY);if(!list)return undefined
    const sync=()=>setPhone(list.matches);list.addEventListener('change',sync);sync()
    return()=>list.removeEventListener('change',sync)
  },[])
  return phone
}

export function PhoneTop({tab,onTab,onSearch,hashtag,onClearTag,single}){
  return <div className="rl-tt-top">
    {single?<PlainLink className="rl-tt-icon" to="/reels" aria-label={t('Back')}><Icon name="chevron" size={22}/></PlainLink>:<span className="rl-tt-icon is-empty" aria-hidden="true"/>}
    <div className="rl-tt-tabs" role="tablist" aria-label={t('Travel Reels')}>
      <button type="button" role="tab" aria-selected={tab==='FOLLOWING'} className={tab==='FOLLOWING'?'is-on':''} onClick={()=>onTab('FOLLOWING')}>{t('Following')}</button>
      <button type="button" role="tab" aria-selected={tab===''} className={tab===''?'is-on':''} onClick={()=>onTab('')}>{t('For you')}</button>
    </div>
    <button type="button" className="rl-tt-icon" onClick={onSearch} aria-label={t('Search people')}><Icon name="search" size={22}/></button>
    {hashtag&&<button type="button" className="rl-tt-tag" onClick={onClearTag} aria-label={t('Clear #{value0}',{value0:hashtag})}>#{hashtag} ✕</button>}
  </div>
}

export function PhoneBottom({author}){
  const workspace=useWorkspace(),signedIn=useSession(),navigate=useNavigate()
  const [adding,setAdding]=useState(false),[busy,setBusy]=useState(false)
  const home=workspaceRoles[workspace?.role]?.home||'/dashboard'
  const profile=async()=>{
    if(author){navigate(`/social/users/${encodeURIComponent(author)}`);return}
    if(busy)return;setBusy(true)
    try{const me=await api('/users/me',{cache:'no-store'});if(me?.public_user_reference)navigate(`/social/users/${encodeURIComponent(me.public_user_reference)}`)}catch{/* not signed in or offline */}finally{setBusy(false)}
  }
  return <>
    <nav className="rl-tt-bar" aria-label={t('Travel Reels')}>
      <PlainLink to={home} className="rl-tt-item"><Icon name="home" size={22}/><span>{t('Home')}</span></PlainLink>
      {signedIn?<button type="button" className="rl-tt-add" onClick={()=>setAdding(true)} aria-label={t('Add')} aria-haspopup="dialog"><Icon name="plus" size={24}/></button>
        :<PlainLink to="/login" className="rl-tt-add" aria-label={t('Add')}><Icon name="plus" size={24}/></PlainLink>}
      {signedIn?<button type="button" className="rl-tt-item" onClick={profile} disabled={busy}><Icon name="user" size={22}/><span>{t('Profile')}</span></button>
        :<PlainLink to="/login" className="rl-tt-item"><Icon name="user" size={22}/><span>{t('Profile')}</span></PlainLink>}
    </nav>
    {adding&&<div className="rl-tt-sheet" role="dialog" aria-modal="true" aria-label={t('Add')} onClick={()=>setAdding(false)}>
      <div className="rl-tt-card" onClick={e=>e.stopPropagation()}>
        <h2>{t('What do you want to post?')}</h2>
        <Link to="/social/post?type=REEL" className="rl-tt-kind"><Icon name="video" size={22}/>{t('Reel')}</Link>
        <Link to="/social/post?type=PHOTO" className="rl-tt-kind"><Icon name="grid" size={22}/>{t('Photo')}</Link>
        <Link to="/social/post?type=REVIEW" className="rl-tt-kind"><Icon name="star" size={22}/>{t('Review')}</Link>
        <button type="button" className="rl-tt-cancel" onClick={()=>setAdding(false)}>{t('Cancel')}</button>
      </div>
    </div>}
  </>
}

export function PhoneSearch({onClose}){
  const [text,setText]=useState(''),[state,setState]=useState({items:[],loading:false,error:'',done:false})
  useEffect(()=>{
    const q=text.trim();if(q.length<2){setState({items:[],loading:false,error:'',done:false});return undefined}
    let alive=true;setState(s=>({...s,loading:true,error:''}))
    const id=setTimeout(()=>{api(`/social/users?q=${encodeURIComponent(q)}`,{cache:'no-store'}).then(r=>alive&&setState({items:r.items||[],loading:false,error:'',done:true})).catch(e=>alive&&setState({items:[],loading:false,error:fieldErrorText(e),done:true}))},350)
    return()=>{alive=false;clearTimeout(id)}
  },[text])
  return <div className="rl-tt-search" role="dialog" aria-modal="true" aria-label={t('Search people')}>
    <div className="rl-tt-field">
      <Icon name="search" size={20}/>
      <input type="search" autoFocus value={text} maxLength={50} onChange={e=>setText(e.target.value)} placeholder={t('Search people')} aria-label={t('Search people')}/>
      <button type="button" onClick={onClose}>{t('Cancel')}</button>
    </div>
    <div className="rl-tt-results" aria-live="polite">
      {state.loading&&<p role="status">{t('Searching…')}</p>}
      {state.error&&<p role="alert">{state.error}</p>}
      {!state.loading&&!state.error&&state.done&&!state.items.length&&<p>{t('No people found.')}</p>}
      {state.items.map(u=><Link key={u.reference} to={`/social/users/${encodeURIComponent(u.reference)}`} className="rl-tt-person" onClick={onClose}>
        {u.profile_image_url?<img src={src(u.profile_image_url)} alt=""/>:<span className="rl-tt-face"><Icon name="user" size={20}/></span>}<b>{u.name}</b>
      </Link>)}
    </div>
  </div>
}

// Share sheet: each app opens its own "share this link" page. Instagram and TikTok have no such page, so "More" hands over to the phone's share sheet.
export function ShareSheet({post,url,onClose,onNote}){
  const text=post.caption||t('Travel Reels'),both=encodeURIComponent(`${text} ${url}`),link=encodeURIComponent(url),words=encodeURIComponent(text)
  const apps=[
    ['WhatsApp','W','#25d366',`https://wa.me/?text=${both}`],
    ['Facebook','f','#1877f2',`https://www.facebook.com/sharer/sharer.php?u=${link}`],
    ['Telegram','T','#229ed9',`https://t.me/share/url?url=${link}&text=${words}`],
    ['X','X','#111',`https://twitter.com/intent/tweet?url=${link}&text=${words}`],
    [t('Message'),'SMS','#16a34a',`sms:?body=${both}`],
    [t('Email'),'@','#e10b17',`mailto:?subject=${words}&body=${both}`]
  ]
  const copy=async()=>{try{await navigator.clipboard.writeText(url);onNote(t('Link copied'))}catch{onNote(url)}onClose()}
  const more=async()=>{try{await navigator.share({title:t('Travel Reels'),text,url})}catch(e){if(e?.name!=='AbortError')onNote(url,true)}onClose()}
  return <PanelShell title={t('Share to')} onClose={onClose}>
    <div className="rl-share">
      {apps.map(([name,mark,color,href])=><a key={name} className="rl-share-app" href={href} target="_blank" rel="noopener noreferrer" onClick={onClose}><span style={{background:color}}>{mark}</span><small>{name}</small></a>)}
      <button type="button" className="rl-share-app" onClick={copy}><span className="is-plain"><Icon name="document" size={22}/></span><small>{t('Copy link')}</small></button>
      {typeof navigator.share==='function'&&<button type="button" className="rl-share-app" onClick={more}><span className="is-plain"><Icon name="share" size={22}/></span><small>{t('More')}</small></button>}
    </div>
  </PanelShell>
}
