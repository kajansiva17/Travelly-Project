import { t } from '../../i18n/language.js'
import {useState} from 'react'
import {Header,ErrorNotice} from '../../components/components'
import {Compact} from '../owner/OwnerRates'
import {FlowShell,usePaged} from '../booking/flow/FlowParts'
import {Thumb} from '../booking/BookingCardParts'
import Chip from '../../components/ui/Chip'
import {Notice,Empty} from '../ticketing/TicketParts'
import {CODE_LABELS,codeLabel} from '../../i18n/codeLabels.js'

// One layout for every Admin list page: optional filter row, compact rows, paging, and a details view
// (opened with Details, closed with Back) so nothing needs a long page. Presentation only; pages pass their own data.
//   row(item) -> { title, meta, status, tone, actions }     detail(item) -> node
export default function AdminList({heading,title,icon='document',info,tabs,notice,error,filters,filterCols=3,items,empty,row,detail,detailTitle,detailLabel,custom,footer}){
  const [open,setOpen]=useState(null)
  // The opened record is re-read from the latest items, so details never show a stale version after a save.
  const keyOf=i=>row?(row(i).key??i.id):i.id
  const current=open&&items?(items.find(i=>keyOf(i)===keyOf(open))||open):open
  const showDetail=current&&detail
  return <><Header/><FlowShell heading={heading} icon={icon} title={showDetail&&detailTitle?detailTitle(current):title} info={info} tabs={tabs}>
    <Compact.Provider value={true}>
    <Notice>{notice}</Notice><ErrorNotice error={error}/>
    {custom?custom
      :showDetail
        ?<><div className="tk-pane tk-detail">{detail(current)}</div><div className="flow-actions"><button type="button" className="ui-button ui-button-secondary" onClick={()=>setOpen(null)}>{t('Back to list')}</button></div></>
        :<>
          {filters&&<div className="tk-grid" style={{'--cols':filterCols}}>{filters}</div>}
          <div className="tk-pane ad-pane">
            {items===null&&!error?<p role="status">{t('Loading…')}</p>:(items||[]).length
              ?<div className="tk-rows ad-rows">{(items||[]).map((item,i)=>{const r=row(item);return <article className="bc-card ad-row" key={r.key||item.id||i}>
                <Thumb icon={icon} round size={44}/>
                <div className="bc-body"><strong className="bc-name">{r.title}</strong>{r.meta&&<span className="bc-sub">{r.meta}</span>}</div>
                <div className="bc-side ad-side">{r.status&&<Chip tone={r.tone||'muted'}>{r.status}</Chip>}{r.actions}{detail&&<button type="button" className="ui-button ui-button-secondary" onClick={()=>setOpen(item)}>{t(detailLabel||'Details')}</button>}</div></article>})}</div>
              :items!==null&&<Empty>{empty}</Empty>}
          </div>
          <div className="flow-actions">{footer||<span/>}<span/></div>
        </>}
    </Compact.Provider>
  </FlowShell></>
}

const hidden=/token|secret|pin|qr|email|phone|contact|path|password|hash|digest/i
// Plain facts of a record (one nested level), without anything private. Used for details views.
export function factsOf(item){
  const out=[]
  const add=(k,v)=>{if(v==null||typeof v==='object'||hidden.test(k))return;out.push([codeLabel(k),typeof v==='string'&&(CODE_LABELS[v]||/^[A-Z0-9]+(_[A-Z0-9]+)+$/.test(v))?codeLabel(v):String(v)])}
  Object.entries(item||{}).forEach(([k,v])=>{if(v&&typeof v==='object'&&!Array.isArray(v))Object.entries(v).forEach(([k2,v2])=>add(k+' '+k2,v2));else add(k,v)})
  return out
}
export function Facts({entries,cols=3}){
  const paged=usePaged(entries,cols*3)
  return <><dl className="tk-facts" style={{'--cols':cols}}>{paged.slice.map(([k,v])=><div key={k}><dt>{k}</dt><dd title={v}>{v}</dd></div>)}</dl>{paged.pages>1&&<div className="tk-bar">{paged.pager}</div>}</>
}
