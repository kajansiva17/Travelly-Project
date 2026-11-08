import { useEffect, useSyncExternalStore } from 'react'
import { getLanguage, subscribeLanguage } from './language.js'

export function useLanguage() {
  const language = useSyncExternalStore(subscribeLanguage, getLanguage, () => 'en')
  useEffect(() => { document.documentElement.lang = language }, [language])
  return language
}
