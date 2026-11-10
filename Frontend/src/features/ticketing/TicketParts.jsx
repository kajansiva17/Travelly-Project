import React,{useState} from 'react'
import {Field} from '../owner/OwnerRates'
import '../../styles/ticketing.css'

// Small shared pieces for the Ticket pages. They hold no business rules, only presentation.

// The green checkmark banner shown after a successful action.
export function Notice({children}){return children?<p role="status" className="success-banner">✓ {children}</p>:null}

// Short empty message inside a card (same look as every other dashboard's empty state).
export function Empty({children}){return <p className="flow-note" role="status">{children}</p>}

// A date and a time, each its own labelled field. value is "YYYY-MM-DDTHH:mm" or ''.
export function DateTimeFields({label,value,onChange,help,min}){
  const [time,setTime]=useState('')
  const date=value?value.slice(0,10):'',clock=value?value.slice(11,16):time
  const open=e=>{try{e.target.showPicker&&e.target.showPicker()}catch{}}
  const change=(d,t)=>{setTime(t);onChange(d?`${d}T${t||'08:00'}`:'')}
  return <>
    <Field label={`${label} date`} help={help}><input required type="date" name={`${label}-date`} value={date} min={min} onClick={open} onChange={e=>change(e.target.value,clock)}/></Field>
    <Field label={`${label} time`}><input required type="time" name={`${label}-time`} value={clock} onClick={open} onChange={e=>change(date,e.target.value)}/></Field>
  </>
}

// A number with − and + buttons.
export function Counter({label,value,min,max,onChange,hint}){
  return <div className="tk-counter"><span id={`ct-${label}`}>{label}{hint&&<small> {hint}</small>}</span>
    <span className="tk-counter-ctl">
      <button type="button" className="ui-button ui-button-secondary" aria-label={`Fewer: ${label}`} disabled={value<=min} onClick={()=>onChange(value-1)}>−</button>
      <output aria-labelledby={`ct-${label}`}>{value}</output>
      <button type="button" className="ui-button ui-button-secondary" aria-label={`More: ${label}`} disabled={value>=max} onClick={()=>onChange(value+1)}>+</button>
    </span></div>
}
