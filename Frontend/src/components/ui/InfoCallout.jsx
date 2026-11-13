import { Icon } from '../components'

export default function InfoCallout({ icon = 'shield', className = '', children }) {
  return <aside className={`ui-callout${className ? ' ' + className : ''}`}>
    <Icon name={icon} size={24} aria-hidden="true"/><div>{children}</div>
  </aside>
}
