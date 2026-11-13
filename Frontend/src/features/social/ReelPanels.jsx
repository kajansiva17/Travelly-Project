import { t } from '../../i18n/language.js'
import React,{useEffect,useRef,useState} from 'react'
import {api} from '../../services/api'
import {Icon} from '../../components/components'
import {fieldErrorMap,fieldErrorText} from '../../services/fieldErrors.js'
import {formatDateTime} from '../../i18n/dateTime.js'
import {VISIBILITY,parseTags} from './socialModel'

/* Panels that open over the reel (contract 03SO, section 3): comments with one level of replies, the ⋯ menu, report, edit, remove. */
export function PanelShell({title,onClose,children}){
  const ref=useRef(null)
  useEffect(()=>{ref.current?.focus()},[])
  return <section className="rl-panel" role="dialog" aria-label={title} ref={ref} tabIndex={-1} onKeyDown={e=>{if(e.key==='Escape'){e.stopPropagation();onClose()}}}>
    <header><h3>{title}</h3><button type="button" className="rl-x" onClick={onClose} aria-label={t('Close')}><Icon name="close" size={20}/></button></header>
    <div className="rl-panel-body">{children}</div></section>
}

function Comment({item,onReply,onRemove,reply=false}){
  return <li className={'rl-comment'+(reply?' is-reply':'')}>
    <div><strong>{item.author?.name}</strong> <small>{formatDateTime(item.created_at)}</small></div>
    <p>{item.text}</p>
    <div className="rl-comment-actions">{!reply&&<button type="button" onClick={()=>onReply(item)}>{t('Reply')}</button>}{reply&&<button type="button" onClick={()=>onReply(item)}>{t('Reply')}</button>}{item.can_remove&&<button type="button" onClick={()=>onRemove(item)}>{t('Remove')}</button>}</div>
    {(item.replies||[]).length>0&&<ul>{item.replies.map(r=><Comment key={r.id} item={r} reply onReply={onReply} onRemove={onRemove}/>)}</ul>}
  </li>
}
export function CommentsPanel({post,onClose,onCount}){
  const [data,setData]=useState(null),[error,setError]=useState(''),[text,setText]=useState(''),[parent,setParent]=useState(null),[busy,setBusy]=useState(false),fields=useRef({})
  const load=()=>api(`/social/posts/${post.id}/comments`,{cache:'no-store'}).then(result=>{setData(result);setError('');onCount(result.comment_count)}).catch(e=>setError(fieldErrorText(e)))
  useEffect(()=>{load()},[post.id])
  async function send(e){
    e.preventDefault();if(busy||!text.trim())return
    setBusy(true);setError('')
    try{await api(`/social/posts/${post.id}/comments`,{method:'POST',body:JSON.stringify({text:text.trim(),...(parent?{parent_id:parent.id}:{})})});setText('');setParent(null);await load()}
    catch(err){fields.current=fieldErrorMap(err);setError(fields.current.text||fieldErrorText(err))}
    finally{setBusy(false)}
  }
  async function remove(item){
    setBusy(true)
    try{await api(`/social/comments/${item.id}/remove`,{method:'POST',body:JSON.stringify({})});await load()}catch(err){setError(fieldErrorText(err))}finally{setBusy(false)}
  }
  const items=data?.items||[]
  return <PanelShell title={t('Comments')} onClose={onClose}>
    {error&&<p className="tk-line is-warn" role="alert">{error}</p>}
    {!data&&!error?<p role="status">{t('Loading…')}</p>:data&&(items.length?<ul className="rl-comments">{items.map(c=><Comment key={c.id} item={c} onReply={setParent} onRemove={remove}/>)}</ul>:<p className="tk-line" role="status">{t('No comments yet.')}</p>)}
    <form className="rl-compose" onSubmit={send}>
      {parent&&<p className="tk-line">{t('Replying to {value0}',{value0:parent.author?.name||''})} <button type="button" onClick={()=>setParent(null)}>{t('Cancel')}</button></p>}
      <input name="text" value={text} maxLength={1000} aria-label={t('Write a comment')} placeholder={t('Write a comment')} onChange={e=>setText(e.target.value)}/>
      <button type="submit" className="ui-button ui-button-primary" disabled={busy||!text.trim()}>{busy?t('Sending…'):t('Send')}</button></form>
  </PanelShell>
}

export function MenuPanel({post,onClose,onChoose}){
  return <PanelShell title={t('More')} onClose={onClose}><div className="rl-menu">
    {post.is_mine
      ?<><button type="button" className="ui-button ui-button-secondary" onClick={()=>onChoose('edit')}>{t('Edit')}</button><button type="button" className="ui-button ui-button-secondary" onClick={()=>onChoose('remove')}>{t('Remove')}</button></>
      :<button type="button" className="ui-button ui-button-secondary" onClick={()=>onChoose('report')}>{t('Report')}</button>}</div></PanelShell>
}

