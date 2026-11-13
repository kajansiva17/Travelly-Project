import { t } from '../i18n/language.js'
import { useState } from 'react'
import { Icon } from './components'
import { useWorkspace } from '../context/workspaceContext'
import AiAssistant from '../features/ai/AiAssistant'

export function TravellyAiPanel({ className = '' }) {
  // Chat opens the Travelly AI panel (Find a ride / Help); Talk by voice opens it and listens for one spoken answer (contract 03AI).
  const workspace = useWorkspace(), [panel, setPanel] = useState(null)
  const first = (workspace?.user?.display_name || workspace?.user?.full_name || '').trim().split(/\s+/)[0]
  return <section className={'workspace-card reference-ai travelly-ai-card ' + className} aria-label={t('Travelly AI')}>
    <div className="workspace-card-heading"><h2><Icon name="spark"/>{t('Travelly AI')}</h2></div>
    <div className="reference-ai-content"><div><p>{first ? t("Hi {value0}! I'm your Travelly AI assistant", { value0: first }) : t("Hi! I'm your Travelly AI assistant")}</p><div className="reference-ai-actions"><button type="button" aria-label={t('Chat with Travelly AI')} onClick={() => setPanel('chat')}><Icon name="chat" size={17}/><span className="ai-label-short">{t('Chat')}</span><span className="ai-label-full">{t('Chat with Travelly AI')}</span></button><button type="button" aria-label={t('Talk by voice')} onClick={() => setPanel('voice')}><Icon name="mic" size={17}/><span className="ai-label-short">{t('Speak')}</span><span className="ai-label-full">{t('Talk by voice')}</span></button></div></div><svg className="reference-ai-robot" viewBox="0 0 120 120" role="img" aria-label={t('Travelly AI assistant')}><path d="M60 14v13" stroke="#7054c8" strokeWidth="5" strokeLinecap="round"/><circle cx="60" cy="10" r="6" fill="#9e5cff"/><rect x="23" y="27" width="74" height="60" rx="25" fill="#eff8ff" stroke="#fff" strokeWidth="4"/><rect x="34" y="39" width="52" height="35" rx="17" fill="#13449b"/><circle cx="50" cy="57" r="5" fill="#adf7ff"/><circle cx="70" cy="57" r="5" fill="#adf7ff"/><path d="M50 67q10 7 20 0" fill="none" stroke="#adf7ff" strokeWidth="3" strokeLinecap="round"/><path d="M41 85v21h38V85" fill="#d8edff" stroke="#fff" strokeWidth="3"/><path d="M37 80q-15 10-9 25M83 80q15 10 9 25" fill="none" stroke="#d8edff" strokeWidth="11" strokeLinecap="round"/></svg></div>
    {panel && <AiAssistant initialTab="search" startVoice={panel === 'voice'} onClose={() => setPanel(null)}/>}
  </section>
}
