import React from 'react'

/* Rounded white box with a red check; label may contain links. */
export default function Checkbox({ children, className = '', ...props }) {
  return <label className={`ui-checkbox${className ? ' ' + className : ''}`}>
    <input type="checkbox" {...props}/>
    <span className="ui-checkbox-box" aria-hidden="true"/>
    <span>{children}</span>
  </label>
}
