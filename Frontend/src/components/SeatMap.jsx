import { t } from '../i18n/language.js'
import {useLayoutEffect,useRef,useState} from 'react'
import '../styles/ticketSeats.css'

// Top-down picture of the vehicle, drawn entirely with code (SVG + CSS, no image files).
// Sri Lanka drives on the left, so the Driver sits on the RIGHT of the front row and the door is on the LEFT.
// seat: {code,row,column,deck,type,bookable,status?}; status is only present for a departure.
const SEAT=40,GAP=8,EDGE=16,PADX=34,PADTOP=84,PADBOTTOM=52

function Wheel({size=26,detail=false}){
  if(!detail)return <svg viewBox="0 0 32 32" width={size} height={size} aria-hidden="true" focusable="false">
    <circle cx="16" cy="16" r="12" fill="none" stroke="currentColor" strokeWidth="3"/>
    <circle cx="16" cy="16" r="3" fill="currentColor"/>
    <path d="M4.5 16h8M19.5 16h8M16 19.5V28" stroke="currentColor" strokeWidth="3" strokeLinecap="round"/>
  </svg>
  // Big, simple steering wheel that reads at a glance: thick ring, three spokes, hub, white outline.
  return <svg viewBox="0 0 64 64" width={size} height={size} aria-hidden="true" focusable="false">
    <g fill="none" strokeLinecap="round">
      <circle cx="32" cy="32" r="26" stroke="#fff" strokeWidth="13"/>
      <path d="M8 34 H56 M32 34 V58" stroke="#fff" strokeWidth="11"/>
      <circle cx="32" cy="32" r="26" stroke="#161b22" strokeWidth="8"/>
      <path d="M8 34 H56 M32 34 V58" stroke="#161b22" strokeWidth="6"/>
      <circle cx="32" cy="32" r="26" stroke="#fff" strokeOpacity=".3" strokeWidth="1.6" transform="rotate(-30 32 32)" strokeDasharray="30 200"/>
    </g>
    <circle cx="32" cy="34" r="11" fill="#fff"/>
    <circle cx="32" cy="34" r="9" fill="#2d343e" stroke="#0e1217" strokeWidth="1.5"/>
    <circle cx="32" cy="34" r="3.2" fill="#cdd3db"/>
  </svg>
}

const BACK='M8.5,23 C5.5,15 7,6.5 13.5,5.5 L26.5,5.5 C33,6.5 34.5,15 31.5,23 Z'
function SeatShape(){
  return <svg className="seat-art" viewBox="0 0 40 40" aria-hidden="true" focusable="false">
    <rect className="s-arm" x="1.5" y="15" width="5" height="20" rx="2.5"/>
    <rect className="s-arm" x="33.5" y="15" width="5" height="20" rx="2.5"/>
    <rect className="s-cushion" x="6.5" y="20" width="27" height="18" rx="7"/>
    <path d="M10,34.5 Q20,37 30,34.5" className="s-stitch"/>
    <path className="s-back" d={BACK}/>
    <path d={BACK} fill="url(#sg)" stroke="none"/>
    <rect className="s-head" x="12.5" y="1" width="15" height="6.5" rx="3.2"/>
    <rect x="14" y="2.3" width="12" height="1.6" rx=".8" fill="#fff" fillOpacity=".55"/>
  </svg>
}

// The vehicle body is computed from the seat grid so it always fits, whether 10 or 40 seats.
function body(W,H,inset){
  const x=12+inset,r=W-12-inset,top=10+inset,bot=H-6-inset,mid=W/2
  return `M${x},${bot-20} L${x},100 C${x},44 ${x+36},${top} ${mid},${top} C${r-36},${top} ${r},44 ${r},100 L${r},${bot-20} Q${r},${bot} ${r-20},${bot} L${x+20},${bot} Q${x},${bot} ${x},${bot-20} Z`
}

