import { useEffect, useRef, useState } from 'react'
import { languages, setLanguage, t } from '../i18n/language.js'
import { useLanguage } from '../i18n/useLanguage.js'

export default function LanguageSelector() {
  const language = useLanguage()
  const [open, setOpen] = useState(false)
  const box = useRef(null)
  // Phones show a globe with a drop-down arrow; tapping it drops a small list (English / தமிழ் / සිංහල) below it.
  useEffect(() => {
    if (!open) return undefined
    const away = event => { if (!box.current?.contains(event.target)) setOpen(false) }
    const key = event => { if (event.key === 'Escape') setOpen(false) }
    document.addEventListener('pointerdown', away)
    document.addEventListener('keydown', key)
    return () => { document.removeEventListener('pointerdown', away); document.removeEventListener('keydown', key) }
  }, [open])
  return <label className="language" ref={box}>
    <span aria-hidden="true">◎</span>
    <select aria-label={t('Language')} value={language} onChange={event => setLanguage(event.target.value)}>
      {languages.map(item => <option key={item.code} value={item.code} lang={item.code}>{item.name}</option>)}
    </select>
    <button type="button" className="language-code" aria-label={t('Language')} aria-haspopup="listbox" aria-expanded={open} onClick={() => setOpen(value => !value)}>
      <svg className="language-globe" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M3 12h18"/><path d="M12 3c2.6 2.6 3.9 5.6 3.9 9s-1.3 6.4-3.9 9c-2.6-2.6-3.9-5.6-3.9-9S9.4 5.6 12 3Z"/></svg>
      <svg className="language-arrow" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>
    </button>
    {open && <ul className="language-menu" role="listbox" aria-label={t('Language')}>
      {languages.map(item => <li key={item.code} role="none"><button type="button" role="option" lang={item.code} aria-selected={item.code === language} className={item.code === language ? 'is-on' : ''} onClick={() => { setLanguage(item.code); setOpen(false) }}>{item.name}</button></li>)}
    </ul>}
  </label>
}
