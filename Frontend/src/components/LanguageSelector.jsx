import React from 'react'
import { languages, setLanguage, t } from '../i18n/language.js'
import { useLanguage } from '../i18n/useLanguage.js'

export default function LanguageSelector() {
  const language = useLanguage()
  return <label className="language">
    <span aria-hidden="true">◎</span>
    <select aria-label={t('Language')} value={language} onChange={event => setLanguage(event.target.value)}>
      {languages.map(item => <option key={item.code} value={item.code} lang={item.code}>{item.name}</option>)}
    </select>
  </label>
}
