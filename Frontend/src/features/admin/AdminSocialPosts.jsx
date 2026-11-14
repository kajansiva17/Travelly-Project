import { t } from '../../i18n/language.js'
import {useEffect,useRef,useState} from 'react'
import {api} from '../../services/api'
import {Field,RateErrors} from '../owner/OwnerRates'
import Chip from '../../components/ui/Chip'
import {formatDateTime} from '../../i18n/dateTime.js'
import {fieldErrorMap,fieldErrorText} from '../../services/fieldErrors.js'
import {src} from '../social/mediaSrc'
import AdminList,{Facts} from './AdminList'

/* Admin → Social reviews (contract 03SO, section 5): GET /admin/social/posts (latest 200, each with open_reports and signed media links),
   reported posts first. Hide or Restore a post with a reason and a confirm step: POST .../moderation { expected_version, action, reason }.
   Hiding or restoring closes the post's open reports. Every decision is audited by the server. */
const FILTERS=[['reported','Reported','?reported=true'],['all','All posts',''],['hidden','Hidden','?status=HIDDEN']]
const TYPE={REEL:'Reel',PHOTO:'Photo',REVIEW:'Review'}
const when=value=>value?formatDateTime(value):'—'
const reportLine=report=>typeof report==='string'?report:[report?.reason||report?.text||'',when(report?.created_at||report?.reported_at||report?.at)].filter(Boolean).join(' · ')

function Media({post}){
  if(!post.media_url&&!post.thumbnail_url)return null
  return post.post_type==='REEL'
    ?<video className="as-media" src={src(post.media_url)} poster={src(post.thumbnail_url)||undefined} controls preload="none"/>
    :<img className="as-media" src={src(post.media_url||post.thumbnail_url)} alt={post.caption||t('Post')}/>
}
function Moderation({post,onChanged}){
  const [done,setDone]=useState(''),[action,setAction]=useState(null),[reason,setReason]=useState(''),[confirm,setConfirm]=useState(false),[busy,setBusy]=useState(false),[message,setMessage]=useState(''),[errors,setErrors]=useState({}),sending=useRef(false)
  const hidden=post.moderation_status==='HIDDEN',verb=hidden?'RESTORE':'HIDE',reports=post.open_reports||[]
  async function send(){
    if(sending.current)return
    sending.current=true;setBusy(true);setMessage('');setErrors({})
    try{
      const saved=await api(`/admin/social/posts/${post.id}/moderation`,{method:'POST',body:JSON.stringify({expected_version:post.version,action:verb,reason:reason.trim()})})
      setAction(null);setConfirm(false);setReason('');const text=hidden?t('The post is visible again.'):t('The post is hidden.');setDone(text);onChanged('',false,saved)
    }catch(error){
      setConfirm(false);setErrors(fieldErrorMap(error));setMessage(fieldErrorText(error))
      if(error.code==='VERSION_CONFLICT'||error.code==='NO_CHANGE')onChanged('',true)
    }finally{sending.current=false;setBusy(false)}
  }
  return <RateErrors.Provider value={errors}><div className="tk-pane as-detail">
    <div className="as-top"><Media post={post}/>
      <div className="as-info"><Facts cols={2} entries={[[t('Author'),`${post.author?.name||'—'} · ${post.author?.reference||''}`],[t('Type'),t(TYPE[post.post_type]||post.post_type)],[t('Status'),hidden?t('Hidden'):t('Visible')],[t('Who can see it'),t(post.visibility==='PUBLIC'?'Everyone':post.visibility==='FOLLOWERS'?'Followers':'Only me')],[t('Published'),when(post.published_at)],[t('Caption'),post.caption||'—']]}/>
        <h4 className="as-h">{t('Open reports')} ({reports.length})</h4>
        {reports.length?<ul className="as-reports">{reports.map((r,i)=><li key={i}>{reportLine(r)}</li>)}</ul>:<p className="tk-line">{t('No open reports.')}</p>}</div></div>
    {message&&<p className="tk-line is-warn" role="alert">{message}</p>}
    {done?<p className="tk-line" role="status"><Chip tone="success" icon="check">{done}</Chip></p>
      :!action?<div className="tk-bar"><button type="button" className={'ui-button '+(hidden?'ui-button-secondary':'ui-button-primary')} onClick={()=>{setAction(verb);setMessage('')}}>{hidden?t('Restore'):t('Hide')}</button></div>
      :confirm
        ?<div className="tk-hold"><p className="tk-line"><strong>{hidden?t('Show this post again?'):t('Hide this post from everyone?')}</strong> {reason.trim()}</p>
          <div className="tk-bar"><button type="button" className="ui-button ui-button-primary" disabled={busy} onClick={send}>{busy?t('Please wait…'):hidden?t('Yes, restore'):t('Yes, hide')}</button><button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={()=>setConfirm(false)}>{t('Back')}</button></div></div>
        :<div className="tk-bar ap-record"><div className="ap-reference"><Field label="Reason" help="Why you are doing this. It is kept in the audit record."><input name="reason" maxLength="500" value={reason} onChange={e=>setReason(e.target.value)}/></Field></div>
          <button type="button" className="ui-button ui-button-secondary" onClick={()=>{setAction(null);setReason('');setErrors({})}}>{t('Cancel')}</button>
          <button type="button" className="ui-button ui-button-primary" disabled={!reason.trim()} onClick={()=>{setMessage('');setConfirm(true)}}>{hidden?t('Restore'):t('Hide')}</button></div>}
  </div></RateErrors.Provider>
}