function VehicleArt({W,H,driverX}){
  const lw=14,rw=W-14-12,wy1=96,wy2=H-96
  return <svg className="vehicle-art" width={W} height={H+14} viewBox={`0 0 ${W} ${H+14}`} aria-hidden="true" focusable="false">
    <defs>
      <linearGradient id="sg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#fff" stopOpacity=".55"/><stop offset=".55" stopColor="#fff" stopOpacity="0"/><stop offset="1" stopColor="#000" stopOpacity=".14"/></linearGradient>
      <linearGradient id="vb" x1="0" x2="1"><stop offset="0" stopColor="#cfd5dc"/><stop offset=".18" stopColor="#f7f9fb"/><stop offset=".82" stopColor="#f7f9fb"/><stop offset="1" stopColor="#cfd5dc"/></linearGradient>
      <linearGradient id="vf" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#c9d2dd"/><stop offset="1" stopColor="#b9c4d1"/></linearGradient>
      <linearGradient id="vg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#6e93b3"/><stop offset="1" stopColor="#bcd4e6"/></linearGradient>
      <radialGradient id="vh"><stop offset="0" stopColor="#fffbe6"/><stop offset="1" stopColor="#f2c744"/></radialGradient>
      <filter id="vs" x="-10%" y="-5%" width="120%" height="115%"><feDropShadow dx="0" dy="5" stdDeviation="5" floodOpacity=".28"/></filter>
    </defs>
    {[[0,wy1],[W-12,wy1],[0,wy2],[W-12,wy2]].map(([x,y],i)=><g key={i}>
      <rect x={x} y={y-30} width="12" height="60" rx="5" fill="#23272e"/>
      <rect x={x+(x? 2:4)} y={y-24} width="6" height="48" rx="3" fill="#3c424c"/></g>)}
    <path d={body(W,H,0)} fill="url(#vb)" stroke="#7b8490" strokeWidth="2.5" filter="url(#vs)"/>
    <path d={body(W,H,9)} fill="url(#vf)" stroke="#c3cad2" strokeWidth="1.5"/>
    {/* windscreen */}
    <path d={`M${W/2-(W/2-48)},66 C${W/2-(W/2-60)},34 ${W/2-60},28 ${W/2},28 C${W/2+60},28 ${W/2+(W/2-60)},34 ${W/2+(W/2-48)},66 Z`} fill="url(#vg)" stroke="#6f8397" strokeWidth="1.5"/>
    <path d={`M${W/2-(W/2-60)},58 C${W/2-(W/2-70)},40 ${W/2-50},36 ${W/2-20},35`} fill="none" stroke="#fff" strokeOpacity=".55" strokeWidth="2" strokeLinecap="round"/>
    {/* dashboard with instrument cluster in front of the Driver */}
    <rect x="34" y="62" width={W-68} height="16" rx="8" fill="#39404a" stroke="#1d2229" strokeWidth="1.2"/>
    <rect x="40" y="64" width={W-80} height="3" rx="1.5" fill="#fff" fillOpacity=".18"/>
    {/* bonnet line, headlights, mirrors, rear */}
    <ellipse cx="34" cy="62" rx="9" ry="5" transform="rotate(-48 34 62)" fill="url(#vh)" stroke="#b58a12" strokeWidth="1.2"/>
    <ellipse cx={W-34} cy="62" rx="9" ry="5" transform={`rotate(48 ${W-34} 62)`} fill="url(#vh)" stroke="#b58a12" strokeWidth="1.2"/>
    <rect x="4" y="80" width="14" height="10" rx="5" fill="#5d6570"/><rect x={W-18} y="80" width="14" height="10" rx="5" fill="#5d6570"/>
    <rect x="26" y={H-18} width="22" height="8" rx="3" fill="#ff1017" stroke="#ad0b10"/><rect x={W-48} y={H-18} width="22" height="8" rx="3" fill="#ff1017" stroke="#ad0b10"/>
    <rect x="62" y={H-16} width={W-124} height="6" rx="3" fill="#a9afb8"/>
  </svg>
}

// The drawing keeps its fixed 40px seat units; the whole picture is scaled (CSS transform) to the space the page gives it,
// so the full vehicle and every seat are always visible, with proportions untouched and no scrolling.
const MAX_SCALE=1.3,DECK_GAP=24,TITLE=22
function useBox(ref){
  const [box,setBox]=useState({w:0,h:0})
  useLayoutEffect(()=>{
    const el=ref.current;if(!el)return
    const read=()=>setBox({w:el.clientWidth,h:el.clientHeight})
    read();if(typeof ResizeObserver==='undefined')return
    const watch=new ResizeObserver(read);watch.observe(el);return ()=>watch.disconnect()
  },[ref])
  return box
}

