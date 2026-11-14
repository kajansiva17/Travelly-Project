import { t, getLanguage } from '../../i18n/language.js'
import {useCallback,useEffect,useRef,useState} from 'react'
import {Icon} from '../../components/components'
import Chip from '../../components/ui/Chip'
import {PlaceSearch} from '../owner/OwnerRates'
import {publicRead} from '../../services/api'
import {useNavigate} from '../passenger/travelRouter'
import {useWorkspace} from '../../context/workspaceContext'
import {recognitionConstructor,speak,speechLang} from '../driver/roadAlertSpeech'
import {aiErrorText,topicRows} from './aiApi'
import {askHelp,helpTopics,searchAssist} from './aiRequests'
import {buildDraft,isHire,missingFor,ticketQuery,writeDraft} from './aiDraft'
import {helpTarget} from './aiHelp'
import {codeEnglish} from '../../i18n/codeLabels.js'

/* Travelly AI chat panel (contract 03AI): "Find a ride" fills the search form step by step and shows it for checking;
   "Help" answers questions about the app from the help guide. The AI never books or pays: the person presses Search,
   chooses a vehicle and books by hand. Text the AI returns is shown as returned. */
const SERVICES=[['local','Local hire'],['airport','Airport hire'],['long-distance','Long distance'],['ticket','Ticket booking']]
const SELECTS={service:SERVICES,journey:[['ONE_WAY','One way'],['RETURN','Return']],duration:[['ONE_DAY','One day'],['MULTI_DAY','Multi-day']]}
const INPUT_TYPE={date:'date',return_date:'date',time:'time',return_time:'time',hours:'number',passengers:'number',large_luggage:'number',small_luggage:'number'}
const freshSearch=()=>({messages:[],filters:{},asking:null,summary:[],ready:false,formPath:null,places:{}})

// One editable row of the "Check your search" card. Pickup and destination use the verified place search for hire.
function CardRow({row,filters,places,onChange,onPlace,hire}){
  const field=row.field,value=filters[field]??row.value??''
  const id='ai-'+field
  let control
  if(SELECTS[field])control=<select id={id} value={value} onChange={e=>onChange(field,e.target.value)}>{SELECTS[field].map(([v,l])=><option key={v} value={v}>{t(l)}</option>)}</select>
  else if((field==='pickup'||field==='destination')&&hire)control=<PlaceSearch compact label={row.label} name={id} value={places[field]||null} onChange={place=>onPlace(field,place)} querySeed={String(value||'')}/>
  else control=<input id={id} type={INPUT_TYPE[field]||'text'} min={INPUT_TYPE[field]==='number'?'0':undefined} value={value} onChange={e=>onChange(field,e.target.value)}/>
  const place=(field==='pickup'||field==='destination')&&hire
  return <div className={'ai-row'+(place?' is-place':'')}>{!place&&<label htmlFor={id}>{row.label}</label>}{control}</div>
}

function CheckCard({reply,state,onChange,onPlace,onSearch,onEditForm,busy,problem}){
  const hire=isHire(state.filters.service),missing=missingFor(state.filters,state.places)
  const labels=Object.fromEntries((reply.summary||[]).map(r=>[r.field,r.label]))
  const needed=missing.map(f=>labels[f]||codeEnglish(f)).join(', ')
  return <section className="ai-card" aria-label={t('Check your search')}>
    <h3>{t('Check your search')}</h3>
    <div className="ai-rows">{(reply.summary||[]).map(row=><CardRow key={row.field} row={row} filters={state.filters} places={state.places} hire={hire} onChange={onChange} onPlace={onPlace}/>)}</div>
    {missing.length>0&&<p className="ai-hint" role="status">{t('Still needed: {value0}',{value0:needed})}</p>}
    {problem&&<p className="ai-hint is-warn" role="status">{problem}</p>}
    <div className="ai-card-actions"><button type="button" className="ui-button ui-button-primary" disabled={busy||missing.length>0} onClick={onSearch}>{t('Search')}</button>
      <button type="button" className="ui-button ui-button-secondary" disabled={busy} onClick={onEditForm}>{t('Edit in form')}</button></div>
  </section>
}

