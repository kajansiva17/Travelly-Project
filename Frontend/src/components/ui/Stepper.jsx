import { t } from '../../i18n/language.js'
import { Icon } from '../components'

/* steps: array of labels; current: 1-based active step. */
export default function Stepper({ steps, current = 1, label = 'Progress', className = '', onSelect }) {
  return <ol className={`ui-stepper${className ? ' ' + className : ''}`} aria-label={t(label)}>
    {steps.map((text, index) => {
      const number = index + 1
      const state = number === current ? 'current' : number < current ? 'done' : 'todo'
      const inner = <><span className="ui-step-dot">{state === 'done' ? <Icon name="check" size={16} aria-hidden="true"/> : number}</span><span className="ui-step-label">{t(text)}</span></>
      return <li key={text} className={`ui-step ui-step-${state}`} aria-current={state === 'current' ? 'step' : undefined}>
        {onSelect && state === 'done'
          ? <button type="button" className="ui-step-button" aria-label={t('Go back to {value0}', { value0: t(text) })} onClick={() => onSelect(index)}>{inner}</button>
          : inner}
      </li>
    })}
  </ol>
}
