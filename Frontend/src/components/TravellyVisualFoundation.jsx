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

export function TravellyField({label,help,optional,children,className='',...props}){   // `optional` only marks the field in the form code; it is not a DOM attribute
 return <label className={`travelly-field ${className}`.trim()} {...props}><span>{label}</span>{children}{help&&<small>{help}</small>}</label>
}






export function TravellyState({kind='empty',title,children,action,className=''}){
 const icon={empty:'spark',loading:'clock',error:'alert'}[kind]||'spark'
 return <TravellyGlassPanel className={`travelly-state ${kind} ${className}`.trim()} role={kind==='error'?'alert':undefined}><Icon name={icon} size={28}/><div><h3>{title}</h3>{children&&<p>{children}</p>}{action&&<div>{action}</div>}</div></TravellyGlassPanel>
}