export function ReportPanel({post,onClose}){
  const [reason,setReason]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState(''),[done,setDone]=useState(false)
  async function send(e){
    e.preventDefault();setBusy(true);setError('')
    try{await api(`/social/posts/${post.id}/report`,{method:'POST',body:JSON.stringify({reason:reason.trim()})});setDone(true)}
    catch(err){setError(fieldErrorMap(err).reason||fieldErrorText(err))}finally{setBusy(false)}
  }
  return <PanelShell title={t('Report')} onClose={onClose}>
    {done?<p className="tk-line" role="status">{t('Thank you. Your report was sent.')}</p>
      :<form className="rl-form" onSubmit={send}>
        {error&&<p className="tk-line is-warn" role="alert">{error}</p>}
        <label>{t('Reason')} <span className="req" aria-hidden="true">*</span><input name="reason" minLength={3} maxLength={500} value={reason} onChange={e=>setReason(e.target.value)}/></label>
        <div className="rl-actions"><button type="button" className="ui-button ui-button-secondary" onClick={onClose}>{t('Cancel')}</button><button type="submit" className="ui-button ui-button-primary" disabled={busy||reason.trim().length<3}>{busy?t('Sending…'):t('Send report')}</button></div></form>}
  </PanelShell>
}

export function EditPanel({post,onClose,onSaved,onConflict}){
  const [form,setForm]=useState({caption:post.caption||'',hashtags:(post.hashtags||[]).join(', '),location_name:post.location_name||'',visibility:post.visibility,rating:post.rating||''}),[busy,setBusy]=useState(false),[error,setError]=useState(''),[errors,setErrors]=useState({})
  const set=name=>e=>setForm(c=>({...c,[name]:e.target.value}))
  async function save(e){
    e.preventDefault();setBusy(true);setError('');setErrors({})
    try{
      const body={expected_version:post.version,caption:form.caption,hashtags:parseTags(form.hashtags),location_name:form.location_name,visibility:form.visibility,...(post.post_type==='REVIEW'&&form.rating?{rating:Number(form.rating)}:{})}
      onSaved(await api(`/social/posts/${post.id}`,{method:'PATCH',body:JSON.stringify(body)}))
    }catch(err){
      setErrors(fieldErrorMap(err));setError(fieldErrorText(err))
      if(err.code==='VERSION_CONFLICT')onConflict()
    }finally{setBusy(false)}
  }
  return <PanelShell title={t('Edit')} onClose={onClose}>
    <form className="rl-form" onSubmit={save}>
      {error&&<p className="tk-line is-warn" role="alert">{error}</p>}
      <label>{t('Caption')}<input name="caption" maxLength={2200} value={form.caption} onChange={set('caption')}/>{errors.caption&&<small className="is-warn">{errors.caption}</small>}</label>
      <label>{t('Hashtags')}<input name="hashtags" value={form.hashtags} onChange={set('hashtags')}/>{errors.hashtags&&<small className="is-warn">{errors.hashtags}</small>}</label>
      <label>{t('Place')}<input name="location_name" maxLength={160} value={form.location_name} onChange={set('location_name')}/></label>
      <label>{t('Who can see it')}<select name="visibility" value={form.visibility} onChange={set('visibility')}>{VISIBILITY.map(([value,label])=><option key={value} value={value}>{t(label)}</option>)}</select></label>
      {post.post_type==='REVIEW'&&<label>{t('Rating')}<select name="rating" value={form.rating} onChange={set('rating')}>{[1,2,3,4,5].map(n=><option key={n} value={n}>{n} ★</option>)}</select>{errors.rating&&<small className="is-warn">{errors.rating}</small>}</label>}
      <div className="rl-actions"><button type="button" className="ui-button ui-button-secondary" onClick={onClose}>{t('Cancel')}</button><button type="submit" className="ui-button ui-button-primary" disabled={busy}>{busy?t('Saving…'):t('Save')}</button></div></form>
  </PanelShell>
}

export function RemovePanel({post,onClose,onRemoved}){
  const [busy,setBusy]=useState(false),[error,setError]=useState('')
  async function remove(){
    setBusy(true);setError('')
    try{await api(`/social/posts/${post.id}/remove`,{method:'POST',body:JSON.stringify({})});onRemoved()}catch(err){setError(fieldErrorText(err))}finally{setBusy(false)}
  }
  return <PanelShell title={t('Remove')} onClose={onClose}>
    {error&&<p className="tk-line is-warn" role="alert">{error}</p>}
    <p className="tk-line"><strong>{t('Remove this post?')}</strong></p>
    <div className="rl-actions"><button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={onClose}>{t('Cancel')}</button><button type="button" className="ui-button ui-button-primary" disabled={busy} onClick={remove}>{busy?t('Please wait…'):t('Yes, remove')}</button></div>
  </PanelShell>
}