export default function SeatMap({seats,selected=[],onToggle,isDisabled,editable=false,label}){
  const stage=useRef(null),box=useBox(stage)
  const decks=[...new Set(seats.map(s=>s.deck||1))].sort((a,b)=>a-b)
  const sized=decks.map(deck=>{
    const own=seats.filter(s=>(s.deck||1)===deck)
    const rows=[...new Set(own.map(s=>s.row))].sort((a,b)=>a-b)
    const columns=Math.max(...own.map(s=>s.column))+1
    const gridW=EDGE*2+columns*SEAT+(columns+1)*GAP
    const gridH=rows.length*SEAT+(rows.length-1)*GAP
    return {deck,own,rows,columns,W:gridW+PADX*2,H:gridH+PADTOP+PADBOTTOM}
  })
  const title=decks.length>1?TITLE:0
  const totalW=sized.reduce((sum,d)=>sum+d.W,0)+DECK_GAP*(sized.length-1)
  const totalH=Math.max(0,...sized.map(d=>d.H+14))+title
  const scale=box.w&&box.h?Math.min(box.w/totalW,box.h/totalH,MAX_SCALE):0
  return <div className="seat-map" role="group" aria-label={label||t('Seat layout')}>
    <div className="seat-stage" ref={stage}>
      <div className="seat-scaler" style={{width:totalW,height:totalH,transform:`translate(-50%,-50%) scale(${scale||0.01})`,visibility:scale?'visible':'hidden'}}>
        {sized.map(({deck,own,rows,columns,W,H})=>{
          const firstPassengerRow=rows.find(r=>r>0)
          const dc=Math.max(0,...own.filter(x=>x.type==='CREW').map(x=>x.column))
          const driverX=PADX+EDGE+GAP*(dc+1)+SEAT*dc+SEAT/2
          return <div className="seat-deck" key={deck}>
            {decks.length>1&&<p className="seat-deck-title">{t('Deck {value0}',{value0:deck})}</p>}
            <div className="vehicle-shell" style={{width:W,height:H+14}}>
              <VehicleArt W={W} H={H} driverX={driverX}/>
              <div className="seat-grid-map" style={{left:PADX,top:PADTOP,gridTemplateColumns:`${EDGE}px repeat(${columns},${SEAT}px) ${EDGE}px`}}>
                {firstPassengerRow!=null&&<span className="vehicle-door" aria-hidden="true" style={{gridColumn:1,gridRow:rows.indexOf(firstPassengerRow)+1}}>{t('DOOR')}</span>}
                {rows.flatMap(r=>own.filter(s=>s.row===r).map(s=>{
                  const crew=s.type==='CREW'
                  const notSold=s.bookable===false&&!crew
                  const taken=s.status&&s.status!=='AVAILABLE'
                  const unavailable=crew||notSold||taken||(isDisabled&&isDisabled(s))
                  const chosen=selected.includes(s.code)
                  const cls=['seat',crew?'crew':'',notSold?'not-sold':'',taken?'booked':'',chosen?'selected':''].filter(Boolean).join(' ')
                  return <button type="button" key={`${deck}-${s.row}-${s.column}`} className={cls}
                    style={{gridRow:rows.indexOf(r)+1,gridColumn:s.column+2}}
                    disabled={!onToggle||crew||(!editable&&unavailable)}
                    aria-pressed={chosen} aria-label={crew?t('Driver seat'):t(unavailable?'Seat {value0} unavailable':'Seat {value0}',{value0:s.code})}
                    onClick={()=>onToggle&&onToggle(s)}>
                    {crew?<span className="wheel-big"><Wheel size={54} detail/></span>:<><SeatShape/><span className="seat-num">{s.code}</span></>}
                  </button>
                }))}
              </div>
            </div>
          </div>
        })}
      </div>
    </div>
    <ul className="seat-legend" aria-label={t('Seat colours')}>
      {editable
        ?<><li><i className="swatch"/> {t('For sale')}</li><li><i className="swatch not-sold"/> {t('Not for sale')}</li></>
        :<><li><i className="swatch"/> {t('Available')}</li><li><i className="swatch booked"/> {t('Booked')}</li><li><i className="swatch selected"/> {t('Selected')}</li><li><i className="swatch not-sold"/> {t('Not available')}</li></>}
      <li><i className="swatch crew"><Wheel/></i> {t('Driver')}</li>
    </ul>
  </div>
}
