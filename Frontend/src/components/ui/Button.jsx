import { Icon } from '../components'

/* variant: primary (red gradient) | secondary (white glass).
   arrow adds a trailing arrow; back adds a leading one (secondary Back button). */
export default function Button({ variant = 'primary', arrow = false, back = false, icon, type = 'button', className = '', children, ...props }) {
  return <button type={type} className={`ui-button ui-button-${variant}${className ? ' ' + className : ''}`} {...props}>
    {back && <Icon name="arrow" size={20} className="ui-back-arrow" aria-hidden="true"/>}
    {icon && <Icon name={icon} size={20} aria-hidden="true"/>}
    <span>{children}</span>
    {arrow && <Icon name="arrow" size={20} aria-hidden="true"/>}
  </button>
}