export default function AdminSocialPosts(){
  const [filter,setFilter]=useState('reported'),[items,setItems]=useState(null),[error,setError]=useState(null),[notice,setNotice]=useState(''),[fresh,setFresh]=useState({})
  const load=()=>api('/admin/social/posts'+FILTERS.find(f=>f[0]===filter)[2],{cache:'no-store'}).then(r=>{setItems(r.items||[]);setError(null);return r.items||[]}).catch(e=>{setError(e);setItems(items||[]);return null})
  useEffect(()=>{setItems(null);setFresh({});load()},[filter])
  /* After Hide or Restore the open details show the post as it is now. Hiding closes its reports, so under "Reported" the post
     leaves the list: then it is read again from the full list (GET /admin/social/posts). */
  const keep=post=>post?.id&&setFresh(current=>({...current,[post.id]:post}))
  async function changed(id,saved){
    if(saved?.id===id&&saved.moderation_status)keep(saved)
    const list=await load()
    if(list&&!list.some(p=>p.id===id))api('/admin/social/posts',{cache:'no-store'}).then(r=>keep((r.items||[]).find(p=>p.id===id))).catch(()=>{})
    else if(list)setFresh(current=>{const next={...current};delete next[id];return next})
  }
  return <AdminList heading={t('Social reviews')} icon="video" title={t('Posts')} info={t('Hiding a post removes it from every feed. Restoring shows it again. Each decision is kept in the audit record.')} notice={notice} error={error}
    filters={<div className="tk-bar" role="group" aria-label={t('Show')}>{FILTERS.map(([code,name])=><Chip key={code} tone="info" selected={filter===code} onClick={()=>setFilter(code)}>{t(name)}</Chip>)}</div>} filterCols={1}
    items={items} empty={filter==='reported'?t('No post has an open report.'):t('No posts.')}
    row={p=>{const reports=(p.open_reports||[]).length;return {key:p.id,title:`${p.author?.name||'—'} · ${t(TYPE[p.post_type]||p.post_type)}`,meta:`${(p.caption||'').slice(0,90)||'—'} · ${when(p.published_at)}${reports?` · ${t('{value0} open reports',{value0:reports})}`:''}`,status:p.moderation_status==='HIDDEN'?t('Hidden'):t('Visible'),tone:p.moderation_status==='HIDDEN'?'danger':'success'}}}
    detailTitle={p=>`${p.author?.name||''} · ${t(TYPE[p.post_type]||p.post_type)}`}
    detail={p=><Moderation key={p.id} post={fresh[p.id]||p} onChanged={(text,quiet,saved)=>{if(text)setNotice(text);changed(p.id,saved)}}/>}/>
}
