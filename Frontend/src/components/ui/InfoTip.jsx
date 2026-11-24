import { useEffect, useId, useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Icon } from '../components'
import { t } from '../../i18n/language.js'

/* Small "i" button that shows a longer helper text on hover, tap or keyboard focus.
   Use it to keep forms short instead of printing long hints under every field.
   The text is drawn on the page itself (not inside the field), so it is never cut off by a card, and it is moved to stay inside the screen. */
export default function InfoTip({ children, label = 'More information', className = '' }) {
  const id = useId(), button = useRef(null), tip = useRef(null)
  const [open, setOpen] = useState(false), [at, setAt] = useState({ left: 8, top: 0 })
  useLayoutEffect(() => {
    if (!open || !button.current || !tip.current) return
    const b = button.current.getBoundingClientRect(), w = tip.current.offsetWidth, h = tip.current.offsetHeight
    const left = Math.max(8, Math.min(b.left - 8, window.innerWidth - w - 8))
    let top = b.bottom + 6
    if (top + h > window.innerHeight - 8 && b.top - h - 6 > 8) top = b.top - h - 6
    setAt({ left, top })
  }, [open, children])
  useEffect(() => {
    if (!open) return undefined
    const close = () => setOpen(false), key = event => { if (event.key === 'Escape') setOpen(false) }
    window.addEventListener('scroll', close, true); window.addEventListener('resize', close); window.addEventListener('keydown', key)
    return () => { window.removeEventListener('scroll', close, true); window.removeEventListener('resize', close); window.removeEventListener('keydown', key) }
  }, [open])
  return <span className={`ui-infotip${className ? ' ' + className : ''}`} onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)} onFocus={() => setOpen(true)} onBlur={() => setOpen(false)}>
    <button type="button" ref={button} aria-label={t(label)} aria-describedby={open ? id : undefined}><Icon name="help" size={15} aria-hidden="true"/></button>
    {open && createPortal(<span role="tooltip" id={id} ref={tip} className="ui-infotip-pop" style={{ left: at.left, top: at.top }}>{typeof children === 'string' ? t(children) : children}</span>, document.body)}
  </span>
}
