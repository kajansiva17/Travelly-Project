import { t } from '../../i18n/language.js'
import {useEffect,useRef,useState} from 'react'
import {api} from '../../services/api'
import {Icon} from '../../components/components'

/* Contact bar for the people on a live booking: Call buttons + a Chat button.
   GET /bookings/{id}/contacts gives `allowed` (numbers may be shown: inside the Admin's window before the start, always for Book now), `contacts`,
   `chat` (open from confirmation until the trip ends) and `opens_at`. The call button opens the phone's own dialer (tel:); nothing is kept on the device.
   `lazy` asks for the number only when tapped (long lists, such as the travellers of a departure). Chat: GET/POST /bookings/{id}/messages, refreshed while open. */
const label=role=>role==='DRIVER'?t('Call driver'):role==='OWNER'?t('Call owner'):t('Call passenger')
const roleName=role=>role==='DRIVER'?t('Driver'):role==='OWNER'?t('Owner'):t('Passenger')
const clock=iso=>{try{return new Date(iso).toLocaleString([],{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'})}catch{return ''}}
const hour=iso=>{try{return new Date(iso).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})}catch{return ''}}

export function ChatPanel({bookingId,onClose}){
  const [items,setItems]=useState(null),[canWrite,setCanWrite]=useState(true),[text,setText]=useState(''),[busy,setBusy]=useState(false),[problem,setProblem]=useState(''),end=useRef(null),count=useRef(0)
  const path=`/bookings/${encodeURIComponent(bookingId)}/messages`
  const load=()=>api(path,{cache:'no-store'}).then(r=>{setItems(r.items||[]);setCanWrite(r.can_write!==false);setProblem(p=>p===t('Messages could not be loaded.')?'':p)}).catch(()=>setProblem(t('Messages could not be loaded.')))
  useEffect(()=>{load();const timer=setInterval(()=>{if(!document.hidden)load()},5000);return()=>clearInterval(timer)},[bookingId])
  useEffect(()=>{if((items||[]).length!==count.current){count.current=(items||[]).length;end.current?.scrollIntoView?.({block:'end'})}},[items])
  useEffect(()=>{const key=event=>{if(event.key==='Escape')onClose()};window.addEventListener('keydown',key);return()=>window.removeEventListener('keydown',key)},[])
  async function send(event){
    event.preventDefault();const body=text.trim();if(!body||busy)return
    setBusy(true);setProblem('')
    try{await api(path,{method:'POST',body:JSON.stringify({body})});setText('');await load()}
    catch(error){setProblem(error?.code==='CHAT_CLOSED'?t('This chat is closed because the trip is over.'):t('The message could not be sent. Please try again.'));load()}
    finally{setBusy(false)}
  }
  return <div className="chat-backdrop" role="presentation" onMouseDown={event=>{if(event.target===event.currentTarget)onClose()}}>
    <section className="chat-panel" role="dialog" aria-modal="true" aria-label={t('Booking chat')}>
      <header className="chat-head"><span className="chat-title"><Icon name="chat" size={18}/>{t('Booking chat')}</span><button type="button" className="ui-button ui-button-secondary chat-close" onClick={onClose} aria-label={t('Close')}><Icon name="close" size={16}/></button></header>
      <div className="chat-list" aria-live="polite">
        {items===null&&!problem&&<p className="chat-empty" role="status">{t('Loading…')}</p>}
        {items&&!items.length&&<p className="chat-empty">{t('No messages yet. Say hello.')}</p>}
        {(items||[]).map(m=><div key={m.id} className={'chat-row'+(m.mine?' is-mine':'')}><div className="chat-bubble">{!m.mine&&<strong className="chat-who">{m.name?m.name+' · ':''}{roleName(m.role)}</strong>}<p>{m.body}</p><small>{hour(m.created_at)}</small></div></div>)}
        <span ref={end}/>
      </div>
      {problem&&<p className="chat-problem" role="alert">{problem}</p>}
      {canWrite?<form className="chat-form" onSubmit={send}>
        <textarea rows={1} maxLength={500} value={text} placeholder={t('Type a message')} aria-label={t('Type a message')} onChange={event=>setText(event.target.value)} onKeyDown={event=>{if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();send(event)}}}/>
        <button type="submit" className="ui-button ui-button-primary" disabled={busy||!text.trim()}>{busy?t('Sending…'):t('Send')}</button>
      </form>:<p className="chat-closed">{t('This chat is closed because the trip is over.')}</p>}
    </section>
  </div>
}

export default function CallContact({bookingId,refreshKey,lazy=false}){
  const [info,setInfo]=useState(null),[busy,setBusy]=useState(false),[none,setNone]=useState(false),[chat,setChat]=useState(false)
  const read=()=>api(`/bookings/${encodeURIComponent(bookingId)}/contacts`,{cache:'no-store'})
  useEffect(()=>{
    if(!bookingId||lazy)return undefined
    let alive=true
    read().then(r=>alive&&setInfo(r||null)).catch(()=>alive&&setInfo(null))
    return()=>{alive=false}
  },[bookingId,refreshKey])
  if(!bookingId)return null
  const contacts=info?.allowed?info.contacts||[]:[]
  const soon=info&&!info.allowed&&info.opens_at
  async function dial(){
    if(busy)return;setBusy(true);setNone(false)
    try{const r=await read();const list=r?.allowed?r.contacts||[]:[];if(list[0]?.phone)window.location.href=`tel:${list[0].phone}`;else setNone(true)}catch{setNone(true)}finally{setBusy(false)}
  }
  if(!lazy&&!info?.chat&&!contacts.length)return null
  return <span className="call-contacts">
    {lazy?<button type="button" className="ui-button ui-button-secondary call-contact" disabled={busy} onClick={dial} title={t('The number is shown only while the trip is on.')}><Icon name="phone" size={16}/>{t('Call passenger')}</button>
      :contacts.map(c=><a key={c.role} className="ui-button ui-button-secondary call-contact" href={`tel:${c.phone}`} title={t('The number is shown only while the trip is on.')}><Icon name="phone" size={16}/><span>{label(c.role)}</span><small>{c.name?c.name+' · ':''}{c.phone}</small></a>)}
    {(lazy||info?.chat)&&<button type="button" className="ui-button ui-button-secondary call-contact" onClick={()=>setChat(true)}><Icon name="chat" size={16}/>{t('Chat')}</button>}
    {none&&<small role="status">{t('No number to call right now.')}</small>}
    {!lazy&&soon&&<small className="call-soon" role="status">{t('You can call from {value0}. Until then, send a message.',{value0:clock(info.opens_at)})}</small>}
    {chat&&<ChatPanel bookingId={bookingId} onClose={()=>setChat(false)}/>}
  </span>
}
