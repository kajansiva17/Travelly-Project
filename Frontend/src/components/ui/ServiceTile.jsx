import { Link } from 'react-router-dom'
import { Icon } from '../components'

/* Service card (Travel & Booking, choose service). Pass `to` for a link,
   `onClick` for a selectable tile, or neither for a static tile.
   `image` is an optional illustration URL shown on the right. */
export default function ServiceTile({ icon, title, description, image, selected = false, disabled = false, badge, to, onClick, className = '' }) {
  // An unavailable tile is never selected, never clickable and shows no chevron.
  if (disabled) { selected = false; onClick = undefined; to = undefined }
  const classes = `ui-tile${selected ? ' ui-tile-selected' : ''}${disabled ? ' ui-tile-disabled' : ''}${className ? ' ' + className : ''}`
  const body = <>
    <span className="ui-tile-icon"><Icon name={icon} size={30} aria-hidden="true"/></span>
    <span className="ui-tile-text"><strong>{title}</strong>{description && <small>{description}</small>}</span>
    {image && <img className="ui-tile-image" src={image} alt="" loading="lazy" decoding="async"/>}
    {badge && <span className="ui-tile-badge">{badge}</span>}
    {selected ? <span className="ui-tile-mark"><Icon name="check" size={16} aria-hidden="true"/></span>
      : (to || onClick) && <span className="ui-tile-go"><Icon name="chevron" size={18} aria-hidden="true"/></span>}
  </>
  if (disabled) return <div className={classes} aria-disabled="true">{body}</div>
  if (to) return <Link className={classes} to={to}>{body}</Link>
  if (onClick) return <button type="button" className={classes} aria-pressed={selected} onClick={onClick}>{body}</button>
  return <div className={classes}>{body}</div>
}
