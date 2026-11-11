import React from 'react'
import {Icon} from '../components'

// Centered empty state: soft icon, short title, one friendly sentence and an optional next action.
export default function EmptyState({icon='document',title,children,action}){
  return <div className="ui-empty" role="status"><span className="ui-empty-icon"><Icon name={icon} size={28}/></span><h3>{title}</h3><p>{children}</p>{action}</div>
}
