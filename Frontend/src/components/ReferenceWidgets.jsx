import { t } from '../i18n/language.js'
import React, { useState } from 'react'
import { Icon, useNotice } from './components'
import { useWorkspace } from '../context/workspaceContext'
import AiAssistant from '../features/ai/AiAssistant'

export function UnavailableFeature({ icon = 'clock', children, compact = false }) {
  return <div className={'reference-unavailable' + (compact ? ' compact' : '')}><span className="reference-orb"><Icon name={icon} size={28}/></span><strong>{t('Not available yet')}</strong><p>{children}</p></div>
}

export function ItineraryPreview({ booking }) {
  const stops = booking?.itinerary?.itinerary?.stops || []
  return <div className="reference-route"><ol>{stops.length ? stops.map((stop, index) => <li key={index}><Icon name="pin" size={16}/><div><strong>{t(stop.place?.label) || t('Unreported stop')}</strong><small>{index === 0 ? t('Pickup') : index === stops.length - 1 ? t('Destination') : t('Planned stop')}</small></div></li>) : <li><Icon name="route"/><div><strong>{t('No itinerary to preview')}</strong><small>{t('Choose an assigned journey to review its stops.')}</small></div></li>}</ol></div>
}

export function PlatformMapPlaceholder() {
  return <div className="reference-platform-map"><svg viewBox="0 0 240 390" aria-hidden="true"><path d="M107 18C85 53 116 65 87 108C52 156 36 205 43 249C47 293 69 344 110 366C145 381 190 353 198 319C213 258 177 208 164 168C151 128 145 98 126 77C117 65 127 38 107 18Z"/></svg><div><Icon name="pin" size={30}/><strong>{t('Live trip positions are unavailable')}</strong><p>{t('Current APIs do not supply vehicle locations. No live markers or trip totals are shown.')}</p></div><small>{t('Illustrative island outline · no live tracking')}</small></div>
}

export function TravellyHelp() {
  const notice = useNotice()
  return <button className="reference-help" aria-label={t('Travelly help')} onClick={() => notice({ title: 'Travelly help', message: 'Review your journeys in My Trips and your documents in Profile. Owner and Driver applications are reviewed independently. Automated chat and voice assistance are not available yet.' })}><Icon name="headset" size={25}/><span>{t('Help')}</span></button>
}

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
