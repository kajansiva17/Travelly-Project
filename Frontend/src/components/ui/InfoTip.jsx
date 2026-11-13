import { useId } from 'react'
import { Icon } from '../components'

/* Small "i" button that shows a longer helper text on hover or keyboard focus.
   Use it to keep forms short instead of printing long hints under every field. */
export default function InfoTip({ children, label = 'More information', className = '' }) {
  const id = useId()
  return <span className={`ui-infotip${className ? ' ' + className : ''}`}>
    <button type="button" aria-label={label} aria-describedby={id}><Icon name="help" size={15} aria-hidden="true"/></button>
    <span role="tooltip" id={id}>{children}</span>
  </span>
}
