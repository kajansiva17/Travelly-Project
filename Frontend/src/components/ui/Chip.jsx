import { Icon } from '../components'

/* tone: default | success (green tick) | info (blue). Renders a button when
   onClick is given (selectable chip), otherwise a static span. */
export default function Chip({ tone = 'default', icon, selected = false, onClick, className = '', children, ...props }) {
  const classes = `ui-chip ui-chip-${tone}${selected ? ' ui-chip-selected' : ''}${className ? ' ' + className : ''}`
  const content = <>{(icon || tone === 'success') && <Icon name={icon || 'check'} size={16} aria-hidden="true"/>}<span>{children}</span></>
  return onClick
    ? <button type="button" className={classes} aria-pressed={selected} onClick={onClick} {...props}>{content}</button>
    : <span className={classes} {...props}>{content}</span>
}
