import React from 'react'
import { Icon } from './components'

/**
 * Shared presentational primitives for the reference-led Travelly workspace.
 * They deliberately contain no fetching, persistence, or workflow decisions.
 */
export function TravellyGlassPanel({as:Tag='section',className='',children,...props}){
 return <Tag className={`travelly-glass-panel ${className}`.trim()} {...props}>{children}</Tag>
}

export function TravellyStatusChip({tone='info',icon,children,className='',...props}){
 return <span className={`travelly-status-chip ${tone} ${className}`.trim()} {...props}>{icon&&<Icon name={icon} size={15}/>}<span>{children}</span></span>
}

export function TravellyField({label,help,children,className='',...props}){
 return <label className={`travelly-field ${className}`.trim()} {...props}><span>{label}</span>{children}{help&&<small>{help}</small>}</label>
}

export function TravellyBookingStepper({steps=[],current=0}){
 return <ol className="travelly-booking-stepper" aria-label="Booking progress">
  {steps.map((step,index)=><li key={step.id||step.label||index} className={index<current?'complete':index===current?'current':''}>
   <span aria-hidden="true">{index<current?<Icon name="check" size={15}/>:index+1}</span><strong>{step.label||step}</strong>
  </li>)}
 </ol>
}

export function TravellyVehicleCard({title,meta,children,action,className=''}){
 return <article className={`travelly-vehicle-card ${className}`.trim()}><div className="travelly-card-icon"><Icon name="car" size={23}/></div><div><h3>{title}</h3>{meta&&<p>{meta}</p>}</div>{children}{action&&<div className="travelly-card-action">{action}</div>}</article>
}

export function TravellyTripSummaryCard({title,items=[],action,className=''}){
 return <TravellyGlassPanel className={`travelly-trip-summary ${className}`.trim()}><header><Icon name="calendar" size={22}/><h3>{title}</h3></header><dl>{items.map(item=><div key={item.label}><dt>{item.label}</dt><dd>{item.value}</dd></div>)}</dl>{action&&<footer>{action}</footer>}</TravellyGlassPanel>
}

export function TravellyFareCard({title='Fare summary',items=[],total,children,className=''}){
 return <TravellyGlassPanel className={`travelly-fare-card ${className}`.trim()}><header><Icon name="wallet" size={22}/><h3>{title}</h3></header><dl>{items.map(item=><div key={item.label}><dt>{item.label}</dt><dd>{item.value}</dd></div>)}</dl>{children}{total&&<footer><span>{total.label}</span><strong>{total.value}</strong></footer>}</TravellyGlassPanel>
}

export function TravellyTimelineCard({title,items=[],className=''}){
 return <TravellyGlassPanel className={`travelly-timeline-card ${className}`.trim()}><h3>{title}</h3><ol>{items.map((item,index)=><li key={item.id||index}><span className={`travelly-timeline-dot ${item.tone||'info'}`}/><div><strong>{item.title}</strong>{item.detail&&<p>{item.detail}</p>}</div>{item.time&&<time>{item.time}</time>}</li>)}</ol></TravellyGlassPanel>
}

export function TravellyState({kind='empty',title,children,action,className=''}){
 const icon={empty:'spark',loading:'clock',error:'alert'}[kind]||'spark'
 return <TravellyGlassPanel className={`travelly-state ${kind} ${className}`.trim()} role={kind==='error'?'alert':undefined}><Icon name={icon} size={28}/><div><h3>{title}</h3>{children&&<p>{children}</p>}{action&&<div>{action}</div>}</div></TravellyGlassPanel>
}