function HelpAnswer({help,workspace,onOpen,onAsk}){
  // The help path is a Passenger path: it opens this person's own workspace copy, and no button shows for a page their role cannot open.
  const target=helpTarget(help.path,{role:workspace?.role||'PASSENGER',allowed:workspace?.allowed||[]})
  return <div className="ai-help">
    {help.title&&<strong>{help.title}</strong>}
    {help.answer&&<p>{help.answer}</p>}
    {help.steps?.length>0&&<>{help.steps_language==='en'&&help.note&&<p className="ai-note">{help.note}</p>}<ol>{help.steps.map((step,i)=><li key={i}>{step}</li>)}</ol></>}
    <div className="ai-help-actions">
      {target&&<button type="button" className="ui-button ui-button-primary" onClick={()=>onOpen(target)}>{help.found===false?t('Support'):t('Open this page')}</button>}
    </div>
    {help.related?.length>0&&<div className="ai-chips">{help.related.map(r=><Chip key={r.topic_id||r.title} tone="info" onClick={()=>onAsk(r.title)}>{r.title}</Chip>)}</div>}
  </div>
}

export default function AiAssistant({onClose,initialTab='search',startVoice=false}){
  const navigate=useNavigate(),workspace=useWorkspace()
  const dialog=useRef(null),list=useRef(null),recognizer=useRef(null),latest=useRef(null)
  const [tab,setTab]=useState(initialTab),[search,setSearch]=useState(freshSearch),[help,setHelp]=useState({messages:[],topics:null})
  const [text,setText]=useState(''),[busy,setBusy]=useState(false),[listening,setListening]=useState(false),[micNote,setMicNote]=useState(''),[blocked,setBlocked]=useState(false),[cardProblem,setCardProblem]=useState('')
  const Recognition=recognitionConstructor()
  useEffect(()=>{latest.current={search,help,tab}},[search,help,tab])
  useEffect(()=>{dialog.current?.showModal();return()=>{stopMic();globalThis.speechSynthesis?.cancel?.();try{dialog.current?.close()}catch{/* Already closed. */}}},[])
  useEffect(()=>{if(list.current)list.current.scrollTop=list.current.scrollHeight},[search.messages.length,help.messages.length,tab,busy])
  // "What can I ask?": every help topic, read once when the Help tab is first opened.
  useEffect(()=>{
    if(tab!=='help'||help.topics!==null)return undefined
    let alive=true
    helpTopics(getLanguage()).then(r=>{if(alive)setHelp(h=>({...h,topics:topicRows(r)}))}).catch(()=>{if(alive)setHelp(h=>({...h,topics:[]}))})
    return()=>{alive=false}
  },[tab,help.topics])
  const stopMic=()=>{const r=recognizer.current;recognizer.current=null;try{r&&r.abort&&r.abort()}catch{/* Already stopped. */}}

  const close=useCallback(()=>onClose&&onClose(),[onClose])
  const say=question=>{if(question)speak(question,speechLang(getLanguage()))}   // text is always shown; speech only when the device has a voice for the language

  async function sendSearch(message,{label,fromVoice=false}={}){
    const value=String(message||'').trim().slice(0,500);if(!value||busy)return
    const state=latest.current.search
    setText('');setBusy(true);setCardProblem('')
    setSearch(s=>({...s,messages:[...s.messages,{role:'user',text:label||value}]}))
    try{
      const r=await searchAssist({message:value,language:getLanguage(),filters:state.filters,asking:state.asking})
      setSearch(s=>({...s,filters:r.filters||{},asking:r.asking||null,summary:r.summary||[],ready:Boolean(r.ready),formPath:r.form_path||null,messages:[...s.messages,{role:'ai',text:r.question,notes:r.notes||[],options:r.options||[],ready:Boolean(r.ready),reply:r}]}))
      if(fromVoice)say(r.question)
    }catch(error){setSearch(s=>({...s,messages:[...s.messages,{role:'ai',text:aiErrorText(error),error:true}]}))}
    finally{setBusy(false)}
  }
  async function sendHelp(question,{fromVoice=false}={}){
    const value=String(question||'').trim().slice(0,500);if(!value||busy)return
    setText('');setBusy(true)
    setHelp(h=>({...h,messages:[...h.messages,{role:'user',text:value}]}))
    try{
      const r=await askHelp({question:value,language:getLanguage()})
      setHelp(h=>({...h,messages:[...h.messages,{role:'ai',help:r}]}))
    }catch(error){setHelp(h=>({...h,messages:[...h.messages,{role:'ai',text:aiErrorText(error),error:true}]}))}
    finally{setBusy(false)}
  }
  const submit=(value,options)=>latest.current.tab==='search'?sendSearch(value,options):sendHelp(value,options)

  // One tap, one answer: the microphone listens once and is off again. It is never on between answers.
  function mic(){
    if(!Recognition||blocked||busy)return
    if(listening){stopMic();setListening(false);return}
    globalThis.speechSynthesis?.cancel?.()
    setMicNote('')
    const recognition=new Recognition()
    recognition.lang=speechLang(getLanguage());recognition.interimResults=false;recognition.maxAlternatives=1;recognition.continuous=false
    let got=false
    recognition.onresult=event=>{const said=event.results?.[0]?.[0]?.transcript||'';if(!said||got)return;got=true;recognizer.current=null;setListening(false);submit(said,{fromVoice:true})}
    recognition.onerror=event=>{
      recognizer.current=null;setListening(false)
      if(event.error==='not-allowed'||event.error==='service-not-allowed'){setBlocked(true);setMicNote(t('The microphone is not allowed. You can type instead.'))}
      else if(event.error==='no-speech')setMicNote(t('We did not hear anything. Try again or type.'))
      else if(event.error!=='aborted')setMicNote(t('Voice did not work. You can type instead.'))
    }
    recognition.onend=()=>{if(recognizer.current===recognition){recognizer.current=null;setListening(false)}}
    recognizer.current=recognition;setListening(true)
    try{recognition.start()}catch{recognizer.current=null;setListening(false);setMicNote(t('Voice did not work. You can type instead.'))}
  }
  useEffect(()=>{if(startVoice&&Recognition)mic()},[])   // "Talk by voice" opens the panel and starts listening once

  // --- the "Check your search" card ---
  const edit=(field,value)=>{setCardProblem('');setSearch(s=>({...s,filters:{...s.filters,[field]:value}}))}
  const pickPlace=(field,place)=>setSearch(s=>({...s,places:{...s.places,[field]:place||undefined},filters:place?{...s.filters,[field]:place.label}:s.filters}))
  const go=path=>{close();navigate(path)}
  async function runSearch(){
    const f=latest.current.search.filters
    if(f.service==='ticket'){go('/travel/book/tickets?'+ticketQuery(f));return}
    setBusy(true);setCardProblem('')
    try{
      const services=(await publicRead('/service-types')).items||[]
      const draft=buildDraft(f,{services,places:latest.current.search.places})
      if(!draft.serviceTypeId){setCardProblem(t('This service is not available right now. Try another service.'));return}
      writeDraft(draft);go('/travel/book/vehicles')
    }catch(error){setCardProblem(aiErrorText(error))}
    finally{setBusy(false)}
  }
  async function editInForm(){
    const s=latest.current.search,f=s.filters
    if(f.service==='ticket'){go('/travel/book/tickets?'+ticketQuery(f));return}
    try{
      let services=[];if(isHire(f.service)){services=(await publicRead('/service-types')).items||[]}
      writeDraft(buildDraft(f,{services,places:s.places}))
    }catch{/* The form still opens, without the saved values. */}
    go(s.formPath||'/travel/book/service')
  }

  const lastAi=[...search.messages].reverse().find(m=>m.role==='ai'),convo=tab==='search'?search.messages:help.messages
  const placeholder=tab==='search'?t('Where do you want to go?'):t('Ask how to do something in Travelly')
  const micHidden=!Recognition||blocked
  return <dialog ref={dialog} className="ai-dialog" aria-label={t('Travelly AI')} onClose={close} onClick={e=>{if(e.target===dialog.current)dialog.current.close()}}>
    <div className="ai-panel">
      <header className="ai-head"><h2><Icon name="spark" size={20}/>{t('Travelly AI')}</h2><button type="button" className="ai-x" aria-label={t('Close')} onClick={()=>dialog.current.close()}><Icon name="close" size={20}/></button></header>
      <div className="ai-tabs" role="tablist" aria-label={t('Travelly AI')}>{[['search','Find a ride'],['help','Help']].map(([id,name])=><button key={id} type="button" role="tab" aria-selected={tab===id} className={tab===id?'is-active':''} onClick={()=>setTab(id)}>{t(name)}</button>)}</div>
      <div className="ai-messages" ref={list} role="log" aria-live="polite">
        {tab==='help'&&help.topics&&help.topics.length>0&&<section className="ai-topics" aria-label={t('What can I ask?')}><strong>{t('What can I ask?')}</strong><div className="ai-chips">{help.topics.map(topic=><Chip key={topic.id} tone="info" onClick={()=>sendHelp(topic.title)}>{topic.title}</Chip>)}</div></section>}
        {convo.length===0&&<p className="ai-intro">{t('Hi! Tell me where you want to go, or ask how to do something in Travelly.')}</p>}
        {convo.map((m,i)=>m.role==='user'
          ?<div className="ai-msg is-user" key={i}>{m.text}</div>
          :<div className={'ai-msg is-ai'+(m.error?' is-error':'')} key={i}>
            {m.notes?.map((n,k)=><p className="ai-note" key={k}>{n}</p>)}
            {m.help?<HelpAnswer help={m.help} workspace={workspace} onOpen={go} onAsk={sendHelp}/>:<p>{m.text}</p>}
            {m.options?.length>0&&m===lastAi&&!busy&&<div className="ai-chips" role="group" aria-label={t('Quick replies')}>{m.options.map(o=><Chip key={o.value} tone="info" onClick={()=>sendSearch(o.value,{label:o.label})}>{o.label}</Chip>)}</div>}
            {m.ready&&m===lastAi&&<CheckCard reply={m.reply} state={search} onChange={edit} onPlace={pickPlace} onSearch={runSearch} onEditForm={editInForm} busy={busy} problem={cardProblem}/>}
          </div>)}
        {busy&&<div className="ai-msg is-ai is-busy" role="status"><span className="ai-dots" aria-label={t('Thinking…')}><i/><i/><i/></span></div>}
      </div>
      {(micNote||!Recognition)&&<p className="ai-hint" role="status">{micNote||t('Voice is not available on this device. You can type instead.')}</p>}
      <form className="ai-composer" onSubmit={e=>{e.preventDefault();submit(text)}}>
        <input type="text" name="ai-message" value={text} maxLength={500} placeholder={placeholder} aria-label={placeholder} onChange={e=>setText(e.target.value)}/>
        {!micHidden&&<button type="button" className={'ai-mic'+(listening?' is-live':'')} aria-label={listening?t('Stop listening'):t('Speak')} title={listening?t('Stop listening'):t('Speak')} onClick={mic} disabled={busy}><Icon name="mic" size={22}/></button>}
        <button type="submit" className="ui-button ui-button-primary" disabled={busy||!text.trim()}>{t('Send')}</button>
      </form>
      {listening&&<p className="ai-hint" role="status">{t('Listening…')}</p>}
    </div>
  </dialog>
}
