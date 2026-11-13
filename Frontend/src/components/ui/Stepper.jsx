import { Icon } from '../components'

/* steps: array of labels; current: 1-based active step. */
export default function Stepper({ steps, current = 1, label = 'Progress', className = '', onSelect }) {
  return <ol className={`ui-stepper${className ? ' ' + className : ''}`} aria-label={label}>
    {steps.map((text, index) => {
      const number = index + 1
      const state = number === current ? 'current' : number < current ? 'done' : 'todo'
      const inner = <><span className="ui-step-dot">{state === 'done' ? <Icon name="check" size={16} aria-hidden="true"/> : number}</span><span className="ui-step-label">{text}</span></>
      return <li key={text} className={`ui-step ui-step-${state}`} aria-current={state === 'current' ? 'step' : undefined}>
        {onSelect && state === 'done'
          ? <button type="button" className="ui-step-button" aria-label={`Go back to ${text}`} onClick={() => onSelect(index)}>{inner}</button>
          : inner}
      </li>
    })}
  </ol>
}
