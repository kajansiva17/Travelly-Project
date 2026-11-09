import React from 'react'
import '../styles/ticketSeats.css'

// Draws any seat layout from data (row, column, deck). It never assumes a vehicle type.
// seat: {code,row,column,deck,type,bookable,status?}; status is only present for a departure.
export default function SeatMap({seats,selected=[],onToggle,isDisabled,editable=false,label='Seat layout'}){
  const decks=[...new Set(seats.map(s=>s.deck||1))].sort((a,b)=>a-b)
  return <div className="seat-map" role="group" aria-label={label}>
    {decks.map(deck=>{
      const own=seats.filter(s=>(s.deck||1)===deck)
      const rows=[...new Set(own.map(s=>s.row))].sort((a,b)=>a-b)
      const columns=Math.max(...own.map(s=>s.column))+1
      return <div className="seat-deck" key={deck}>
        {decks.length>1&&<p className="seat-deck-title">Deck {deck}</p>}
        <div className="seat-grid-map" style={{gridTemplateColumns:`repeat(${columns},44px)`}}>
          {rows.flatMap(r=>own.filter(s=>s.row===r).map(s=>{
            const crew=s.type==='CREW'
            const unavailable=crew||s.bookable===false||(s.status&&s.status!=='AVAILABLE')||(isDisabled&&isDisabled(s))
            const chosen=selected.includes(s.code)
            const cls=['seat',crew?'crew':'',s.bookable===false&&!crew?'not-sold':'',s.status==='HELD'?'held':'',s.status==='BOOKED'?'booked':'',chosen?'selected':''].filter(Boolean).join(' ')
            return <button type="button" key={`${deck}-${s.row}-${s.column}`} className={cls}
              style={{gridRow:rows.indexOf(r)+1,gridColumn:s.column+1}}
              disabled={!onToggle||crew||(!editable&&unavailable)}
              aria-pressed={chosen} aria-label={crew?'Driver seat':`Seat ${s.code}${unavailable?' unavailable':''}`}
              onClick={()=>onToggle&&onToggle(s)}>{crew?'🚐':s.code}</button>
          }))}
        </div>
      </div>
    })}
  </div>
}
