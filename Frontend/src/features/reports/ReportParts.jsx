import { t } from '../../i18n/language.js'
import {useEffect,useRef,useState} from 'react'
import {api} from '../../services/api'
import {Icon} from '../../components/components'
import {fieldErrorText} from '../../services/fieldErrors.js'
import {FIRST_MONTH,thisMonth} from './reportModel'

/* Shared pieces of the Owner and Admin monthly reports (contract 03RP). Mobile first: tiles in 2 columns (1 under 360px),
   tables that become stacked cards on phones, a full-width Download PDF button at the bottom. */
export function MonthPicker({value,onChange,disabled}){
  return <label className="rp-month"><span>{t('Month')}</span>
    <input type="month" name="month" value={value} min={FIRST_MONTH} max={thisMonth()} disabled={disabled} onChange={e=>{const v=e.target.value;if(v&&v>=FIRST_MONTH&&v<=thisMonth())onChange(v)}}/></label>
}

// tone: '' | 'good' | 'bad'. The icon repeats the meaning so colour is not the only cue.
export function Tiles({items}){
  return <div className="rp-tiles">{items.map(({key,label,value,tone='',onClick})=>{
    const inner=<><span className="rp-tile-label">{tone==='good'&&<Icon name="check" size={14}/>}{tone==='bad'&&<Icon name="alert" size={14}/>}{label}</span><strong>{value}</strong></>
    return onClick?<button type="button" key={key} className={'rp-tile '+tone} onClick={onClick}>{inner}</button>:<div key={key} className={'rp-tile '+tone}>{inner}</div>})}</div>
}

/* Income − expenses = profit or loss. Green with a ✓ for profit, red with a ▼ for loss. */
export function ResultCard({income,expenses,profit,loss,labels,children,compact=false,ops=['−','=']}){
  const [a,b,c]=labels
  return <section className={'rp-result '+(loss?'is-loss':'is-profit')+(compact?' is-compact':'')} aria-label={t('Month result')}>
    <div><span>{a}</span><strong>{income}</strong></div><i aria-hidden="true">{ops[0]}</i>
    <div><span>{b}</span><strong>{expenses}</strong></div><i aria-hidden="true">{ops[1]}</i>
    <div className="rp-result-main"><span>{loss?<>▼ </>:<>✓ </>}{c}</span><strong>{profit}</strong></div>
    {children}
  </section>
}

/* A table on wide screens, stacked cards on phones. columns: [{key,label,render?,top?}] — `top` columns (date, amount) lead the card. */
export function DataTable({columns,rows,empty,label}){
  if(!rows||!rows.length)return <p className="tk-line" role="status">{empty}</p>
  return <div className="rp-scroll"><table className="rp-table" aria-label={label}>
    <thead><tr>{columns.map(c=><th key={c.key} scope="col">{c.label}</th>)}</tr></thead>
    <tbody>{rows.map((row,i)=><tr key={row.id||i}>{columns.map(c=><td key={c.key} data-label={c.label} data-top={c.top?'1':undefined}>{c.render?c.render(row):row[c.key]??'—'}</td>)}</tr>)}</tbody></table></div>
}

// Fetches a PDF with the Bearer token as a blob, then opens it (object URL, new tab) or saves it, and revokes the URL later.
export async function fetchPdf(path){return api(path,{binary:true,timeoutMs:60_000,cache:'no-store'})}
export function showPdf(blob,{filename,download=false}){
  const url=URL.createObjectURL(blob),link=document.createElement('a')
  link.href=url;link.rel='noopener'
  if(download)link.download=filename;else link.target='_blank'
  document.body.appendChild(link);link.click();link.remove()
  setTimeout(()=>URL.revokeObjectURL(url),60_000)
}
export function usePdf({path,filename,download}){
  const [state,setState]=useState({busy:false,error:''}),busy=useRef(false)
  const run=async()=>{
    if(busy.current)return
    busy.current=true;setState({busy:true,error:''})
    try{showPdf(await fetchPdf(path),{filename,download});setState({busy:false,error:''})}
    catch(error){setState({busy:false,error:fieldErrorText(error)})}
    finally{busy.current=false}
  }
  return {...state,run}
}

// Reads one report for a period. One request at a time; a newer period replaces an older answer.
export function useReport(path,enabled=true){
  const [state,setState]=useState({data:null,loading:true,error:''}),run=useRef(0)
  useEffect(()=>{
    if(!enabled||!path)return undefined
    const mine=++run.current;setState(s=>({data:null,loading:true,error:''}))
    api(path,{cache:'no-store'}).then(data=>{if(mine===run.current)setState({data,loading:false,error:''})}).catch(error=>{if(mine===run.current)setState({data:null,loading:false,error:fieldErrorText(error)})})
    return()=>{run.current++}
  },[path,enabled])
  return state
}
