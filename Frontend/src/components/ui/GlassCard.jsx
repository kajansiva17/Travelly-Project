
/* Frosted-glass surface used for every card and form panel. */
export default function GlassCard({ as: Tag = 'section', strong = false, className = '', children, ...props }) {
  return <Tag className={`ui-card${strong ? ' ui-card-strong' : ''}${className ? ' ' + className : ''}`} {...props}>{children}</Tag>
}
