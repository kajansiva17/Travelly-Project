import React from 'react'
import { Link } from 'react-router-dom'
import { Icon } from '../components'

/* Segmented tab bar (Travel & Booking). items: [{ label, to?, active?, icon? }].
   An item with `to` is a link; the active item is the current page. */
export default function Tabs({ items, label = 'Sections', className = '' }) {
  return <nav className={`ui-tabs${className ? ' ' + className : ''}`} aria-label={label}>
    {items.map(item => {
      const body = <>{item.icon && <Icon name={item.icon} size={20} aria-hidden="true"/>}<span>{item.label}</span></>
      const classes = 'ui-tab' + (item.active ? ' is-active' : '')
      return item.to && !item.active
        ? <Link key={item.label} className={classes} to={item.to}>{body}</Link>
        : <span key={item.label} className={classes} aria-current={item.active ? 'page' : undefined}>{body}</span>
    })}
  </nav>
}
