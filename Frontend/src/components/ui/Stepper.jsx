import React from 'react'

/* steps: array of labels; current: 1-based active step. */
export default function Stepper({ steps, current = 1, label = 'Progress', className = '' }) {
  return <ol className={`ui-stepper${className ? ' ' + className : ''}`} aria-label={label}>
    {steps.map((text, index) => {
      const number = index + 1
      const state = number === current ? 'current' : number < current ? 'done' : 'todo'
      return <li key={text} className={`ui-step ui-step-${state}`} aria-current={state === 'current' ? 'step' : undefined}>
        <span className="ui-step-dot">{number}</span><span className="ui-step-label">{text}</span>
      </li>
    })}
  </ol>
}
