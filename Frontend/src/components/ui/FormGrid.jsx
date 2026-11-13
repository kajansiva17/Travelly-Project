
/* columns: 1-4 equal columns on desktop; collapses to one column on phones.
   Give a child className="ui-span-all" to span the full row. */
export default function FormGrid({ columns = 2, className = '', children }) {
  return <div className={`ui-grid ui-grid-${columns}${className ? ' ' + className : ''}`}>{children}</div>
}
