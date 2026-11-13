import { useId } from 'react'
import { Icon } from '../components'

/* Label above a control, with required star, helper text and error.
   Use it with Input / Select, or wrap any custom control as children;
   a render function receives { id, describedBy, invalid }. */
export default function FormField({ label, required = false, hint, error, id, className = '', children }) {
  const auto = useId()
  const fieldId = id || auto
  const describedBy = error ? `${fieldId}-error` : hint ? `${fieldId}-hint` : undefined
  const control = typeof children === 'function' ? children({ id: fieldId, describedBy, invalid: Boolean(error) }) : children
  return <div className={`ui-field${error ? ' ui-field-invalid' : ''}${className ? ' ' + className : ''}`}>
    {label && <label htmlFor={fieldId}>{label}{required && <span className="ui-required" aria-hidden="true"> *</span>}</label>}
    {control}
    {error ? <span className="ui-field-error" id={`${fieldId}-error`} role="alert">{error}</span>
      : hint ? <small className="ui-field-hint" id={`${fieldId}-hint`}>{hint}</small> : null}
  </div>
}

/* Text input with optional leading icon (name from components.jsx Icon). */
export function Input({ icon, invalid = false, className = '', ...props }) {
  return <span className={`ui-control${icon ? ' ui-control-icon' : ''}${className ? ' ' + className : ''}`}>
    {icon && <Icon name={icon} size={20} aria-hidden="true"/>}
    <input aria-invalid={invalid || undefined} {...props}/>
  </span>
}

/* Select with the same chrome and a chevron. */
export function Select({ icon, invalid = false, className = '', children, ...props }) {
  return <span className={`ui-control ui-control-select${icon ? ' ui-control-icon' : ''}${className ? ' ' + className : ''}`}>
    {icon && <Icon name={icon} size={20} aria-hidden="true"/>}
    <select aria-invalid={invalid || undefined} {...props}>{children}</select>
    <Icon name="chevron" size={20} className="ui-select-chevron" aria-hidden="true"/>
  </span>
}
